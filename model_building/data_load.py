import itertools
import json
import numpy as np
import pandas as pd
import pickle
from sklearn import preprocessing

from dictionaries import *

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

def get_clean_data(directory,drop_not_happy='H',drop_gender=True):
    '''
    Should we drop "Are you happy with your program?"
    '''
    data = pd.read_csv(directory,dtype=str)

    # dropping PII + skill_test + timestamp + year + raw_industry
    data = data.drop(data.columns[[0,1,3,24]], axis=1)

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
    data = data.drop(['industry'], axis=1)

    # if drop where all values are unhapppy
    if drop_not_happy == 'H':
        data = data[data.happy == 'Yes']
        data = data.drop(['happy'], axis=1)
    if drop_not_happy == 'NH':
        data = data[data.happy == 'No']

    # drop gender data
    if drop_gender:
        data = data.drop(['gender'], axis=1)

    data.index = data.index.map(int)
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

def get_encoded_data(directory,model_name,drop_not_happy='H'):
    df = get_clean_data(directory,drop_not_happy)

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
        with open('exported_model_files/'+model_name+'_'+col+'_encoded_dictionary.json', 'w') as f:
            json.dump(row,f,cls=NpEncoder)

    with open('exported_model_files/'+model_name+'_cols.txt', 'w') as f:
        for col in col_list:
            f.write(col)
            f.write('\n')

    return [df,encoded_dict_list]

def get_encoded_dict(model_name):
    cols = []

    with open('exported_model_files/'+model_name+'_cols.txt', 'r') as f:
        for line in f:
            # remove linebreak which is the last character of the string
            currentPlace = line[:-1]
            # add item to the list
            cols.append(currentPlace)
    encoded_dict = {}
    for col in cols:
        with open('exported_model_files/'+model_name+'_'+col+'_encoded_dictionary.json', 'r') as f:
            row = json.loads(f.read())
        encoded_dict[col] = row
    return encoded_dict

def save_model(model,cat,model_name):
    with open('exported_model_files/'+model_name+'.pkl', 'wb') as fid:
        pickle.dump(model, fid,2)
    with open('exported_model_files/'+model_name+'_cat', 'wb') as fid:
        pickle.dump(cat, fid,2)

def retrieve_prediction_labels(model,prediction):
    # returns a dictionary for each label and their probability in the prediction
    labels = model.classes_
    results = prediction[0]
    results_dict = {}
    for i in range(len(results)):
        results_dict[INV_INDEX_PROGRAM[labels[i]]] = np.round(results[i],4)
    return results_dict

def test_model(model_name,vector):
    print("Loading CAT file...")
    pkl_file = open('exported_model_files/'+model_name+'_cat', 'rb')
    index_dict = pickle.load(pkl_file)
    new_vector = np.zeros(len(index_dict))

    print("Loading model...")
    pkl_file = open('exported_model_files/'+model_name+'.pkl', 'rb')
    model = pickle.load(pkl_file)
    prediction = model.predict_proba(vector)
    print("Results:")
    print(retrieve_prediction_labels(model,prediction))

# Defining methods to help normaliz the data
def normalize_3_variables(df3,x,y,column,hue):
    normalized_data = df3[[x,y,column,hue]]
    normalized_data = normalized_data.groupby([x,y,column,hue],as_index=False).size().reset_index()
    normalized_data = normalized_data.rename(index=str,columns = {0:"percent"})
    normalized_data["percent"] = 100*(normalized_data["percent"]/sum(normalized_data["percent"]))
    return normalized_data

def normalize_2_variables(df2,x,y,column):
    normalized_data = df2[[x,y,column]]
    normalized_data = normalized_data.groupby([x,y,column],as_index=False).size().reset_index()
    normalized_data = normalized_data.rename(index=str,columns = {0:"percent"})
    normalized_data["percent"] = 100*(normalized_data["percent"]/sum(normalized_data["percent"]))
    return normalized_data

def normalize_1_variables(df1,x,y):
    normalized_data = df1[[x,y]]
    normalized_data = normalized_data.groupby([x,y],as_index=False).size().reset_index()
    normalized_data = normalized_data.rename(index=str,columns = {0:"percent"})
    normalized_data["percent"] = 100*(normalized_data["percent"]/sum(normalized_data["percent"]))
    return normalized_data

