import matplotlib.pyplot as plt
from matplotlib.pyplot import figure
import numpy as np
import pandas as pd
import pickle
from sklearn import metrics, tree, svm
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import KFold,cross_val_score,train_test_split,LeaveOneOut
from sklearn.naive_bayes import MultinomialNB

from . dictionaries import *

# Functions from data load

class NpEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NpEncoder, self).default(obj)

def get_clean_data(directory,drop_not_happy):
    '''
    Should we drop "Are you happy with your program?"
    '''
    data = pd.read_csv(directory,dtype=str)

    # renaming data for readability
    data = data.rename(index=str,columns = READ_HEADERS)
    data.program = data.program.map(READ_PROGRAMS)
    data.problem_type = data.problem_type.map(READ_PROBLEMS)
    data.creative = data.creative.map(READ_CREATIVE)
    data.outdoors = data.outdoors.map(READ_OUTDOORS)
    data.career = data.career.map(READ_CAREERS)
    data.group_work = data.group_work.map(READ_GROUPWORK)
    data.liked_courses = data.liked_courses.map(READ_COURSES)
    data.disliked_courses = data.disliked_courses.map(READ_COURSES)
    data.programming = data.programming.map(READ_PROGRAMMING)
    data.join_clubs = data.join_clubs.map(READ_CLUBS)
    data.not_clubs = data.not_clubs.map(READ_CLUBS)
    data.liked_projects = data.liked_projects.map(READ_PROJECTS)
    data.disliked_projects = data.disliked_projects.map(READ_PROJECTS)
    data.tv_shows = data.tv_shows.map(READ_TV)
    data.alternate_degree = data.alternate_degree.map(READ_ALTERNATE_DEGREE)
    data.expensive_equipment = data.expensive_equipment.map(READ_EQUIPMENT)
    data.drawing = data.drawing.map(READ_DRAWING)
    data.essay = data.essay.map(READ_ESSAY)

    # Cleaning industry data
    data.index.name = 'id'
    industry_data = data["industry"].str.split(";", expand = True)
    industry_data = industry_data.replace(READ_INDUSTRY)
    binary_industry_data = np.array([np.arange(len(data))]*8).T
    binary_industry_data = pd.DataFrame(binary_industry_data, columns=READ_INDUSTRY.values())
    binary_industry_data.index.name = 'id'
    for col in binary_industry_data.columns:
        binary_industry_data[col].values[:] = '0'

    for index, row in industry_data.iterrows():
        for i in range(8):
            try:
                binary_industry_data.iloc[int(index), binary_industry_data.columns.get_loc(row[i])] = '1'
            except:
                error = "None_Type detected"

    data.index = data.index.map(int)
    binary_industry_data.index = binary_industry_data.index.map(int)
    data = (data.merge(binary_industry_data, left_on='id', right_on='id',how='left'))

    # if drop where all values are unhapppy
    if drop_not_happy:
        data = data[data.happy == 'Yes']
    data.index = data.index.map(int)
    # dropping PII + gender + skill_test + timestamp + year + raw_industry
    data = data.drop(data.columns[[0,1,3,4,8,24]], axis=1)
    return data

def transform_post_dict(post_dict):
    print("Transforming post_dict...")
    post_dict = json.dumps(dict(post_dict))
    post_dict = json.loads(post_dict)
    post_dict = dict(post_dict)
    industries = post_dict['industry']
    post_dict['architecture'] = '0'
    post_dict['automotive'] = '0'
    post_dict['business'] = '0'
    post_dict['construction'] = '0'
    post_dict['health'] = '0'
    post_dict['environment'] = '0'
    post_dict['manufacturing'] = '0'
    post_dict['technology'] = '0'
    for industry in industries:
        post_dict[industry] = '1'
    return dict(post_dict)

def get_encoded_data(directory,model_name,drop_not_happy):
    df = get_clean_data(directory,drop_not_happy)
    df = df.drop(['happy'], axis=1)

    col_list = list(df.columns)
    encoded_dict_list = []
    for col in col_list:
        keys = df[col].unique()
        le = preprocessing.LabelEncoder()
        le.fit(list(keys))
        df[col] = le.transform(list(df[col]))
        vals = df[col].unique()
        keys = list(le.inverse_transform(vals))
        cd = dict(zip(keys,vals))
        row = {str(col):cd}
        encoded_dict_list.append(row)
        with open('poc/quiz/exported_model_files/'+model_name+'_'+col+'_encoded_dictionary.json', 'w') as f:
            json.dump(row,f,cls=NpEncoder)

    with open('poc/quiz/exported_model_files/'+model_name+'_cols.txt', 'w') as f:
        for col in col_list:
            f.write(col)
            f.write('\n')

    return [df,encoded_dict_list]

def get_encoded_dict(model_name):
    cols = []

    with open('poc/quiz/exported_model_files/'+model_name+'_cols.txt', 'r') as f:
        for line in f:
            # remove linebreak which is the last character of the string
            currentPlace = line[:-1]
            # add item to the list
            cols.append(currentPlace)
    encoded_dict = {}
    for col in cols:
        with open('poc/quiz/exported_model_files/'+model_name+'_'+col+'_encoded_dictionary.json', 'r') as f:
            row = json.loads(f.read())
        encoded_dict[col] = row
    return encoded_dict

