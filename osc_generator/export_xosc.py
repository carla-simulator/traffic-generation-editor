# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO - Export XOSC
"""
import os.path
from datetime import datetime
# XML is only written here, not read. Therefore, we can directly use the standard xml.etree library
import xml.etree.ElementTree as etree   # nosec
# pylint: disable=no-name-in-module,no-member
from qgis.core import Qgis, QgsFeatureRequest, QgsMessageLog, QgsProject
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from defusedxml import minidom

from .helper_functions import set_metadata

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'export_xosc_dialog.ui'))


class ExportXOSCDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Dialog class for exporting OpenSCENARIO XML files.
    """

    def __init__(self, parent=None):
        """Initialization of ExportXMLDialog"""
        super(ExportXOSCDialog, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.select_path_button.pressed.connect(self.select_output)
        self.map_selection.currentTextChanged.connect(self.user_defined_map)
        self.load_road_network()

    def select_output(self):
        """Prompts user to select output file"""
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            filter="OpenSCENARIO (*.xosc)")
        # Update text field only if user press 'OK'
        if filename:
            if filename[-4:] != "xosc":
                filename += ".xosc"
            self.select_path.setText(filename)

    def save_file(self):
        """Exports OpenSCENARIO file by reading attibutes from QGIS"""
        if self.select_path.text() != "":
            filepath = self.select_path.text()
            road_network = self.map_selection.currentText()
            if self.map_selection.currentText() == "User Defined":
                road_network = self.map_selection_user_defined.text()
            gen_xml = GenerateXML(filepath, road_network)
            gen_xml.main()
            # remember Road Network for future
            set_metadata(road_network_filepath=road_network)
        else:
            message = "No export path was selected"
            iface.messageBar().pushMessage("Warning", message, level=Qgis.Warning)
            QgsMessageLog.logMessage(message, level=Qgis.Warning)

    def user_defined_map(self):
        """Enables/Disables text field for user defined maps"""
        if self.map_selection.currentText() == "User Defined":
            self.map_selection_user_defined.setEnabled(True)
        else:
            self.map_selection_user_defined.setDisabled(True)

    def load_road_network(self):
        """Auto populates road network if available"""
        if QgsProject.instance().mapLayersByName("Metadata"):
            metadata_layer = QgsProject.instance().mapLayersByName("Metadata")[0]
            road_network = ""
            for feature in metadata_layer.getFeatures():
                road_network = feature["Road Network"]

            index = self.map_selection.findText(road_network)
            if index == -1:
                self.map_selection.setCurrentText("User Defined")
                self.map_selection_user_defined.setText(road_network)
            else:
                self.map_selection.setCurrentIndex(index)


