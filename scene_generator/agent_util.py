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
from utils import parse_routes_file,artifact_generator
import csv
import argparse
from argparse import RawTextHelpFormatter
import pandas as pd
import random
from ruamel import yaml
import re
import shutil
from samplers.Random import Random_Search
from samplers.Grid import Grid_Search
from samplers.RNS import Random_Neighborhood_Search

weather_map = ['cloudiness','precipitation','precipitation_deposits','sun_altitude_angle','wind_intensity','sun_azimuth_angle','wetness','fog_distance','fog_density']

track_list = ['sub-track1','sub-track2','sub-track3','sub-track4','sub-track5']

def write_sampler_results(route_path,folder,parameter_values,joined_parameters,data_path,route_root):
    """
    Parameters returned by the sampler
    """
    with open(route_path + "sampled_parameters.csv", 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(parameter_values)

    with open(route_root + "sampled_parameters.csv", 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(parameter_values)


    with open(folder + "/scene_parameters.csv", 'w') as csvfile1: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile1, delimiter = ',')
        writer.writerows(joined_parameters)


def parameter_sampler(dynamic_parameters,static_parameters,folder,simulation_run,route_path,y,sampler,data_path,total_scenes,scene_num,initial_condition,constraints,route_root,data_root):
    """
    The sampler code that takes in current step hyperparameters and returns new hyperparameter set
    1. Random Search
    2. Grid Search
    3. Halton Search
    4. Random Neighborhood Search
    """
    for entry in constraints:
        #print(entry[1])
        if entry[0] == "weather_delta":
            weather_step = entry[1]
        elif entry[0] == "traffic_density_delta":
            traffic_step = entry[1]
        elif entry[0] == "pedestrian_density_delta":
            pedestrian_step = entry[1]
    #return weather_step, traffic_step, pedestrian_step

    #print(weather_step)
    #print(traffic_step)
    #print(pedestrian_step)

    if sampler == "Random":
        parameter_values, sampled_parameters = Random_Search(dynamic_parameters,folder,simulation_run,route_path,y,scene_num,initial_condition,weather_step,traffic_step,pedestrian_step)
    if sampler == "Grid":
        parameter_values, sampled_parameters = Grid_Search(dynamic_parameters,folder,simulation_run,route_path,y,initial_condition,weather_step,traffic_step,pedestrian_step)
    if sampler == "Random_Neighborhood_Search":
        parameter_values, sampled_parameters = Random_Neighborhood_Search(dynamic_parameters,folder,simulation_run,scene_num,route_path,y,initial_condition,weather_step,traffic_step,pedestrian_step,route_root,data_root)



    joined_parameters = sampled_parameters + static_parameters

    write_sampler_results(route_path,folder,parameter_values,joined_parameters,data_path,route_root)

    #print(sampled_param_values)
    return joined_parameters


def prepare_data(data_val):
    """
    Process data for samplers
    """
    static_parameters = []
    dynamic_parameters = []
    for entry in data_val:
        if isinstance(entry[1], list):
            dynamic_parameters.append((entry[0],entry[1][0],entry[1][1]))
        else:
            static_parameters.append(entry)

    return static_parameters, dynamic_parameters

def organize_parameters(param_vals):
    """
    Organize varying scene parameters
    """
    weather_list = []
    #camera_fault_type = 0
    for val in param_vals:
        if val[0] == 'traffic_density':
            traffic_info = int(val[1])
        elif val[0] == 'town':
            town_info = "Town0%d"%int(val[1])
            town_number = int(val[1])
        else:
            weather_list.append(val)
    return weather_list,traffic_info,town_info,town_number


def set_scene_weather(weather_map,joined_parameter_list):
    """
    Weather parameters for the scene
    """
    weather = []
    for entry in weather_map:
        for data in joined_parameter_list:
            if entry == data[0]:
                weather.append(str(data[1]))
    return weather

def write_weather_data(weather,data_file):
    """
    Write weather data into a file for simulator
    """
    with open(data_file, 'w') as csvfile:
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerows(weather)


def decode_scene_description(scene_config):
    """
    Decode the scene description to extract scene related information
    """
    manual_scene_specification = []
    varying_entities = []
    varying_parameters = []
    sampler = []
    weather_val = []
    traffic_val = []
    town_description_val = []
    data_val = []
    initial_condition = []
    constraints = []
    #num_scenes = scene_config['Total Simulation Runs']
    for entry in scene_config['Scenario Description']:
        if entry == 'weather':
            val = 0
            for data in scene_config['Scenario Description']['weather']:
                if scene_config['Scenario Description']['weather'][data] is False:
                    data_val.append((data,0))
                else:
                    data_val.append((data,scene_config['Scenario Description']['weather'][data]))
                    varying_parameters.append(data)
                    val+=1
            if val > 0:
                varying_entities.append(entry)
        elif entry == 'traffic_density':
            if scene_config['Scenario Description']['traffic_density'] is False:
                data_val.append((entry,0))
            else:
                data_val.append((entry,scene_config['Scenario Description']['traffic_density']))
                varying_entities.append(entry)
                varying_parameters.append(entry)
        elif entry == 'town':
            if scene_config['Scenario Description']['town'] is False:
                data_val.append((entry,5))
            else:
                data_val.append((entry,scene_config['Scenario Description']['town']))
                varying_entities.append(entry)
                varying_parameters.append(entry)

    for entry in scene_config['Constraints']:
        constraints.append((entry,scene_config['Constraints'][entry]))

    for entry in scene_config['Initial Conditions']:
        if entry == "weather":
            for data in scene_config['Initial Conditions']['weather']:
                weather_val.append((data,scene_config['Initial Conditions']['weather'][data]))

        elif entry == 'traffic_density':
                initial_traffic_density = int(scene_config['Initial Conditions']['traffic_density'])

        elif entry == 'pedestrian_density':
                initial_pedestrian_density = int(scene_config['Initial Conditions']['pedestrian_density'])

        elif entry == 'region':
                initial_location = str(scene_config['Initial Conditions']['region'])


    for entry in weather_val:
        if entry[0] in varying_parameters:
            initial_condition.append((entry[0],int(entry[1])))

    if "traffic_density" in varying_parameters:
        initial_condition.append(("traffic_density",int(initial_traffic_density)))
    if "pedestrian_density" in varying_parameters:
        initial_condition.append(("pedestrian_density",int(initial_pedestrian_density)))


    return varying_entities, varying_parameters, data_val, initial_condition, initial_location, initial_traffic_density, initial_pedestrian_density, constraints


def generate_scene_artifact_files(path,scene_config,sampler,folder,simulation_run,route_path,y,data_path,total_scenes,data_file,scene_num,route_root,data_root):
    """
    All the processing scripts for scenes go here
    """
    weather_data = []
    joined_parameter_list = []
    varying_scene_entities, varying_scene_parameters, data_val, initial_condition, initial_location, initial_traffic_density, initial_pedestrian_density, constraints = decode_scene_description(scene_config)
    static_parameters, dynamic_parameters = prepare_data(data_val)
    joined_parameter_list = parameter_sampler(dynamic_parameters,static_parameters,folder,simulation_run,route_path,y,sampler,data_path,total_scenes,scene_num,initial_condition,constraints,route_root,data_root)
    weather_list,traffic_info,town_info,town_number = organize_parameters(joined_parameter_list) #Organize the selected hyperparameters
    weather = set_scene_weather(weather_map,joined_parameter_list) #weather description
    weather_data.append(weather)
    write_weather_data(weather_data,data_file) #write weather to file
    carla_route = path + '/leaderboard/data/town%d_route/'%town_number
    if not os.path.exists(carla_route):
        print("Error. Route File for town%d not found!!!"%town_number)
        sys.exit(1)
    if simulation_run == 0 and scene_num == 1:
        carla_route  = carla_route + "region%s.xml"%initial_location
    else:
        carla_route = carla_route + "region%s.xml"%scene_num   #%track_list[scene_num-1]

    global_route,town = parse_routes_file(carla_route,False) #global route by reading one route from CARLA AD
    artifact_generator(carla_route,weather,scene_num,town_info,folder)
