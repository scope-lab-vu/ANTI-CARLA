#!/usr/bin/python3
import os
import sys
import numpy as np

weather_parameters = ['cloudiness','precipitation','precipitation_deposits','wind_intensity','sun_azimuth_angle','wetness','fog_distance','fog_density']

def next_prime():
    def is_prime(num):
        "Checks if num is a prime value"
        for i in range(2,int(num**0.5)+1):
            if(num % i)==0: return False
        return True

    prime = 3
    while(1):
        if is_prime(prime):
            yield prime
        prime += 2

def vdc(n, base=2):
    vdc, denom = 0, 1
    while n:
        denom *= base
        n, remainder = divmod(n, base)
        vdc += remainder/float(denom)
    return vdc

def normalize_vals(sample,parameter):
    if parameter in weather_parameters:
        min,max = 0,100
    elif parameter == "sun_altitude_angle":
        min,max = 0,90
    elif parameter == 'road_segments':
        min,max = 0,6
    elif parameter == 'traffic_density':
        min,max = 10,20
    elif parameter == 'sensor_faults':
        min,max = 0,15

    sample = sample * (max - min) + min

    return round(sample)

def halton(size, dim):
    seq = []
    primeGen = next_prime()
    next(primeGen)
    for d in range(dim):
        base = next(primeGen)
        seq.append([vdc(i, base) for i in range(size)])
    return seq

def Halton_Sequence(current_hyperparameters,folder,simulation_run,root,y,total_scenes,exploration):
    distributions = []
    new_hyperparameters_list = []
    parameters = []
    samples = halton(total_scenes, len(current_hyperparameters))
    for i in range(len(samples[0])):
        temp = []
        for j in range(len(samples)):
            temp.append(samples[j][i])
        parameters.append(temp)
    #print(parameters)
    #distributions = parameters[simulation_run]
    for index,hype in enumerate(current_hyperparameters):
        sample = normalize_vals(parameters[simulation_run][index],hype[0])
        distributions.append(sample)
        new_hyperparameters_list.append((hype[0],sample))
    #print(new_hyperparameters_list)

    return distributions, new_hyperparameters_list