class GenerateXML():
    """
    Class for generating OpenSCENARIO files.
    """

    def __init__(self, filepath, road_network):
        self._filepath = filepath
        self._road_network = road_network
        self._warning_message = []

    def is_float(self, value):
        """
        Checks value if it can be converted to float.

        Args:
            value (string): value to check if can be converted to float

        Returns:
            bool: True if float, False if not
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

    def main(self):
        """
        Main function for generating OpenSCENARIO files.
        """
        root = etree.Element("OpenSCENARIO")
        self.get_header(root)
        self.get_parameter_declarations(root)
        etree.SubElement(root, "CatalogLocations")
        self.get_road_network(root)
        self.get_entities(root)
        storyboard = etree.SubElement(root, "Storyboard")
        self.get_init(storyboard)
        story = etree.SubElement(storyboard, "Story")
        story.set("name", "OSC Generated Story")
        act = etree.SubElement(story, "Act")
        act.set("name", "OSC Generated Act")
        self.get_maneuvers(act)
        self.get_story_start_trigger(act)
        self.get_story_stop_trigger(act)
        self.get_end_eval_criteria(storyboard)

        generated_xml = etree.tostring(root)
        self.write_xosc(generated_xml)

    def get_header(self, root):
        """
        Set up header for OpenSCENARIO file.

        Args:
            root: [XML element] root layer
        """
        header = etree.SubElement(root, "FileHeader")
        header.set("revMajor", "1")
        header.set("revMinor", "0")
        header.set("date", datetime.today().strftime("%Y-%m-%dT%H:%M:%S"))
        header.set("description", "Generated OpenSCENARIO File")
        header.set("author", "QGIS OSCGenerator Plugin")

    def get_parameter_declarations(self, root):
        """
        Set up user-defined parameters for OpenSCENARIO file.

        Args:
            root: [XML element] root layer
        """
        param_declare_group = etree.SubElement(root, "ParameterDeclarations")
        if QgsProject.instance().mapLayersByName("Parameter Declarations"):
            param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
            for feature in param_layer.getFeatures():
                param_name = feature["Parameter Name"]
                param_type = feature["Type"]
                param_value = feature["Value"]

                param = etree.SubElement(param_declare_group, "ParameterDeclaration")
                param.set("name", param_name)
                param.set("type", param_type)
                param.set("value", param_value)

    def get_road_network(self, root):
        """
        Set up road network for OpenSCENARIO file.

        Args:
            root: [XML element] root layer
        """
        road_network = etree.SubElement(root, "RoadNetwork")
        road_network_logic_file = etree.SubElement(road_network, "LogicFile")
        road_network_logic_file.set("filepath", self._road_network)
        road_network_scene_graph = etree.SubElement(road_network, "SceneGraphFile")
        road_network_scene_graph.set("filepath", "")

    def get_entities(self, root):
        """
        Gets entity list from layers and export into OpenSCENARIO file.

        Args:
            root: [XML element] root layer
        """
        entity = etree.SubElement(root, "Entities")
        # Ego Vehicles
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            vehicle_ego_layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in vehicle_ego_layer.getFeatures():
                veh_id = "Ego_" + str(feature["id"])
                model = feature["Vehicle Model"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(veh_id))
                vehicle = etree.SubElement(entity_object, "Vehicle")
                vehicle.set("name", model)
                vehicle.set("vehicleCategory", "car")
                self.get_generic_vehicle_properties(vehicle, is_ego=True)

        # Vehicles
        if QgsProject.instance().mapLayersByName("Vehicles"):
            vehicle_layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in vehicle_layer.getFeatures():
                veh_id = "Vehicle_" + str(feature["id"])
                model = feature["Vehicle Model"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(veh_id))
                vehicle = etree.SubElement(entity_object, "Vehicle")
                vehicle.set("name", model)
                vehicle.set("vehicleCategory", "car")
                self.get_generic_vehicle_properties(vehicle, is_ego=False)

        # Pedestrians
        if QgsProject.instance().mapLayersByName("Pedestrians"):
            pedestrian_layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in pedestrian_layer.getFeatures():
                ped_id = "Pedestrian_" + str(feature["id"])
                walker_type = feature["Walker"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(ped_id))
                walker = etree.SubElement(entity_object, "Pedestrian")
                walker.set("name", walker_type)
                walker.set("model", walker_type)
                walker.set("mass", "90.0")
                walker.set("pedestrianCategory", "pedestrian")
                self.get_generic_walker_properties(walker)

        # Static Objects
        if QgsProject.instance().mapLayersByName("Static Objects"):
            props_layer = QgsProject.instance().mapLayersByName("Static Objects")[0]
            for feature in props_layer.getFeatures():
                prop_id = "Prop_" + str(feature["id"])
                prop = feature["Prop"]
                prop_type = feature["Prop Type"]
                physics = feature["Physics"]
                mass = str(feature["Mass"])
                if physics:
                    physics = "on"
                else:
                    physics = "off"

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(prop_id))
                prop_obj = etree.SubElement(entity_object, "MiscObject")
                prop_obj.set("miscObjectCategory", prop_type)
                prop_obj.set("mass", mass)
                prop_obj.set("name", prop)
                param_declaration = etree.SubElement(   # pylint: disable=unused-variable
                    prop_obj, "ParameterDeclarations")
                bounding_box = etree.SubElement(prop_obj, "BoundingBox")
                boundbox_center = etree.SubElement(bounding_box, "Center")
                boundbox_center.set("x", "0.4")
                boundbox_center.set("y", "0.4")
                boundbox_center.set("z", "0.2")
                dimensions = etree.SubElement(bounding_box, "Dimensions")
                dimensions.set("width", "0.8")
                dimensions.set("length", "0.8")
                dimensions.set("height", "1")
                properties_parent = etree.SubElement(prop_obj, "Properties")
                properties = etree.SubElement(properties_parent, "Property")
                properties.set("name", "physics")
                properties.set("value", physics)

    def get_generic_vehicle_properties(self, vehicle, is_ego=False):
        """
        Generate vehicle properties.
        Properties are ignored by CARLA simulator, hence generic numbers are used.
        (as of CARLA 0.9.10)

        Args:
            vehicle: [XML element]
            is_ego: [bool] set whether vehicle is ego
        """
        etree.SubElement(vehicle, "ParameterDeclarations")
        performance = etree.SubElement(vehicle, "Performance")
        performance.set("maxSpeed", "69.444")
        performance.set("maxAcceleration", "200")
        performance.set("maxDeceleration", "10.0")
        bounding_box = etree.SubElement(vehicle, "BoundingBox")
        boundbox_center = etree.SubElement(bounding_box, "Center")
        boundbox_center.set("x", "1.5")
        boundbox_center.set("y", "0.0")
        boundbox_center.set("z", "0.9")
        boundbox_dimension = etree.SubElement(bounding_box, "Dimensions")
        boundbox_dimension.set("width", "2.1")
        boundbox_dimension.set("length", "4.5")
        boundbox_dimension.set("height", "1.8")
        axles = etree.SubElement(vehicle, "Axles")
        axle_front = etree.SubElement(axles, "FrontAxle")
        axle_front.set("maxSteering", "0.5")
        axle_front.set("wheelDiameter", "0.6")
        axle_front.set("trackWidth", "1.8")
        axle_front.set("positionX", "3.1")
        axle_front.set("positionZ", "0.3")
        axle_rear = etree.SubElement(axles, "RearAxle")
        axle_rear.set("maxSteering", "0.0")
        axle_rear.set("wheelDiameter", "0.6")
        axle_rear.set("trackWidth", "1.8")
        axle_rear.set("positionX", "0.0")
        axle_rear.set("positionZ", "0.3")
        properties_group = etree.SubElement(vehicle, "Properties")
        properties = etree.SubElement(properties_group, "Property")
        properties.set("name", "type")
        if is_ego:
            properties.set("value", "ego_vehicle")
        else:
            properties.set("value", "simulation")

    def get_generic_walker_properties(self, walker):
        """
        Generate pedestrian properties.
        Properties are ignored by CARLA simulator, hence generic numbers are used.
        (as of CARLA 0.9.10)

        Args:
            walker: [XML element]
        """
        etree.SubElement(walker, "ParameterDeclarations")
        bounding_box = etree.SubElement(walker, "BoundingBox")
        boundbox_center = etree.SubElement(bounding_box, "Center")
        boundbox_center.set("x", "1.5")
        boundbox_center.set("y", "0.0")
        boundbox_center.set("z", "0.9")
        boundbox_dimemsion = etree.SubElement(bounding_box, "Dimensions")
        boundbox_dimemsion.set("width", "1.0")
        boundbox_dimemsion.set("length", "1.0")
        boundbox_dimemsion.set("height", "1.8")
        properties_group = etree.SubElement(walker, "Properties")
        properties = etree.SubElement(properties_group, "Property")
        properties.set("name", "type")
        properties.set("value", "simulation")

    def get_init(self, storyboard):
        """
        Set up init for OpenSCENARIO file.

        Args:
            storyboard: [XML element]
        """
        init = etree.SubElement(storyboard, "Init")
        init_act = etree.SubElement(init, "Actions")
        self.get_environment_actions(init_act)

        # Ego Vehicle
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            vehicle_ego_layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in vehicle_ego_layer.getFeatures():
                veh_id = "Ego_" + str(feature["id"])
                orientation = feature["Orientation"]
                pos_x = feature["Pos X"]
                pos_y = feature["Pos Y"]
                pos_z = feature["Pos Z"]
                init_speed = feature["Init Speed"]
                agent = feature["Agent"]
                agent_camera = str(feature["Agent Camera"]).lower()

                if agent == "User Defined":
                    agent = feature["Agent User Defined"]

                entity = etree.SubElement(init_act, "Private")
                entity.set("entityRef", str(veh_id))
                self.entity_teleport_action(entity, orientation, pos_x, pos_y, pos_z)
                self.vehicle_controller(entity, str(feature["id"]), agent, agent_camera, is_ego=True)
                if init_speed != 0:
                    self.set_init_speed(entity, init_speed)

        # Vehicle
        if QgsProject.instance().mapLayersByName("Vehicles"):
            vehicle_layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in vehicle_layer.getFeatures():
                veh_id = "Vehicle_" + str(feature["id"])
                orientation = feature["Orientation"]
                pos_x = feature["Pos X"]
                pos_y = feature["Pos Y"]
                pos_z = feature["Pos Z"]
                init_speed = feature["Init Speed"]
                agent = feature["Agent"]
                agent_camera = str(feature["Agent Camera"]).lower()

                if agent == "User Defined":
                    agent = feature["Agent User Defined"]

                entity = etree.SubElement(init_act, "Private")
                entity.set("entityRef", str(veh_id))
                self.entity_teleport_action(entity, orientation, pos_x, pos_y, pos_z)
                self.vehicle_controller(entity, str(feature["id"]), agent, agent_camera, is_ego=False)
                if init_speed != 0:
                    self.set_init_speed(entity, init_speed)

        # Pedestrian
        if QgsProject.instance().mapLayersByName("Pedestrians"):
            walker_layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in walker_layer.getFeatures():
                ped_id = "Pedestrian_" + str(feature["id"])
                orientation = feature["Orientation"]
                pos_x = feature["Pos X"]
                pos_y = feature["Pos Y"]
                pos_z = feature["Pos Z"]
                init_speed = feature["Init Speed"]

                entity = etree.SubElement(init_act, "Private")
                entity.set("entityRef", ped_id)
                self.entity_teleport_action(entity, orientation, pos_x, pos_y, pos_z)
                if init_speed != 0:
                    self.set_init_speed(entity, init_speed)

        # Static Objects
        if QgsProject.instance().mapLayersByName("Static Objects"):
            props_layer = QgsProject.instance().mapLayersByName("Static Objects")[0]
            for feature in props_layer.getFeatures():
                prop_id = "Prop_" + str(feature["id"])
                orientation = feature["Orientation"]
                pos_x = feature["Pos X"]
                pos_y = feature["Pos Y"]
                pos_z = feature["Pos Z"]

                entity = etree.SubElement(init_act, "Private")
                entity.set("entityRef", prop_id)
                self.entity_teleport_action(entity, orientation, pos_x, pos_y, pos_z)

    def entity_teleport_action(self, entity, orientation, pos_x, pos_y, pos_z):
        """
        Writes OpenSCENARIO tags for entity teleport action

        Args:
            entity: [XML element]
            orientation: [double] orientation of entity
            pos_x: [double] position x of entity (in meters)
            pos_y: [double] position y of entity (in meters)
            pos_z: [double] position z of entity (in meters)
        """
        private_act = etree.SubElement(entity, "PrivateAction")
        teleport_action = etree.SubElement(private_act, "TeleportAction")
        teleport_pos = etree.SubElement(teleport_action, "Position")
        teleport_worldpos = etree.SubElement(teleport_pos, "WorldPosition")
        teleport_worldpos.set("x", str(pos_x))
        teleport_worldpos.set("y", str(pos_y))
        teleport_worldpos.set("z", str(pos_z))
        teleport_worldpos.set("h", str(orientation))

    def vehicle_controller(self, entity, veh_id, agent, agent_camera, is_ego):
        """
        Writes ControllerAction OpenSCENARIO tags for vehicles

        Args:
            entity: [XML element]
            ved_id: [int] used to link agent to entity
            agent: [string] to set controller agent
            agent_camera: [bool] enable/disable attach_camera for simple_vehicle_control
            is_ego: [bool] used to determine prefix for controller name
        """
        if is_ego:
            controller_id = f"HeroAgent_{veh_id}"
        else:
            controller_id = f"VehicleAgent_{veh_id}"

        private_act = etree.SubElement(entity, "PrivateAction")
        controller_act = etree.SubElement(private_act, "ControllerAction")
        controller_assign = etree.SubElement(controller_act, "AssignControllerAction")
        controller = etree.SubElement(controller_assign, "Controller")
        controller.set("name", controller_id)
        controller_properties_group = etree.SubElement(controller, "Properties")
        controller_properties = etree.SubElement(controller_properties_group, "Property")
        controller_properties.set("name", "module")
        if agent == "simple_vehicle_control":
            controller_properties.set("value", agent)
            attach_camera = etree.SubElement(controller_properties_group, "Property")
            attach_camera.set("name", "attach_camera")
            attach_camera.set("value", agent_camera)
        else:
            controller_properties.set("value", agent)

        overrides = etree.SubElement(controller_act, "OverrideControllerValueAction")
        override_throttle = etree.SubElement(overrides, "Throttle")
        override_throttle.set("value", "0")
        override_throttle.set("active", "false")
        override_brake = etree.SubElement(overrides, "Brake")
        override_brake.set("value", "0")
        override_brake.set("active", "false")
        override_clutch = etree.SubElement(overrides, "Clutch")
        override_clutch.set("value", "0")
        override_clutch.set("active", "false")
        override_parking_brake = etree.SubElement(overrides, "ParkingBrake")
        override_parking_brake.set("value", "0")
        override_parking_brake.set("active", "false")
        override_steering = etree.SubElement(overrides, "SteeringWheel")
        override_steering.set("value", "0")
        override_steering.set("active", "false")
        override_gear = etree.SubElement(overrides, "Gear")
        override_gear.set("number", "0")
        override_gear.set("active", "false")

    def get_environment_actions(self, init_act):
        """
        Writes environment variables.
        If no environment variables are set, throws an exception.

        Args:
            init_act: [XML element]
        """
        # Set initial values for environment variables
        time_of_day = "2020-10-23T06:00:00"
        time_animation = "false"
        cloud_state = "free"
        fog_range = "100000"
        sun_intensity = "0.85"
        sun_azimuth = "0"
        sun_elevation = "1.31"
        percip_type = "dry"
        percip_intensity = "0"

        try:
            env_layer = QgsProject.instance().mapLayersByName("Environment")[0]
            for feature in env_layer.getFeatures():
                time_of_day = feature["Datetime"]
                time_animation = str(feature["Datetime Animation"]).lower()
                cloud_state = feature["Cloud State"]
                fog_range = str(feature["Fog Visual Range"])
                sun_intensity = str(feature["Sun Intensity"])
                sun_azimuth = str(feature["Sun Azimuth"])
                sun_elevation = str(feature["Sun Elevation"])
                percip_type = feature["Precipitation Type"]
                percip_intensity = str(feature["Precipitation Intensity"])
        except IndexError:
            error_message = "No environment variables detected, using defaults"
            iface.messageBar().pushMessage("Info", error_message, level=Qgis.Info)
            QgsMessageLog.logMessage(error_message, level=Qgis.Info)
            self._warning_message.append(f"Info: {error_message}")

            time_of_day = "2020-10-23T06:00:00"
            time_animation = "false"
            cloud_state = "free"
            fog_range = "100000"
            sun_intensity = "0.85"
            sun_azimuth = "0"
            sun_elevation = "1.31"
            percip_type = "dry"
            percip_intensity = "0"

        global_act = etree.SubElement(init_act, "GlobalAction")
        env_act = etree.SubElement(global_act, "EnvironmentAction")
        environ = etree.SubElement(env_act, "Environment")
        environ.set("name", "Environment1")

        env_time = etree.SubElement(environ, "TimeOfDay")
        env_time.set("animation", time_animation)
        env_time.set("dateTime", time_of_day)

        weather = etree.SubElement(environ, "Weather")
        weather.set("cloudState", cloud_state)
        weather_sun = etree.SubElement(weather, "Sun")
        weather_sun.set("intensity", sun_intensity)
        weather_sun.set("azimuth", sun_azimuth)
        weather_sun.set("elevation", sun_elevation)
        weather_fog = etree.SubElement(weather, "Fog")
        weather_fog.set("visualRange", fog_range)
        weather_percip = etree.SubElement(weather, "Precipitation")
        weather_percip.set("precipitationType", percip_type)
        weather_percip.set("intensity", percip_intensity)

        env_road = etree.SubElement(environ, "RoadCondition")
        env_road.set("frictionScaleFactor", "1.0")

    def set_init_speed(self, entity, init_speed):
        """
        Writes OpenSCENARIO tags for initial speed

        Args:
            entity: [XML element]
            init_speed: [str, int, float] initial speed of entity to be converted
                       to string when writing XML
        """
        if not self.is_float(init_speed):
            init_speed = "$" + init_speed
        private_act = etree.SubElement(entity, "PrivateAction")
        long_act = etree.SubElement(private_act, "LongitudinalAction")
        speed_act = etree.SubElement(long_act, "SpeedAction")
        speed_act_dynamics = etree.SubElement(speed_act, "SpeedActionDynamics")
        speed_act_dynamics.set("dynamicsShape", "step")
        speed_act_dynamics.set("value", "0.1")
        speed_act_dynamics.set("dynamicsDimension", "distance")
        speed_target = etree.SubElement(speed_act, "SpeedActionTarget")
        speed_target_absolute = etree.SubElement(speed_target, "AbsoluteTargetSpeed")
        speed_target_absolute.set("value", str(init_speed))

    def get_maneuvers(self, act):
        """
        Gets maneuvers from QGIS layer.
        If no maneuvers are detected, create a minimal XML structure.

        Args:
            act: [XML element]
        """
        if QgsProject.instance().mapLayersByName("Maneuvers"):
            layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]
            if layer.featureCount() == 0:
                self.generate_minimal_maneuver(act)
                error_message = "No maneuvers set... Generating minimal maneuvers"
                iface.messageBar().pushMessage("Error", error_message, level=Qgis.Warning)
                QgsMessageLog.logMessage(error_message, level=Qgis.Warning)
                self._warning_message.append(f"Warning: {error_message}")
            else:
                # Find unique entities and group together
                unique_entities = set()
                for feature in layer.getFeatures():
                    entity = feature["Entity"]
                    unique_entities.add(entity)

                for entity in unique_entities:
                    man_group = etree.SubElement(act, "ManeuverGroup")
                    man_group.set("maximumExecutionCount", "1")
                    man_group_name = f"Maneuver group for {entity}"
                    man_group.set("name", man_group_name)

                    query = f"\"Entity\" is '{entity}'"
                    request = QgsFeatureRequest().setFilterExpression(query)
                    for feature in layer.getFeatures(request):
                        man_id = feature["id"]
                        entity = feature["Entity"]
                        man_type = feature["Maneuver Type"]
                        entity_man_type = feature["Entity: Maneuver Type"]
                        global_act_type = feature["Global: Act Type"]

                        actors = etree.SubElement(man_group, "Actors")
                        actors.set("selectTriggeringEntities", "false")
                        actors_entity_ref = etree.SubElement(actors, "EntityRef")
                        actors_entity_ref.set("entityRef", entity)

                        maneuver = etree.SubElement(man_group, "Maneuver")
                        maneuver_name = "Maneuver ID " + str(feature["id"])
                        maneuver.set("name", maneuver_name)
                        event = etree.SubElement(maneuver, "Event")
                        event_name = "Event Maneuver ID " + str(feature["id"])
                        event.set("name", event_name)
                        event.set("priority", "overwrite")

                        if man_type == "Entity Maneuvers":
                            if entity_man_type == "Waypoint":
                                self.get_waypoints(man_id, event)
                            elif entity_man_type == "Longitudinal":
                                self.get_longitudinal_maneuvers(man_id, event)
                            elif entity_man_type == "Lateral":
                                self.get_lateral_maneuvers(man_id, event)

                        elif man_type == "Global Actions":
                            if global_act_type == "InfrastructureAction":
                                action = etree.SubElement(event, "Action")
                                action.set("name", "Traffic Light Maneuver ID " + str(feature["id"]))
                                global_action = etree.SubElement(action, "GlobalAction")
                                infra_action = etree.SubElement(global_action, "InfrastructureAction")
                                traffic_signal_action = etree.SubElement(infra_action, "TrafficSignalAction")
                                traffic_signal_state = etree.SubElement(
                                    traffic_signal_action, "TrafficSignalStateAction")
                                traffic_id = "id=" + str(feature["Infra: Traffic Light ID"])
                                traffic_signal_state.set("name", traffic_id)
                                traffic_signal_state.set("state", feature["Infra: Traffic Light State"])

                        self.get_maneuver_start_trigger(feature, event)

                        if feature["Stop Trigger Enabled"]:
                            self.get_maneuver_stop_trigger(feature, event)
        else:
            # No maneuvers defined by user
            man_group = etree.SubElement(act, "ManeuverGroup")
            man_group.set("maximumExecutionCount", "1")
            man_group.set("name", "No Maneuvers Group")
            actors = etree.SubElement(man_group, "Actors")
            actors.set("selectTriggeringEntities", "false")

            error_message = "No maneuvers set"
            iface.messageBar().pushMessage("Error", error_message, level=Qgis.Warning)
            QgsMessageLog.logMessage(error_message, level=Qgis.Warning)
            self._warning_message.append(f"Warning: {error_message}")

    def generate_minimal_maneuver(self, act):
        """
        Creates a minimal XML structure to meet OpenSCENARIO specifications
        when no maneuvers are set.
        Entity reference will take any one vehicle spawned (prioritizing ego).

        Creates a speed action at position +100 meters, to prevent scenario from
        exiting immediately after being run.

        Args:
            act: [XML element]
        """
        entity = ""
        pos_x = 0
        pos_y = 0
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            if layer.featureCount() != 0:
                for feature in layer.getFeatures():
                    entity = "Ego_" + str(feature["id"])
                    pos_x = feature["Pos X"]
                    pos_y = feature["Pos Y"]
                    break
            else:
                if QgsProject.instance().mapLayersByName("Vehicles"):
                    layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
                    if layer.featureCount() != 0:
                        for feature in layer.getFeatures():
                            entity = "Vehicle_" + str(feature["id"])
                            pos_x = feature["Pos X"]
                            pos_y = feature["Pos Y"]
                            break
                    else:
                        error_message = "No vehicles available to set asbare minimum entity reference for maneuvers"
                        iface.messageBar().pushMessage("Error", error_message, level=Qgis.Critical)
                        QgsMessageLog.logMessage(error_message, level=Qgis.Critical)
                        self._warning_message.append(f"Critical: {error_message}")

        man_group = etree.SubElement(act, "ManeuverGroup")
        man_group.set("maximumExecutionCount", "1")
        man_group.set("name", "No Maneuvers Group")
        actors = etree.SubElement(man_group, "Actors")
        actors.set("selectTriggeringEntities", "false")
        actors_entity_ref = etree.SubElement(actors, "EntityRef")
        actors_entity_ref.set("entityRef", entity)

        man = etree.SubElement(man_group, "Maneuver")
        man.set("name", "Generated Maneuver - non user specified")
        event = etree.SubElement(man, "Event")
        event.set("name", "Generated Event - non user defined")
        event.set("priority", "overwrite")
        action = etree.SubElement(event, "Action")
        action.set("name", "Generated Action - non user defined")
        private_action = etree.SubElement(action, "PrivateAction")
        long_act = etree.SubElement(private_action, "LongitudinalAction")
        speed_act = etree.SubElement(long_act, "SpeedAction")
        speed_act_dynamics = etree.SubElement(speed_act, "SpeedActionDynamics")
        speed_act_dynamics.set("dynamicsShape", "step")
        speed_act_dynamics.set("dynamicsDimension", "distance")
        speed_act_dynamics.set("value", "10.0")
        speed_target = etree.SubElement(speed_act, "SpeedActionTarget")
        speed_target_absolute = etree.SubElement(speed_target, "AbsoluteTargetSpeed")
        speed_target_absolute.set("value", "5.0")

        start_trig = etree.SubElement(event, "StartTrigger")
        cond_gorup = etree.SubElement(start_trig, "ConditionGroup")
        cond = etree.SubElement(cond_gorup, "Condition")
        cond.set("name", "StartCondition")
        cond.set("delay", "0")
        cond.set("conditionEdge", "rising")
        by_entity_cond = etree.SubElement(cond, "ByEntityCondition")
        trig_entity = etree.SubElement(by_entity_cond, "TriggeringEntities")
        trig_entity.set("triggeringEntitiesRule", "any")
        entity_ref = etree.SubElement(trig_entity, "EntityRef")
        entity_ref.set("entityRef", entity)
        entity_cond = etree.SubElement(by_entity_cond, "EntityCondition")
        reach_pos_cond = etree.SubElement(entity_cond, "ReachPositionCondition")
        reach_pos_cond.set("tolerance", "2.0")
        pos = etree.SubElement(reach_pos_cond, "Position")
        world_pos = etree.SubElement(pos, "WorldPosition")
        world_pos.set("x", str(pos_x + 100))
        world_pos.set("y", str(pos_y + 100))
        world_pos.set("z", "0")

    def get_waypoints(self, maneuver_id, event):
        """
        Writes waypoints with the same maneuver ID.

        Args:
            maneuver_id: [int] used to match waypoints to same maneuver
            event: [XML element]
        """
        action = etree.SubElement(event, "Action")
        action_name = f"Action for Manuever ID {maneuver_id}"
        action.set("name", action_name)
        private_action = etree.SubElement(action, "PrivateAction")
        routing_act = etree.SubElement(private_action, "RoutingAction")
        assign_route = etree.SubElement(routing_act, "AssignRouteAction")
        route = etree.SubElement(assign_route, "Route")
        route.set("name", "OSC Generated Route")
        route.set("closed", "false")

        waypoint_layer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]
        query = f"\"Maneuver ID\" is '{maneuver_id}'"
        request = QgsFeatureRequest().setFilterExpression(query)
        for feature in waypoint_layer.getFeatures(request):
            waypoint = etree.SubElement(route, "Waypoint")
            waypoint.set("routeStrategy", feature["Route Strategy"])
            position = etree.SubElement(waypoint, "Position")
            world_position = etree.SubElement(position, "WorldPosition")
            world_position.set("x", str(feature["Pos X"]))
            world_position.set("y", str(feature["Pos Y"]))
            world_position.set("z", str(feature["Pos Z"]))
            world_position.set("h", str(feature["Orientation"]))

    def get_longitudinal_maneuvers(self, maneuver_id, event):
        """
        Writes waypoints with the same maneuver ID.

        Args:
            maneuver_id: [int] used to match waypoints to same maneuver
            event: [XML element]
        """
        action = etree.SubElement(event, "Action")
        action_name = f"Action for Manuever ID {maneuver_id}"
        action.set("name", action_name)
        private_action = etree.SubElement(action, "PrivateAction")
        long_act = etree.SubElement(private_action, "LongitudinalAction")

        long_man_layer = QgsProject.instance().mapLayersByName("Longitudinal Maneuvers")[0]
        expression = f"\"Maneuver ID\" is '{maneuver_id}'"
        request = QgsFeatureRequest().setFilterExpression(expression)
        for feature in long_man_layer.getFeatures(request):
            act_type = feature["Type"]
            if act_type == "SpeedAction":
                speed_act = etree.SubElement(long_act, act_type)
                speed_act_dynamics = etree.SubElement(speed_act, "SpeedActionDynamics")
                speed_act_dynamics.set("dynamicsShape", feature["Dynamics Shape"])
                speed_act_dynamics.set("value", str(feature["Dynamics Value"]))
                speed_act_dynamics.set("dynamicsDimension", feature["Dynamics Dimension"])

                speed_target = etree.SubElement(speed_act, "SpeedActionTarget")
                speed_target_type = feature["Speed Target"]
                if speed_target_type == "RelativeTargetSpeed":
                    relative_target_speed = etree.SubElement(speed_target, speed_target_type)
                    relative_target_speed.set("entityRef", feature["Ref Entity"])
                    relative_target_speed.set("value", str(feature["Target Speed"]))
                    relative_target_speed.set("speedTargetValueType", feature["Target Type"])
                    relative_target_speed.set("continuous", str(feature["Continuous"]).lower())
                elif speed_target_type == "AbsoluteTargetSpeed":
                    absolute_target_speed = etree.SubElement(speed_target, speed_target_type)
                    absolute_target_speed.set("value", str(feature["Target Speed"]))

            elif act_type == "LongitudinalDistanceAction":
                long_dist_act = etree.SubElement(long_act, act_type)
                long_dist_act.set("entityRef", feature["Ref Entity"])
                long_dist_act.set("freespace", str(feature["Freespace"]).lower())
                long_dist_act.set("continuous", str(feature["Continuous"]).lower())
                dynamic_constraints = etree.SubElement(long_dist_act, "DynamicConstraints")
                dynamic_constraints.set("maxAcceleration", str(feature["Max Acceleration"]))
                dynamic_constraints.set("maxDeceleration", str(feature["Max Deceleration"]))
                dynamic_constraints.set("maxSpeed", str(feature["Max Speed"]))

    def get_lateral_maneuvers(self, maneuver_id, event):
        """
        Writes waypoints with the same maneuver ID.

        Args:
            maneuver_id: [int] used to match waypoints to same maneuver
            event: [XML element]
        """
        action = etree.SubElement(event, "Action")
        action_name = f"Action for Manuever ID {maneuver_id}"
        action.set("name", action_name)
        private_action = etree.SubElement(action, "PrivateAction")
        lat_act = etree.SubElement(private_action, "LateralAction")

        lat_man_layer = QgsProject.instance().mapLayersByName("Lateral Maneuvers")[0]
        expression = f"\"Maneuver ID\" is '{maneuver_id}'"
        request = QgsFeatureRequest().setFilterExpression(expression)
        for feature in lat_man_layer.getFeatures(request):
            act_type = feature["Type"]
            if act_type == "LaneChangeAction":
                lane_change_act = etree.SubElement(lat_act, act_type)
                lane_change_dynamics = etree.SubElement(lane_change_act, "LaneChangeActionDynamics")
                lane_change_dynamics.set("dynamicsShape", feature["Dynamics Shape"])
                lane_change_dynamics.set("value", str(feature["Dynamics Value"]))
                lane_change_dynamics.set("dynamicsDimension", feature["Dynamics Dimension"])

                lane_target = etree.SubElement(lane_change_act, "LaneChangeTarget")
                target_choice = feature["Lane Target"]
                if target_choice == "RelativeTargetLane":
                    relative_target_lane = etree.SubElement(lane_target, target_choice)
                    relative_target_lane.set("entityRef", feature["Ref Entity"])
                    relative_target_lane.set("value", feature["Lane Target Value"])
                elif target_choice == "AbsoluteTargetLane":
                    absolute_target_lane = etree.SubElement(lane_target, target_choice)
                    absolute_target_lane.set("value", feature["Lane Target Value"])

            elif act_type == "LaneOffsetAction":
                lane_offset_act = etree.SubElement(lat_act, act_type)
                lane_offset_dynamics = etree.SubElement(lane_offset_act, "LaneOffsetActionDynamics")
                lane_offset_dynamics.set("maxLateralAcc", str(feature["Max Lateral Acceleration"]))
                lane_offset_dynamics.set("dynamicsShape", feature["Dynamics Shape"])
                lane_target = etree.SubElement(lane_offset_act, "LaneOffsetTarget")
                target_choice = feature["Lane Target"]
                if target_choice == "RelativeTargetLaneOffset":
                    relative_target_lane = etree.SubElement(lane_target, target_choice)
                    relative_target_lane.set("entityRef", feature["Ref Entity"])
                    relative_target_lane.set("value", feature["Lane Target Value"])
                elif target_choice == "AbsoluteTargetLaneOffset":
                    absolute_target_lane = etree.SubElement(lane_target, target_choice)
                    absolute_target_lane.set("value", feature["Lane Target Value"])

            elif act_type == "LateralDistanceAction":
                lat_dist_act = etree.SubElement(lat_act, act_type)
                lat_dict_dynamics = etree.SubElement(lat_dist_act, "DynamicConstraints")
                lat_dict_dynamics.set("maxAcceleration", str(feature["Max Acceleration"]))
                lat_dict_dynamics.set("maxDeceleration", str(feature["Max Deceleration"]))
                lat_dict_dynamics.set("maxSpeed", str(feature["Max Speed"]))

    def get_maneuver_start_trigger(self, feature, event):
        """
        Writes start triggers for maneuver.

        Args:
            feature: [dictionary] used to get variables from QGIS attributes table
            event: [XML element]
        """
        start_trigger = etree.SubElement(event, "StartTrigger")
        cond_group = etree.SubElement(start_trigger, "ConditionGroup")
        cond = etree.SubElement(cond_group, "Condition")
        cond_name = f'Condition for Maneuver ID {str(feature["id"])}'
        cond.set("name", cond_name)
        cond.set("delay", "0")
        cond.set("conditionEdge", "rising")

        if feature["Start Trigger"] == "by Entity":
            by_entity_cond = etree.SubElement(cond, "ByEntityCondition")
            trig_entity = etree.SubElement(by_entity_cond, "TriggeringEntities")
            trig_entity.set("triggeringEntitiesRule", "any")
            trig_entity_ref = etree.SubElement(trig_entity, "EntityRef")
            trig_entity_ref.set("entityRef", feature["Start - Entity: Ref Entity"])
            entity_cond = etree.SubElement(by_entity_cond, "EntityCondition")
            entity_cond_element = etree.SubElement(entity_cond, feature["Start - Entity: Condition"])

            if (feature["Start - Entity: Condition"] == "EndOfRoadCondition"
                or feature["Start - Entity: Condition"] == "OffroadCondition"
                    or feature["Start - Entity: Condition"] == "StandStillCondition"):
                entity_cond_element.set("duration", str(feature["Start - Entity: Duration"]))

            if (feature["Start - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Start - Entity: Condition"] == "RelativeSpeedCondition"
                    or feature["Start - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("entityRef", feature["Start - Entity: Ref Entity"])

            if (feature["Start - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Start - Entity: Condition"] == "AccelerationCondition"
                or feature["Start - Entity: Condition"] == "SpeedCondition"
                or feature["Start - Entity: Condition"] == "RelativeSpeedCondition"
                or feature["Start - Entity: Condition"] == "TraveledDistanceCondition"
                    or feature["Start - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("value", str(feature["Start - Entity: Value"]))

            if (feature["Start - Entity: Condition"] == "TimeHeadwayCondition"
                    or feature["Start - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("freespace", str(feature["Start - Entity: Freespace"]).lower())

            if feature["Start - Entity: Condition"] == "TimeHeadwayCondtion":
                entity_cond_element.set("alongRoute", str(feature["Start - Entity: Along Route"]).lower())

            if (feature["Start - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Start - Entity: Condition"] == "AccelerationCondition"
                or feature["Start - Entity: Condition"] == "SpeedCondition"
                or feature["Start - Entity: Condition"] == "RelativeSpeedCondition"
                    or feature["Start - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("rule", feature["Start - Entity: Rule"])

            if feature["Start - Entity: Condition"] == "ReachPositionCondition":
                entity_cond_element.set("tolerance", str(feature["Start - WorldPos: Tolerance"]))
                position = etree.SubElement(entity_cond_element, "Position")
                world_position = etree.SubElement(position, "WorldPosition")
                world_position.set("x", str(feature["Start - WorldPos: X"]))
                world_position.set("y", str(feature["Start - WorldPos: Y"]))
                world_position.set("z", str(feature["Start - WorldPos: Z"]))
                world_position.set("h", str(feature["Start - WorldPos: Heading"]))

        elif feature["Start Trigger"] == "by Value":
            by_value_cond = etree.SubElement(cond, "ByValueCondition")
            value_cond_element = etree.SubElement(by_value_cond, feature["Start - Value: Condition"])

            if feature["Start - Value: Condition"] == "ParameterCondition":
                value_cond_element.set("parameterRef", feature["Start - Value: Param Ref"])

            if (feature["Start - Value: Condition"] == "UserDefinedValueCondition"
                    or feature["Start - Value: Condition"] == "TrafficSignalCondition"):
                value_cond_element.set("name", feature["Start - Value: Name"])

            if (feature["Start - Value: Condition"] == "ParameterCondition"
                or feature["Start - Value: Condition"] == "SimulationTimeCondition"
                    or feature["Start - Value: Condition"] == "UserDefinedValueCondition"):
                value_cond_element.set("value", str(feature["Start - Value: Value"]))

            if (feature["Start - Value: Condition"] == "ParameterCondition"
                or feature["Start - Value: Condition"] == "TimeOfDayCondition"
                or feature["Start - Value: Condition"] == "SimulationTimeCondition"
                    or feature["Start - Value: Condition"] == "UserDefinedValueCondition"):
                value_cond_element.set("rule", feature["Start - Value: Rule"])

            if feature["Start - Value: Condition"] == "TrafficSignalCondition":
                value_cond_element.set("state", feature["Start - Value: State"])

            if feature["Start - Value: Condition"] == "StoryboardElementStateCondition":
                value_cond_element.set("storyboardElementType", feature["Start - Value: Sboard Type"])
                value_cond_element.set("storyboardElementRef", feature["Start - Value: Sboard Element"])
                value_cond_element.set("state", feature["Start - Value: Sboard State"])

            if feature["Start - Value: Condition"] == "TrafficSignalControllerCondition":
                value_cond_element.set("trafficSignalControllerRef", feature["Value: TController Ref"])
                value_cond_element.set("phase", feature["Start - Value: TController Phase"])

    def get_maneuver_stop_trigger(self, feature, event):
        """
        Writes stop triggers for maneuvers if enabled.

        Args:
            feature: [dictionary] used to get variables from QGIS attributes table
            event: [XML element]
        """
        stop_trigger = etree.SubElement(event, "StopTrigger")
        cond_group = etree.SubElement(stop_trigger, "ConditionGroup")
        cond = etree.SubElement(cond_group, "Condition")
        cond_name = f'Condition for Maneuver ID {str(feature["id"])}'
        cond.set("name", cond_name)
        cond.set("delay", "0")
        cond.set("conditionEdge", "rising")

        if feature["Stop Trigger"] == "by Entity":
            by_entity_cond = etree.SubElement(cond, "ByEntityCondition")
            trig_entity = etree.SubElement(by_entity_cond, "TriggeringEntities")
            trig_entity.set("triggeringEntitiesRule", "any")
            trig_entity_ref = etree.SubElement(trig_entity, "EntityRef")
            trig_entity_ref.set("entityRef", feature["Stop - Entity: Ref Entity"])
            entity_cond = etree.SubElement(by_entity_cond, "EntityCondition")
            entity_cond_element = etree.SubElement(entity_cond, feature["Stop - Entity: Condition"])

            if (feature["Stop - Entity: Condition"] == "EndOfRoadCondition"
                or feature["Stop - Entity: Condition"] == "OffroadCondition"
                    or feature["Stop - Entity: Condition"] == "StandStillCondition"):
                entity_cond_element.set("duration", str(feature["Stop - Entity: Duration"]))

            if (feature["Stop - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Stop - Entity: Condition"] == "RelativeSpeedCondition"
                    or feature["Stop - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("entityRef", feature["Stop - Entity: Ref Entity"])

            if (feature["Stop - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Stop - Entity: Condition"] == "AccelerationCondition"
                or feature["Stop - Entity: Condition"] == "SpeedCondition"
                or feature["Stop - Entity: Condition"] == "RelativeSpeedCondition"
                or feature["Stop - Entity: Condition"] == "TraveledDistanceCondition"
                    or feature["Stop - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("value", str(feature["Stop - Entity: Value"]))

            if (feature["Stop - Entity: Condition"] == "TimeHeadwayCondition"
                    or feature["Stop - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("freespace", str(feature["Stop - Entity: Freespace"]).lower())

            if feature["Stop - Entity: Condition"] == "TimeHeadwayCondtion":
                entity_cond_element.set("alongRoute", str(feature["Stop - Entity: Along Route"]).lower())

            if (feature["Stop - Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Stop - Entity: Condition"] == "AccelerationCondition"
                or feature["Stop - Entity: Condition"] == "SpeedCondition"
                or feature["Stop - Entity: Condition"] == "RelativeSpeedCondition"
                    or feature["Stop - Entity: Condition"] == "RelativeDistanceCondition"):
                entity_cond_element.set("rule", feature["Stop - Entity: Rule"])

            if feature["Stop - Entity: Condition"] == "ReachPositionCondition":
                entity_cond_element.set("tolerance", str(feature["Stop - WorldPos: Tolerance"]))
                position = etree.SubElement(entity_cond_element, "Position")
                world_position = etree.SubElement(position, "WorldPosition")
                world_position.set("x", str(feature["Stop - WorldPos: X"]))
                world_position.set("y", str(feature["Stop - WorldPos: Y"]))
                world_position.set("z", str(feature["Stop - WorldPos: Z"]))
                world_position.set("h", str(feature["Stop - WorldPos: Heading"]))

        elif feature["Stop Trigger"] == "by Value":
            by_value_cond = etree.SubElement(cond, "ByValueCondition")
            value_cond_element = etree.SubElement(by_value_cond, feature["Stop - Value: Condition"])

            if feature["Stop - Value: Condition"] == "ParameterCondition":
                value_cond_element.set("parameterRef", feature["Stop - Value: Param Ref"])

            if (feature["Stop - Value: Condition"] == "UserDefinedValueCondition"
                    or feature["Stop - Value: Condition"] == "TrafficSignalCondition"):
                value_cond_element.set("name", feature["Stop - Value: Name"])

            if (feature["Stop - Value: Condition"] == "ParameterCondition"
                or feature["Stop - Value: Condition"] == "SimulationTimeCondition"
                    or feature["Stop - Value: Condition"] == "UserDefinedValueCondition"):
                value_cond_element.set("value", str(feature["Stop - Value: Value"]))

            if (feature["Stop - Value: Condition"] == "ParameterCondition"
                or feature["Stop - Value: Condition"] == "TimeOfDayCondition"
                or feature["Stop - Value: Condition"] == "SimulationTimeCondition"
                    or feature["Stop - Value: Condition"] == "UserDefinedValueCondition"):
                value_cond_element.set("rule", feature["Stop - Value: Rule"])

            if feature["Stop - Value: Condition"] == "TrafficSignalCondition":
                value_cond_element.set("state", feature["Stop - Value: State"])

            if feature["Stop - Value: Condition"] == "StoryboardElementStateCondition":
                value_cond_element.set("storyboardElementType", feature["Stop - Value: Sboard Type"])
                value_cond_element.set("storyboardElementRef", feature["Stop - Value: Sboard Element"])
                value_cond_element.set("state", feature["Stop - Value: Sboard State"])

            if feature["Stop - Value: Condition"] == "TrafficSignalControllerCondition":
                value_cond_element.set("trafficSignalControllerRef", feature["Value: TController Ref"])
                value_cond_element.set("phase", feature["Stop - Value: TController Phase"])

    def get_story_start_trigger(self, act):
        """
        Writes story start triggers.

        Args:
            act: [XML element]
        """
        act_start = etree.SubElement(act, "StartTrigger")
        cond_group = etree.SubElement(act_start, "ConditionGroup")
        time_cond = etree.SubElement(cond_group, "Condition")
        time_cond.set("name", "StartTime")
        time_cond.set("delay", "0")
        time_cond.set("conditionEdge", "rising")
        time_cond_value = etree.SubElement(time_cond, "ByValueCondition")
        sim_time = etree.SubElement(time_cond_value, "SimulationTimeCondition")
        sim_time.set("rule", "equalTo")
        sim_time.set("value", "0")

    def get_story_stop_trigger(self, act):
        """
        Writes story stop triggers.

        Args:
            act: [XML element]
        """
        stop = etree.SubElement(act, "StopTrigger")
        cond_group = etree.SubElement(stop, "ConditionGroup")
        cond = etree.SubElement(cond_group, "Condition")
        cond.set("name", "EndCondition")
        cond.set("delay", "0")
        cond.set("conditionEdge", "rising")
        by_value_cond = etree.SubElement(cond, "ByValueCondition")
        sim_time = etree.SubElement(by_value_cond, "SimulationTimeCondition")
        sim_time.set("rule", "equalTo")
        sim_time.set("value", "100")

    def get_end_eval_criteria(self, storyboard):
        """
        Writes scenario completion scenario checks for scenario_runner.

        Args:
            storyboard: [XML element]
        """
        stop = etree.SubElement(storyboard, "StopTrigger")

        if QgsProject.instance().mapLayersByName("End Evaluation KPIs"):
            env_eval_layer = QgsProject.instance().mapLayersByName("End Evaluation KPIs")[0]
            for feature in env_eval_layer.getFeatures():
                cond_name = feature["Condition Name"]
                delay = str(feature["Delay"])
                cond_edge = feature["Condition Edge"]
                param_ref = feature["Parameter Ref"]
                value = str(feature["Value"])
                rule = feature["Rule"]

                cond_gorup = etree.SubElement(stop, "ConditionGroup")
                cond = etree.SubElement(cond_gorup, "Condition")
                cond.set("name", cond_name)
                cond.set("delay", delay)
                cond.set("conditionEdge", cond_edge)
                by_value_cond = etree.SubElement(cond, "ByValueCondition")
                param_cond = etree.SubElement(by_value_cond, "ParameterCondition")
                param_cond.set("parameterRef", param_ref)
                param_cond.set("value", value)
                param_cond.set("rule", rule)

        else:
            error_message = "No end evaluation KPIs detected"
            iface.messageBar().pushMessage("Warning", error_message, level=Qgis.Warning)
            QgsMessageLog.logMessage(error_message, level=Qgis.Warning)
            self._warning_message.append(f"Warning: {error_message}")

    def write_xosc(self, generated_xml):
        """
        Save and export pretty printed XOSC file.

        Args:
            generated_xml: [string] generated XML from ElementTree
        """
        reparsed_xml = minidom.parseString(generated_xml).toprettyxml(indent="    ")
        xosc_file = open(self._filepath, "w")
        xosc_file.write(reparsed_xml)
        xosc_file.close()

        msg = QMessageBox()
        if self._warning_message:
            msg.setIcon(QMessageBox.Warning)
            text = f"Exported OpenSCENARIO file {self._filepath} has warnings!\n\n"
            text += "\n".join(self._warning_message)
        else:
            msg.setIcon(QMessageBox.Information)
            text = f"Successfully exported OpenSCENARIO file to {self._filepath}"
        msg.setText(text)
        msg.setWindowTitle("OpenSCENARIO Export")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