def heatmapify(df,one_var,list_one,two_var,list_two):
    return_list = []
    for one in list_one:
        new_list = []
        rez1 = df.loc[(df[one_var]==one)]
        for two in list_two:
            rez2 = rez1.loc[(rez1[two_var]==two)]
            if(len(rez2)>0):
                (new_list).append((float(rez2["percent"])))
            else:
                (new_list).append(0.0)
        (return_list).append((new_list))
    heatmapdf = pd.DataFrame(return_list, index=list_one, columns=list_two)
    return heatmapdf

def permu(lists,model_name,program_count):

    pkl_file = open('exported_model_files/'+model_name+'_cat', 'rb')
    index_dict = pickle.load(pkl_file)
    new_vector = np.zeros(len(index_dict))

    pkl_file = open('exported_model_files/'+model_name+'.pkl', 'rb')
    model = pickle.load(pkl_file)
    print("model loaded...")
    def fn(lists, group=[], result=[]):
        if not lists:
            p = np.array(group).reshape(1, -1)
            pred = INV_INDEX_PROGRAM[model.predict(p)[0]]
            program_count[pred] = program_count[pred] + 1
            return
        first, rest = lists[0], lists[1:]
        for letter in first:
            fn(rest, group + [letter], result)
    result = []
    fn(lists, result=result)
    return program_count

def check_skew(model_name,column_list):
    encoded_dictionary = get_encoded_dict(model_name)

    d_problem_type = encoded_dictionary['problem_type']['problem_type']
    d_creative = encoded_dictionary['creative']['creative']
    d_outdoors = encoded_dictionary['outdoors']['outdoors']
    d_career = encoded_dictionary['career']['career']
    d_group_work = encoded_dictionary['group_work']['group_work']
    d_liked_courses = encoded_dictionary['liked_courses']['liked_courses']
    d_disliked_courses = encoded_dictionary['disliked_courses']['disliked_courses']
    d_programming = encoded_dictionary['programming']['programming']
    d_join_clubs = encoded_dictionary['join_clubs']['join_clubs']
    d_not_clubs = encoded_dictionary['not_clubs']['not_clubs']
    d_liked_projects = encoded_dictionary['liked_projects']['liked_projects']
    d_disliked_projects = encoded_dictionary['disliked_projects']['disliked_projects']
    d_tv_shows = encoded_dictionary['tv_shows']['tv_shows']
    d_alternate_degree = encoded_dictionary['alternate_degree']['alternate_degree']
    d_expensive_equipment = encoded_dictionary['expensive_equipment']['expensive_equipment']
    d_drawing = encoded_dictionary['drawing']['drawing']
    d_essay = encoded_dictionary['essay']['essay']
    d_architecture = encoded_dictionary['architecture']['architecture']
    d_automotive = encoded_dictionary['automotive']['automotive']
    d_business = encoded_dictionary['business']['business']
    d_construction = encoded_dictionary['construction']['construction']
    d_health = encoded_dictionary['health']['health']
    d_environment = encoded_dictionary['environment']['environment']
    d_manufacturing = encoded_dictionary['manufacturing']['manufacturing']
    d_technology = encoded_dictionary['technology']['technology']

    test_variables = []
    if 'problem_type' in column_list :
        test_variables.append(list(d_problem_type.values()))
    if 'creative' in column_list :
        test_variables.append(list(d_creative.values()))
    if 'outdoors' in column_list :
        test_variables.append(list(d_outdoors.values()))
    if 'career' in column_list :
        test_variables.append(list(d_career.values()))
    if 'group_work' in column_list :
        test_variables.append(list(d_group_work.values()))
    if 'liked_courses' in column_list :
        test_variables.append(list(d_liked_courses.values()))
    if 'disliked_courses' in column_list :
        test_variables.append(list(d_disliked_courses.values()))
    if 'programming' in column_list :
        test_variables.append(list(d_programming.values()))
    if 'join_clubs' in column_list :
        test_variables.append(list(d_join_clubs.values()))
    if 'not_clubs' in column_list :
        test_variables.append(list(d_not_clubs.values()))
    if 'liked_projects' in column_list :
        test_variables.append(list(d_liked_projects.values()))
    if 'disliked_projects' in column_list :
        test_variables.append(list(d_disliked_projects.values()))
    if 'tv_shows' in column_list :
        test_variables.append(list(d_tv_shows.values()))
    if 'alternate_degree' in column_list :
        test_variables.append(list(d_alternate_degree.values()))
    if 'expensive_equipment' in column_list :
        test_variables.append(list(d_expensive_equipment.values()))
    if 'drawing' in column_list :
        test_variables.append(list(d_drawing.values()))
    if 'essay' in column_list :
        test_variables.append(list(d_essay.values()))
    if 'architecture' in column_list :
        test_variables.append(list(d_architecture.values()))
    if 'automotive' in column_list :
        test_variables.append(list(d_automotive.values()))
    if 'business' in column_list :
        test_variables.append(list(d_business.values()))
    if 'construction' in column_list :
        test_variables.append(list(d_construction.values()))
    if 'health' in column_list :
        test_variables.append(list(d_health.values()))
    if 'environment' in column_list :
        test_variables.append(list(d_environment.values()))
    if 'manufacturing' in column_list :
        test_variables.append(list(d_manufacturing.values()))
    if 'technology' in column_list :
        test_variables.append(list(d_technology.values()))

    program_count = {
            'mech': 0,
            'bmed': 0,
            'swe': 0,
            'tron': 0,
            'cive': 0,
            'chem': 0,
            'syde': 0,
            'msci': 0,
            'ce': 0,
            'elec': 0,
            'nano': 0,
            'geo': 0,
            'env': 0,
            'arch-e': 0,
            'arch': 0
            }

    re = permu(test_variables,model_name,program_count)

    return re

