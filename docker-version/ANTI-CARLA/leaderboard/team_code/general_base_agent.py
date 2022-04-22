import time
import os
import datetime
import pathlib
import json

import cv2
import carla

from leaderboard.autoagents import autonomous_agent
from team_code.planner import RoutePlanner

import numpy as np
from PIL import Image, ImageDraw


SAVE_PATH = os.environ.get('SAVE_PATH', None)


class BaseAgent(autonomous_agent.AutonomousAgent):
    def general_base_agent_setup(self, path_to_conf_file, parsed_sensors, data_to_record, record_frequency, display, record_folder):
        self.track = autonomous_agent.Track.SENSORS
        self.config_path = path_to_conf_file
        self.base_agent_step = -1
        self.wall_start = time.time()
        self.initialized = False
        self.sensor = parsed_sensors
        self.data_to_record = data_to_record
        self.record_frequency = record_frequency
        self.display = display
        self._sensor_data = {
            'width': 800,
            'height': 600,
            'fov': 100
        }
        self.displayed_views = []
        self._3d_bb_distance = 50
        self.weather_id = None
        for sensor in self.sensor:
            if "rgb" in sensor['name']:
                self.displayed_views.append(sensor['name'])

        self.save_path = None
        if len(self.data_to_record) != 0:
            now = datetime.datetime.now()
            string = pathlib.Path(os.environ['ROUTES']).stem + '_'
            string += '_'.join(map(lambda x: '%02d' % x, (now.month, now.day, now.hour, now.minute, now.second)))

            #self.save_path = pathlib.Path(os.environ['SAVE_PATH']) / string
            self.save_path = pathlib.Path(record_folder)
            #self.save_path.mkdir(parents=True, exist_ok=False)

            for sensor_name in self.data_to_record:
                (self.save_path / sensor_name).mkdir(parents=True, exist_ok=True)

    def sensors(self):

        return self.sensor

    def save(self, input_data):
        self.tick_data, self.view_data = self.tick_recorded_data(input_data)
        if self.base_agent_step % self.record_frequency == 0:
            frame = self.base_agent_step // self.record_frequency
            for recorded_sensor_name in self.data_to_record:
                if ("rgb" or "segmentation") in recorded_sensor_name:
                    Image.fromarray(self.tick_data[recorded_sensor_name]).save(self.save_path / recorded_sensor_name / ('%04d.png' % frame))
                else:
                    np.save(self.save_path / recorded_sensor_name / ('%04d.npy' % frame), self.tick_data[recorded_sensor_name], allow_pickle=True)

    def tick_recorded_data(self, input_data):
        self.base_agent_step += 1
        result = {}
        view_data = {}
        for recorded_sensor in self.data_to_record:
            for sensor in self.sensor:
                if sensor['name'] == recorded_sensor:
                    if "rgb" in sensor['name']:
                        result[sensor['name']] = cv2.cvtColor(input_data[sensor['id']][1][:, :, :3], cv2.COLOR_BGR2RGB)
                    elif "radar" in sensor['name']:
                        result[sensor['name']] = cv2.cvtColor(input_data[sensor['id']][1][:, :, :3], cv2.COLOR_BGR2RGB)
                    elif "lidar" in sensor['name']:
                        result[sensor['name']] = input_data[sensor['id']][1]
                    elif "imu" in sensor['name']:
                        result[sensor['name']] = input_data[sensor['id']][1][-1]
                    elif "gnss" in sensor['name']:
                        result[sensor['name']] = input_data[sensor['id']][1][:2]
                    elif "speed" in sensor['name']:
                        result[sensor['name']] = input_data[sensor['id']][1]['speed']
                    elif "segmentation_camera" in sensor['name']:
                        result[sensor['name']] = input_data[sensor['id']][1][:, :, 2]
        for sensor in self.sensor:
            if "rgb" in sensor['name']:
                view_data[sensor['name']] = cv2.cvtColor(input_data[sensor['id']][1][:, :, :3], cv2.COLOR_BGR2RGB)

        return result, view_data

    def display_view(self):

        if len(self.view_data) == 0:
            print("Unable to display the view, no rgb camera available")
        else:

            #rgb = Image.fromarray(self.tick_data['rgb_camera_center'])

            #_draw_rgb = ImageDraw.Draw(rgb)
            rgb_tick_data_list = []
            for rgb_sensor in self.view_data.keys():
                #print(rgb_sensor)
                rgb_tick_data_list.append(self.view_data[rgb_sensor])
            _combined = Image.fromarray(np.hstack(rgb_tick_data_list))
            #_combined = Image.fromarray(np.hstack([self.tick_data['rgb_camera_left'], rgb, self.tick_data['rgb_camera_right']]))
            _draw = ImageDraw.Draw(_combined)
            cv2.imshow('map', cv2.cvtColor(np.array(_combined), cv2.COLOR_BGR2RGB))
            cv2.waitKey(1)
