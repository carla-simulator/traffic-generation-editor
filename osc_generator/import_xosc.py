# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Import XOSC
"""
from distutils.util import strtobool
import os
import math
import xmlschema
# pylint: disable=no-name-in-module, no-member
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from qgis.PyQt import QtWidgets, uic
from qgis.core import QgsProject, QgsFeature, QgsPointXY, QgsGeometry
from defusedxml import ElementTree as etree
import ad_map_access as ad
from .helper_functions import (layer_setup_environment, layer_setup_metadata, layer_setup_vehicle,
                               layer_setup_walker, layer_setup_props, layer_setup_end_eval,
                               layer_setup_maneuvers_and_triggers, layer_setup_maneuvers_lateral,
                               layer_setup_maneuvers_longitudinal, layer_setup_maneuvers_waypoint,
                               layer_setup_parameters, is_float, display_message, resolve,
                               set_metadata)

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
        if self.import_path.text() != "":
            filepath = self.import_path.text()
            schema_path = resolve("OpenSCENARIO_1_0_0.xsd")
            schema = xmlschema.XMLSchema(schema_path)
            if schema.is_valid(filepath):
                read_xosc = ImportXOSC(filepath)
                read_xosc.import_xosc()
            else:
                error_iterator = schema.iter_errors(filepath)
                err = []
                text = "XML validation failed with errors: \n\n"
                for idx, validation_error in enumerate(error_iterator, start=1):
                    err.append(f"[{idx}] {validation_error.reason} \n"
                               f"Path: {validation_error.path}"
                               f"\nMessage: {validation_error.message}")

                text += "\n\n".join(err)
                msg = QMessageBox()
                msg.setIcon(QMessageBox.Warning)
                msg.setText(text)
                msg.setWindowTitle("XML Validation Failed")
                msg.setStandardButtons(QMessageBox.Ok)
                msg.exec()

                message = f"File {filepath} did not pass XML validation!"
                display_message(message, level="Critical")
        else:
            message = "No file path was given for importing"
            display_message(message, level="Critical")


class ImportXOSC():
    """
    Class to import an existing OpenSCENARIO file
    """

    def __init__(self, filepath):
        self._filepath = filepath
        self._invert_y = False
        self._warning_message = []
        self._root = None

        self.setup_qgis_layers()

    def setup_qgis_layers(self):
        """
        Initiates layers in QGIS if they are not already created.
        """
        layer_setup_environment()
        layer_setup_metadata()
        layer_setup_vehicle()
        layer_setup_walker()
        layer_setup_props()
        layer_setup_end_eval()
        layer_setup_maneuvers_and_triggers()
        layer_setup_maneuvers_lateral()
        layer_setup_maneuvers_longitudinal()
        layer_setup_maneuvers_waypoint()
        layer_setup_parameters()

    def import_xosc(self):
        """
        Main import method
        """
        tree = etree.parse(self._filepath)
        self._root = tree.getroot()

        self.parse_osc_metadata()
        self.parse_paremeter_declarations()

        if self._root.findall(".//EnvironmentAction"):
            env_node = self._root.findall(".//EnvironmentAction")[0]
            self.parse_enviroment_actions(env_node)
        else:
            self._warning_message.append("No environment actions found")

        if self._root.findall(".//Entities"):
            entity_node = self._root.findall(".//Entities")[0]
            self.parse_entities(entity_node)
        else:
            self._warning_message.append("No entities found")

        if self._root.findall(".//Storyboard/StopTrigger/ConditionGroup"):
            end_eval_node = self._root.findall(".//Storyboard/StopTrigger")[0]
            self.parse_end_evals(end_eval_node)
        else:
            self._warning_message.append("No end evaluation KPIs found")

        if self._root.findall(".//Story"):
            story_node = self._root.findall(".//Story")[0]
            self.parse_maneuvers(story_node)
        else:
            self._warning_message.append("No maneuvers found")

        msg = QMessageBox()
        if self._warning_message:
            msg.setIcon(QMessageBox.Warning)
            text = f"Imported OpenSCENARIO file {self._filepath} has warnings!\n\n"
            text += "\n".join(self._warning_message)
        else:
            msg.setIcon(QMessageBox.Information)
            text = f"Successfully imported OpenSCENARIO file {self._filepath}"
        msg.setText(text)
        msg.setWindowTitle("OpenSCENARIO Import")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()

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

        set_metadata(rev_major=rev_major,
                     rev_minor=rev_minor,
                     description=description,
                     author=author,
                     road_network_filepath=road_network_filepath,
                     scene_graph_filepath=scene_graph_filepath)

    def parse_paremeter_declarations(self):
        """
        Parses parameter declarations
        """
        param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
        param_name = ""
        param_type = ""
        param_value = ""

        param_group_node = self._root.find(".//ParameterDeclarations")
        for param_node in param_group_node.iter("ParameterDeclaration"):
            param_name = param_node.attrib.get("name")
            param_type = param_node.attrib.get("type")
            param_value = param_node.attrib.get("value")

            feature = QgsFeature()
            feature.setAttributes([
                param_name,
                param_type,
                param_value
            ])
            param_layer.dataProvider().addFeature(feature)

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
        friction_scale_factor = road_condition.attrib.get("frictionScaleFactor")    # pylint: disable=unused-variable

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
        for scenario_object in entity_node.iter("ScenarioObject"):
            for pedestrian in scenario_object.iter("Pedestrian"):
                parent = parent_map[pedestrian]
                actor_name = parent.attrib.get("name")
                self.parse_pedestrian(pedestrian, actor_name)

            for vehicle in scenario_object.iter("Vehicle"):
                parent = parent_map[vehicle]
                actor_name = parent.attrib.get("name")
                self.parse_vehicle(vehicle, actor_name)

            for props in scenario_object.iter("MiscObject"):
                parent = parent_map[props]
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

        world_pos_x = 0
        world_pos_y = 0
        world_pos_z = 0
        world_pos_heading = 0
        world_pos = found_init.find(".//WorldPosition")
        if world_pos is not None:
            world_pos_x = world_pos.attrib.get("x")
            world_pos_y = world_pos.attrib.get("y")
            world_pos_z = world_pos.attrib.get("z")
            world_pos_heading = world_pos.attrib.get("h")
        else:
            message = (f"Non WorldPosition waypoints are not supported (Entity: {actor_name})"
                       "Defaulting to WorldPos 0, 0, 0")
            display_message(message, level="Info")
            self._warning_message.append(message)

        init_speed_tag = found_init.find(".//AbsoluteTargetSpeed")
        if init_speed_tag is not None:
            init_speed = init_speed_tag.attrib.get("value")
            # Parse in declared parameter (remove the $)
            if not is_float(init_speed):
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

        world_pos_x = 0
        world_pos_y = 0
        world_pos_z = 0
        world_pos_heading = 0
        world_pos = found_init.find(".//WorldPosition")
        if world_pos is not None:
            world_pos_x = world_pos.attrib.get("x")
            world_pos_y = world_pos.attrib.get("y")
            world_pos_z = world_pos.attrib.get("z")
            world_pos_heading = world_pos.attrib.get("h")
        else:
            message = (f"Non WorldPosition waypoints are not supported (Entity: {actor_name})"
                       "Defaulting to WorldPos 0, 0, 0")
            display_message(message, level="Info")
            self._warning_message.append(message)

        init_speed_tag = found_init.find(".//AbsoluteTargetSpeed")
        if init_speed_tag is not None:
            init_speed = init_speed_tag.attrib.get("value")
            # Parse in declared parameter (remove the $)
            if not is_float(init_speed):
                init_speed = init_speed[1:]
        else:
            init_speed = 0

        vehicle_controller_tag = found_init.find(".//AssignControllerAction")
        if vehicle_controller_tag is not None:
            agent_tag = vehicle_controller_tag.find(".//Property")
            agent = agent_tag.attrib.get("value")
            if agent == "simple_vehicle_control":
                agent_tag = vehicle_controller_tag.find(".//Property[@name='attach_camera']")
                agent_camera = strtobool(agent_tag.attrib.get("value").lower())
            else:
                agent_camera = False
        else:
            agent_camera = False
            agent = "simple_vehicle_control"
            message = (f"No vehicle controller agent defined for {actor_name}, using "
                       "'simple_vehicle_control'")
            self._warning_message.append(message)
            display_message(message, level="Warning")

        model = vehicle.attrib.get("name")

        if self._invert_y:
            world_pos_y = -float(world_pos_y)

        polygon_points = self.get_polygon_points(
            world_pos_x, world_pos_y, world_pos_heading, "Vehicle")

        vehicle_layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
        entity_id = self.get_entity_id(vehicle_layer)

        feature = QgsFeature()
        feature.setAttributes([
            entity_id,
            model,
            world_pos_heading,
            world_pos_x,
            world_pos_y,
            world_pos_z,
            init_speed,
            agent,
            agent_camera
        ])
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

        world_pos_x = 0
        world_pos_y = 0
        world_pos_z = 0
        world_pos_heading = 0
        world_pos = found_init.find(".//WorldPosition")
        if world_pos is not None:
            world_pos_x = world_pos.attrib.get("x")
            world_pos_y = world_pos.attrib.get("y")
            world_pos_z = world_pos.attrib.get("z")
            world_pos_heading = world_pos.attrib.get("h")
        else:
            message = (f"Non WorldPosition waypoints are not supported (Entity: {actor_name})"
                       "Defaulting to WorldPos 0, 0, 0")
            display_message(message, level="Info")
            self._warning_message.append(message)

        model = prop.attrib.get("name")
        model_type = prop.attrib.get("miscObjectCategory")
        mass = prop.attrib.get("mass")

        if self._invert_y:
            world_pos_y = -float(world_pos_y)

        physics = False
        for prop_property in prop.iter("Property"):
            physics = strtobool(prop_property.attrib.get("value").lower())

        polygon_points = self.get_polygon_points(
            world_pos_x, world_pos_y, world_pos_heading, "Prop")

        props_layer = QgsProject.instance().mapLayersByName("Static Objects")[0]
        entity_id = self.get_entity_id(props_layer)

        feature = QgsFeature()
        feature.setAttributes([
            entity_id,
            model,
            model_type,
            world_pos_heading,
            mass,
            world_pos_x,
            world_pos_y,
            world_pos_z,
            physics
        ])
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
        """
        Get entity box points
        """
        angle = float(angle)
        pos_x = float(pos_x)
        pos_y = float(pos_y)

        if entity_type in ["Pedestrian", "Vehicle"]:
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
            bot_right_y = pos_y + (-0.5 * math.sin(angle) - 0.5 * math.cos(angle))
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

        else:
            raise ValueError("Unknown entity_type")

    def parse_end_evals(self, end_eval_node):
        """
        Parses end evaluation KPI information and saves into QGIS layers

        Args:
            end_eval_node (XML element): Node that contains the end_evaluations
        """
        # Clear existing paramters
        end_eval_layer = QgsProject.instance().mapLayersByName("End Evaluation KPIs")[0]
        current_features = [feat.id() for feat in end_eval_layer.getFeatures()]
        end_eval_layer.dataProvider().deleteFeatures(current_features)

        for condition in end_eval_node.iter("Condition"):
            cond_name = condition.attrib.get("name")
            cond_edge = condition.attrib.get("conditionEdge")
            delay = condition.attrib.get("delay")

            param_condition = condition.find(".//ParameterCondition")
            param_ref = param_condition.attrib.get("parameterRef")
            value = param_condition.attrib.get("value")
            rule = param_condition.attrib.get("rule")

            if value == "":
                value = 0.

            feature = QgsFeature()
            feature.setAttributes([
                cond_name,
                float(delay),
                cond_edge,
                param_ref,
                float(value),
                rule
            ])

            end_eval_layer.dataProvider().addFeature(feature)

    def parse_maneuvers(self, story_node):
        """
        Parses maneuver information and saves into QGIS layers

        Args:
            story_node (XML element): Node that contains the maneuvers
        """
        maneuver_layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]

        for maneuver_group in story_node.iter("ManeuverGroup"):
            # Default values (so attributes can be saved into QGIS)
            # Will be changed based on what is parsed from OpenSCENARIO file
            # Irrelevant information will be handled during export
            man_id = self.get_entity_id(maneuver_layer)
            man_type = "Entity Maneuvers"
            entity = None
            entity_act_type = "Waypoint"
            global_act_type = "InfrastructureAction"
            infra_traffic_id = 0
            infra_traffic_state = "green"

            entity_node = maneuver_group.find(".//Actors/EntityRef")
            # For blank maneuvers / no maneuvers set
            if entity_node is None:
                message = ("Maneuver does not have an entity reference! "
                           "This maneuver will be skipped.")
                display_message(message, level="Info")
                self._warning_message.append(message)
                break
            entity = entity_node.attrib.get("entityRef")

            waypoint_act = maneuver_group.find(".//Maneuver/Event/Action/PrivateAction/RoutingAction")
            if waypoint_act is None:
                private_act_node = maneuver_group.find(".//Maneuver/Event/Action/PrivateAction")
                private_act_type_node = list(private_act_node.iter())[1]
                private_act_type = private_act_type_node.tag
                if private_act_type == "LongitudinalAction":
                    entity_act_type = "Longitudinal"
                    self.parse_maneuvers_longitudinal(private_act_type_node, man_id)
                elif private_act_type == "LateralAction":
                    entity_act_type = "Lateral"
                    self.parse_maneuvers_lateral(private_act_type_node, man_id)
            else:
                self.parse_waypoints(waypoint_act, man_id, entity)

            infra_act_node = maneuver_group.find(".//Maneuver/Event/Action/GlobalAction/InfrastructureAction")
            if infra_act_node is None:
                message = ("Infrastructure Action not found! "
                           "Import only supports infrastructure action currently.")
                display_message(message, level="Info")
                self._warning_message.append(message)
            else:
                man_type = "Global Actions"
                traffic_signal_node = infra_act_node.find(".//TrafficSignalAction/TrafficSignalStateAction")
                infra_traffic_id = traffic_signal_node.attrib.get("name")[3:]
                infra_traffic_state = traffic_signal_node.attrib.get("state")

            # Start Triggers (Default Values)
            start_trigger = "by Entity"
            start_entity_cond = "EndOfRoadCondition"
            start_entity_ref_entity = ""
            start_entity_duration = 0
            start_entity_value = 0
            start_entity_rule = "lessThan"
            start_entity_rel_dist_type = "cartesianDistance"
            start_entity_frespace = False
            start_entity_along_route = False
            start_value_cond = "ParameterCondition"
            start_value_param_ref = ""
            start_value_name = ""
            start_value_datetime = "2020-10-22T18:00:00"
            start_value_value = 0
            start_value_rule = "lessThan"
            start_value_state = ""
            start_value_storyboard_type = "story"
            start_value_storyboard_element = ""
            start_value_storyboard_state = "completeState"
            start_value_traffic_controller_ref = ""
            start_value_traffic_controller_phase = ""
            start_world_pos_tolerance = 0
            start_world_pos_x = 0
            start_world_pos_y = 0
            start_world_pos_z = 0
            start_world_pos_heading = 0

            start_trigger_node = maneuver_group.find(".//Maneuver/Event/StartTrigger")
            if start_trigger_node is not None:
                # Check Entity Condition, if not, check Value Condition
                condition_node = start_trigger_node.find(".//ConditionGroup/Condition/ByEntityCondition")
                if condition_node is not None:
                    start_trigger = "by Entity"
                    entity_ref_node = condition_node.find(".//TriggeringEntities/EntityRef")
                    start_entity_ref_entity = entity_ref_node.attrib.get("entityRef")

                    entity_cond_node = condition_node.find(".//EntityCondition")
                    entity_cond_node = list(entity_cond_node.iter())[1]
                    start_entity_cond = entity_cond_node.tag

                    if "duration" in entity_cond_node.attrib:
                        start_entity_duration = entity_cond_node.attrib.get("duration")

                    if "entityRef" in entity_cond_node.attrib:
                        start_entity_ref_entity = entity_cond_node.attrib.get("entityRef")

                    if "value" in entity_cond_node.attrib:
                        start_entity_value = entity_cond_node.attrib.get("value")

                    if "freespace" in entity_cond_node.attrib:
                        start_entity_frespace = strtobool(entity_cond_node.attrib.get("freespace").lower())

                    if "alongRoute" in entity_cond_node.attrib:
                        start_entity_along_route = strtobool(entity_cond_node.attrib.get("alongRoute").lower())

                    if "rule" in entity_cond_node.attrib:
                        start_entity_rule = entity_cond_node.attrib.get("rule")

                    if "tolerance" in entity_cond_node.attrib:
                        start_world_pos_tolerance = entity_cond_node.attrib.get("tolerance")
                        world_pos_node = entity_cond_node.find(".//Position/WorldPosition")

                        if world_pos_node is not None:
                            start_world_pos_x = float(world_pos_node.attrib.get("x"))
                            start_world_pos_y = float(world_pos_node.attrib.get("y"))
                            start_world_pos_z = float(world_pos_node.attrib.get("z"))
                            start_world_pos_heading = float(world_pos_node.attrib.get("h"))
                        else:
                            message = ("Non WorldPosition waypoints are not supported (Maneuver ID: "
                                       f"{str(man_id)} Entity: {entity}) Defaulting to WorldPos 0, 0, 0")
                            display_message(message, level="Info")
                            self._warning_message.append(message)

                else:
                    condition_node = start_trigger_node.find(".//ConditionGroup/Condition/ByValueCondition")
                    start_trigger = "by Value"
                    value_cond_node = list(condition_node.iter())[1]
                    start_value_cond = value_cond_node.tag

                    if "parameterRef" in value_cond_node.attrib:
                        start_value_param_ref = value_cond_node.attrib.get("parameterRef")

                    if "name" in value_cond_node.attrib:
                        start_value_name = value_cond_node.attrib.get("name")

                    if "value" in value_cond_node.attrib:
                        start_value_value = value_cond_node.attrib.get("value")

                    if "rule" in value_cond_node.attrib:
                        start_value_rule = value_cond_node.attrib.get("rule")

                    if "state" in value_cond_node.attrib:
                        start_value_state = value_cond_node.attrib.get("state")

                    if "storyboardElementType" in value_cond_node.attrib:
                        start_value_storyboard_type = value_cond_node.attrib.get("storyboardElementType")
                        start_value_storyboard_element = value_cond_node.attrib.get("storyboardElementRef")
                        start_value_storyboard_state = value_cond_node.attrib.get("state")

                    if "trafficSignalControllerRef" in value_cond_node.attrib:
                        start_value_traffic_controller_ref = value_cond_node.attrib.get("trafficSignalControllerRef")
                        start_value_traffic_controller_phase = value_cond_node.attrib.get("phase")

            # Stop Triggers (Default Values)
            stop_trigger_enabled = False
            stop_trigger = "by Entity"
            stop_entity_cond = "EndOfRoadCondition"
            stop_entity_ref_entity = ""
            stop_entity_duration = 0
            stop_entity_value = 0
            stop_entity_rule = "lessThan"
            stop_entity_rel_dist_type = "cartesianDistance"
            stop_entity_freespace = False
            stop_entity_along_route = False
            stop_value_cond = "ParameterCondition"
            stop_value_param_ref = ""
            stop_value_name = ""
            stop_value_datetime = "2020-10-22T18:00:00"
            stop_value_value = 0
            stop_value_rule = "lessThan"
            stop_value_state = ""
            stop_value_storyboard_type = "story"
            stop_value_storyboard_element = ""
            stop_value_storyboard_state = "completeState"
            stop_value_traffic_controller_ref = ""
            stop_value_traffic_controller_phase = ""
            stop_world_pos_tolerance = 0
            stop_world_pos_x = 0
            stop_world_pos_y = 0
            stop_world_pos_z = 0
            stop_world_pos_heading = 0

            stop_trigger_node = maneuver_group.find(".//Maneuver/Event/StopTrigger")
            if stop_trigger_node is not None:
                stop_trigger_enabled = True
                # Check Entity Condition, if not, check Value Condition
                condition_node = stop_trigger_node.find(".//ConditionGroup/Condition/ByEntityCondition")
                if condition_node is not None:
                    stop_trigger = "by Entity"
                    entity_ref_node = condition_node.find(".//TriggeringEntities/EntityRef")
                    stop_entity_ref_entity = entity_ref_node.attrib.get("entityRef")

                    entity_cond_node = condition_node.find(".//EntityCondition")
                    entity_cond_node = list(entity_cond_node.iter())[1]
                    stop_entity_cond = entity_cond_node.tag

                    if "duration" in entity_cond_node.attrib:
                        stop_entity_duration = entity_cond_node.attrib.get("duration")

                    if "entityRef" in entity_cond_node.attrib:
                        stop_entity_ref_entity = entity_cond_node.attrib.get("entityRef")

                    if "value" in entity_cond_node.attrib:
                        stop_entity_value = entity_cond_node.attrib.get("value")

                    if "freespace" in entity_cond_node.attrib:
                        stop_entity_frespace = strtobool(entity_cond_node.attrib.get(   # pylint: disable=unused-variable
                            "freespace").lower())

                    if "alongRoute" in entity_cond_node.attrib:
                        stop_entity_along_route = strtobool(entity_cond_node.attrib.get("alongRoute").lower())

                    if "rule" in entity_cond_node.attrib:
                        stop_entity_rule = entity_cond_node.attrib.get("rule")

                    if "tolerance" in entity_cond_node.attrib:
                        stop_world_pos_tolerance = entity_cond_node.attrib.get("tolerance")
                        world_pos_node = entity_cond_node.find(".//Position/WorldPosition")

                        if world_pos_node is not None:
                            stop_world_pos_x = float(world_pos_node.attrib.get("x"))
                            stop_world_pos_y = float(world_pos_node.attrib.get("y"))
                            stop_world_pos_z = float(world_pos_node.attrib.get("z"))
                            stop_world_pos_heading = float(world_pos_node.attrib.get("h"))
                        else:
                            message = ("Non WorldPosition waypoints are not supported (Maneuver ID: "
                                       f"{str(man_id)} Entity: {entity}) Defaulting to WorldPos 0, 0, 0")
                            display_message(message, level="Info")
                            self._warning_message.append(message)

                else:
                    condition_node = stop_trigger_node.find(".//ConditionGroup/Condition/ByValueCondition")
                    stop_trigger = "by Value"
                    value_cond_node = list(condition_node.iter())[1]
                    stop_value_cond = value_cond_node.tag

                    if "parameterRef" in value_cond_node.attrib:
                        stop_value_param_ref = value_cond_node.attrib.get("parameterRef")

                    if "name" in value_cond_node.attrib:
                        stop_value_name = value_cond_node.attrib.get("name")

                    if "value" in value_cond_node.attrib:
                        stop_value_value = value_cond_node.attrib.get("value")

                    if "rule" in value_cond_node.attrib:
                        stop_value_rule = value_cond_node.attrib.get("rule")

                    if "state" in value_cond_node.attrib:
                        stop_value_state = value_cond_node.attrib.get("state")

                    if "storyboardElementType" in value_cond_node.attrib:
                        stop_value_storyboard_type = value_cond_node.attrib.get("storyboardElementType")
                        stop_value_storyboard_element = value_cond_node.attrib.get("storyboardElementRef")
                        stop_value_storyboard_state = value_cond_node.attrib.get("state")

                    if "trafficSignalControllerRef" in value_cond_node.attrib:
                        stop_value_traffic_controller_ref = value_cond_node.attrib.get("trafficSignalControllerRef")
                        stop_value_traffic_controller_phase = value_cond_node.attrib.get("phase")

            feature = QgsFeature()
            feature.setAttributes([
                man_id,
                man_type,
                entity,
                entity_act_type,
                global_act_type,
                infra_traffic_id,
                infra_traffic_state,
                start_trigger,
                start_entity_cond,
                start_entity_ref_entity,
                start_entity_duration,
                start_entity_value,
                start_entity_rule,
                start_entity_rel_dist_type,
                start_entity_frespace,
                start_entity_along_route,
                start_value_cond,
                start_value_param_ref,
                start_value_name,
                start_value_datetime,
                start_value_value,
                start_value_rule,
                start_value_state,
                start_value_storyboard_type,
                start_value_storyboard_element,
                start_value_storyboard_state,
                start_value_traffic_controller_ref,
                start_value_traffic_controller_phase,
                start_world_pos_tolerance,
                start_world_pos_x,
                start_world_pos_y,
                start_world_pos_z,
                start_world_pos_heading,
                stop_trigger_enabled,
                stop_trigger,
                stop_entity_cond,
                stop_entity_ref_entity,
                stop_entity_duration,
                stop_entity_value,
                stop_entity_rule,
                stop_entity_rel_dist_type,
                stop_entity_freespace,
                stop_entity_along_route,
                stop_value_cond,
                stop_value_param_ref,
                stop_value_name,
                stop_value_datetime,
                stop_value_value,
                stop_value_rule,
                stop_value_state,
                stop_value_storyboard_type,
                stop_value_storyboard_element,
                stop_value_storyboard_state,
                stop_value_traffic_controller_ref,
                stop_value_traffic_controller_phase,
                stop_world_pos_tolerance,
                stop_world_pos_x,
                stop_world_pos_y,
                stop_world_pos_z,
                stop_world_pos_heading
            ])
            maneuver_layer.dataProvider().addFeature(feature)

    def parse_waypoints(self, waypoint_node, man_id, entity):
        """
        Parses waypoint maneuvers and saves into QGIS layers

        Args:
            waypoint_node (XML element): Node that contains RoutingAction
            man_id (int): Maneuver ID to differentiate maneuvers
            entity (str): Entity name for maneuver
        """
        waypoint_layer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]

        world_pos_x = 0
        world_pos_y = 0
        world_pos_z = 0
        world_pos_heading = 0
        waypoint_id = 1

        for waypoint in waypoint_node.iter("Waypoint"):
            route_strat = waypoint.attrib.get("routeStrategy")
            world_pos_node = waypoint.find(".//Position/WorldPosition")

            if world_pos_node is not None:
                world_pos_x = float(world_pos_node.attrib.get("x"))
                world_pos_y = float(world_pos_node.attrib.get("y"))
                world_pos_z = float(world_pos_node.attrib.get("z"))
                world_pos_heading = float(world_pos_node.attrib.get("h"))
            else:
                message = ("Non WorldPosition waypoints are not supported (Maneuver ID: "
                           f"{str(man_id)} Entity: {entity})")
                display_message(message, level="Info")
                self._warning_message.append(message)
                break

            feature = QgsFeature()
            feature.setAttributes([
                man_id,
                entity,
                waypoint_id,
                world_pos_heading,
                world_pos_x,
                world_pos_y,
                world_pos_z,
                route_strat
            ])

            # Create ENU point and convert to GEO for display in QGIS
            enupoint = ad.map.point.createENUPoint(world_pos_x, world_pos_y, world_pos_z)
            geopoint = ad.map.point.toGeo(enupoint)
            feature.setGeometry(
                QgsGeometry.fromPointXY(QgsPointXY(geopoint.longitude, geopoint.latitude)))
            waypoint_layer.dataProvider().addFeature(feature)

            waypoint_id += 1

    def parse_maneuvers_longitudinal(self, long_act_node, man_id):
        """
        Parse longitudinal maneuvers and saves into QGIS layers

        Args:
            long_act_node (XML element): XML node that contains LongitudinalAction
            man_id (int): Maneuver ID to differentiate maneuvers
        """
        long_man_layer = QgsProject.instance().mapLayersByName("Longitudinal Maneuvers")[0]

        # Default values
        long_type = "SpeedAction"
        speed_target = "RelativeTargetSpeed"
        entity_ref = ""
        dynamics_shape = "linear"
        dynamics_dimension = "rate"
        dynamics_value = "0"
        target_type = "delta"
        target_speed = "0"
        continuous = True
        freespace = True
        max_accel = "0"
        max_decel = "0"
        max_speed = "0"

        long_type_node = list(long_act_node.iter())[1]
        long_type = long_type_node.tag
        if long_type == "SpeedAction":
            speed_dynamics_node = long_type_node.find(".//SpeedActionDynamics")
            dynamics_shape = speed_dynamics_node.attrib.get("dynamicsShape")
            dynamics_value = speed_dynamics_node.attrib.get("value")
            dynamics_dimension = speed_dynamics_node.attrib.get("dynamicsDimension")

            speed_target_node = long_act_node.find(".//SpeedActionTarget")
            speed_target_node = list(speed_target_node.iter())[1]
            speed_target = speed_target_node.tag

            if speed_target == "RelativeTargetSpeed":
                rel_target_speed_node = speed_target_node
                entity_ref = rel_target_speed_node.attrib.get("entityRef")
                target_speed = rel_target_speed_node.attrib.get("value")
                target_type = rel_target_speed_node.attrib.get("speedTargetValueType")
                continuous = strtobool(rel_target_speed_node.attrib.get("continuous").lower())
            elif speed_target == "AbsoluteTargetSpeed":
                abs_target_speed_node = speed_target_node
                target_speed = abs_target_speed_node.attrib.get("value")

        elif long_type == "LongitudinalDistanceAction":
            entity_ref = long_act_node.attrib.get("entityRef")
            freespace = strtobool(long_act_node.attrib.get("freespace").lower())
            continuous = strtobool(long_act_node.attrib.get("continuous").lower())

            dynamic_constrain_node = long_act_node.find(".//DynamicConstraints")
            max_accel = dynamic_constrain_node.attrib.get("maxAcceleration")
            max_decel = dynamic_constrain_node.attrib.get("maxDeceleration")
            max_speed = dynamic_constrain_node.attrib.get("maxSpeed")

        feature = QgsFeature()
        feature.setAttributes([
            man_id,
            long_type,
            speed_target,
            entity_ref,
            dynamics_shape,
            dynamics_dimension,
            dynamics_value,
            target_type,
            target_speed,
            continuous,
            freespace,
            max_accel,
            max_decel,
            max_speed
        ])
        long_man_layer.dataProvider().addFeature(feature)

    def parse_maneuvers_lateral(self, lat_act_node, man_id):
        """
        Parse longitudinal maneuvers and saves into QGIS layers

        Args:
            lat_act_node (XML element): XML node that contains LateralAction
            man_id (int): Maneuver ID to differentiate maneuvers
        """
        lat_man_layer = QgsProject.instance().mapLayersByName("Lateral Maneuvers")[0]

        # Default values
        lat_type = "LaneChangeAction"
        lane_target = "RelativeTargetLane"
        entity_ref = ""
        dynamics_shape = "linear"
        dynamics_dimension = "rate"
        dynamics_value = "0"
        lane_target_value = "0"
        max_lat_accel = "0"
        max_accel = "0"
        max_decel = "0"
        max_speed = "0"

        lat_type_node = list(lat_act_node.iter())[1]
        lat_type = lat_type_node.tag

        if lat_type == "LaneChangeAction":
            dynamics_node = lat_type_node.find(".//LaneChangeActionDynamics")
            dynamics_shape = dynamics_node.attrib.get("dynamicsShape")
            dynamics_value = dynamics_node.attrib.get("value")
            dynamics_dimension = dynamics_node.attrib.get("dynamicsDimension")

            lane_target_node = lat_type_node.find(".//LaneChangeTarget")
            lane_target_choice_node = list(lane_target_node.iter())[1]
            lane_target = lane_target_choice_node.tag
            if lane_target == "RelativeTargetLane":
                rel_target_node = lane_target_choice_node
                entity_ref = rel_target_node.attrib.get("entityRef")
                lane_target_value = rel_target_node.attrib.get("value")
            elif lane_target == "AbsoluteTargetLane":
                abs_target_node = lane_target_choice_node
                lane_target_value = abs_target_node.attrib.get("value")

        elif lat_type == "LaneOffsetAction":
            dynamics_node = lat_type_node.find(".//LaneOffsetActionDynamics")
            max_lat_accel = dynamics_node.attrib.get("maxLateralAcc")
            dynamics_shape = dynamics_node.attrib.get("dynamicsShape")

            lane_target_node = lat_act_node.find(".//LaneOffsetTarget")
            lane_target_choice_node = list(lane_target_node.iter())[1]
            lane_target = lane_target_choice_node.tag
            if lane_target == "RelativeTargetLaneOffset":
                rel_target_node = lane_target_choice_node
                entity_ref = rel_target_node.attrib.get("entityRef")
                lane_target_value = rel_target_node.attrib.get("value")
            elif lane_target == "AbsoluteTargetLaneOffset":
                abs_target_node = lane_target_choice_node
                lane_target_value = abs_target_node.attrib.get("value")

        elif lat_type == "LateralDistanceAction":
            dynamic_constrain_node = lat_type_node.find(".//DynamicConstraints")
            max_accel = dynamic_constrain_node.attrib.get("maxAcceleration")
            max_decel = dynamic_constrain_node.attrib.get("maxDeceleration")
            max_speed = dynamic_constrain_node.attrib.get("maxSpeed")

        feature = QgsFeature()
        feature.setAttributes([
            man_id,
            lat_type,
            lane_target,
            entity_ref,
            dynamics_shape,
            dynamics_dimension,
            dynamics_value,
            lane_target_value,
            max_lat_accel,
            max_accel,
            max_decel,
            max_speed
        ])
        lat_man_layer.dataProvider().addFeature(feature)