def check_gender_bias(directory,model_name,column_list):
    drop_gender=False

    gender_data = get_clean_data(directory,drop_gender=drop_gender)[['program','gender']]
    gender_data = gender_data.reset_index()
    gender_data = gender_data.drop(['id'], axis=1)

    test_data = get_encoded_data(directory,model_name)[0]
    test_data = test_data[column_list]
    test_data = test_data.reset_index()
    test_data = test_data.drop(['program','id'], axis=1)

    pkl_file = open('exported_model_files/'+model_name+'_cat', 'rb')
    index_dict = pickle.load(pkl_file)
    new_vector = np.zeros(len(index_dict))

    pkl_file = open('exported_model_files/'+model_name+'.pkl', 'rb')
    model = pickle.load(pkl_file)

    predictions ={}
    for i in range(0,len(test_data)):
        vector = np.asarray(test_data.loc[i,])
        vector = np.array(vector).reshape(1, -1)
        predictions[i] = INV_INDEX_PROGRAM[model.predict(vector)[0]]

    gender_data['predicted_program'] = pd.Series(predictions)
    gender_count = {}
    for i in range(0,len(gender_data)):
        try:
            program_count = gender_count[gender_data.loc[i,'gender']]
            try:
                program_count[gender_data.loc[i,'predicted_program']] =program_count[gender_data.loc[i,'predicted_program']] + 1
            except:
                program_count[gender_data.loc[i,'predicted_program']] = 0

            gender_count[gender_data.loc[i,'gender']] = program_count
        except:
            gender_count[gender_data.loc[i,'gender']] = {
                                                            'mech': 0,
                                                            'bmed': 0,
                                                            'swe': 0,
                                                            'tron': 0,
                                                            'cive': 0,
                                                            'chem': 0,
                                                            'syde': 0,
                                                            'msci': 0,
                                                            'ce': 0,
                                                            'elec': 0,
                                                            'nano': 0,
                                                            'geo': 0,
                                                            'env': 0,
                                                            'arch-e': 0,
                                                            'arch': 0
                                                            }
            program_count = gender_count[gender_data.loc[i,'gender']]
            try:
                program_count[gender_data.loc[i,'predicted_program']] =program_count[gender_data.loc[i,'predicted_program']] + 1
            except:
                program_count[gender_data.loc[i,'predicted_program']] = 0
            gender_count[gender_data.loc[i,'gender']] = program_count
    return gender_count

