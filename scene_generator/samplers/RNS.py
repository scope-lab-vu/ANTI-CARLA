#!/usr/bin/python3
import textx
import numpy as np
import lxml.etree
import lxml.builder
import sys
import glob
import os
from xml.etree import ElementTree
import xml.etree.ElementTree as ET
from textx.metamodel import metamodel_from_file
import utils
import csv
import argparse
from argparse import RawTextHelpFormatter
import pandas as pd
import random
from sklearn.utils import shuffle
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import RBF, ConstantKernel as C
from sklearn.preprocessing import StandardScaler
from itertools import product
from statistics import mean,median
from ast import literal_eval
from sklearn.neighbors import KNeighborsRegressor
from sklearn.neighbors import KDTree
#from scene_interpreter import sampling_rules, compositional_rules

weather_parameters = ['cloudiness','precipitation','precipitation_deposits','sun_altitude_angle','wind_intensity','sun_azimuth_angle','wetness','fog_distance','fog_density']

def sampling_rules(sample,value,weather_step,traffic_step,pedestrian_step):
    """
    Describes the sampling rules for selecting the weather samples
    The weather samples can only gradually increase in steps rather than having big jumps
    """
    #print(sample)
    if sample in weather_parameters:
        min,max = (int(value)-weather_step,int(value)+weather_step)
        if min < 0:
            min = 0
        if max > 100:
            max = 100
        step = 1.0
    elif sample == "traffic":
        min,max = (int(value)-traffic_step,int(value)+traffic_step)
        if min < 0:
            min = 0
        if max > 100:
            max = 100
        step = 1.0
    else:
        min,max = (int(value)-2,int(value)+2)
        step = 1.0

    return min, max, step


def read_parameter_file(file):
    """
    Read csv files
    """
    data = []
    with open(file, newline='') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) > 1:
                row_data = []
                for i in range(len(row)):
                    row_data.append(float(row[i]))
                data.append(row_data)
            elif len(row) == 1:
                data.append(row)

    return data

