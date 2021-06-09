# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Import XOSC
"""
import os
import math
from qgis.PyQt import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from qgis.utils import iface
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsFeature, QgsPointXY, QgsGeometry

from defusedxml import ElementTree as etree
# import xml.etree.ElementTree as etree

from .helper_functions import HelperFunctions

import ad_map_access as ad

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_xosc_dialog.ui'))

class ImportXOSCDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Dialog class for importing OpenSCENARIO XML files.
    """
    def __init__(self, parent=None):
        """Initialization of ExportXMLDialog"""
        super(ImportXOSCDialog, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.import_path_button.pressed.connect(self.select_input)

    def select_input(self):
        """Prompts user to select file to import"""
        filename, _filter = QFileDialog.getOpenFileName(
            self,
            caption="Select OpenSCENARIO file to import",
            filter="OpenSCENARIO (*.xosc)")
        # Update text field only if user press 'OK'
        if filename:
            self.import_path.setText(filename)

    def open_file(self):
        """Opens OpenSCENARIO file and start parsing into QGIS layers"""
        if self.import_path.text() is not "":
            filepath = self.import_path.text()
            read_xosc = ImportXOSC(filepath)
            read_xosc.import_xosc()
        else:
            message = "No file path was given for importing"
            HelperFunctions().display_message(message, level="Critical")


class ImportXOSC():
    def __init__(self, filepath):
        self._filepath = filepath
        self._invert_y = False

    def import_xosc(self):
        tree = etree.parse(self._filepath)
        self._root = tree.getroot()

        self.parse_osc_metadata()

        if self._root.findall(".//EnvironmentAction"):
            env_node = self._root.findall(".//EnvironmentAction")[0]
            self.parse_enviroment_actions(env_node)
        
        if self._root.findall(".//Entities"):
            entity_node = self._root.findall(".//Entities")[0]
            self.parse_entities(entity_node)

    def parse_osc_metadata(self):
        """
        Parses OpenSCENARIO Metadata (File Headers, Road Network, Scene Graph File)
        """
        file_header_node = self._root.findall(".//FileHeader")[0]
        rev_major = file_header_node.attrib.get("revMajor")
        rev_minor = file_header_node.attrib.get("revMinor")
        description = file_header_node.attrib.get("description")
        if description[:6] == "CARLA:":
            self._invert_y = True
            description = description[6:]
        author = file_header_node.attrib.get("author")

        logic_file = self._root.findall(".//RoadNetwork/LogicFile")[0]
        road_network_filepath = logic_file.attrib.get("filepath")
        scene_graph_file = self._root.findall(".//RoadNetwork/SceneGraphFile")[0]
        scene_graph_filepath = scene_graph_file.attrib.get("filepath")

        if not QgsProject.instance().mapLayersByName("Metadata"):
            HelperFunctions().layer_setup_metadata()
        
        metadata_layer = QgsProject.instance().mapLayersByName("Metadata")[0]
        current_features = [feat.id() for feat in metadata_layer.getFeatures()]
        metadata_layer.dataProvider().deleteFeatures(current_features)

        feature = QgsFeature()
        feature.setAttributes([
            int(rev_major),
            int(rev_minor),
            description,
            author,
            road_network_filepath,
            scene_graph_filepath
        ])
        metadata_layer.dataProvider().addFeature(feature)


    def parse_enviroment_actions(self, env_node):        
        """
        Parses environment information and saves into QGIS layer

        Args:
            env_node (XML element)
        """
        environment = env_node.findall("Environment")
        for element in environment:
            time_of_day = element.find("TimeOfDay")
            weather = element.find("Weather")
            sun = weather.find("Sun")
            fog = weather.find("Fog")
            precipitation = weather.find("Precipitation")
            road_condition = element.find("RoadCondition")

        datetime = time_of_day.attrib.get("dateTime")
        datatime_animation = time_of_day.attrib.get("animation")
        
        cloud = weather.attrib.get("cloudState")
        fog_range = fog.attrib.get("visualRange")
        sun_azimuth = sun.attrib.get("azimuth")
        sun_elevation = sun.attrib.get("elevation")
        sun_intensity = sun.attrib.get("intensity")
        precip_intensity = precipitation.attrib.get("intensity")
        precip_type = precipitation.attrib.get("precipitationType")
        friction_scale_factor = road_condition.attrib.get("frictionScaleFactor")

        if not QgsProject.instance().mapLayersByName("Environment"):
            HelperFunctions().layer_setup_environment()

        env_layer = QgsProject.instance().mapLayersByName("Environment")[0]
        current_features = [feat.id() for feat in env_layer.getFeatures()]
        env_layer.dataProvider().deleteFeatures(current_features)

        feature = QgsFeature()
        feature.setAttributes([datetime, datatime_animation,
                               cloud, fog_range,
                               sun_intensity, sun_azimuth, sun_elevation,
                               precip_type, precip_intensity])
        env_layer.dataProvider().addFeature(feature)

    def parse_entities(self, entity_node):
        """
        Parses entity information and saves into QGIS layers

        Args:
            entity_node (XML element): Node that contains the entity
        """
        parent_map = {c: p for p in entity_node.iter() for c in p}
        print(parent_map)
        for scenario_object in entity_node.iter("ScenarioObject"):
            for pedestrian in scenario_object.iter("Pedestrian"):
                print("Trying out mapping...")
                parent = parent_map[pedestrian]
                print("Got the parent! -->", parent.tag, parent.attrib)
                actor_name = parent.attrib.get("name")

                self.parse_pedestrian(pedestrian, actor_name)
            
            for vehicle in scenario_object.iter("Vehicle"):
                print("Trying out mapping...")
                parent = parent_map[vehicle]
                print("Got the parent! -->", parent.tag, parent.attrib)
                actor_name = parent.attrib.get("name")

                self.parse_vehicle(vehicle, actor_name)

            for props in scenario_object.iter("MiscObject"):
                print("Trying out mapping...")
                parent = parent_map[props]
                print("Got the parent! -->", parent.tag, parent.attrib)
                actor_name = parent.attrib.get("name")

                self.parse_prop(props, actor_name)
        
    def parse_pedestrian(self, pedestrian, actor_name):
        """
        Extracts information for pedestrian and inserts into QGIS layer 

        Args:
            pedestrian (XML element)
            actor_name (string): actor name to match in Init and get positions
        """
        # Query to get Init elements of same actor
        query = f".//Private[@entityRef='{actor_name}']"
        found_init = self._root.find(query)

        world_pos = found_init.find(".//WorldPosition")
        world_pos_x = world_pos.attrib.get("x")
        world_pos_y = world_pos.attrib.get("y")
        world_pos_z = world_pos.attrib.get("z")
        world_pos_heading = world_pos.attrib.get("h")
        
        init_speed_tag = found_init.find(".//AbsoluteTargetSpeed")
        if init_speed_tag is not None:
            init_speed = init_speed_tag.attrib.get("value")
            # Parse in declared parameter (remove the $)
            if not HelperFunctions().is_float(init_speed):
                init_speed = init_speed[1:]
        else:
            init_speed = 0
        
        model = pedestrian.attrib.get("model")

        if self._invert_y:
            world_pos_y = -float(world_pos_y)

        polygon_points = self.get_polygon_points(
            world_pos_x, world_pos_y, world_pos_heading, "Pedestrian")

        walker_layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
        entity_id = self.get_entity_id(walker_layer)
        
        feature = QgsFeature()
        feature.setAttributes([entity_id,
                               model,
                               world_pos_heading,
                               world_pos_x,
                               world_pos_y,
                               world_pos_z,
                               init_speed])
        feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
        walker_layer.dataProvider().addFeature(feature)
    
    def parse_vehicle(self, vehicle, actor_name):
        """
        Extracts information for vehicle and inserts into QGIS layer 

        Args:
            vehicle (XML element)
            actor_name (string): actor name to match in Init and get positions
        """
        # Query to get Init elements of same actor
        query = f".//Private[@entityRef='{actor_name}']"
        found_init = self._root.find(query)

        world_pos = found_init.find(".//WorldPosition")
        world_pos_x = world_pos.attrib.get("x")
        world_pos_y = world_pos.attrib.get("y")
        world_pos_z = world_pos.attrib.get("z")
        world_pos_heading = world_pos.attrib.get("h")
        
        init_speed_tag = found_init.find(".//AbsoluteTargetSpeed")
        if init_speed_tag is not None:
            init_speed = init_speed_tag.attrib.get("value")
            # Parse in declared parameter (remove the $)
            if not HelperFunctions().is_float(init_speed):
                init_speed = init_speed[1:]
        else:
            init_speed = 0

        vehicle_controller_tag = found_init.find(".//AssignControllerAction")
        if vehicle_controller_tag is not None:
            agent_tag = vehicle_controller_tag.find(".//Property")
            agent = agent_tag.attrib.get("value")
            if agent == "simple_vehicle_control":
                agent_tag = vehicle_controller_tag.find(".//Property[@name='attach_camera']")
                agent_camera = agent_tag.attrib.get("value")
                agent_camera = True if agent_camera == "true" else False
            else:
                agent_camera = False
        else:
            agent = "simple_vehicle_control"
            message = (f"No vehicle controller agent defined for {actor_name}, using "
                "'simple_vehicle_control'")
            self._warning_message.append(message)
            HelperFunctions().display_message(message)

        model = vehicle.attrib.get("name")

        if self._invert_y:
            world_pos_y = -float(world_pos_y)

        polygon_points = self.get_polygon_points(
            world_pos_x, world_pos_y, world_pos_heading, "Vehicle")

        vehicle_layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
        entity_id = self.get_entity_id(vehicle_layer)
        
        feature = QgsFeature()
        feature.setAttributes([entity_id,
                               model,
                               world_pos_heading,
                               world_pos_x,
                               world_pos_y,
                               world_pos_z,
                               init_speed,
                               agent,
                               agent_camera])
        feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
        vehicle_layer.dataProvider().addFeature(feature)
    
    def parse_prop(self, prop, actor_name):
        """
        Extracts information for static objects and inserts into QGIS layer 

        Args:
            prop (XML element)
            actor_name (string): actor name to match in Init and get positions
        """
        # Query to get Init elements of same actor
        query = f".//Private[@entityRef='{actor_name}']"
        found_init = self._root.find(query)

        world_pos = found_init.find(".//WorldPosition")
        world_pos_x = world_pos.attrib.get("x")
        world_pos_y = world_pos.attrib.get("y")
        world_pos_z = world_pos.attrib.get("z")
        world_pos_heading = world_pos.attrib.get("h")
        
        model = prop.attrib.get("name")
        model_type = prop.attrib.get("miscObjectCategory")
        mass = prop.attrib.get("mass")

        if self._invert_y:
            world_pos_y = -float(world_pos_y)

        physics = False
        for prop_property in prop.iter("Property"):
            physics = prop_property.attrib.get("value")
            if physics == "on":
                physics = True
            else:
                physics = False

        polygon_points = self.get_polygon_points(
            world_pos_x, world_pos_y, world_pos_heading, "Prop")

        props_layer = QgsProject.instance().mapLayersByName("Static Objects")[0]
        entity_id = self.get_entity_id(props_layer)
        
        feature = QgsFeature()
        feature.setAttributes([entity_id,
                               model,
                               model_type,
                               world_pos_heading,
                               mass,
                               world_pos_x,
                               world_pos_y,
                               world_pos_z,
                               physics])
        feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
        props_layer.dataProvider().addFeature(feature)

    def get_entity_id(self, layer):
        """
        Gets the largest entity ID from the layer.
        If there are none, generates a new one.

        Args:
            layer (QGIS layer): Layer to get entity ID from

        Returns:
            [int]: Entity ID
        """
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largest_id = layer.maximumValue(idx)
            entity_id = largest_id + 1
        else:
            entity_id = 1
        
        return entity_id

    def get_polygon_points(self, pos_x, pos_y, angle, entity_type):

        angle = float(angle)
        pos_x = float(pos_x)
        pos_y = float(pos_y)

        if entity_type == "Pedestrian" or entity_type == "Vehicle":
            if entity_type == "Pedestrian":
                poly_edge_center = 0.4
                poly_edge_hor = 0.3
                poly_edge_ver = 0.35
            
            if entity_type == "Vehicle":
                poly_edge_center = 2.5
                poly_edge_hor = 2
                poly_edge_ver = 1
            
            bot_left_x = pos_x + (-poly_edge_hor * math.cos(angle) - poly_edge_ver * math.sin(angle))
            bot_left_y = pos_y + (-poly_edge_hor * math.sin(angle) + poly_edge_ver * math.cos(angle))
            bot_right_x = pos_x + (-poly_edge_hor * math.cos(angle) + poly_edge_ver * math.sin(angle))
            bot_right_y = pos_y + (-poly_edge_hor * math.sin(angle) - poly_edge_ver * math.cos(angle))
            top_left_x = pos_x + (poly_edge_hor * math.cos(angle) - poly_edge_ver * math.sin(angle))
            top_left_y = pos_y + (poly_edge_hor * math.sin(angle) + poly_edge_ver * math.cos(angle))
            top_center_x = pos_x + poly_edge_center * math.cos(angle)
            top_center_y = pos_y + poly_edge_center * math.sin(angle)
            top_right_x = pos_x + (poly_edge_hor * math.cos(angle) + poly_edge_ver * math.sin(angle))
            top_right_y = pos_y + (poly_edge_hor * math.sin(angle) - poly_edge_ver * math.cos(angle))

            # Create ENU points for polygon
            bot_left = ad.map.point.createENUPoint(x=bot_left_x, y=bot_left_y, z=0)
            bot_right = ad.map.point.createENUPoint(x=bot_right_x, y=bot_right_y, z=0)
            top_left = ad.map.point.createENUPoint(x=top_left_x, y=top_left_y, z=0)
            top_center = ad.map.point.createENUPoint(x=top_center_x, y=top_center_y, z=0)
            top_right = ad.map.point.createENUPoint(x=top_right_x, y=top_right_y, z=0)

            # Convert back to Geo points
            bot_left = ad.map.point.toGeo(bot_left)
            bot_right = ad.map.point.toGeo(bot_right)
            top_left = ad.map.point.toGeo(top_left)
            top_center = ad.map.point.toGeo(top_center)
            top_right = ad.map.point.toGeo(top_right)

            # Create polygon
            polygon_points = [QgsPointXY(bot_left.longitude, bot_left.latitude),
                              QgsPointXY(bot_right.longitude, bot_right.latitude),
                              QgsPointXY(top_right.longitude, top_right.latitude),
                              QgsPointXY(top_center.longitude, top_center.latitude),
                              QgsPointXY(top_left.longitude, top_left.latitude)]

            return polygon_points
        
        elif entity_type == "Prop":
            bot_left_x = pos_x + (-0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            bot_left_y = pos_y + (-0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            bot_right_x = pos_x + (-0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            bot_right_y =  pos_y + (-0.5 * math.sin(angle) - 0.5 * math.cos(angle))
            top_left_x = pos_x + (0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            top_left_y = pos_y + (0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            top_right_x = pos_x + (0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            top_right_y = pos_y + (0.5 * math.sin(angle) - 0.5 * math.cos(angle))

            # Create ENU points for polygon
            bot_left = ad.map.point.createENUPoint(x=bot_left_x, y=bot_left_y, z=0)
            bot_right = ad.map.point.createENUPoint(x=bot_right_x, y=bot_right_y, z=0)
            top_left = ad.map.point.createENUPoint(x=top_left_x, y=top_left_y, z=0)
            top_right = ad.map.point.createENUPoint(x=top_right_x, y=top_right_y, z=0)

            # Convert back to Geo points
            bot_left = ad.map.point.toGeo(bot_left)
            bot_right = ad.map.point.toGeo(bot_right)
            top_left = ad.map.point.toGeo(top_left)
            top_right = ad.map.point.toGeo(top_right)

            # Create polygon
            polygon_points = [QgsPointXY(bot_left.longitude, bot_left.latitude),
                              QgsPointXY(bot_right.longitude, bot_right.latitude),
                              QgsPointXY(top_right.longitude, top_right.latitude),
                              QgsPointXY(top_left.longitude, top_left.latitude)]

            return polygon_points
