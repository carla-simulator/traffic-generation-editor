# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

'''
Carla_connect - map update
'''

import glob
import os.path
import os
import sys
import numpy as np
import carla
# pylint: disable=no-name-in-module, import-error
from qgis.utils import iface
from qgis.core import Qgis
import ad_map_access as ad
from ad_map_access_qgis import ADMapQgs, Globs

try:
    sys.path.append(glob.glob('**/carla-*%d.%d-%s.egg' % (
        sys.version_info.major,
        sys.version_info.minor,
        'win-amd64' if os.name == 'nt' else 'linux-x86_64'))[0])
except IndexError:
    pass


class MapUpdate():
    '''
    Class to read, load, change map from carla.
    '''

    def __init__(self, host='localhost', port=2000):
        '''
        Connects to carla running in background.
        '''
        try:
            self.carla_client = carla.Client(host, port)
            if host == 'localhost':
                self.carla_client.set_timeout(5.0)
            else:
                self.carla_client.set_timeout(15.0)
        except RuntimeError as error:
            print('RuntimeError: {}'.format(error))
            print(' Could not connect to carla instint.')
            print(' Make sure the Carla 0.9.10 or greater is running.')
        self.iface = iface
        self.current_map = None
        self.open_drive_map = None
        self.admap = None
        self.world = None
        self.init_map_succeeded = False
        self.available_map = []

    def get_available_map(self):
        '''
        Gets all available maps in carla.
        returns: carla world
        '''
        self.available_map = self.carla_client.get_available_maps()
        return self.available_map

    def get_world(self):
        '''
        Method to get carla world.
        Returns :world
        '''
        world = self.carla_client.get_world()
        return world

    def change_map(self, currenttown):
        '''
        menthod to change map in qgis.
        '''
        self.carla_client.load_world(currenttown)

    def read_map(self):
        '''
        Method to read the map and stores it in ROOT_DIRECTORY
        '''
        self.world = self.carla_client.get_world()
        self.current_map = self.world.get_map()
        self.open_drive_map = self.current_map.to_opendrive()
        self.iface.messageBar().pushMessage("Info", "Map stored ", level=Qgis.Info)
        actor_list = self.world.get_actors()
        for actor in actor_list.filter('sensor.camera.rgb'):
            print("Spawned_Camera " + str(actor.get_location()))

    def map_init(self):
        '''
        Method that reads map from ROOT_DIRECTORY and update on qgis.
        '''
        xodr_path = '/tmp/tempfile.xodr'    # nosec
        file_name = (xodr_path)
        self.init_map_succeeded = False
        open_drive_content = self.open_drive_map
        self.init_map_succeeded = ad.map.access.initFromOpenDriveContent(
            open_drive_content, 0.2, ad.map.intersection.IntersectionType.Unknown,
            ad.map.landmark.TrafficLightType.UNKNOWN)
        if self.init_map_succeeded and not ad.map.access.isENUReferencePointSet():
            ad.map.access.setENUReferencePoint(ad.map.point.createGeoPoint(ad.map.point.Longitude(8.4421163),
                                                                           ad.map.point.Latitude(49.0192671),
                                                                           ad.map.point.Altitude(0.)))
            Globs.log.warning("OpenDrive file '{}' doesn't provide GEO reference point. Setting a default at {}".format(
                file_name, ad.map.access.getENUReferencePoint()))

    def map_update(self):
        '''
        Method to update map, layers in Qgis.
        '''
        self.admap = ADMapQgs()
        self.admap.layers.create_all()
        self.admap.data_added()

    def map_unload(self):
        '''
        Method to unload loaded map from QGIS.
        '''
        self.admap = ADMapQgs()
        ad.map.access.cleanup()
        self.admap.layers.remove_all()
        self.admap = None


class CameraSetup():
    '''
    Class to setup camera.
    argv:
    world: carla world
    camposx: x coordinate where the camera has to be placed
    camposy: y coordinate where the camera has to be placed
    sensor_defination_file-path: the path of file infrastrcutre which contanins attributes of camera.
    '''

    def __init__(self, world, camposx, camposy, height):
        '''
        initialize the variables.
        '''
        self.world = world
        self.sensors = None
        self.camera_position_x = camposx
        self.camera_position_y = camposy
        self.height = height

    def spawn(self):
        '''
        Method to initiate the spawn process
        '''
        self.sensors = self.setup_sensors()
        return self.sensors

    def sensor_list(self):
        '''
        method that returns list of sensors
        '''
        return self.sensors

    def setup_sensors(self):
        '''
        Method to read camera attributes from infrastructure.json file
        argv:
        sensor_definition: path to the infrastructure.json file
        return:
        actors: returns carla actor ie camera.
        '''
        actors = []
        bp_library = self.world.get_blueprint_library()
        calibration = None
        try:
            bp = bp_library.find("sensor.camera.rgb")   # pylint: disable=invalid-name
            bp.set_attribute('role_name', str("CAM_TOP"))
            bp.set_attribute('image_size_x', str(1600))
            bp.set_attribute('image_size_y', str(1600))
            bp.set_attribute('fov', str(100))
            sensor_location = carla.Location(x=float(self.camera_position_x), y=abs((float(self.camera_position_y))),
                                             z=float(self.height))
            sensor_rotation = carla.Rotation(pitch=-90, roll=0, yaw=0)
            calibration = np.identity(3)
            calibration[0, 2] = 1600 / 2.0
            calibration[1, 2] = 1600 / 2.0
            calibration[0, 0] = calibration[1, 1] = 1600 / (2.0 * np.tan(0.5 * np.radians(100)))
        except KeyError as e:   # pylint: disable=invalid-name
            print("Sensor will not be spawned, because sensor spec is invalid: '{}'".format(e))

        sensor_transform = carla.Transform(sensor_location, sensor_rotation)
        sensor = self.world.spawn_actor(bp, sensor_transform)
        actor_list = self.world.get_actors()
        print("Camera Added at height " + str(self.height) + "meters")
        for actor in actor_list.filter('sensor.camera.rgb'):
            print("Camera " + str(actor.get_location()))
        if calibration is not None:
            sensor.calibration = calibration
        actors.append(sensor)
        return actors