def store_random_scene(random_scene_file,new_parameter):
    """
    Store randomly sampled scene parameters separately
    """
    with open(random_scene_file, 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(new_parameter)


def read_previous_stats(scenario_score_file,similarity_score_file):
    """
    Read Stats file to return collisions, martingales and risk
    """
    #collisions = []
    scenario_scores = []
    similarity_scores = []
    #martingales = []
    #risks = []
    #collision = pd.read_csv(collision_file, usecols = [0], header=None, index_col=False)
    #for index, row in collision.iterrows():
    #    collisions.append(float(row))
    scenario_score = pd.read_csv(scenario_score_file, usecols = [0], header=None, index_col=False)
    for index, row in scenario_score.iterrows():
        scenario_scores.append(float(row))
    similarity = pd.read_csv(similarity_score_file, usecols = [0], header=None, index_col=False)
    for index, row in similarity.iterrows():
        similarity_scores.append(float(row))
    #martingale = pd.read_csv(stats_file, usecols = [0], header=None, index_col=False)
    #for index, row in martingale.iterrows():
    #   martingales.append(float(row))
    #risk = pd.read_csv(stats_file, usecols = [1], header=None, index_col=False)
    #for index, row in risk.iterrows():
    #   risks.append(float(row))
    #print(risks)

    return scenario_scores, similarity_scores


def cartesian_product(*arrays):
    la = len(arrays)
    dtype = np.result_type(*arrays)
    arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
    for i, a in enumerate(np.ix_(*arrays)):
        arr[...,i] = a
    return arr.reshape(-1, la)


def get_sample_choice(current_hyperparameters,simulation_run,scene_num,initial_condition,weather_step,traffic_step,pedestrian_step,route_root):
    """
    Get choices of the sample array
    """
    choices_array = []
    distributions = []
    previous_hyperparameters = []
    new_hyperparameters_list = []
    # if simulation_run <= 0:
    #     for i in range(len(current_hyperparameters)):
    #         if current_hyperparameters[i][0] == 'sun_altitude_angle':
    #             parameter_distribution = 45.0
    #         elif current_hyperparameters[i][0] == 'precipitation':
    #             parameter_distribution = 0.0
    #         elif current_hyperparameters[i][0] == 'cloudiness':
    #             parameter_distribution = 0.0
    #         else:
    #             parameter_distribution = 0.0
    #         distributions.append(int(parameter_distribution))
    if simulation_run == 0 and scene_num == 1:
        for entry in initial_condition:
            distributions.append(int(entry[1]))
            #new_hyperparameters_list.append((entry[0],int(entry[1])))
    else:
        for i in range(len(current_hyperparameters)):
            if current_hyperparameters[i][0] in weather_parameters:
                step = weather_step
            elif current_hyperparameters[i][0] == 'traffic':
                step = traffic_step
            elif current_hyperparameters[i][0] == 'pedestrian':
                step = pedestrian_step
            else:
                step = 5
            choice_list = np.arange(current_hyperparameters[i][1],current_hyperparameters[i][2],step)
            choices_array.append(choice_list)
            parameter_distribution = random.choice(choice_list)
            distributions.append(int(parameter_distribution))
    print(distributions)

    return choices_array, distributions


def check_similarity(parameters,scenario_score,similarity_score_file,neighbours,threshold,window,random_scene):
    param = []
    score = []
    val = []
    similarity_scores = []
    #param = np.array(parameters[-window:-2])
    param = np.array(parameters)
    tree = KDTree(param)
    # curr = np.array(parameters[-1]).reshape(1,-1)
    curr = np.array(np.array(random_scene).reshape(1,-1))
    dist = tree.query(curr, k=neighbours)
    for dist1 in dist[0][0]:
        if dist1 < threshold:
            val.append(dist1)
    if len(val) == neighbours:
        similarity_score = 1.0
    else:
        similarity_score = 0.0


    return similarity_score

def store_objective_stats(similarity_score,similarity_score_file):
    stats = []
    #stats.append(objective)
    stats.append(similarity_score)
    with open(similarity_score_file, 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(stats)

def check_scenario_status(parameter,score):
    """
    Check if the sampled variables have higher risk than training scenes
    """
    if score == 100:
        return 1
    else:
        return 0

def sample_closeby_regions(parameters,current_hyperparameters,weather_step,traffic_step,pedestrian_step):
    """
    Sample closeby regions
    """
    distributions = []
    choices_array = []
    for i,curr in enumerate(current_hyperparameters):
        if curr[0] == "traffic_density" or curr[0] == "sensor_faults":
            min, max = curr[1], curr[2]
            step = 1.0
        else:
            min,max,step = sampling_rules(curr[0],parameters[i],weather_step,traffic_step,pedestrian_step)
        choice_list = np.arange(min,max,step)
        #print(choice_list)
        choices_array.append(choice_list)
        parameter_distribution = random.choice(choice_list)
        distributions.append(int(parameter_distribution))

    return distributions


def Random_Neighborhood_Search(current_hyperparameters,folder,simulation_run,scene_num,route_path,y,initial_condition,weather_step,traffic_step,pedestrian_step,route_root,data_root):

# (current_hyperparameters,folder,simulation_run,root,y,path,data_folder,exploration)
    """
    Random Search for scene selection
    """
    neighbours = 7
    threshold = 10.0
    window = 12
    new_hyperparameters_list = []
    parameters = []
    collisions = []
    selected_parameters = []
    #previous_stats_file = root + "scene%d"%(simulation_run-1)
    parameter_file = route_root + "sampled_parameters.csv"
    #collision_file = data_folder + "collision_stats.csv"
    #stats_file = data_folder + "ood_stats.csv"
    scenario_score_file = data_root + "test_score.csv"
    similarity_score_file = data_root + "similarity_score.csv"
    random_scene_file = route_root + "random_scene.csv"
    parameter_length = len(current_hyperparameters)

    choices_array, distributions = get_sample_choice(current_hyperparameters,simulation_run,scene_num,initial_condition,weather_step,traffic_step,pedestrian_step,route_root)

    if simulation_run == 0 and scene_num == 1:
        new_parameter = distributions
        similarity_score = 0
        store_random_scene(random_scene_file,new_parameter)
    else:
        parameters = read_parameter_file(parameter_file)
        random_scenes = read_parameter_file(random_scene_file)
        scenario_score, similarity = read_previous_stats(scenario_score_file,similarity_score_file)
        status = check_scenario_status(parameters[-1],scenario_score[-1])
        print("performance_status:%d"%status)
        print("similarity:%d"%similarity[-1])
        if status == 0 and similarity[-1] != 1:
            print("---------------------")
            print("Sampling closeby areas")
            print("---------------------")
            new_parameter = sample_closeby_regions(parameters[-1],current_hyperparameters,weather_step,traffic_step,pedestrian_step)
        else:
            print("---------------------")
            print("Randomly sampling new area")
            print("---------------------")
            new_parameter = distributions
            store_random_scene(random_scene_file,new_parameter)

    if simulation_run >= window:
        similarity_score = check_similarity(parameters,scenario_score,similarity_score_file,neighbours,threshold,window,random_scenes[-1])
    else:
        similarity_score = 0.0

    store_objective_stats(similarity_score,similarity_score_file)

    for i in range(len(current_hyperparameters)):
        new_hyperparameters_list.append((current_hyperparameters[i][0],new_parameter[i]))
        selected_parameters.append(new_parameter[i])


    return selected_parameters, new_hyperparameters_list
