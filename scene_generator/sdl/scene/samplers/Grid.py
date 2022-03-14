#!/usr/bin/python3
import csv
import pandas as pd
import random
import numpy as np
from itertools import product

weather_parameters = ['cloudiness','precipitation','precipitation_deposits','sun_altitude_angle','wind_intensity','sun_azimuth_angle','wetness','fog_distance','fog_density']

def Grid_Search(current_hyperparameters,folder,simulation_run,root,y,exploration):
    """
    The random sampler takes in the hyperparameters of the current step and returns a new hyperparameter set that is randomly sampled
    """
    new_hyperparameters_list = []
    choices_array = []
    distributions = []
    for i in range(len(current_hyperparameters)):
        if current_hyperparameters[i][0] in weather_parameters:
            if current_hyperparameters[i][0] == "precipitation":
                min,max,step = 0,100,5
            elif current_hyperparameters[i][0] == "cloudiness":
                min,max,step = 0,100,5
            elif current_hyperparameters[i][0] == "sun_altitude_angle":
                min,max,step = 45,90,5
            else:
                min,max,step = 0,100,0
        elif current_hyperparameters[i][0] == "camera_faults":
            min,max,step = 0,5,1
        elif current_hyperparameters[i][0] == 'road_segments':
            min,max,step = 0,6,1

        choice_list = np.arange(min,max,step)
        choices_array.append(choice_list)

    combination = list(product(*choices_array))
    parameter_distribution = combination[simulation_run]
    for i in range(len(parameter_distribution)):
        distributions.append(int(parameter_distribution[i]))
        new_hyperparameters_list.append((current_hyperparameters[i][0],int(parameter_distribution[i])))
        #print(new_hyperparameters_list)
    print(distributions)

    return distributions, new_hyperparameters_list
