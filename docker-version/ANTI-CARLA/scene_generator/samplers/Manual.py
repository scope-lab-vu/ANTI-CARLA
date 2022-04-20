#!/usr/bin/python3
import csv
import pandas as pd
import random
import numpy as np

def ManualEntry(manual_scene_specification,folder,simulation_run,root,y,dynamic_parameters,static_parameters):
    """
    Manual entry provided by the user
    """
    distributions = []
    new_hyperparameters_list = []
    updated_parameter_list = []
    joined_parameter_list = dynamic_parameters + static_parameters
    for entry in manual_scene_specification[int(simulation_run)]:
        print(entry)
        if entry == 'weather':
            for data in manual_scene_specification[int(simulation_run)]['weather']:
                print(data)
                for sample_entry in joined_parameter_list:
                    if data == sample_entry[0]:
                        val = int(manual_scene_specification[int(simulation_run)]['weather'][data])
                        updated_parameter_list.append((data,val))
                        print(updated_parameter_list)
                        distributions.append(val)
        else:
            for sample_entry in joined_parameter_list:
                if entry == sample_entry[0]:
                    if manual_scene_specification[int(simulation_run)][entry] == None:
                        val = 0
                    else:
                        val = int(manual_scene_specification[int(simulation_run)][entry])
                    updated_parameter_list.append((entry,val))
                    print(updated_parameter_list)
                    distributions.append(val)

    with open(root + "sampled_parameters.csv", 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerow(distributions)

    with open(folder + "/scene_parameters.csv", 'w') as csvfile: #Always save the selected hyperparameters for optimization algorithms
        writer = csv.writer(csvfile, delimiter = ',')
        writer.writerows(updated_parameter_list)

    return updated_parameter_list
