#!/usr/bin/env python
# Copyright (c) 2018-2019 Intel Corporation.
# authors: German Ros (german.ros@intel.com), Felipe Codevilla (felipe.alcm@gmail.com)
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
CARLA Challenge Evaluator Routes

Provisional code to evaluate Autonomous Agents for the CARLA Autonomous Driving challenge
"""
from __future__ import print_function
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)
warnings.simplefilter(action='ignore', category=UserWarning)
import traceback
import argparse
from argparse import RawTextHelpFormatter
from datetime import datetime
from distutils.version import LooseVersion
import importlib
import os
import sys
import gc
import pkg_resources
import sys
import carla
import copy
import signal
import csv
import pandas as pd
from ruamel import yaml
from srunner.scenariomanager.carla_data_provider import *
from srunner.scenariomanager.timer import GameTime
from srunner.scenariomanager.watchdog import Watchdog
from leaderboard.scenarios.scenario_manager import ScenarioManager
from leaderboard.scenarios.route_scenario import RouteScenario
from leaderboard.envs.sensor_interface import SensorInterface, SensorConfigurationInvalid
from leaderboard.autoagents.agent_wrapper import  AgentWrapper, AgentError
from leaderboard.utils.statistics_manager import StatisticsManager
from leaderboard.utils.route_indexer import RouteIndexer


sensors_to_icons = {
    'sensor.camera.rgb':        'carla_camera',
    'sensor.camera.semantic_segmentation': 'carla_camera',
    'sensor.camera.depth':      'carla_camera',
    'sensor.lidar.ray_cast':    'carla_lidar',
    'sensor.lidar.ray_cast_semantic':    'carla_lidar',
    'sensor.other.radar':       'carla_radar',
    'sensor.other.gnss':        'carla_gnss',
    'sensor.other.imu':         'carla_imu',
    'sensor.opendrive_map':     'carla_opendrive_map',
    'sensor.speedometer':       'carla_speedometer'
}


class LeaderboardEvaluator(object):

    """
    TODO: document me!
    """

    ego_vehicles = []

    # Tunable parameters
    client_timeout = 10.0  # in seconds
    wait_for_world = 20.0  # in seconds
    frame_rate = 20.0      # in Hz

    def __init__(self, args, statistics_manager):
        """
        Setup CARLA client and world
        Setup ScenarioManager
        """
        self.statistics_manager = statistics_manager
        self.sensors = None
        self.sensor_icons = []
        self._vehicle_lights = carla.VehicleLightState.Position | carla.VehicleLightState.LowBeam

        # First of all, we need to create the client that will send the requests
        # to the simulator. Here we'll assume the simulator is accepting
        # requests in the localhost at port 2000.
        self.client = carla.Client(args.host, int(args.port))
        if args.timeout:
            self.client_timeout = float(args.timeout)
        self.client.set_timeout(self.client_timeout)

        self.traffic_manager = self.client.get_trafficmanager(int(args.trafficManagerPort))

        dist = pkg_resources.get_distribution("carla")
        if dist.version != 'leaderboard':
            if LooseVersion(dist.version) < LooseVersion('0.9.10'):
                raise ImportError("CARLA version 0.9.10.1 or newer required. CARLA version found: {}".format(dist))

        # Load agent
        module_name = os.path.basename(args.agent).split('.')[0]
        sys.path.insert(0, os.path.dirname(args.agent))
        self.module_agent = importlib.import_module(module_name)

        # Create the ScenarioManager
        self.manager = ScenarioManager(args.timeout, args.debug > 1)

        # Time control for summary purposes
        self._start_time = GameTime.get_time()
        self._end_time = None

        # Create the agent timer
        self._agent_watchdog = Watchdog(int(float(args.timeout)))
        signal.signal(signal.SIGINT, self._signal_handler)

    def _signal_handler(self, signum, frame):
        """
        Terminate scenario ticking when receiving a signal interrupt
        """
        if self._agent_watchdog and not self._agent_watchdog.get_status():
            raise RuntimeError("Timeout: Agent took too long to setup")
        elif self.manager:
            self.manager.signal_handler(signum, frame)

    def __del__(self):
        """
        Cleanup and delete actors, ScenarioManager and CARLA world
        """

        self._cleanup()
        if hasattr(self, 'manager') and self.manager:
            del self.manager
        if hasattr(self, 'world') and self.world:
            del self.world

    def _cleanup(self):
        """
        Remove and destroy all actors
        """

        # Simulation still running and in synchronous mode?
        if self.manager and self.manager.get_running_status() \
                and hasattr(self, 'world') and self.world:
            # Reset to asynchronous mode
            settings = self.world.get_settings()
            settings.synchronous_mode = False
            settings.fixed_delta_seconds = None
            settings.no_rendering_mode = False
            self.world.apply_settings(settings)
            self.traffic_manager.set_synchronous_mode(False)

        if self.manager:
            self.manager.cleanup()

        CarlaDataProvider.cleanup()

        for i, _ in enumerate(self.ego_vehicles):
            if self.ego_vehicles[i]:
                self.ego_vehicles[i].destroy()
                self.ego_vehicles[i] = None
        self.ego_vehicles = []

        if self._agent_watchdog:
            self._agent_watchdog.stop()

        if hasattr(self, 'agent_instance') and self.agent_instance:
            self.agent_instance.destroy()
            self.agent_instance = None

        if hasattr(self, 'statistics_manager') and self.statistics_manager:
            self.statistics_manager.scenario = None

    def _prepare_ego_vehicles(self, ego_vehicles, wait_for_ego_vehicles=False):
        """
        Spawn or update the ego vehicles
        """
        if not wait_for_ego_vehicles:
            for vehicle in ego_vehicles:
                self.ego_vehicles.append(CarlaDataProvider.request_new_actor(vehicle.model,
                                                                             vehicle.transform,
                                                                             vehicle.rolename,
                                                                             color=vehicle.color,
                                                                             vehicle_category=vehicle.category))

            #print("num of ego:", len(self.ego_vehicles))

        else:
            ego_vehicle_missing = True
            while ego_vehicle_missing:
                self.ego_vehicles = []
                ego_vehicle_missing = False
                for ego_vehicle in ego_vehicles:
                    ego_vehicle_found = False
                    carla_vehicles = CarlaDataProvider.get_world().get_actors().filter('vehicle.*')
                    for carla_vehicle in carla_vehicles:
                        if carla_vehicle.attributes['role_name'] == ego_vehicle.rolename:
                            ego_vehicle_found = True
                            self.ego_vehicles.append(carla_vehicle)
                            break
                    if not ego_vehicle_found:
                        ego_vehicle_missing = True
                        break

            for i, _ in enumerate(self.ego_vehicles):
                self.ego_vehicles[i].set_transform(ego_vehicles[i].transform)

        # sync statedata_path + "/" + folder + "/" +"run%s"%y+ "/"
        CarlaDataProvider.get_world().tick()
        #print("num of ego:", len(self.ego_vehicles))

    def _load_and_wait_for_world(self, args, town, ego_vehicles=None):
        """
        Load a new CARLA world and provide data to CarlaDataProvider
        """

        self.world = self.client.load_world(town)
        settings = self.world.get_settings()
        settings.fixed_delta_seconds = 1.0 / self.frame_rate
        settings.synchronous_mode = True
        #settings.no_rendering_mode = True
        self.world.apply_settings(settings)

        self.world.reset_all_traffic_lights()

        CarlaDataProvider.set_client(self.client)
        CarlaDataProvider.set_world(self.world)
        CarlaDataProvider.set_traffic_manager_port(int(args.trafficManagerPort))

        self.traffic_manager.set_synchronous_mode(True)
        self.traffic_manager.set_random_device_seed(int(args.trafficManagerSeed))

        # Wait for the world to be ready
        if CarlaDataProvider.is_sync_mode():
            self.world.tick()
        else:
            self.world.wait_for_tick()

        if CarlaDataProvider.get_map().name != town:
            raise Exception("The CARLA server uses the wrong map!"
                            "This scenario requires to use map {}".format(town))

    def _register_statistics(self, config, checkpoint, entry_status, crash_message=""):
        """
        Computes and saved the simulation statistics
        """
        # register statistics
        current_stats_record = self.statistics_manager.compute_route_statistics(
            config,
            self.manager.scenario_duration_system,
            self.manager.scenario_duration_game,
            crash_message
        )

        print("\033[1m> Registering the route statistics\033[0m")
        self.statistics_manager.save_record(current_stats_record, config.index, checkpoint)
        self.statistics_manager.save_entry_status(entry_status, False, checkpoint)

    def _load_and_run_scenario(self, args, config, sensors_info, data_to_record, record_frequency, display, record_folder,data_folder,route_folder,traffic_amount):
        """
        Load and run the scenario given by config.

        Depending on what code fails, the simulation will either stop the route and
        continue from the next one, or report a crash and stop.
        """
        crash_message = ""
        entry_status = "Started"

        print("\n\033[1m========= Preparing {} (repetition {}) =========".format(config.name, config.repetition_index))
        print("> Setting up the agent\033[0m")

        # Prepare the statistics of the route
        self.statistics_manager.set_route(config.name, config.index)

        # Set up the user's agent, and the timer to avoid freezing the simulation
        try:
            self._agent_watchdog.start()
            agent_class_name = getattr(self.module_agent, 'get_entry_point')()
            print(agent_class_name)
            self.agent_instance = getattr(self.module_agent, agent_class_name)(args.agent_config, sensors_info, data_to_record, record_frequency, display, record_folder)
            config.agent = self.agent_instance

            # Check and store the sensors
            if not self.sensors:
                self.sensors = self.agent_instance.sensors()
                track = self.agent_instance.track

                AgentWrapper.validate_sensor_configuration(self.sensors, track, args.track)

                self.sensor_icons = [sensors_to_icons[sensor['type']] for sensor in self.sensors]
                self.statistics_manager.save_sensors(self.sensor_icons, args.checkpoint)

            self._agent_watchdog.stop()

        except SensorConfigurationInvalid as e:
            # The sensors are invalid -> set the ejecution to rejected and stop
            print("\n\033[91mThe sensor's configuration used is invalid:")
            print("> {}\033[0m\n".format(e))
            traceback.print_exc()

            crash_message = "Agent's sensors were invalid"
            entry_status = "Rejected"

            self._register_statistics(config, args.checkpoint, entry_status, crash_message)
            self._cleanup()
            sys.exit(-1)

        except Exception as e:
            # The agent setup has failed -> start the next route
            print("\n\033[91mCould not set up the required agent:")
            print("> {}\033[0m\n".format(e))
            traceback.print_exc()

            crash_message = "Agent couldn't be set up"

            self._register_statistics(config, args.checkpoint, entry_status, crash_message)
            self._cleanup()
            return

        print("\033[1m> Loading the world\033[0m")

        # Load the world and the scenario
        try:
            self._load_and_wait_for_world(args, config.town, config.ego_vehicles)
            self._prepare_ego_vehicles(config.ego_vehicles, False)
            scenario = RouteScenario(traffic_amount,world=self.world, config=config, debug_mode=args.debug)
            self.statistics_manager.set_scenario(scenario.scenario)

            # self.agent_instance._init()
            # self.agent_instance.sensor_interface = SensorInterface()

            # Night mode
            if config.weather.sun_altitude_angle < 0.0:
                for vehicle in scenario.ego_vehicles:
                    vehicle.set_light_state(carla.VehicleLightState(self._vehicle_lights))

            # Load scenario and run it
            if args.record:
                self.client.start_recorder("{}/{}_rep{}.log".format(args.record, config.name, config.repetition_index))
            self.manager.load_scenario(scenario, self.agent_instance, config.repetition_index)

        except Exception as e:
            # The scenario is wrong -> set the ejecution to crashed and stop
            print("\n\033[91mThe scenario could not be loaded:")
            print("> {}\033[0m\n".format(e))
            traceback.print_exc()

            crash_message = "Simulation crashed"
            entry_status = "Crashed"

            self._register_statistics(config, args.checkpoint, entry_status, crash_message)

            if args.record:
                self.client.stop_recorder()

            self._cleanup()
            sys.exit(-1)

        print("\033[1m> Running the route\033[0m")

        # Run the scenario
        # try:
        self.manager.run_scenario()

        # except AgentError as e:
        #     # The agent has failed -> stop the route
        #     print("\n\033[91mStopping the route, the agent has crashed:")
        #     print("> {}\033[0m\n".format(e))
        #     traceback.print_exc()

        #     crash_message = "Agent crashed"

        # except Exception as e:
        #     print("\n\033[91mError during the simulation:")
        #     print("> {}\033[0m\n".format(e))
        #     traceback.print_exc()

        #     crash_message = "Simulation crashed"
        #     entry_status = "Crashed"

        # Stop the scenario
        try:
            print("\033[1m> Stopping the route\033[0m")
            self.manager.stop_scenario()
            self._register_statistics(config, args.checkpoint, entry_status, crash_message)

            if args.record:
                self.client.stop_recorder()

            # Remove all actors
            scenario.remove_all_actors()

            self._cleanup()

        except Exception as e:
            print("\n\033[91mFailed to stop the scenario, the statistics might be empty:")
            print("> {}\033[0m\n".format(e))
            traceback.print_exc()

            crash_message = "Simulation crashed"

        if crash_message == "Simulation crashed":
            sys.exit(-1)

    def read_simulation_param(self,route_folder,x):
        """
        Get the traffic and fault type information information from the route folder
        """
        hyperparameters = []
        parameters = pd.read_csv(route_folder + "/scene_parameters.csv", usecols = [0,1], header=None, index_col=False)
        for index, row in parameters.iterrows():
            if row[0] == x:
                hyperparameters.append(int(row[1]))

        return hyperparameters[0]

    def compute_scenario_score(self,collision, infractions, out_of_lane,driving_score,test_score_file):
        stats = []
        #scenario_score = 0.5 * collision + 0.25 * float(infractions) + 0.25 * float(out_of_lane)
        #scenario_score = risk + float(infractions) + float(out_of_lane)
        #stats.append(round(scenario_score,2))
        stats.append(driving_score)
        with open(test_score_file, 'a') as csvfile: #Always save the selected hyperparameters for optimization algorithms
            writer = csv.writer(csvfile, delimiter = ',')
            writer.writerow(stats)

        print("---------------------")
        #print("Avg Scene Risk:%0.2f"%risk)
        print("Scene Score:%0.2f"%driving_score)
        print("---------------------")

    def run(self, args, sensors_info, data_to_record, record_frequency, display, record_folder,data_folder,route_folder,data_root,run_root,infractions_to_record):
        """
        Run the challenge mode
        """
        # agent_class_name = getattr(self.module_agent, 'get_entry_point')()
        # self.agent_instance = getattr(self.module_agent, agent_class_name)(args.agent_config)

        traffic_amount = self.read_simulation_param(route_folder,x='traffic_density')

        filename = data_folder + "simulation_data.csv"
        stats_file = run_root + "infraction_stats_over_run.csv"
        test_score_file = run_root + "test_score.csv"

        route_indexer = RouteIndexer(args.routes, args.scenarios, args.repetitions)
        if args.resume:
            route_indexer.resume(args.checkpoint)
            self.statistics_manager.resume(args.checkpoint)
        else:
            self.statistics_manager.clear_record(args.checkpoint)
            route_indexer.save_state(args.checkpoint)

        while route_indexer.peek():
            # setup
            config = route_indexer.next()

            # run
            self._load_and_run_scenario(args, config, sensors_info, data_to_record, record_frequency, display, record_folder,data_folder,route_folder,traffic_amount)

            for obj in gc.get_objects():
                try:
                    if torch.is_tensor(obj) or (hasattr(obj, 'data') and torch.is_tensor(obj.data)):
                        print(type(obj), obj.size())
                except:
                    pass

            route_indexer.save_state(args.checkpoint)

        # save global statistics
        print("\033[1m> Registering the global statistics\033[0m")
        global_stats_record = self.statistics_manager.compute_global_statistics(route_indexer.total)
        collision, infractions, out_of_lane, driving_score = StatisticsManager.save_global_record(global_stats_record,infractions_to_record,self.sensor_icons, route_indexer.total, args.checkpoint,filename,stats_file)
        self.compute_scenario_score(collision, infractions, out_of_lane,driving_score,test_score_file)

def decode_agent_description(agent_config):
    """
    Decode the agent information
    """
    sensors_info = []
    controller = []
    data_to_record = []
    for entry in agent_config['Controller']:
        if agent_config['Controller'][entry] is True:
            controller.append(str(entry))

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

    record_frequency = agent_config['Record Frequency'] #*20
    record_location = agent_config['Record Location']
    display = agent_config['Display']

    return controller, sensors_info, data_to_record, int(record_frequency), display

def decode_scene_description(scene_config):
    infractions_to_record = []
    for entry in scene_config['Infraction Metrics']:
        if scene_config['Infraction Metrics'][entry] is False:
            pass
        else:
            infractions_to_record.append(entry)

    return infractions_to_record


def read_yaml(yaml_file):
    """
    Read the input yaml file entered by the user
    """
    with open(yaml_file) as file:
        config = yaml.safe_load(file)

    return config

def create_root_folder(data_path,y,args):
    paths = []
    folders = [args.data_folder,args.routes_folder,args.record_folder]
    for folder in folders:
        new_path = data_path + "/" + folder + "/" +"run%s"%y+ "/" + "simulation%d"%args.simulation_number + "/"
        if not os.path.exists(new_path):
            os.makedirs(new_path, exist_ok=True) #creates a new dir everytime with max number
        paths.append(new_path)
    run_root = data_path + "/" + args.data_folder + "/" +"run%s"%y+ "/"
    #paths.append(run_root)

    return paths,run_root

def read_folder_number(path,routes_folder):
    """
    Write the folder number in which the routes are stored
    """
    path = path + "/" + routes_folder + "/"
    file1 = open(path + "tmp.txt", "r")
    y = file1.read()
    file1.close() #to change file access modes
    os.remove(path + "tmp.txt")

    return y

def is_float(tested_string):
    try:
        float(tested_string)
        return True
    except ValueError:
        return False

def parse_sensors(sensors_before_parse):
    sensors_after_parse = []
    for sensor in sensors_before_parse:
        temp_sensor_dict = {}
        for sensor_info in sensor[1]:
            key = sensor_info.split(":")[0]
            item = sensor_info.split(":")[1]
            if is_float(item):
                item = float(item)
            temp_sensor_dict[key] = item
        if "rgb" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.camera.rgb'
        elif "radar" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.other.radar'
        elif "lidar" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.lidar.ray_cast'
        elif "imu" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.other.imu'
        elif "gnss" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.other.gnss'
        elif "speedometer" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.speedometer'
        elif "segmentation_camera" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.camera.semantic_segmentation'
        elif "collision_detector" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.other.collision'
        elif "obstacle_detector" in sensor[0]:
            temp_sensor_dict['type'] = 'sensor.other.obstacle'
        temp_sensor_dict['name'] = sensor[0]
        sensors_after_parse.append(temp_sensor_dict)
    return sensors_after_parse

def main():
    description = "CARLA AD Leaderboard Evaluation: evaluate your Agent in CARLA scenarios\n"

    # general parameters
    parser = argparse.ArgumentParser(description=description, formatter_class=RawTextHelpFormatter)
    parser.add_argument('--host', default='localhost',
                        help='IP of the host server (default: localhost)')
    parser.add_argument('--port', default='2000', help='TCP port to listen to (default: 2000)')
    parser.add_argument('--trafficManagerPort', default='8000',
                        help='Port to use for the TrafficManager (default: 8000)')
    parser.add_argument('--trafficManagerSeed', default='0',
                        help='Seed used by the TrafficManager (default: 0)')
    parser.add_argument('--debug', type=int, help='Run with debug output', default=0)
    parser.add_argument('--record', type=str, default='',
                        help='Use CARLA recording feature to create a recording of the scenario')
    parser.add_argument('--timeout', default="10.0",
                        help='Set the CARLA client timeout value in seconds')

    # simulation setup
    parser.add_argument('--routes',
                        help='Name of the route to be executed. Point to the route_xml_file to be executed.',
                        required=True)
    parser.add_argument('--scenarios',
                        help='Name of the scenario annotation file to be mixed with the route.',
                        required=True)
    parser.add_argument('--repetitions',
                        type=int,
                        default=1,
                        help='Number of repetitions per route.')

    # agent-related options
    parser.add_argument("-a", "--agent", type=str, help="Path to Agent's py file to evaluate", required=True)
    parser.add_argument("--agent-config", type=str, help="Path to Agent's configuration file", default="")

    parser.add_argument("--track", type=str, default='SENSORS', help="Participation track: SENSORS, MAP")
    parser.add_argument('--resume', type=bool, default=False, help='Resume execution from last checkpoint?')
    parser.add_argument("--checkpoint", type=str,
                        default='./simulation_results.json',
                        help="Path to checkpoint used for saving statistics and resuming")
    parser.add_argument('--simulation_number', type=int, help='Type the simulation folder to store the data')
    parser.add_argument('--scene_number', type=int, default=1, help='Type the scene number to be executed')
    parser.add_argument('--project_path', type=str, help='Type the simulation folder to store the data')
    parser.add_argument('--routes_folder', type=str, help='Location to store routes')
    parser.add_argument('--data_folder', type=str, help='Location to store simulation statistics')
    parser.add_argument('--record_folder', type=str, help='Location to store recorded data by sensors')
    parser.add_argument('--sdl', type=str, help='Location of scenario description files')


    arguments = parser.parse_args()

    statistics_manager = StatisticsManager()

    try:
        data_path = arguments.project_path
        y = read_folder_number(data_path,arguments.routes_folder)
        paths,run_root = create_root_folder(data_path,y,arguments)
        data_folder = paths[0] + "scene%d"%arguments.scene_number + '/'
        os.makedirs(data_folder, exist_ok=True)
        route_folder = paths[1] + "scene%d"%arguments.scene_number + '/'
        os.makedirs(route_folder, exist_ok=True)
        record_folder = paths[2] + "scene%d"%arguments.scene_number + '/'
        os.makedirs(record_folder, exist_ok=True)
        # image_folder = paths[2] + "scene%d"%arguments.simulation_number + '/'
        # os.makedirs(image_folder, exist_ok=True)

        arguments.routes = route_folder + "route.xml"
        agent_description = arguments.sdl + '/' + 'agent_description.yml'
        scene_description = arguments.sdl + '/' + 'scene_description.yml'
        agent_config = read_yaml(agent_description)
        scene_config = read_yaml(scene_description)
        infractions_to_record = decode_scene_description(scene_config)
        print(infractions_to_record)
        controller, sensors_info, data_to_record, record_frequency, display = decode_agent_description(agent_config)
        sensors_info = parse_sensors(sensors_info)
        #print(sensors_info)
        #print(data_to_record)
        #print(record_frequency)
        #print(display)
        if str(controller[0]).strip() == "Transfuser":
            arguments.agent = "transfuser_agent.py"
            arguments.agent_config = arguments.project_path + "/trained_models/transfuser"
        elif str(controller[0]).strip() == 'Learning_by_cheating':
            arguments.agent = arguments.project_path +  "/leaderboard/team_code/image_agent.py"
            arguments.agent_config = arguments.project_path + "/trained_models/Learning_by_cheating/model.ckpt"
        else:
            arguments.agent = 'own_agent.py' #"transfuser_agent.py"
            arguments.agent_config = arguments.project_path + "/trained_models/transfuser"

        leaderboard_evaluator = LeaderboardEvaluator(arguments, statistics_manager)
        leaderboard_evaluator.run(arguments, sensors_info, data_to_record, record_frequency, display, record_folder,data_folder,route_folder,paths[0],run_root,infractions_to_record)

    except Exception as e:
        traceback.print_exc()
    finally:
        del leaderboard_evaluator




if __name__ == '__main__':
    main()