def check_happy_bias(directory,model_name,column_list):
    drop_gender = True
    drop_not_happy = 'NH'

    happy_data = get_clean_data(directory,drop_gender=drop_gender,drop_not_happy=drop_not_happy)[['program']]
    happy_data = happy_data.reset_index()
    happy_data = happy_data.drop(['id'], axis=1)

    test_data = get_encoded_data(directory,model_name,drop_not_happy='NH')[0]
    test_data = test_data[column_list]
    test_data = test_data.reset_index()
    test_data = test_data.drop(['program','id'], axis=1)

    pkl_file = open('exported_model_files/'+model_name+'_cat', 'rb')
    index_dict = pickle.load(pkl_file)
    new_vector = np.zeros(len(index_dict))

    pkl_file = open('exported_model_files/'+model_name+'.pkl', 'rb')
    model = pickle.load(pkl_file)

    predictions ={}
    for i in range(0,len(test_data)):
        vector = np.asarray(test_data.loc[i,])
        vector = np.array(vector).reshape(1, -1)
        predictions[i] = INV_INDEX_PROGRAM[model.predict(vector)[0]]

    happy_data['predicted_program'] = pd.Series(predictions)

    pred_to_orig = {
                'mech-orig': 0,
                'bmed-orig': 0,
                'swe-orig': 0,
                'tron-orig': 0,
                'cive-orig': 0,
                'chem-orig': 0,
                'syde-orig': 0,
                'msci-orig': 0,
                'ce-orig': 0,
                'elec-orig': 0,
                'nano-orig': 0,
                'geo-orig': 0,
                'env-orig': 0,
                'arch-e-orig': 0,
                'arch-orig': 0
                }

    for i in range(0,len(happy_data)):
        try:
            prediction_count = pred_to_orig[str(happy_data.loc[i,'predicted_program']+'-orig')]
            try:
                prediction_count[happy_data.loc[i,'program']] =prediction_count[happy_data.loc[i,'program']] + 1
            except:
                prediction_count[happy_data.loc[i,'program']] = 0

            pred_to_orig[str(happy_data.loc[i,'predicted_program']+'-orig')] = prediction_count
        except:
            pred_to_orig[str(happy_data.loc[i,'predicted_program']+'-orig')] = {
                                                            'mech': 0,
                                                            'bmed': 0,
                                                            'swe': 0,
                                                            'tron': 0,
                                                            'cive': 0,
                                                            'chem': 0,
                                                            'syde': 0,
                                                            'msci': 0,
                                                            'ce': 0,
                                                            'elec': 0,
                                                            'nano': 0,
                                                            'geo': 0,
                                                            'env': 0,
                                                            'arch-e': 0,
                                                            'arch': 0
                                                            }
            prediction_count = pred_to_orig[str(happy_data.loc[i,'predicted_program']+'-orig')]
            try:
                prediction_count[happy_data.loc[i,'program']] =prediction_count[happy_data.loc[i,'program']] + 1
            except:
                prediction_count[happy_data.loc[i,'program']] = 0

            pred_to_orig[str(happy_data.loc[i,'predicted_program']+'-orig')] = prediction_count
    return pred_to_orig
'''
Might need these later

# def get_one_hot_encoded_data(directory):
#     df = get_clean_data(directory)
#     keys = df['current_average'].unique()
#     le = preprocessing.LabelEncoder()
#     le.fit(list(keys))
#     df['current_average'] = le.transform(list(df['current_average']))
#
#     df = pd.get_dummies(df)
#     return df
#
# def merged_encoding(directory,label_encode,one_hot_encode,drop_pref=False):
#
#     df = get_clean_data(directory)
#
#     if drop_pref == True:
#         df = df[df['current_average']!='Prefer not to say']
#
#     for col in label_encode:
#         keys = df[col].unique()
#         le = preprocessing.LabelEncoder()
#         le.fit(list(keys))
#         df[col] = le.transform(list(df[col]))
#
#     df = pd.get_dummies(df,columns=one_hot_encode)
#
#     return df
'''