def save_model(model,cat,model_name):
    with open('poc/quiz/exported_model_files/'+model_name+'.pkl', 'wb') as fid:
        pickle.dump(model, fid,2)
    with open('poc/quiz/exported_model_files/'+model_name+'_cat', 'wb') as fid:
        pickle.dump(cat, fid,2)

def retrieve_prediction_labels(model,prediction):
    # returns a dictionary for each label and their probability in the prediction
    labels = model.classes_
    results = prediction[0]
    results_dict = {}
    for i in range(len(results)):
        results_dict[INV_INDEX_PROGRAM[labels[i]]] = np.round(results[i],4)
    return results_dict

# Define Parameters
MODEL_NAME = 'nb_ohe_f0_d0_b7_c36_v0'

d0 = 'poc/quiz/exported_model_files/d0.csv'

c36 = ['creative',
       'outdoors',
       'career',
       'group_work',
       'liked_courses',
       'disliked_courses',
       'join_clubs',
       'not_clubs',
       'liked_projects',
       'disliked_projects',
       'alternate_degree',
       'drawing',
       'essay',
       'architecture',
       'automotive',
       'business',
       'construction',
       'health',
       'environment',
       'manufacturing',
       'technology',
       'program'
]

b0 = False # this is only relevant when we want to use untreated data for code d0

b7 = {
    'mech': 100,
    'bmed': 100,
    'swe': 100,
    'tron': 100,
    'cive': 100,
    'chem': 100,
    'syde': 100,
    'msci': 100,
    'ce': 40,
    'elec': 100,
    'nano': 100,
    'geo': 100,
    'env': 100,
    'arch-e': 100,
    'arch': 100
    }

v0 = 1

ohe =  [
        'problem_type',
        'creative',
        'outdoors',
        'career',
        'group_work',
        'liked_courses',
        'disliked_courses',
        'programming',
        'join_clubs',
        'not_clubs',
        'liked_projects',
        'disliked_projects',
        'tv_shows',
        'alternate_degree',
        'expensive_equipment',
        'drawing',
        'essay'
        ]

ohe = [value for value in ohe if value in  column_list]

#model_name = 'model-type_encoding_directory_datastructure_column-set_version'
# experiment_model_name = 'dataSet_dataBalance_columnSet_dataBalanceMultiple'
experiment_model_name = 'd0_b7_c36_v0'
directory = d0
data_balance = b7
column_list = c36
data_balance_multiple = v0 # Ratio of other programs to program in binary classifier. 2 means double of other programs, 0.5 means half


# Supporting Functions for RE-Building the model on the Heroku Server

# Building New model
model_name = 'nb_ohe_f0_'+ experiment_model_name
data = get_merged_encoded_data(directory,model_name,one_hot_encode=ohe,column_list = column_list,drop_not_happy='H',data_balance=data_balance)

x_df = data.drop(axis=1,columns=["program"])
y_df = data["program"]

X = np.array(x_df) # convert dataframe into np array
Y = np.array(y_df) # convert dataframe into np array

mnb = MultinomialNB()
model = mnb.fit(X, Y) # fit the model using training data

cat = data.drop('program',axis=1)
cat = dict(zip(cat.columns,range(cat.shape[1])))

save_model(data,model,cat,model_name)

# Scoring models
model_name = model_name
temp_model_name = model_name

model_data = pd.read_csv('poc/quiz/exported_model_files/'+model_name+'.csv',dtype=str)
ohe = ohe_main
# Loading test data
if 'le' in model_name:
    test_data_t7 = get_label_encoded_data('poc/quiz/exported_model_files/t7.csv',model_name='t7',column_list=column_list,drop_not_happy='H',data_balance=False)[0]
elif 'ohe' in model_name:
    test_data_t7 = get_merged_encoded_data(directory = 'poc/quiz/exported_model_files/t7.csv',model_name ='t7',one_hot_encode=ohe,column_list = column_list,drop_not_happy='H',data_balance=False)

test_data_t7_temp = test_data_t7.copy()[list(model_data.columns)].head(210)

# Loading model files
pkl_file = open('poc/quiz/exported_model_files/'+model_name+'_cat', 'rb')
index_dict = pickle.load(pkl_file)
new_vector = np.zeros(len(index_dict))

pkl_file = open('poc/quiz/exported_model_files/'+model_name+'.pkl', 'rb')
model = pickle.load(pkl_file)

# Preparing Loading data
test_array = np.array(test_data_t7_temp.drop(axis=1,columns=["program"]))
test_actual = np.array(test_data_t7_temp["program"])

mclass_t3 = get_mclass_t3(temp_model_name,model,test_array,test_actual)
mclass_RR = get_mclass_rr(temp_model_name,model,test_array,test_actual)
mclass_accuracy = get_mclass_accuracy(temp_model_name,model,test_array,test_actual)
mclass_reassignment = get_mclass_reassignment(temp_model_name,model)

print("Model:  "+model_name)
print("t3:  "+str(mclass_t3))
print("RR:  "+str(mclass_RR))
print("Accuracy:  "+str(mclass_accuracy))
