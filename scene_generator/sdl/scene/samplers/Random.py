#!/usr/bin/python3
import csv
import pandas as pd
import random
import numpy as np



def Random_Search(current_hyperparameters,folder,simulation_run,root,y,exploration):
    """
    The random sampler takes in the hyperparameters of the current step and returns a new hyperparameter set that is randomly sampled
    """
    new_hyperparameters_list = []
    choices_array = []
    distributions = []
    if simulation_run <= 0:
        for i in range(len(current_hyperparameters)):
            if current_hyperparameters[i][0] == 'sun_altitude_angle':
                parameter_distribution = 45.0
            elif current_hyperparameters[i][0] == 'precipitation':
                parameter_distribution = 0.0
            elif current_hyperparameters[i][0] == 'cloudiness':
                parameter_distribution = 0.0
            else:
                parameter_distribution = 0.0
            distributions.append(int(parameter_distribution))
            new_hyperparameters_list.append((current_hyperparameters[i][0],int(parameter_distribution)))
    else:
        for i in range(len(current_hyperparameters)):
            if current_hyperparameters[i][0] == 'segment_number' or 'traffic' or 'camera_faults':
                step = 1
            else:
                step = 5
            choice_list = np.arange(current_hyperparameters[i][1],current_hyperparameters[i][2],step)
            choices_array.append(choice_list)
            parameter_distribution = random.choice(choice_list)
            distributions.append(int(parameter_distribution))
            new_hyperparameters_list.append((current_hyperparameters[i][0],int(parameter_distribution)))

    print(distributions)

    return distributions, new_hyperparameters_list
