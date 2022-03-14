#!/usr/bin/python3
import csv
import pandas as pd
import random
import numpy as np

weather_parameters = ['cloudiness','precipitation','precipitation_deposits','sun_altitude_angle','wind_intensity','sun_azimuth_angle','wetness','fog_distance','fog_density']


def Random_Search(current_hyperparameters,folder,simulation_run,route_path,y,scene_num,initial_condition,weather_step,traffic_step,pedestrian_step):
    """
    The random sampler takes in the hyperparameters of the current step and returns a new hyperparameter set that is randomly sampled
    """

    new_hyperparameters_list = []
    choices_array = []
    distributions = []
    if simulation_run == 0 and scene_num == 1:
        for entry in initial_condition:
            distributions.append(int(entry[1]))
            new_hyperparameters_list.append((entry[0],int(entry[1])))
    else:
        for i in range(len(current_hyperparameters)):
            print(current_hyperparameters[i][0])
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
            new_hyperparameters_list.append((current_hyperparameters[i][0],int(parameter_distribution)))

    print(distributions)

    return distributions, new_hyperparameters_list
