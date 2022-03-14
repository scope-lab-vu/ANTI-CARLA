#!/usr/bin/python3
import warnings
warnings.simplefilter(action='ignore', category=UserWarning)
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

def sampling_rules(sample):
    """
    Describes the sampling rules for selecting the weather samples
    The weather samples can only gradually increase in steps rather than having big jumps
    """
    #print(sample)
    if sample[0] in weather_parameters:
        min,max = (int(sample[1])-5,int(sample[1])+5)
        if min < 0:
            min = 0
        if max > 100:
            max = 100
        step = 1.0
    elif sample[0] == "road_segments":
        if sample[1] == 6:
            min,max = (0,2)
        else:
            min,max = (int(sample[1]),int(sample[1])+2)
        step = 1.0

    return min, max, step


def vector_2d(array):
    return np.array(array).reshape((-1, 1))

def gaussian_process(parameters, scores, x1x2, parameter_length):
    parameters = np.array(parameters).reshape((-1,parameter_length))
    #print(parameters)
    scores = vector_2d(scores)
    #print(scores)
    x1x2 = np.array(x1x2).reshape((-1,parameter_length))
    # Train gaussian process
    kernel = C(1.0, (1e-3, 1e3)) * RBF(10, (1e-2, 1e2))
    gp = GaussianProcessRegressor(kernel, n_restarts_optimizer=5000)
    gp.fit(parameters,scores)
    y_mean, y_std = gp.predict(x1x2, return_std=True)
    y_std = y_std.reshape((-1, 1))

    return y_mean, y_std

def next_parameter_by_ei(y_max,y_mean, y_std, x1x2):
    # Calculate expected improvement from 95% confidence interval
    expected_improvement = (y_mean + 1.96 * y_std) - y_max
    #expected_improvement = y_min - (y_mean - 1.96 * y_std)
    expected_improvement[expected_improvement < 0] = 0
    max_index = expected_improvement.argmax()
    # Select next choice
    next_parameter = x1x2[max_index]
    print(next_parameter)
    return next_parameter

def next_parameter_by_ucb(y_max,y_mean, y_std, x1x2):
    # Calculate expected improvement from 95% confidence interval
    kappa = 30.
    ucb = y_mean + np.sqrt(kappa) * y_std
    max_index = ucb.argmax()
    # Select next choice
    next_parameter = x1x2[max_index]
    print("New Parameter{}".format(next_parameter))
    return next_parameter

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

