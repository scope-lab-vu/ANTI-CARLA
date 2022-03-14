#!/usr/bin/python3
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
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
from utils import parse_routes_file,artifact_generator
from agent_util import generate_scene_artifact_files
import csv
import argparse
from argparse import RawTextHelpFormatter
import pandas as pd
import random
from ruamel import yaml
import re
import shutil
from samplers.Random import Random_Search

def read_yaml(yaml_file):
    """
    Read the input yaml file entered by the user
    """
    with open(yaml_file) as file:
        config = yaml.safe_load(file)

    return config

def decode_sampler_description(sampler_config):
    """
    Decode the sampler information
    """
    sampler = []
    for entry in sampler_config['Samplers']:
        if sampler_config['Samplers'][entry] is True:
            sampler.append(entry)

    if len(sampler) > 1:
        print("Warning multiple samplers are selected in the specification file!!!!")
        sys.exit(1)
    if len(sampler) == 0:
        print("Warning no samplers are selected in the specification file!!!!")
        sys.exit(1)

    return sampler[0]


def decode_agent_description(agent_config):
    """
    Decode the agent information
    """
    sensors_info = []
    controller = []
    data_to_record = []
    for entry in agent_config['Controller']:
        if agent_config['Controller'][entry] is True:
            controller.append(entry)

    if len(controller) > 1:
        print("Warning multiple controllers are selected in the agent specification file!!!!")
        sys.exit(1)
    if len(controller) == 0:
        print("Warning no controller is selected in the agent specification file!!!!")
        sys.exit(1)

    for entry in agent_config['Sensors']:
        if agent_config['Sensors'][entry] is False:
            pass
        else:
            sensors_info.append((entry,agent_config['Sensors'][entry]))

    for entry in agent_config['Data Recorder']:
        if agent_config['Data Recorder'][entry] is False:
            pass
        else:
            data_to_record.append(entry)

    record_frequency = agent_config['Record Frequency']*20
    #record_location = agent_config['Record Location']
    #print(record_location)


    return str(controller[0]), sensors_info, data_to_record, int(record_frequency)



def main(args,root,y,path,data_root,route_root,sim_data_root):
    """
    Main that hosts the scenario generation in loop
    """
    scene_num = args.scene_num
    simulation_run = args.simulation_num
    total_scenes = args.total_scenes
    #exploration = args.exploration_runs
    route_path = root[0]
    data_path = root[1]
    print("----------------------------------------------")
    print("Simulation%d Execution"%simulation_run)
    print("----------------------------------------------")
    #carla_route = path + '/leaderboard/data/town5_route/'
    folder = route_path + "scene%d"%scene_num #folder to store all the xml generated
    os.makedirs(folder, exist_ok=True)
    data_file = folder + "/weather_data.csv"
    scene_description = args.sdl + '/' + 'scene_description.yml'
    agent_description = args.sdl + '/' + 'agent_description.yml'
    sampler_description = args.sdl + '/' + 'sampler_description.yml'
    scene_config = read_yaml(scene_description)
    agent_config = read_yaml(agent_description)
    sampler_config = read_yaml(sampler_description)
    sampler = decode_sampler_description(sampler_config)
    #controller, sensors_info, data_to_record, record_frequency = decode_agent_description(agent_config)
    generate_scene_artifact_files(path,scene_config,sampler,folder,simulation_run,route_path,y,data_path,total_scenes,data_file,scene_num,route_root,sim_data_root)
    write_folder_number(y,data_root)

def write_folder_number(y,path):
    """
    Write the folder number in which the routes are stored
    """
    file1 = open(path + "tmp.txt","w")
    file1.write(str(y))
    file1.close()

def create_root_folder(args,path):
    paths = []
    roots = []
    folders = [args.routes_folder,args.data_folder]
    for folder in folders:
        root = path + "/" + folder + "/"
        dirlist = [item for item in os.listdir(root) if os.path.isdir(os.path.join(root,item))]
        folder_len = len(dirlist)
        if folder_len == 0:
            y = 0
        else:
            if args.simulation_num == 0 and args.scene_num == 1:
                y = folder_len
            else:
                y = folder_len-1

        folder_path = root + "run%d"%y + "/" + "simulation%d"%args.simulation_num + "/"
        os.makedirs(folder_path, exist_ok=True) #creates a new dir everytime with max number
        paths.append(folder_path)
        roots.append(root)
        route_root = path + "/" + args.routes_folder + "/" + "run%d"%y + "/"
        sim_data_root = path + "/" + args.data_folder + "/" + "run%d"%y + "/"

    return paths, y, roots[0], route_root, sim_data_root


if __name__ == '__main__':
        description = "CARLA Scene Generation\n"
        parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
        parser.add_argument('--project_path', type=str, help='Type the simulation folder to store the data')
        parser.add_argument('--simulation_num', type=int, default=1, help='Type the simulation folder to store the data')
        parser.add_argument('--scene_num', type=int, default=1, help='Type the scene number to be executed')
        #parser.add_argument('--optimizer', type=str, default="Random", help='Type the Optimizer to be used for scene selection')
        parser.add_argument('--total_scenes', type=int, help='Total number of scenes')
        #parser.add_argument('--exploration_runs', type=int, help='Total Exploration Runs')
        parser.add_argument('--routes_folder', type=str, help='Location to store routes')
        parser.add_argument('--data_folder', type=str, help='Location to store simulation statistics')
        parser.add_argument('--sdl', type=str, help='Location of scenario description files')

        args = parser.parse_args()
        path = args.project_path
        #if args.simulation_num == 0 and args.scene_num == 1:
            #episode_folder = create_episode_folder(args,path)
        #path = "/home/shreyas/Carla_Research/Testing-Framework/"
        root,y,data_root,route_root,sim_data_root = create_root_folder(args,path)
        #print(root,y,data_root)
        main(args,root,y,path,data_root,route_root,sim_data_root)
