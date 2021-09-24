# -*- coding: utf-8 -*-
# Copyright (c) 2019-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
'''
Carla_Connect - Add Camera
'''
import math
import os
import os.path
import sys
import numpy as np
import pygame
# pylint: disable=no-name-in-module
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.PyQt import QtWidgets, uic
from qgis.gui import QgsMapTool
from qgis.core import (Qgis, QgsFeature, QgsField, QgsGeometry,
                       QgsMessageLog, QgsPointXY, QgsProject,
                       QgsVectorLayer, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
import ad_map_access as ad
from .mapupdate import MapUpdate    # pylint: disable=import-error
from .mapupdate import CameraSetup  # pylint: disable=import-error

if not hasattr(sys, 'argv'):
    sys.argv = ['']

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'camera.ui'))


class CameraDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    '''class for Qtwidget of camera placement'''
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None, host='localhost', port=2000):
        self.camera_layer = None
        super(CameraDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.height = None
        self.selected_height = None
        self.world = MapUpdate(host, port).get_world()
        self.auto_cam_placement = AutoCamera(self.world)
        self.AddCameraposition.pressed.connect(self._insert_camera)
        self.AddCamerabutton.pressed.connect(self.auto_cam_placement.auto_camera_placement)
        self.cameraheight.currentTextChanged.connect(self._camera_height)
        self._camera_layer_setup()

    def _camera_layer_setup(self):
        """
        Sets up layer for camera
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        root_layer.addGroup("Camera")
        osc_layer = root_layer.findGroup("Camera")
        if not QgsProject.instance().mapLayersByName("camera"):
            camera_layer = QgsVectorLayer("Polygon", "camera", "memory")
            QgsProject.instance().addMapLayer(camera_layer, False)
            osc_layer.addLayer(camera_layer)
            dataattributes = [QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double)]
            data_input = camera_layer.dataProvider()
            data_input.addAttributes(dataattributes)
            camera_layer.updateFields()
            labelsettings = QgsPalLayerSettings()
            labelsettings.isExpression = True
            labelsettings.fieldName = "camera"
            camera_layer.setLabeling(QgsVectorLayerSimpleLabeling(labelsettings))
            camera_layer.setLabelsEnabled(True)
            iface.messageBar().pushMessage("Info", "camera layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("camera layer added", level=Qgis.Info)
        self.camera_layer = QgsProject.instance().mapLayersByName("camera")[0]

    def _camera_height(self):
        self.selected_height = self.cameraheight.currentText()
        self.height = self.selected_height[:2]

    def _insert_camera(self):
        '''
        Method to setup Canvas and display layer information
        '''
        self.camera_layer = QgsProject.instance().mapLayersByName("camera")[0]
        iface.setActiveLayer(self.camera_layer)
        iface.messageBar().pushMessage("Info", "Using existing camera layer", level=Qgis.Info)
        QgsMessageLog.logMessage("Using existing vehicle layer", level=Qgis.Info)
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()
        tool = PointTool(canvas, layer, self.height, self.world)
        canvas.setMapTool(tool)


class PointTool(QgsMapTool):
    '''
    class that provides position of the click(placement of the camera)
    argv:
    canvas: iface map canvas.
    layers: iface current layer.
    '''

    def __init__(self, canvas, layer, height, world):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.height = height
        self.world = world
        self.spawn_cam = None
        self.data_input = layer.dataProvider()
        self.canvas.setCursor(Qt.CrossCursor)

    def canvasReleaseEvent(self, event):    # pylint: disable=invalid-name
        '''
        method to dertermine camera positon for manual camera placement
        '''
        xcoordinate = event.pos().x()
        ycoordinate = event.pos().y()
        point = self.canvas.getCoordinateTransform().toMapCoordinates(xcoordinate, ycoordinate)
        # Converting to ENU points
        geopoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=0)
        enupoint = ad.map.point.toENU(geopoint)
        squarepoint = self._spawn_marker(enupoint)
        feature = QgsFeature()
        feature.setAttributes([float(enupoint.x), float(enupoint.y)])
        feature.setGeometry(QgsGeometry.fromPolygonXY([squarepoint]))
        # Call function spawn_camera which spawn camera at provided location
        self.spawn_cam = Spawn(self.world)
        if self.height is None:
            self.height = 10
        self.spawn_cam.spawn_camera(enupoint.x, enupoint.y, self.height)
        self.layer.dataProvider().addFeature(feature)
        self.layer.updateExtents()
        self.canvas.refreshAllLayers()
        self.canvas.unsetMapTool(self)

    def _spawn_marker(self, enupoint):
        '''
        Method to calculated the makers points
        argv:
        enupoints: Center of the camera maker
        return:
        points to spawn square marker
        '''
        camera_orientation = 90
        angle = math.radians(camera_orientation)

        botleftx = float(enupoint.x) + (-2 * math.cos(angle) - 1 * math.sin(angle))
        botlefty = float(enupoint.y) + (-2 * math.sin(angle) + 1 * math.cos(angle))
        botrightx = float(enupoint.x) + (-2 * math.cos(angle) + 1 * math.sin(angle))
        botrighty = float(enupoint.y) + (-2 * math.sin(angle) - 1 * math.cos(angle))
        topleftx = float(enupoint.x) + (1 * math.cos(angle) - 1 * math.sin(angle))
        toplefty = float(enupoint.y) + (1 * math.sin(angle) + 1 * math.cos(angle))
        topcenterx = float(enupoint.x) + 1 * math.cos(angle)
        topcentery = float(enupoint.y) + 1 * math.sin(angle)
        toprightx = float(enupoint.x) + (1 * math.cos(angle) + 1 * math.sin(angle))
        toprighty = float(enupoint.y) + (1 * math.sin(angle) - 1 * math.cos(angle))

        botleft = ad.map.point.createENUPoint(x=botleftx, y=botlefty, z=0)
        botright = ad.map.point.createENUPoint(x=botrightx, y=botrighty, z=0)
        topleft = ad.map.point.createENUPoint(x=topleftx, y=toplefty, z=0)
        topcenter = ad.map.point.createENUPoint(x=topcenterx, y=topcentery, z=0)
        topright = ad.map.point.createENUPoint(x=toprightx, y=toprighty, z=0)

        botleft = ad.map.point.toGeo(botleft)
        botright = ad.map.point.toGeo(botright)
        topleft = ad.map.point.toGeo(topleft)
        topcenter = ad.map.point.toGeo(topcenter)
        topright = ad.map.point.toGeo(topright)

        squarepoints = [QgsPointXY(botleft.longitude, botleft.latitude),
                        QgsPointXY(botright.longitude, botright.latitude),
                        QgsPointXY(topright.longitude, topright.latitude),
                        QgsPointXY(topcenter.longitude, topcenter.latitude),
                        QgsPointXY(topleft.longitude, topleft.latitude)]
        return squarepoints


class AutoCamera():
    """
    Class to automatically spawn and place an observer camera
    """

    def __init__(self, world):
        '''
        Initilize the variable.
        '''
        self.actors_x_position = np.array([])
        self.actors_y_position = np.array([])
        self.world = world

    def auto_camera_placement(self):
        '''
        Function to find the position where camera has to spawnned automatically.
        '''
        if (QgsProject.instance().mapLayersByName("Vehicles - Ego") or
                QgsProject.instance().mapLayersByName("Vehicles") or
                QgsProject.instance().mapLayersByName("Pedestrians")):
            if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
                vehicleegolayer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
                for feature in vehicleegolayer.getFeatures():
                    ego_position_x = np.array(feature["Pos X"])
                    ego_position_y = np.array(feature["Pos Y"])
                    self.actors_x_position = np.append(self.actors_x_position, ego_position_x)
                    self.actors_y_position = np.append(self.actors_y_position, ego_position_y)

            if QgsProject.instance().mapLayersByName("Vehicles"):
                vehiclelayer = QgsProject.instance().mapLayersByName("Vehicles")[0]
                for feature in vehiclelayer.getFeatures():
                    vehicle_position_x = np.array(feature["Pos X"])
                    vehicle_position_y = np.array(feature["Pos Y"])
                    self.actors_x_position = np.append(self.actors_x_position, vehicle_position_x)
                    self.actors_y_position = np.append(self.actors_y_position, vehicle_position_y)

            if QgsProject.instance().mapLayersByName("Pedestrians"):
                vehiclelayer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
                for feature in vehiclelayer.getFeatures():
                    pedestrian_position_x = np.array(feature["Pos X"])
                    pedestrian_position_y = np.array(feature["Pos Y"])
                    self.actors_x_position = np.append(self.actors_x_position, pedestrian_position_x)
                    self.actors_y_position = np.append(self.actors_y_position, pedestrian_position_y)
            self.centroid(self.actors_x_position, self.actors_y_position)
        else:
            errormessage = "No Actors detected: Insert actors to use Auto camera placement"
            iface.messageBar().pushMessage("Error", errormessage, level=Qgis.Critical)
            QgsMessageLog.logMessage(errormessage, level=Qgis.Critical)

    def centroid(self, actorpositionx, actorpositiony):
        '''
        Method that finds centroid of vehicles to be spanwed
        argv:
        ActorposX: X coordinate of the camera
        ActorposY: y coordinate of the camera
        '''
        length = actorpositionx.shape[0]
        sum_x = np.sum(actorpositionx)
        sum_y = np.sum(actorpositiony)
        camera_position_x = sum_x / length
        camera_position_y = sum_y / length
        cameraposition = ad.map.point.createENUPoint(x=camera_position_x, y=camera_position_y, z=0)
        spawn_cam = Spawn(self.world)
        spawn_cam.spawn_camera(cameraposition.x, cameraposition.y, 50)


class Spawn():
    '''
    class to spawn camera at provided position
    argv:
    positionx : position of camera on x co-ordinate
    positiony : position of camera on y co-ordinate
    height = how high the camera has to be placed
    '''
    actor_list = []

    def __init__(self, world):
        '''
        initialize variable
        '''
        self.world = world

    def spawn_camera(self, positionx, positiony, height):
        '''
        Function to spawn camera
        '''
        cam = CameraSetup(self.world, positionx, positiony, height)
        actor = cam.spawn()
        Spawn.actor_list.append(actor)


class ImageProcessor():
    '''
    class to set up py_gam window and process image
    '''
    width = 1200
    height = 1200

    @staticmethod
    def py_game_setup():
        '''
        Function to read data from camera sensor
        '''
        camera_list = Spawn.actor_list
        for actors in camera_list:
            for sensor in actors:
                pygame.init()
                pygame.font.init()
                display = pygame.display.set_mode(
                    (ImageProcessor.width, ImageProcessor.height), pygame.HWSURFACE | pygame.DOUBLEBUF)
                sensor.listen(
                    lambda data: ImageProcessor.render(data, display))    # pylint: disable=cell-var-from-loop

    @staticmethod
    def render(image, display):
        '''
        Function to plot data in Pygame
        '''
        array = np.frombuffer(image.raw_data, dtype=np.dtype("uint8"))
        array = np.reshape(array, (image.height, image.width, 4))
        array = array[:, :, :3]
        array = array[:, :, ::-1]
        surface = pygame.surfarray.make_surface(array.swapaxes(0, 1))
        display.blit(surface, (0, 0))
        pygame.display.flip()

    @staticmethod
    def destroy_all_window():
        '''
        method to destroy camera and exit pygame
        '''
        camera_list = Spawn.actor_list
        for actors in camera_list:
            for sensor in actors:
                sensor.stop()

        pygame.display.quit()
        pygame.quit()