def process_data_from_previous_run(folder,simulation_run,root,y):
    """
    Get hyperparameters and collision data from previous run
    """
    stats = []
    data_folder = "/home/scope/Carla/sampler-braking-example/leaderboard/data/my_data/simulation%d/scene%d"%(y,simulation_run-1)
    simulation_stats = pd.read_csv(data_folder + "/run1.csv", usecols = ['monitor_result','risk'], index_col=False)
    martingale_value = simulation_stats['monitor_result'].mean()
    risk_value = simulation_stats['risk'].mean()
    stats.append(round(float(martingale_value),2))
    stats.append(round(float(risk_value),2))
    with open(root + "ood_stats.csv", 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(stats)

def read_previous_stats(collision_file,stats_file,scenario_score_file,similarity_score_file):
    """
    Read Stats file to return collisions, martingales and risk
    """
    collisions = []
    scenario_scores = []
    objective_scores = []
    martingales = []
    risks = []
    collision = pd.read_csv(collision_file, usecols = [0], header=None, index_col=False)
    for index, row in collision.iterrows():
        collisions.append(float(row))
    scenario_score = pd.read_csv(scenario_score_file, usecols = [0], header=None, index_col=False)
    for index, row in scenario_score.iterrows():
        scenario_scores.append(float(row))
    objective = pd.read_csv(similarity_score_file, usecols = [0], header=None, index_col=False)
    for index, row in objective.iterrows():
        objective_scores.append(float(row))
    martingale = pd.read_csv(stats_file, usecols = [0], header=None, index_col=False)
    for index, row in martingale.iterrows():
       martingales.append(float(row))
    risk = pd.read_csv(stats_file, usecols = [1], header=None, index_col=False)
    for index, row in risk.iterrows():
       risks.append(float(row))
    #print(risks)

    return collisions, martingales, risks, scenario_scores, objective_scores


def cartesian_product(*arrays):
    la = len(arrays)
    dtype = np.result_type(*arrays)
    arr = np.empty([len(a) for a in arrays] + [la], dtype=dtype)
    for i, a in enumerate(np.ix_(*arrays)):
        arr[...,i] = a
    return arr.reshape(-1, la)


def get_sample_choice(current_hyperparameters,simulation_run,previous_stats_file):
    """
    Get choices of the sample array
    """
    choices_array = []
    distributions = []
    previous_hyperparameters = []
    if simulation_run <= 0:
        for i in range(len(current_hyperparameters)):
            if current_hyperparameters[i][0] == 'sun_altitude_angle':
                parameter_distribution = 45.0
            elif current_hyperparameters[i][0] == 'precipitation':
                parameter_distribution = 0.0
            elif current_hyperparameters[i][0] == 'cloudiness':
                parameter_distribution = 50.0
            else:
                parameter_distribution = 0.0
            distributions.append(int(parameter_distribution))
    elif simulation_run > 0:
        parameters = pd.read_csv(previous_stats_file + "/scene_parameters.csv", usecols = [0,1], header=None, index_col=False)
        for index, row in parameters.iterrows():
                previous_hyperparameters.append((row[0],int(row[1])))
        #print(previous_hyperparameters)
        for i in range(len(current_hyperparameters)):
            for hype in previous_hyperparameters:
                if hype[0] == current_hyperparameters[i][0]:
                    if hype[0] == "traffic_density" or hype[0] == "sensor_faults":
                        min, max = current_hyperparameters[i][1], current_hyperparameters[i][2]
                        step = 1.0
                    else:
                        min,max,step = sampling_rules(previous_hyperparameters[i])
            choice_list = np.arange(min,max,step)
            choices_array.append(choice_list)
            parameter_distribution = random.choice(choice_list)
            distributions.append(int(parameter_distribution))
    print(distributions)

    return choices_array, parameter_distribution, distributions


def check_similarity(knn,parameters,scenario_score,similarity_score_file,objective,window,neighbors,threshold):
    param = []
    score = []
    val = []
    similarity_scores = []
    param = np.array(parameters[-window:-2])
    tree = KDTree(param)
    curr = np.array(parameters[-1]).reshape(1,-1)
    dist = tree.query(curr, k=neighbors)
    for dist1 in dist[0][0]:
        if dist1 < threshold:
            val.append(dist1)
    if len(val) == 5:
        similarity_score = 5.0
    elif len(val) == 4 or len(val) == 3:
        similarity_score = 2.5
    else:
        similarity_score = 0.0

    return similarity_score

def store_objective_stats(objective,similarity_score,similarity_score_file):
    stats = []
    stats.append(objective)
    stats.append(similarity_score)
    with open(similarity_score_file, 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(stats)

def Guided_Bayesian_Optimization(current_hyperparameters,folder,simulation_run,root,y,path,data_folder,exploration):
    """
    Bayesian optimization for scene selection
    """
    #exploration = 60
    window = 12
    neighbors = 6
    threshold = 9.0
    new_hyperparameters_list = []
    parameters = []
    collisions = []
    selected_parameters = []
    martingales = []
    data_folder = path + "simulation-data" + "/" + "simulation%d/"%(y)
    previous_stats_file = root + "scene%d"%(simulation_run-1)
    parameter_file = root + "sampled_parameters.csv"
    collision_file = data_folder + "collision_stats.csv"
    stats_file = data_folder + "ood_stats.csv"
    scenario_score_file = data_folder + "scenario_score.csv"
    similarity_score_file = data_folder + "similarity_score.csv"
    parameter_length = len(current_hyperparameters)
    knn = KNeighborsRegressor(n_neighbors=3)

    choices_array, parameter_distribution, distributions = get_sample_choice(current_hyperparameters,simulation_run,previous_stats_file)

    if simulation_run == 0:
        print("---------------------")
        print("Randomly sampling new area")
        print("---------------------")
        new_parameter = distributions
        collisions = 0
        similarity_score = 0
        objective_score = 0
    else:
        parameters = read_parameter_file(parameter_file)
        collisions, martingales, risk, scenario_score, objective = read_previous_stats(collision_file,stats_file,scenario_score_file,similarity_score_file)
        if simulation_run > exploration + window:
            similarity_score = 0 #check_similarity(knn,parameters,scenario_score,similarity_score_file,objective,window,neighbors,threshold)
        else:
            similarity_score = 0
        x1x2 = cartesian_product(*choices_array)
        #print(scenario_score[-1])
        #print(similarity_score)
        objective_score = scenario_score[-1] - similarity_score
        y_max = max(objective)
        y_mean, y_std = gaussian_process(parameters, objective, x1x2, parameter_length)
        #new_parameter = next_parameter_by_ei(y_max, y_mean, y_std, x1x2)
        new_parameter = next_parameter_by_ucb(y_max, y_mean, y_std, x1x2)
        print("---------------------")
        print("Sample predicted by Gaussian Process")
        print("---------------------")
        new_parameter = new_parameter
        #print(objective_score)
    store_objective_stats(objective_score,similarity_score,similarity_score_file)


    for i in range(len(current_hyperparameters)):
        new_hyperparameters_list.append((current_hyperparameters[i][0],new_parameter[i]))
        selected_parameters.append(new_parameter[i])


    return selected_parameters, new_hyperparameters_list
