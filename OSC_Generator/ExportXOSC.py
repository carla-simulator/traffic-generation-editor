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
import xml.etree.ElementTree as etree
# pylint: disable=no-name-in-module,no-member
from qgis.core import Qgis, QgsFeatureRequest, QgsMessageLog, QgsProject
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from PyQt5.QtWidgets import QFileDialog, QMessageBox
from defusedxml import minidom

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ExportXOSC.ui'))

class ExportXOSCDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Dialog class for exporting OpenSCENARIO XML files.
    """
    def __init__(self, parent=None):
        """Initialization of ExportXMLDialog"""
        super(ExportXOSCDialog, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.selectPath_Button.pressed.connect(self.SelectOutput)

    def SelectOutput(self):
        """Prompts uesr to select output file"""
        filename, _filter = QFileDialog.getSaveFileName(
            self,
            filter="OpenSCENARIO (*.xosc)")
        # Update text field only if user press 'OK'
        if filename:
            filename += ".xosc"
            self.selectPath.setText(filename)

    def SaveFile(self):
        """Exports OpenSCENARIO file by reading attibutes from QGIS"""
        if self.selectPath.text() is not "":
            filepath = self.selectPath.text()
            roadNetwork = self.mapSelection.currentText()
            GenXML = GenerateXML(filepath, roadNetwork)
            GenXML.main()
        else:
            iface.messageBar().pushMessage("Warning", "No export path was selected", level=Qgis.Warning)
            QgsMessageLog.logMessage("No export path was selected", level=Qgis.Warning)

class GenerateXML():
    """
    Class for generating OpenSCENARIO files.
    """
    def __init__(self, filepath, roadNetwork):
        self.filepath = filepath
        self.roadNetwork = roadNetwork
        self.warningMessage = []

    def main(self):
        """
        Main function for generating OpenSCENARIO files.
        """
        root = etree.Element("OpenSCENARIO")
        self.GetHeader(root)
        etree.SubElement(root, "ParameterDeclarations")
        etree.SubElement(root, "CatalogLocations")
        self.GetRoadNetwork(root)
        self.GetEntities(root)
        storyboard = etree.SubElement(root, "Storyboard")
        self.GetInit(storyboard)
        story = etree.SubElement(storyboard, "Story")
        story.set("name", "OSC Generated Story")
        act = etree.SubElement(story, "Act")
        act.set("name", "OSC Generated Act")
        self.GetManeuvers(act)
        self.GetStoryStartTrigger(act)
        self.GetStoryStopTrigger(act)
        self.GetEndEvalCriteria(storyboard)

        generatedXML = etree.tostring(root)
        self.WriteXOSC(generatedXML)

    def GetHeader(self, root):
        """
        Set up header for OpenSCENARIO file.
        """
        header = etree.SubElement(root, "FileHeader")
        header.set("revMajor", "1")
        header.set("revMinor", "0")
        header.set("date", datetime.today().strftime("%Y-%m-%d"))
        header.set("description", "Generated OpenSCENARIO File")
        header.set("author", "Wen Jie")

    def GetRoadNetwork(self, root):
        """
        Set up road network for OpenSCENARIO file.
        """
        roadNetwork = etree.SubElement(root, "RoadNetwork")
        roadNetwork_LogicFile = etree.SubElement(roadNetwork, "LogicFile")
        roadNetwork_LogicFile.set("filepath", self.roadNetwork)
        roadNetwork_SceneGraph = etree.SubElement(roadNetwork, "SceneGraphFile")
        roadNetwork_SceneGraph.set("filepath", "")

    def GetEntities(self, root):
        """
        Gets entity list from layers and export into OpenSCENARIO file.
        """
        entity = etree.SubElement(root, "Entities")
        # Ego Vehicles
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            vehicleEgoLayer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in vehicleEgoLayer.getFeatures():
                vehID = "Ego_" + str(feature["id"])
                model = feature["Vehicle Model"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(vehID))
                vehicle = etree.SubElement(entity_object, "Vehicle")
                vehicle.set("name", model)
                vehicle.set("vehicleCategory", "car")
                self.GetGenericVehicleProperties(vehicle, isEgo=True)

        # Vehicles
        if QgsProject.instance().mapLayersByName("Vehicles"):
            vehicleLayer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in vehicleLayer.getFeatures():
                vehID = "Vehicle_" + str(feature["id"])
                model = feature["Vehicle Model"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(vehID))
                vehicle = etree.SubElement(entity_object, "Vehicle")
                vehicle.set("name", model)
                vehicle.set("vehicleCategory", "car")
                self.GetGenericVehicleProperties(vehicle, isEgo=False)

        # Pedestrians
        if QgsProject.instance().mapLayersByName("Pedestrians"):
            pedestrianLayer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in pedestrianLayer.getFeatures():
                pedID = "Pedestrian_" + str(feature["id"])
                walkerType = feature["Walker"]

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(pedID))
                walker = etree.SubElement(entity_object, "Pedestrian")
                walker.set("name", walkerType)
                walker.set("model", walkerType)
                walker.set("mass", "90.0")
                walker.set("pedestrianCategory", "pedestrian")
                self.GetGenericPedestrianProperties(walker)

        # Static Objects
        if QgsProject.instance().mapLayersByName("Static Objects"):
            propsLayer = QgsProject.instance().mapLayersByName("Static Objects")[0]
            for feature in propsLayer.getFeatures():
                propID = "Prop_" + str(feature["id"])
                prop = feature["Prop"]
                propType = feature["Prop Type"]
                physics = feature["Physics"]
                mass = str(feature["Mass"])
                if physics:
                    physics = "on"
                else:
                    physics = "off"

                entity_object = etree.SubElement(entity, "ScenarioObject")
                entity_object.set("name", str(propID))
                propObject = etree.SubElement(entity_object, "MiscObject")
                propObject.set("miscObjectCategory", propType)
                propObject.set("mass", mass)
                propObject.set("name", prop)
                paramDeclare = etree.SubElement(propObject, "ParameterDeclarations")
                boundBox = etree.SubElement(propObject, "BoundingBox")
                boundBox_Center = etree.SubElement(boundBox, "Center")
                boundBox_Center.set("x", "0.4")
                boundBox_Center.set("y", "0.4")
                boundBox_Center.set("z", "0.2")
                dimensions = etree.SubElement(boundBox, "Dimensions")
                dimensions.set("width", "0.8")
                dimensions.set("length", "0.8")
                dimensions.set("height", "1")
                propertiesParent = etree.SubElement(propObject, "Properties")
                properties = etree.SubElement(propertiesParent, "Property")
                properties.set("name", "physics")
                properties.set("value", physics)

    def GetGenericVehicleProperties(self, vehicle, isEgo=False):
        """
        Generate vehicle properties.
        Properties are ignored by CARLA simulator, hence generic numbers are used.
        (as of CARLA 0.9.10)
        """
        etree.SubElement(vehicle, "ParameterDeclarations")
        vehicle_perf = etree.SubElement(vehicle, "Performance")
        vehicle_perf.set("maxSpeed", "69.444")
        vehicle_perf.set("maxAcceleration", "200")
        vehicle_perf.set("maxDeceleration", "10.0")
        vehicle_boundBox = etree.SubElement(vehicle, "BoundingBox")
        vehicle_boundBox_Center = etree.SubElement(vehicle_boundBox, "Center")
        vehicle_boundBox_Center.set("x", "1.5")
        vehicle_boundBox_Center.set("y", "0.0")
        vehicle_boundBox_Center.set("z", "0.9")
        vehicle_boundBox_Dim = etree.SubElement(vehicle_boundBox, "Dimensions")
        vehicle_boundBox_Dim.set("width", "2.1")
        vehicle_boundBox_Dim.set("length", "4.5")
        vehicle_boundBox_Dim.set("height", "1.8")
        vehicle_Axle = etree.SubElement(vehicle, "Axles")
        vehicle_Axle_Front = etree.SubElement(vehicle_Axle, "FrontAxle")
        vehicle_Axle_Front.set("maxSteering", "0.5")
        vehicle_Axle_Front.set("wheelDiameter", "0.6")
        vehicle_Axle_Front.set("trackWidth", "1.8")
        vehicle_Axle_Front.set("positionX", "3.1")
        vehicle_Axle_Front.set("positionZ", "0.3")
        vehicle_Axle_Rear = etree.SubElement(vehicle_Axle, "RearAxle")
        vehicle_Axle_Rear.set("maxSteering", "0.0")
        vehicle_Axle_Rear.set("wheelDiameter", "0.6")
        vehicle_Axle_Rear.set("trackWidth", "1.8")
        vehicle_Axle_Rear.set("positionX", "0.0")
        vehicle_Axle_Rear.set("positionZ", "0.3")
        vehicle_Properties = etree.SubElement(vehicle, "Properties")
        vehicle_Property = etree.SubElement(vehicle_Properties, "Property")
        vehicle_Property.set("name", "type")
        if isEgo:
            vehicle_Property.set("value", "ego_vehicle")
        else:
            vehicle_Property.set("value", "simulation")

    def GetGenericPedestrianProperties(self, walker):
        """
        Generate pedestrian properties.
        Properties are ignored by CARLA simulator, hence generic numbers are used.
        (as of CARLA 0.9.10)
        """
        etree.SubElement(walker, "ParameterDeclarations")
        BoundBox = etree.SubElement(walker, "BoundingBox")
        BoundBox_Center = etree.SubElement(BoundBox, "Center")
        BoundBox_Center.set("x", "1.5")
        BoundBox_Center.set("y", "0.0")
        BoundBox_Center.set("z", "0.9")
        BoundBox_Dim = etree.SubElement(BoundBox, "Dimensions")
        BoundBox_Dim.set("width", "1.0")
        BoundBox_Dim.set("length", "1.0")
        BoundBox_Dim.set("height", "1.8")
        Properties = etree.SubElement(walker, "Properties")
        Property = etree.SubElement(Properties, "Property")
        Property.set("name", "type")
        Property.set("value", "simulation")

    def GetInit(self, storyboard):
        """
        Set up init for OpenSCENARIO file.
        """
        init = etree.SubElement(storyboard, "Init")
        init_Act = etree.SubElement(init, "Actions")
        self.GetEnvironmentActions(init_Act)

        # Ego Vehicle
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            vehicleEgoLayer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in vehicleEgoLayer.getFeatures():
                vehID = "Ego_" + str(feature["id"])
                orientation = feature["Orientation"]
                posX = feature["Pos X"]
                posY = feature["Pos Y"]
                initSpeed = feature["Init Speed"]
                agent = feature["Agent"]
                agentCamera = str(feature["Agent Camera"]).lower()

                Entity = etree.SubElement(init_Act, "Private")
                Entity.set("entityRef", str(vehID))
                self.EntityTeleportAction(Entity, orientation, posX, posY)
                self.EgoEntityController(Entity, str(feature["id"]), agent, agentCamera)
                if initSpeed != 0:
                    self.SetInitSpeed(Entity, initSpeed)

        # Vehicle
        if QgsProject.instance().mapLayersByName("Vehicles"):
            vehicleLayer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in vehicleLayer.getFeatures():
                vehID = "Vehicle_" + str(feature["id"])
                orientation = feature["Orientation"]
                posX = feature["Pos X"]
                posY = feature["Pos Y"]
                initSpeed = feature["Init Speed"]

                Entity = etree.SubElement(init_Act, "Private")
                Entity.set("entityRef", str(vehID))
                self.EntityTeleportAction(Entity, orientation, posX, posY)
                if initSpeed != 0:
                    self.SetInitSpeed(Entity, initSpeed)

        # Pedestrian
        if QgsProject.instance().mapLayersByName("Pedestrians"):
            walkerLayer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in walkerLayer.getFeatures():
                pedID = "Pedestrian_" + str(feature["id"])
                orientation = feature["Orientation"]
                posX = feature["Pos X"]
                posY = feature["Pos Y"]
                initSpeed = feature["Init Speed"]

                Entity = etree.SubElement(init_Act, "Private")
                Entity.set("entityRef", pedID)
                self.EntityTeleportAction(Entity, orientation, posX, posY)
                if initSpeed != 0:
                    self.SetInitSpeed(Entity, initSpeed)

        # Static Objects
        if QgsProject.instance().mapLayersByName("Static Objects"):
            propsLayer = QgsProject.instance().mapLayersByName("Static Objects")[0]
            for feature in propsLayer.getFeatures():
                propID = "Prop_" + str(feature["id"])
                orientation = feature["Orientation"]
                posX = feature["Pos X"]
                posY = feature["Pos Y"]

                Entity = etree.SubElement(init_Act, "Private")
                Entity.set("entityRef", propID)
                self.EntityTeleportAction(Entity, orientation, posX, posY)

    def EntityTeleportAction(self, entity, orientation, posX, posY):
        """
        Writes OpenSCENARIO tags for entity teleport action
        """
        PrivAct = etree.SubElement(entity, "PrivateAction")
        PrivAct_Teleport = etree.SubElement(PrivAct, "TeleportAction")
        PrivAct_Teleport_Pos = etree.SubElement(PrivAct_Teleport, "Position")
        PrivAct_Teleport_WorldPos = etree.SubElement(PrivAct_Teleport_Pos, "WorldPosition")
        PrivAct_Teleport_WorldPos.set("x", str(posX))
        PrivAct_Teleport_WorldPos.set("y", str(posY))
        PrivAct_Teleport_WorldPos.set("z", "0.2")
        PrivAct_Teleport_WorldPos.set("h", str(orientation))

    def EgoEntityController(self, entity, vehID, agent, agentCamera):
        """
        Writes ControllerAction OpenSCENARIO tags for ego vehicles

        Args:
            entity: [XML element]
            vehID: [int] used to link agent to entity
            agent: [string] to set controller agent
            agentCamera: [bool] enable/disable attach_camera for simple_vehicle_control
        """
        ControllerID = "HeroAgent_" + vehID
        PrivAct = etree.SubElement(entity, "PrivateAction")
        PrivAct_Ctrl = etree.SubElement(PrivAct, "ControllerAction")
        PrivAct_CtrlAssign = etree.SubElement(PrivAct_Ctrl, "AssignControllerAction")
        PrivAct_CtrlAssign_Controller = etree.SubElement(PrivAct_CtrlAssign, "Controller")
        PrivAct_CtrlAssign_Controller.set("name", ControllerID)
        PrivAct_CtrlAssign_ControllerProp = etree.SubElement(PrivAct_CtrlAssign_Controller, "Properties")
        PrivAct_CtrlAssign_ControllerPropTag = etree.SubElement(PrivAct_CtrlAssign_ControllerProp, "Property")
        PrivAct_CtrlAssign_ControllerPropTag.set("name", "module")
        if agent == "external_control":
            PrivAct_CtrlAssign_ControllerPropTag.set("value", agent)
        elif agent == "simple_vehicle_control":
            PrivAct_CtrlAssign_ControllerPropTag.set("value", agent)
            PrivAct_CtrlAssign_ControllerPropTag_Cam = etree.SubElement(PrivAct_CtrlAssign_ControllerProp, "Property")
            PrivAct_CtrlAssign_ControllerPropTag_Cam.set("name", "attach_camera")
            PrivAct_CtrlAssign_ControllerPropTag_Cam.set("value", agentCamera)

        PrivAct_Override = etree.SubElement(PrivAct_Ctrl, "OverrideControllerValueAction")
        PrivAct_Override_Throttle = etree.SubElement(PrivAct_Override, "Throttle")
        PrivAct_Override_Throttle.set("value", "0")
        PrivAct_Override_Throttle.set("active", "false")
        PrivAct_Override_Brake = etree.SubElement(PrivAct_Override, "Brake")
        PrivAct_Override_Brake.set("value", "0")
        PrivAct_Override_Brake.set("active", "false")
        PrivAct_Override_Clutch = etree.SubElement(PrivAct_Override, "Clutch")
        PrivAct_Override_Clutch.set("value", "0")
        PrivAct_Override_Clutch.set("active", "false")
        PrivAct_Override_ParkingBrake = etree.SubElement(PrivAct_Override, "ParkingBrake")
        PrivAct_Override_ParkingBrake.set("value", "0")
        PrivAct_Override_ParkingBrake.set("active", "false")
        PrivAct_Override_Steering = etree.SubElement(PrivAct_Override, "SteeringWheel")
        PrivAct_Override_Steering.set("value", "0")
        PrivAct_Override_Steering.set("active", "false")
        PrivAct_Override_Gear = etree.SubElement(PrivAct_Override, "Gear")
        PrivAct_Override_Gear.set("number", "0")
        PrivAct_Override_Gear.set("active", "false")

    def GetEnvironmentActions(self, init_Act):
        """
        Writes environment variables.
        If no environment variables are set, throws an exception.

        Args:
            init_Act: [XML element]
        """
        try:
            envLayer = QgsProject.instance().mapLayersByName("Environment")[0]
            for feature in envLayer.getFeatures():
                timeofDay = feature["Datetime"]
                timeAnim = str(feature["Datetime Animation"]).lower()
                cloudState = feature["Cloud State"]
                fogRange = feature["Fog Visual Range"]
                sunIntensity = feature["Sun Intensity"]
                sunAzimuth = feature["Sun Azimuth"]
                sunElevation = feature["Sun Elevation"]
                precipType = feature["Precipitation Type"]
                precipIntensity = feature["Precipitation Intensity"]

            globalAct = etree.SubElement(init_Act, "GlobalAction")
            envAct = etree.SubElement(globalAct, "EnvironmentAction")
            environ = etree.SubElement(envAct, "Environment")
            environ.set("name", "Environment1")

            envTime = etree.SubElement(environ, "TimeOfDay")
            envTime.set("animation", timeAnim)
            envTime.set("dateTime", timeofDay)

            envWeather = etree.SubElement(environ, "Weather")
            envWeather.set("cloudState", cloudState)
            envWeather_Sun = etree.SubElement(envWeather, "Sun")
            envWeather_Sun.set("intensity", sunIntensity)
            envWeather_Sun.set("azimuth", sunAzimuth)
            envWeather_Sun.set("elevation", sunElevation)
            envWeather_Fog = etree.SubElement(envWeather, "Fog")
            envWeather_Fog.set("visualRange", fogRange)
            envWeather_Precip = etree.SubElement(envWeather, "Precipitation")
            envWeather_Precip.set("precipitationType", precipType)
            envWeather_Precip.set("intensity", precipIntensity)

            envRoad = etree.SubElement(environ, "RoadCondition")
            envRoad.set("frictionScaleFactor", "1.0")
        except IndexError:
            errorMessage = "No environment variables detected"
            iface.messageBar().pushMessage("Error", errorMessage, level=Qgis.Critical)
            QgsMessageLog.logMessage(errorMessage, level=Qgis.Critical)
            self.warningMessage.append(f"Critical: {errorMessage}")

    def SetInitSpeed(self, entity, initSpeed):
        """
        Writes OpenSCENARIO tags for initial speed

        Args:
            entity: [XML element]
            initSpeed: [str, int, float] initial speed of entity to be converted to string when writing XML
        """
        PrivAct = etree.SubElement(entity, "PrivateAction")
        PrivAct_LongAct = etree.SubElement(PrivAct, "LongitudinalAction")
        PrivAct_LongAct_Speed = etree.SubElement(PrivAct_LongAct, "SpeedAction")
        PrivAct_LongAct_SpeedDyn = etree.SubElement(PrivAct_LongAct_Speed, "SpeedActionDynamics")
        PrivAct_LongAct_SpeedDyn.set("dynamicsShape", "step")
        PrivAct_LongAct_SpeedDyn.set("value", "0.1")
        PrivAct_LongAct_SpeedDyn.set("dynamicsDimension", "distance")
        PrivAct_LongAct_SpeedTarget = etree.SubElement(PrivAct_LongAct_Speed, "SpeedActionTarget")
        PrivAct_LongAct_SpeedTarget_AbsTarget = etree.SubElement(PrivAct_LongAct_SpeedTarget, "AbsoluteTargetSpeed")
        PrivAct_LongAct_SpeedTarget_AbsTarget.set("value", str(initSpeed))

    def GetManeuvers(self, Act):
        """
        Gets maneuvers from QGIS layer.
        If no maneuvers are detected, create a minimal XML structure.

        Args:
            Act: [XML element]
        """
        if QgsProject.instance().mapLayersByName("Maneuvers"):
            layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]
            if layer.featureCount() == 0:
                self.MinimalManeuver(Act)
                errorMessage = "No maneuvers set... Generating minimal maneuvers"
                iface.messageBar().pushMessage("Error", errorMessage, level=Qgis.Warning)
                QgsMessageLog.logMessage(errorMessage, level=Qgis.Warning)
                self.warningMessage.append(f"Warning: {errorMessage}")
            else:
                for feature in layer.getFeatures():
                    manID = feature["id"]
                    entity = feature["Entity"]
                    manType = feature["Maneuver Type"]
                    entityManType = feature["Entity: Maneuver Type"]
                    globalActType = feature["Global: Act Type"]

                    ManGroup = etree.SubElement(Act, "ManeuverGroup")
                    ManGroup.set("maximumExecutionCount", "1")
                    ManGroupName = "Maneuver Group for " + feature["Entity"]
                    ManGroup.set("name", ManGroupName)

                    Actors = etree.SubElement(ManGroup, "Actors")
                    Actors.set("selectTriggeringEntities", "false")
                    Actors_EntityRef = etree.SubElement(Actors, "EntityRef")
                    Actors_EntityRef.set("entityRef", entity)

                    Maneuver = etree.SubElement(ManGroup, "Maneuver")
                    ManeuverName = "Maneuver ID " + str(feature["id"])
                    Maneuver.set("name", ManeuverName)
                    Event = etree.SubElement(Maneuver, "Event")
                    EventName = "Event Maneuver ID " + str(feature["id"])
                    Event.set("name", EventName)
                    Event.set("priority", "overwrite")

                    if manType == "Entity Maneuvers":
                        if entityManType == "Waypoint":
                            self.GetWaypoints(manID, Event)

                    elif manType == "Global Actions":
                        if globalActType == "InfrastructureAction":
                            action = etree.SubElement(Event, "Action")
                            action.set("name", "Traffic Light Maneuver ID " + str(feature["id"]))
                            global_action = etree.SubElement(action, "GlobalAction")
                            infra_action = etree.SubElement(global_action, "InfrastructureAction")
                            traffic_signal_action = etree.SubElement(infra_action, "TrafficSignalAction")
                            traffic_signal_state = etree.SubElement(traffic_signal_action, "TrafficSignalStateAction")
                            traffic_ID = "id=" + str(feature["Infra: Traffic Light ID"])
                            traffic_signal_state.set("name", traffic_ID)
                            traffic_signal_state.set("state", feature["Infra: Traffic Light State"])

                    self.GetManeuverStartTrigger(feature, Event)
        else:
            # No maneuvers defined by user
            ManGroup = etree.SubElement(Act, "ManeuverGroup")
            ManGroup.set("maximumExecutionCount", "1")
            ManGroup.set("name", "No Maneuvers Group")
            Actors = etree.SubElement(ManGroup, "Actors")
            Actors.set("selectTriggeringEntities", "false")

            errorMessage = "No maneuvers set"
            iface.messageBar().pushMessage("Error", errorMessage, level=Qgis.Warning)
            QgsMessageLog.logMessage(errorMessage, level=Qgis.Warning)
            self.warningMessage.append(f"Warning: {errorMessage}")

    def MinimalManeuver(self, Act):
        """
        Creates a minimal XML structure to meet OpenSCENARIO specifications
        when no maneuvers are set.
        Entity reference will take any one vehicle spawned (prioritizing ego).

        Creates a speed action at position +100 meters, to prevent scenario from
        exiting immediately after being run.

        Args:
            Act: [XML element]
        """
        entity = ""
        posX = 0
        posY = 0
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            if layer.featureCount() != 0:
                for feature in layer.getFeatures():
                    entity = "Ego_" + str(feature["id"])
                    posX = feature["Pos X"]
                    posY = feature["Pos Y"]
                    break
            else:
                if QgsProject.instance().mapLayersByName("Vehicles"):
                    layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
                    if layer.featureCount() != 0:
                        for feature in layer.getFeatures():
                            entity = "Vehicle_" + str(feature["id"])
                            posX = feature["Pos X"]
                            posY = feature["Pos Y"]
                            break
                    else:
                        errorMessage = "No vehicles available to set as bare minimum entity reference for maneuvers"
                        iface.messageBar().pushMessage("Error", errorMessage, level=Qgis.Critical)
                        QgsMessageLog.logMessage(errorMessage, level=Qgis.Critical)
                        self.warningMessage.append(f"Critical: {errorMessage}")

        ManGroup = etree.SubElement(Act, "ManeuverGroup")
        ManGroup.set("maximumExecutionCount", "1")
        ManGroup.set("name", "No Maneuvers Group")
        Actors = etree.SubElement(ManGroup, "Actors")
        Actors.set("selectTriggeringEntities", "false")
        Actors_EntityRef = etree.SubElement(Actors, "EntityRef")
        Actors_EntityRef.set("entityRef", entity)

        Man = etree.SubElement(ManGroup, "Maneuver")
        Man.set("name", "Generated Maneuver - non user specified")
        Event = etree.SubElement(Man, "Event")
        Event.set("name", "Generated Event - non user defined")
        Event.set("priority", "overwrite")
        Action = etree.SubElement(Event, "Action")
        Action.set("name", "Generated Action - non user defined")
        PrivAct = etree.SubElement(Action, "PrivateAction")
        LongAct = etree.SubElement(PrivAct, "LongitudinalAction")
        SpeedAct = etree.SubElement(LongAct, "SpeedAction")
        SpeedActDynamics = etree.SubElement(SpeedAct, "SpeedActionDynamics")
        SpeedActDynamics.set("dynamicsShape", "step")
        SpeedActDynamics.set("dynamicsDimension", "distance")
        SpeedActDynamics.set("value", "10.0")
        SpeedActTarget = etree.SubElement(SpeedAct, "SpeedActionTarget")
        AbsSpeedTarget = etree.SubElement(SpeedActTarget, "AbsoluteTargetSpeed")
        AbsSpeedTarget.set("value", "5.0")

        StartTrig = etree.SubElement(Event, "StartTrigger")
        CondGroup = etree.SubElement(StartTrig, "ConditionGroup")
        Cond = etree.SubElement(CondGroup, "Condition")
        Cond.set("name", "StartCondition")
        Cond.set("delay", "0")
        Cond.set("conditionEdge", "rising")
        ByEntityCond = etree.SubElement(Cond, "ByEntityCondition")
        TrigEntity = etree.SubElement(ByEntityCond, "TriggeringEntities")
        TrigEntity.set("triggeringEntitiesRule", "any")
        EntityRef = etree.SubElement(TrigEntity, "EntityRef")
        EntityRef.set("entityRef", entity)
        EntityCond = etree.SubElement(ByEntityCond, "EntityCondition")
        ReachPosCond = etree.SubElement(EntityCond, "ReachPositionCondition")
        ReachPosCond.set("tolerance", "2.0")
        Pos = etree.SubElement(ReachPosCond, "Position")
        WorldPos = etree.SubElement(Pos, "WorldPosition")
        WorldPos.set("x", str(posX + 100))
        WorldPos.set("y", str(posY + 100))
        WorldPos.set("z", "0")

    def GetWaypoints(self, maneuverID, event):
        """
        Writes waypoints with the same maneuver ID.

        Args:
            maneuverID: [int] used to match waypoints to same maneuver
            event: [XML element]
        """
        Action = etree.SubElement(event, "Action")
        Action.set("name", "OSC Generated Action")
        PrivAct = etree.SubElement(Action, "PrivateAction")
        RoutingAct = etree.SubElement(PrivAct, "RoutingAction")
        AssignRoute = etree.SubElement(RoutingAct, "AssignRouteAction")
        Route = etree.SubElement(AssignRoute, "Route")
        Route.set("name", "OSC Generated Route")
        Route.set("closed", "false")

        waypointLayer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]
        expression = f"\"Maneuver ID\" is '{maneuverID}'"
        request = QgsFeatureRequest().setFilterExpression(expression)
        for feature in waypointLayer.getFeatures(request):
            Waypoint = etree.SubElement(Route, "Waypoint")
            Waypoint.set("routeStrategy", feature["Route Strategy"])
            Position = etree.SubElement(Waypoint, "Position")
            WorldPosition = etree.SubElement(Position, "WorldPosition")
            WorldPosition.set("x", str(feature["Pos X"]))
            WorldPosition.set("y", str(feature["Pos Y"]))
            WorldPosition.set("z", "0.2")
            WorldPosition.set("h", str(feature["Orientation"]))

    def GetManeuverStartTrigger(self, feature, event):
        """
        Writes waypoints with the same maneuver ID.

        Args:
            feature: [dictionary] used to get variables from QGIS attributes table
            event: [XML element]
        """
        StartTrigger = etree.SubElement(event, "StartTrigger")
        CondGroup = etree.SubElement(StartTrigger, "ConditionGroup")
        Cond = etree.SubElement(CondGroup, "Condition")
        CondName = "Condition for " + feature["Entity"]
        Cond.set("name", CondName)
        Cond.set("delay", "0")
        Cond.set("conditionEdge", "rising")

        if feature["Start Trigger"] == "by Entity":
            ByEntityCond = etree.SubElement(Cond, "ByEntityCondition")
            TrigEntity = etree.SubElement(ByEntityCond, "TriggeringEntities")
            TrigEntity.set("triggeringEntitiesRule", "any")
            TrigEntityRef = etree.SubElement(TrigEntity, "EntityRef")
            TrigEntityRef.set("entityRef", feature["Entity: Ref Entity"])
            EntityCond = etree.SubElement(ByEntityCond, "EntityCondition")
            EntityCondElement = etree.SubElement(EntityCond, feature["Entity: Condition"])

            if (feature["Entity: Condition"] == "EndOfRoadCondition"
                or feature["Entity: Condition"] == "OffroadCondition"
                or feature["Entity: Condition"] == "StandStillCondition"):
                EntityCondElement.set("duration", str(feature["Entity: Duration"]))

            if (feature["Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Entity: Condition"] == "RelativeSpeedCondition"
                or feature["Entity: Condition"] == "RelativeDistanceCondition"):
                EntityCondElement.set("entityRef", feature["Entity: Ref Entity"])

            if (feature["Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Entity: Condition"] == "AccelerationCondition"
                or feature["Entity: Condition"] == "SpeedCondition"
                or feature["Entity: Condition"] == "RelativeSpeedCondition"
                or feature["Entity: Condition"] == "TraveledDistanceCondition"
                or feature["Entity: Condition"] == "RelativeDistanceCondition"):
                EntityCondElement.set("value", str(feature["Entity: Value"]))

            if (feature["Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Entity: Condition"] == "RelativeDistanceCondition"):
                EntityCondElement.set("freespace", str(feature["Entity: Freespace"]).lower())

            if feature["Entity: Condition"] == "TimeHeadwayCondtion":
                EntityCondElement.set("alongRoute", str(feature["Entity: Along Route"]).lower())

            if (feature["Entity: Condition"] == "TimeHeadwayCondition"
                or feature["Entity: Condition"] == "AccelerationCondition"
                or feature["Entity: Condition"] == "SpeedCondition"
                or feature["Entity: Condition"] == "RelativeSpeedCondition"
                or feature["Entity: Condition"] == "RelativeDistanceCondition"):
                EntityCondElement.set("rule", feature["Entity: Rule"])

            if feature["Entity: Condition"] == "ReachPositionCondition":
                EntityCondElement.set("tolerance", str(feature["WorldPos: Tolerance"]))
                position = etree.SubElement(EntityCondElement, "Position")
                world_position = etree.SubElement(position, "WorldPosition")
                world_position.set("x", str(feature["WorldPos: X"]))
                world_position.set("y", str(feature["WorldPos: Y"]))
                world_position.set("z", "0")
                world_position.set("h", str(feature["WorldPos: Heading"]))

        elif feature["Start Trigger"] == "by Value":
            ByValueCond = etree.SubElement(Cond, "ByValueCondition")
            ValueCondElement = etree.SubElement(ByValueCond, feature["Value: Condition"])

            if feature["Value: Condition"] == "ParameterCondition":
                ValueCondElement.set("parameterRef", feature["Value: Param Ref"])

            if (feature["Value: Condition"] == "UserDefinedValueCondition"
                or feature["Value: Condition"] == "TrafficSignalCondition"):
                ValueCondElement.set("name", feature["Value: Name"])

            if (feature["Value: Condition"] == "ParameterCondition"
                or feature["Value: Condition"] == "SimulationTimeCondition"
                or feature["Value: Condition"] == "UserDefinedValueCondition"):
                ValueCondElement.set("value", str(feature["Value: Value"]))

            if (feature["Value: Condition"] == "ParameterCondition"
                or feature["Value: Condition"] == "TimeOfDayCondition"
                or feature["Value: Condition"] == "SimulationTimeCondition"
                or feature["Value: Condition"] == "UserDefinedValueCondition"):
                ValueCondElement.set("rule", feature["Value: Rule"])

            if feature["Value: Condition"] == "TrafficSignalCondition":
                ValueCondElement.set("state", feature["Value: State"])

            if feature["Value: Condition"] == "StoryboardElementStateCondition":
                ValueCondElement.set("storyboardElementType", feature["Value: Sboard Type"])
                ValueCondElement.set("storyboardElementRef", feature["Value: Sboard Element"])
                ValueCondElement.set("state", feature["Value: Sboard State"])

            if feature["Value: Condition"] == "TrafficSignalControllerCondition":
                ValueCondElement.set("trafficSignalControllerRef", feature["Value: TController Ref"])
                ValueCondElement.set("phase", feature["Value: TController Phase"])

    def GetStoryStartTrigger(self, act):
        """
        Writes story start triggers.

        Args:
            act: [XML element]
        """
        act_start = etree.SubElement(act, "StartTrigger")
        ActStart_CondGroup = etree.SubElement(act_start, "ConditionGroup")
        ActStart_TimeCond = etree.SubElement(ActStart_CondGroup, "Condition")
        ActStart_TimeCond.set("name", "StartTime")
        ActStart_TimeCond.set("delay" ,"0")
        ActStart_TimeCond.set("conditionEdge", "rising")
        ActStart_TimeCond_Value = etree.SubElement(ActStart_TimeCond, "ByValueCondition")
        ActStart_TimeCond_Value_SimTime = etree.SubElement(ActStart_TimeCond_Value, "SimulationTimeCondition")
        ActStart_TimeCond_Value_SimTime.set("rule", "equalTo")
        ActStart_TimeCond_Value_SimTime.set("value", "0")

    def GetStoryStopTrigger(self, act):
        """
        Writes story stop triggers.

        Args:
            act: [XML element]
        """
        Stop = etree.SubElement(act, "StopTrigger")
        CondGroup = etree.SubElement(Stop, "ConditionGroup")
        Cond = etree.SubElement(CondGroup, "Condition")
        Cond.set("name", "EndCondition")
        Cond.set("delay" ,"0")
        Cond.set("conditionEdge", "rising")
        ByValueCond = etree.SubElement(Cond, "ByValueCondition")
        SimTime = etree.SubElement(ByValueCond, "SimulationTimeCondition")
        SimTime.set("rule", "equalTo")
        SimTime.set("value", "100")

    def GetEndEvalCriteria(self, storyboard):
        """
        Writes scenario completion scenario checks for scenario_runner.

        Args:
            storyboard: [XML element]
        """
        Stop = etree.SubElement(storyboard, "StopTrigger")

        if QgsProject.instance().mapLayersByName("End Evaluation KPIs"):
            stopTriggerLayer = QgsProject.instance().mapLayersByName("End Evaluation KPIs")[0]
            for feature in stopTriggerLayer.getFeatures():
                condName = feature["Condition Name"]
                delay = str(feature["Delay"])
                condEdge = feature["Condition Edge"]
                paramRef = feature["Parameter Ref"]
                value = str(feature["Value"])
                rule = feature["Rule"]

                StopCondGroup = etree.SubElement(Stop, "ConditionGroup")
                StopCond = etree.SubElement(StopCondGroup, "Condition")
                StopCond.set("name", condName)
                StopCond.set("delay", delay)
                StopCond.set("conditionEdge", condEdge)
                StopCond_ByValue = etree.SubElement(StopCond, "ByValueCondition")
                StopCond_ParamCond = etree.SubElement(StopCond_ByValue, "ParameterCondition")
                StopCond_ParamCond.set("parameterRef", paramRef)
                StopCond_ParamCond.set("value", value)
                StopCond_ParamCond.set("rule", rule)

        else:
            iface.messageBar().pushMessage("Warning", "No end evaluation KPIs detected", level=Qgis.Warning)
            QgsMessageLog.logMessage("No end evaluation KPIs detected", level=Qgis.Warning)

    def WriteXOSC(self, generatedXML):
        """
        Save and export pretty printed XOSC file.

        Args:
            generatedXML: [string] generated XML from ElementTree
        """
        reparsedXML = minidom.parseString(generatedXML).toprettyxml(indent="    ")
        XOSCfile = open(self.filepath, "w")
        XOSCfile.write(reparsedXML)
        XOSCfile.close()

        if self.warningMessage:
            text = f"Exported OpenSCENARIO file to {self.filepath} with warning: \n\n"
            text += "\n".join(self.warningMessage)
        else:
            text = f"Successfully exported OpenSCENARIO file to {self.filepath}"
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setText(text)
        msg.setWindowTitle("OpenSCENARIO Export")
        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec()
