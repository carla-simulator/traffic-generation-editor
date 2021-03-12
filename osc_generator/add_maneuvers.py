# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Maneuvers
"""
import os
import math
# pylint: disable=no-name-in-module, no-member
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.gui import QgsMapTool
from qgis.utils import iface
from qgis.core import (QgsProject, QgsVectorLayer, QgsMessageLog, Qgis, QgsField,
    QgsFeature, QgsGeometry, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBackgroundSettings)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QInputDialog

# AD Map plugin
import ad_map_access as ad

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'add_maneuvers_widget.ui'))


class AddManeuversDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to add scenario maneuvers.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Initialization of AddManeuversDockWidget"""
        super(AddManeuversDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.refreshEntity_Button.pressed.connect(self.refresh_entity)
        self.addManeuver_Button.pressed.connect(self.add_maneuvers)
        self.entityManeuverType.currentTextChanged.connect(self.change_maneuver)
        self.waypointOrientation_useLane.stateChanged.connect(self.override_orientation)
        self.conditionType.currentTextChanged.connect(self.update_start_trigger_condition)
        self.valueCond.currentTextChanged.connect(self.update_value_condition_parameters)
        self.entityCond.currentTextChanged.connect(self.update_entity_condition_parameters)
        self.entitySelection.currentTextChanged.connect(self.update_ref_entity)
        self.lateral_Type.currentTextChanged.connect(self.change_lateral_type)
        self.long_Type.currentTextChanged.connect(self.change_longitudinal_type)
        self.long_SpeedTarget.currentTextChanged.connect(self.change_longitudinal_speed_target)

        self.toggleTrafficLightLabels_Button.pressed.connect(self.toggle_traffic_light_labels)
        self.refreshTrafficLights_Button.pressed.connect(self.refresh_traffic_lights)
        self.entityChoosePosition_Button.pressed.connect(self.get_world_position)

        self._waypoint_layer = None
        self._maneuver_layer = None
        self._long_man_layer = None
        self._lat_man_layer = None
        self._man_id = None
        self._traffic_labels_on = False
        self._traffic_labels_setup = False
        self._traffic_lights_layer = None
        self.layer_setup()
        self.refresh_entity()
        self.refresh_traffic_lights()

    def layer_setup(self):
        """
        Sets up layers for maneuvers
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")

        # Waypoint maneuvers
        if not QgsProject.instance().mapLayersByName("Waypoint Maneuvers"):
            waypoint_layer = QgsVectorLayer("Point", "Waypoint Maneuvers", "memory")
            QgsProject.instance().addMapLayer(waypoint_layer, False)
            osc_layer.addLayer(waypoint_layer)
            # Setup layer attributes
            data_attributes = [QgsField("Maneuver ID", QVariant.Int),
                               QgsField("Entity", QVariant.String),
                               QgsField("Waypoint No", QVariant.Int),
                               QgsField("Orientation", QVariant.Double),
                               QgsField("Pos X", QVariant.Double),
                               QgsField("Pos Y", QVariant.Double),
                               QgsField("Route Strategy", QVariant.String)]
            data_input = waypoint_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            waypoint_layer.updateFields()

            message = "Waypoint maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            message = "Using existing waypoint maneuver layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._waypoint_layer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]
        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_name = "concat('ManID: ', \"Maneuver ID\", ' ', \"Entity\", ' - ', \"Waypoint No\")"
        label_settings.fieldName = label_name
        self._waypoint_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        self._waypoint_layer.setLabelsEnabled(True)

        # Maneuvers + Start Triggers + Stop Triggers
        if not QgsProject.instance().mapLayersByName("Maneuvers"):
            maneuver_layer = QgsVectorLayer("None", "Maneuvers", "memory")
            QgsProject.instance().addMapLayer(maneuver_layer, False)
            osc_layer.addLayer(maneuver_layer)
            # Setup layer attributes
            data_attributes = [QgsField("id", QVariant.Int),
                               QgsField("Maneuver Type", QVariant.String),
                               QgsField("Entity", QVariant.String),
                               QgsField("Entity: Maneuver Type", QVariant.String),
                               QgsField("Start Trigger", QVariant.String),
                               QgsField("Start - Entity: Condition", QVariant.String),
                               QgsField("Start - Entity: Ref Entity", QVariant.String),
                               QgsField("Start - Entity: Duration", QVariant.Double),
                               QgsField("Start - Entity: Value", QVariant.Double),
                               QgsField("Start - Entity: Rule", QVariant.String),
                               QgsField("Start - Entity: RelDistType", QVariant.String),
                               QgsField("Start - Entity: Freespace", QVariant.Bool),
                               QgsField("Start - Entity: Along Route", QVariant.Bool),
                               QgsField("Start - Value: Condition", QVariant.String),
                               QgsField("Start - Value: Param Ref", QVariant.String),
                               QgsField("Start - Value: Name", QVariant.String),
                               QgsField("Start - Value: DateTime", QVariant.String),
                               QgsField("Start - Value: Value", QVariant.Double),
                               QgsField("Start - Value: Rule", QVariant.String),
                               QgsField("Start - Value: State", QVariant.String),
                               QgsField("Start - Value: Sboard Type", QVariant.String),
                               QgsField("Start - Value: Sboard Element", QVariant.String),
                               QgsField("Start - Value: Sboard State", QVariant.String),
                               QgsField("Start - Value: TController Ref", QVariant.String),
                               QgsField("Start - Value: TController Phase", QVariant.String),
                               QgsField("Global: Act Type", QVariant.String),
                               QgsField("Infra: Traffic Light ID", QVariant.Int),
                               QgsField("Infra: Traffic Light State", QVariant.String),
                               QgsField("Start - WorldPos: Tolerance", QVariant.Double),
                               QgsField("Start - WorldPos: X", QVariant.Double),
                               QgsField("Start - WorldPos: Y", QVariant.Double),
                               QgsField("Start - WorldPos: Heading", QVariant.Double),
                               # Stop Triggers
                               QgsField("Stop Trigger Enabled", QVariant.Bool),
                               QgsField("Stop Trigger", QVariant.String),
                               QgsField("Stop - Entity: Condition", QVariant.String),
                               QgsField("Stop - Entity: Ref Entity", QVariant.String),
                               QgsField("Stop - Entity: Duration", QVariant.Double),
                               QgsField("Stop - Entity: Value", QVariant.Double),
                               QgsField("Stop - Entity: Rule", QVariant.String),
                               QgsField("Stop - Entity: RelDistType", QVariant.String),
                               QgsField("Stop - Entity: Freespace", QVariant.Bool),
                               QgsField("Stop - Entity: Along Route", QVariant.Bool),
                               QgsField("Stop - Value: Condition", QVariant.String),
                               QgsField("Stop - Value: Param Ref", QVariant.String),
                               QgsField("Stop - Value: Name", QVariant.String),
                               QgsField("Stop - Value: DateTime", QVariant.String),
                               QgsField("Stop - Value: Value", QVariant.Double),
                               QgsField("Stop - Value: Rule", QVariant.String),
                               QgsField("Stop - Value: State", QVariant.String),
                               QgsField("Stop - Value: Sboard Type", QVariant.String),
                               QgsField("Stop - Value: Sboard Element", QVariant.String),
                               QgsField("Stop - Value: Sboard State", QVariant.String),
                               QgsField("Stop - Value: TController Ref", QVariant.String),
                               QgsField("Stop - Value: TController Phase", QVariant.String),
                               QgsField("Stop - WorldPos: Tolerance", QVariant.Double),
                               QgsField("Stop - WorldPos: X", QVariant.Double),
                               QgsField("Stop - WorldPos: Y", QVariant.Double),
                               QgsField("Stop - WorldPos: Heading", QVariant.Double)]
            data_input = maneuver_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            maneuver_layer.updateFields()

            message = "Maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            message = "Using existing maneuvers layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._maneuver_layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]

        # Longitudinal Maneuvers
        if not QgsProject.instance().mapLayersByName("Longitudinal Maneuvers"):
            long_man_layer = QgsVectorLayer("None", "Longitudinal Maneuvers", "memory")
            QgsProject.instance().addMapLayer(long_man_layer, False)
            osc_layer.addLayer(long_man_layer)
            # Setup layer attributes
            data_attributes = [QgsField("Maneuver ID", QVariant.Int),
                               QgsField("Type", QVariant.String),
                               QgsField("Speed Target", QVariant.String),
                               QgsField("Ref Entity", QVariant.String),
                               QgsField("Dynamics Shape", QVariant.String),
                               QgsField("Dynamics Dimension", QVariant.String),
                               QgsField("Dynamics Value", QVariant.Double),
                               QgsField("Target Type", QVariant.String),
                               QgsField("Target Speed", QVariant.Double),
                               QgsField("Continuous", QVariant.Bool),
                               QgsField("Freespace", QVariant.Bool),
                               QgsField("Max Acceleration", QVariant.Double),
                               QgsField("Max Deceleration", QVariant.Double),
                               QgsField("Max Speed", QVariant.Double)]
            data_input = long_man_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            long_man_layer.updateFields()

            message = "Longitudinal maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            message = "Using existing longitudinal maneuvers layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._long_man_layer = QgsProject.instance().mapLayersByName("Longitudinal Maneuvers")[0]

        # Lateral Maneuvers
        if not QgsProject.instance().mapLayersByName("Lateral Maneuvers"):
            lat_man_layer = QgsVectorLayer("None", "Lateral Maneuvers", "memory")
            QgsProject.instance().addMapLayer(lat_man_layer, False)
            osc_layer.addLayer(lat_man_layer)
            # Setup layer attributes
            data_attributes = [QgsField("Maneuver ID", QVariant.Int),
                               QgsField("Type", QVariant.String),
                               QgsField("Lane Target", QVariant.String),
                               QgsField("Ref Entity", QVariant.String),
                               QgsField("Dynamics Shape", QVariant.String),
                               QgsField("Dynamics Dimension", QVariant.String),
                               QgsField("Dynamics Value", QVariant.Double),
                               QgsField("Lane Target Value", QVariant.String),
                               QgsField("Max Lateral Acceleration", QVariant.Double),
                               QgsField("Max Acceleration", QVariant.Double),
                               QgsField("Max Deceleration", QVariant.Double),
                               QgsField("Max Speed", QVariant.Double)]
            data_input = lat_man_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            lat_man_layer.updateFields()

            message = "Lateral maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            message = "Using existing lateral maneuvers layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._lat_man_layer = QgsProject.instance().mapLayersByName("Lateral Maneuvers")[0]

    def refresh_entity(self):
        """
        Gets list of entities spawned on map and populates drop down
        """
        self.entitySelection.clear()
        self.entityTrig_RefEntity.clear()
        self.lateral_RefEntity.clear()
        self.long_RefEntity.clear()
        self.stop_Entity_RefEntity.clear()

        entities = []
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in layer.getFeatures():
                veh_id = "Ego_" + str(feature["id"])
                entities.append(veh_id)

        if QgsProject.instance().mapLayersByName("Vehicles"):
            layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in layer.getFeatures():
                veh_id = "Vehicle_" + str(feature["id"])
                entities.append(veh_id)

        if QgsProject.instance().mapLayersByName("Pedestrians"):
            layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in layer.getFeatures():
                ped_id = "Pedestrian_" + str(feature["id"])
                entities.append(ped_id)

        self.entitySelection.addItems(entities)
        self.entityTrig_RefEntity.addItems(entities)
        self.lateral_RefEntity.addItems(entities)
        self.long_RefEntity.addItems(entities)
        self.stop_Entity_RefEntity.addItems(entities)

    def update_ref_entity(self):
        """
        Updates start trigger reference entity to match selected entity by default.
        """
        selected_entity = self.entitySelection.currentText()
        # Start Trigger (Ref Entity)
        index = self.entityTrig_RefEntity.findText(selected_entity)
        self.entityTrig_RefEntity.setCurrentIndex(index)

        # Stop Trigger (Ref Entity)
        index = self.stop_Entity_RefEntity.findText(selected_entity)
        self.stop_Entity_RefEntity.setCurrentIndex(index)

        # Lateral reference entity
        index = self.lateral_RefEntity.findText(selected_entity)
        self.lateral_RefEntity.setCurrentIndex(index)

        # Longitudinal reference entity
        index = self.long_RefEntity.findText(selected_entity)
        self.long_RefEntity.setCurrentIndex(index)

    def override_orientation(self):
        """
        Toggles orientation field on and off
        """
        if self.waypointOrientation_useLane.isChecked():
            self.waypointOrientation.setDisabled(True)
        else:
            self.waypointOrientation.setEnabled(True)

    def toggle_traffic_light_labels(self):
        """
        Toggles labels for traffic light IDs
        """
        if self._traffic_labels_setup is False:
            self._traffic_lights_layer = QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT")[0]
            label_settings = QgsPalLayerSettings()
            label_settings.isExpression = True
            label_settings.fieldName = "\"Id\""
            text_format = QgsTextFormat()
            text_background = QgsTextBackgroundSettings()
            text_background.setFillColor(QColor('white'))
            text_background.setEnabled(True)
            text_background.setType(QgsTextBackgroundSettings.ShapeCircle)
            text_format.setBackground(text_background)
            label_settings.setFormat(text_format)
            self._traffic_lights_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            self._traffic_lights_layer.setLabelsEnabled(True)

        if self._traffic_labels_on:
            self._traffic_lights_layer.setLabelsEnabled(False)
            self._traffic_labels_on = False
        else:
            self._traffic_lights_layer.setLabelsEnabled(True)
            self._traffic_labels_on = True

        self._traffic_lights_layer.triggerRepaint()

    def refresh_traffic_lights(self):
        """
        Gets list of traffic light IDs spawned on map and populates drop down
        """
        self.trafficLightID.clear()
        traffic_light_ids = []
        if QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT"):
            layer = QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT")[0]
            for feature in layer.getFeatures():
                traffic_light_id = str(feature["Id"])
                traffic_light_ids.append(traffic_light_id)

        self.trafficLightID.addItems(traffic_light_ids)

    def closeEvent(self, event):
        """
        Dockwidget closing event
        """
        self.closingPlugin.emit()
        event.accept()

    def add_maneuvers(self):
        """
        Insert maneuvers
        """
        self.get_maneuver_id()

        canvas = iface.mapCanvas()

        if self.maneuverType.currentText() == "Entity Maneuvers":
            if self.entityManeuverType.currentText() == "Waypoint":
                entity = self.entitySelection.currentText()
                if self.waypointOrientation_useLane.isChecked():
                    entity_orientation = None
                else:
                    entity_orientation = math.radians(float(self.waypointOrientation.text()))

                entity_attributes = {"Maneuver ID": self._man_id,
                                    "Entity":entity,
                                    "Orientation":entity_orientation,
                                    "Route Strat":self.waypointStrategy.currentText()}
                tool = PointTool(canvas, self._waypoint_layer, entity_attributes, layer_type="Waypoints")
                canvas.setMapTool(tool)
            elif self.entityManeuverType.currentText() == "Longitudinal":
                self.save_longitudinal_attributes()
            elif self.entityManeuverType.currentText() == "Lateral":
                self.save_lateral_attributes()
        elif self.maneuverType.currentText() == "Global Actions":
            # Infrastructure actions are saved inside Maneuvers layer
            pass

        self.save_maneuver_attributes()

    def change_maneuver(self):
        """
        Enables / disables group boxes depending on type of maneuver selected.
        """
        if self.entityManeuverType.currentText() == "Waypoint":
            self.waypointGroup.setEnabled(True)
            self.lateralGroup.setDisabled(True)
            self.longitudinalGroup.setDisabled(True)
        elif self.entityManeuverType.currentText() == "Longitudinal":
            self.waypointGroup.setDisabled(True)
            self.lateralGroup.setDisabled(True)
            self.longitudinalGroup.setEnabled(True)
        elif self.entityManeuverType.currentText() == "Lateral":
            self.waypointGroup.setDisabled(True)
            self.lateralGroup.setEnabled(True)
            self.longitudinalGroup.setDisabled(True)

    def change_lateral_type(self):
        """
        Enables / disables fields for lateral maneuvers based on type of lateral maneuvers.
        """
        if self.lateral_Type.currentText() == "LaneChangeAction":
            self.lateral_DynamicsDim.setEnabled(True)
            self.lateral_DynamicsShape.setEnabled(True)
            self.lateral_DynamicsValue.setEnabled(True)
            self.lateral_LaneTargetValue.setEnabled(True)
            self.lateral_RefEntity.setEnabled(True)
            self.lateral_LaneTarget.setEnabled(True)
            self.lateral_MaxLatAccel.setDisabled(True)
            self.lateral_MaxAccel.setDisabled(True)
            self.lateral_MaxDecel.setDisabled(True)
            self.lateral_MaxSpeed.setDisabled(True)
            lane_targets = ["RelativeTargetLane", "AbsoluteTargetLane"]
            self.lateral_LaneTarget.clear()
            self.lateral_LaneTarget.addItems(lane_targets)

        elif self.lateral_Type.currentText() == "LaneOffsetAction":
            self.lateral_MaxLatAccel.setEnabled(True)
            self.lateral_DynamicsShape.setEnabled(True)
            self.lateral_LaneTargetValue.setEnabled(True)
            self.lateral_RefEntity.setEnabled(True)
            self.lateral_LaneTarget.setEnabled(True)
            self.lateral_MaxAccel.setDisabled(True)
            self.lateral_MaxDecel.setDisabled(True)
            self.lateral_MaxSpeed.setDisabled(True)
            self.lateral_DynamicsDim.setDisabled(True)
            self.lateral_DynamicsValue.setDisabled(True)
            lane_targets = ["RelativeTargetLaneOffset", "AbsoluteTargetLaneOffset"]
            self.lateral_LaneTarget.clear()
            self.lateral_LaneTarget.addItems(lane_targets)

        elif self.lateral_Type.currentText() == "LateralDistanceAction":
            self.lateral_MaxAccel.setEnabled(True)
            self.lateral_MaxDecel.setEnabled(True)
            self.lateral_MaxSpeed.setEnabled(True)
            self.lateral_MaxLatAccel.setDisabled(True)
            self.lateral_LaneTargetValue.setDisabled(True)
            self.lateral_DynamicsDim.setDisabled(True)
            self.lateral_DynamicsShape.setDisabled(True)
            self.lateral_DynamicsValue.setDisabled(True)
            self.lateral_RefEntity.setDisabled(True)
            self.lateral_LaneTarget.setDisabled(True)

    def change_longitudinal_type(self):
        """
        Enables / disables fields for longitudinal maneuvers based on type.
        """
        if self.long_Type.currentText() == "SpeedAction":
            self.long_RefEntity.setEnabled(True)
            self.long_SpeedTarget.setEnabled(True)
            self.long_DynamicsShape.setEnabled(True)
            self.long_DynamicsDim.setEnabled(True)
            self.long_DynamicsValue.setEnabled(True)
            self.long_TargetType.setEnabled(True)
            self.long_TargetSpeedValue.setEnabled(True)
            self.long_Continuous.setEnabled(True)
            self.long_MaxAccel.setDisabled(True)
            self.long_MaxDecel.setDisabled(True)
            self.long_MaxSpeed.setDisabled(True)
            self.long_Freespace.setDisabled(True)
        elif self.long_Type.currentText() == "LongitudinalDistanceAction":
            self.long_MaxAccel.setEnabled(True)
            self.long_MaxDecel.setEnabled(True)
            self.long_MaxSpeed.setEnabled(True)
            self.long_RefEntity.setEnabled(True)
            self.long_Continuous.setEnabled(True)
            self.long_Freespace.setEnabled(True)
            self.long_SpeedTarget.setDisabled(True)
            self.long_DynamicsShape.setDisabled(True)
            self.long_DynamicsDim.setDisabled(True)
            self.long_DynamicsValue.setDisabled(True)
            self.long_TargetType.setDisabled(True)
            self.long_TargetSpeedValue.setDisabled(True)

    def change_longitudinal_speed_target(self):
        """
        Enables / disables fields for longitudinal maneuvers based on type.
        """
        if self.long_SpeedTarget.currentText() == "RelativeTargetSpeed":
            self.long_RefEntity.setEnabled(True)
            self.long_TargetSpeedValue.setEnabled(True)
            self.long_TargetType.setEnabled(True)
            self.long_Continuous.setEnabled(True)
        elif self.long_SpeedTarget.currentText() == "AbsoluteTargetSpeed":
            self.long_TargetSpeedValue.setEnabled(True)
            self.long_RefEntity.setDisabled(True)
            self.long_TargetType.setDisabled(True)
            self.long_Continuous.setDisabled(True)

    def get_world_position(self):
        """
        Gets world position from map
        """
        canvas = iface.mapCanvas()
        entity_attributes = {"Orientation": None}
        tool = PointTool(canvas, self._maneuver_layer, entity_attributes, layer_type="Position", parent=self)
        canvas.setMapTool(tool)

    def update_value_condition_parameters(self):
        """
        Enables / disables parameters for Value Conditions based on condition selected.
        """
        # Parameter Reference
        if self.valueCond.currentText() == "ParameterCondition":
            self.Value_ParamRef.setEnabled(True)
        else:
            self.Value_ParamRef.setDisabled(True)

        # Name
        if (self.valueCond.currentText() == "UserDefinedValueCondition"
            or self.valueCond.currentText() == "TrafficSignalCondition"):
            self.Value_Name.setEnabled(True)
        else:
            self.Value_Name.setDisabled(True)

        # DateTime
        if self.valueCond.currentText() == "TimeOfDayCondition":
            self.Value_DateTime.setEnabled(True)
        else:
            self.Value_DateTime.setDisabled(True)

        # Value
        if (self.valueCond.currentText() == "ParameterCondition"
            or self.valueCond.currentText() == "SimulationTimeCondition"
            or self.valueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Value.setEnabled(True)
        else:
            self.Value_Value.setDisabled(True)

        # Rule
        if (self.valueCond.currentText() == "ParameterCondition"
            or self.valueCond.currentText() == "TimeOfDayCondition"
            or self.valueCond.currentText() == "SimulationTimeCondition"
            or self.valueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Rule.setEnabled(True)
        else:
            self.Value_Rule.setDisabled(True)

        # State
        if self.valueCond.currentText() == "TrafficSignalCondition":
            self.Value_State.setEnabled(True)
        else:
            self.Value_State.setDisabled(True)

        # Storyboard elements
        if self.valueCond.currentText() == "StoryboardElementStateCondition":
            self.StoryboardGroup.setEnabled(True)
        else:
            self.StoryboardGroup.setDisabled(True)

        # Traffic signal controller
        if self.valueCond.currentText() == "TrafficSignalControllerCondition":
            self.TrafficSignalGroup.setEnabled(True)
        else:
            self.TrafficSignalGroup.setDisabled(True)

    def update_entity_condition_parameters(self):
        """
        Enables / disables parameters for Entity Conditions based on condition selected.
        """
        # Entity Ref
        if (self.entityCond.currentText() == "TimeHeadwayCondition"
            or self.entityCond.currentText() == "RelativeSpeedCondition"
            or self.entityCond.currentText() == "RelativeDistanceCondition"
            or self.entityCond.currentText() == "ReachPositionCondition"):
            self.entityTrig_RefEntity.setEnabled(True)
        else:
            self.entityTrig_RefEntity.setDisabled(True)

        # Duration
        if (self.entityCond.currentText() == "EndOfRoadCondition"
            or self.entityCond.currentText() == "OffroadCondition"
            or self.entityCond.currentText() == "StandStillCondition"):
            self.Entity_Duration.setEnabled(True)
        else:
            self.Entity_Duration.setDisabled(True)

        # Value (setting disabled)
        if (self.entityCond.currentText() == "EndOfRoadCondition"
            or self.entityCond.currentText() == "CollisionCondition"
            or self.entityCond.currentText() == "OffroadCondition"
            or self.entityCond.currentText() == "TimeToCollisionCondition"
            or self.entityCond.currentText() == "StandStillCondition"
            or self.entityCond.currentText() == "ReachPositionCondition"
            or self.entityCond.currentText() == "DistanceCondition"):
            self.Entity_Value.setDisabled(True)
        else:
            self.Entity_Value.setEnabled(True)

        # Rule (setting disabled)
        if (self.entityCond.currentText() == "EndOfRoadCondition"
            or self.entityCond.currentText() == "OffroadCondition"
            or self.entityCond.currentText() == "StandStillCondition"
            or self.entityCond.currentText() == "TraveledDistanceCondition"
            or self.entityCond.currentText() == "ReachPositionCondition"):
            self.Entity_Rule.setDisabled(True)
        else:
            self.Entity_Rule.setEnabled(True)

        # Relative Distance
        if self.entityCond.currentText() == "RelativeDistanceCondition":
            self.Entity_RelDistType.setEnabled(True)
        else:
            self.Entity_RelDistType.setDisabled(True)

        # Freespace
        if (self.entityCond.currentText() == "TimeHeadwayCondition"
            or self.entityCond.currentText() == "RelativeDistanceCondition"):
            self.Entity_Freespace.setEnabled(True)
        else:
            self.Entity_Freespace.setDisabled(True)

        # Along Route
        if self.entityCond.currentText() == "TimeHeadwayCondition":
            self.Entity_AlongRoute.setEnabled(True)
        else:
            self.Entity_AlongRoute.setDisabled(True)

        # Position
        if self.entityCond.currentText() == "ReachPositionCondition":
            self.Entity_PositionGroup.setEnabled(True)
        else:
            self.Entity_PositionGroup.setDisabled(True)

    def update_start_trigger_condition(self):
        """
        Enables / disables groups based on trigger condition selected.
        """
        if self.conditionType.currentText() == "by Entity":
            self.EntityConditionGroup.setEnabled(True)
            self.ValueConditionGroup.setDisabled(True)
        else:
            self.EntityConditionGroup.setDisabled(True)
            self.ValueConditionGroup.setEnabled(True)

    def get_maneuver_id(self):
        """
        Generates maneuver ID
        """
        if self._maneuver_layer.featureCount() != 0:
            idx = self._maneuver_layer.fields().indexFromName("id")
            largest_man_id = self._maneuver_layer.maximumValue(idx)
            self._man_id = largest_man_id + 1
        else:
            self._man_id = 1

    def save_maneuver_attributes(self):
        """
        Gets maneuver attributes and saves into QGIS attributes table.
        """
        feature = QgsFeature()
        feature.setAttributes([self._man_id,
                               self.maneuverType.currentText(),
                               self.entitySelection.currentText(),
                               self.entityManeuverType.currentText(),
                               self.conditionType.currentText(),
                               self.entityCond.currentText(),
                               self.entityTrig_RefEntity.currentText(),
                               float(self.Entity_Duration.text()),
                               float(self.Entity_Value.text()),
                               self.Entity_Rule.currentText(),
                               self.Entity_RelDistType.currentText(),
                               self.Entity_Freespace.isChecked(),
                               self.Entity_AlongRoute.isChecked(),
                               self.valueCond.currentText(),
                               self.Value_ParamRef.text(),
                               self.Value_Name.text(),
                               self.Value_DateTime.dateTime().toString("yyyy-MM-ddThh:mm:ss"),
                               float(self.Value_Value.text()),
                               self.Value_Rule.currentText(),
                               self.Value_State.text(),
                               self.Storyboard_Type.currentText(),
                               self.Storyboard_Element.text(),
                               self.Storyboard_State.currentText(),
                               self.TrafficSignal_ControllerRef.text(),
                               self.TrafficSignal_Phase.text(),
                               self.globalActType.currentText(),
                               int(self.trafficLightID.currentText()),
                               self.trafficLightState.currentText(),
                               float(self.entityTolerance.text()),
                               float(self.entityPositionX.text()),
                               float(self.entityPositionY.text()),
                               float(self.entityHeading.text()),
                               # Stop Triggers
                               self.stopTriggersGroup.isChecked(),
                               self.stop_ConditionType.currentText(),
                               self.stop_Entity_Cond.currentText(),
                               self.stop_Entity_RefEntity.currentText(),
                               self.stop_Entity_Duration.text(),
                               self.stop_Entity_Value.text(),
                               self.stop_Entity_Rule.currentText(),
                               self.stop_Entity_RelDistType.currentText(),
                               self.stop_Entity_Freespace.isChecked(),
                               self.stop_Entity_AlongRoute.isChecked(),
                               self.stop_Value_Cond.currentText(),
                               self.stop_Value_ParamRef.text(),
                               self.stop_Value_Name.text(),
                               self.stop_Value_DateTime.dateTime().toString("yyyy-MM-ddThh:mm:ss"),
                               float(self.stop_Value_Value.text()),
                               self.stop_Value_Rule.currentText(),
                               self.stop_Value_State.text(),
                               self.stop_Storyboard_Type.currentText(),
                               self.stop_Storyboard_Element.text(),
                               self.stop_Storyboard_State.currentText(),
                               self.stop_TrafficSignal_ControllerRef.text(),
                               self.stop_TrafficSignal_Phase.text(),
                               float(self.stop_Entity_Tolerance.text()),
                               float(self.stop_Entity_PositionX.text()),
                               float(self.stop_Entity_PositionY.text()),
                               float(self.stop_Entity_Heading.text())])
        self._maneuver_layer.dataProvider().addFeature(feature)

    def save_longitudinal_attributes(self):
        """
        Gets longudinal maneuver attributes and saves into QGIS attributes table.
        """
        feature = QgsFeature()
        feature.setAttributes([self._man_id,
                               self.long_Type.currentText(),
                               self.long_SpeedTarget.currentText(),
                               self.long_RefEntity.currentText(),
                               self.long_DynamicsShape.currentText(),
                               self.long_DynamicsDim.currentText(),
                               float(self.long_DynamicsValue.text()),
                               self.long_TargetType.currentText(),
                               float(self.long_TargetSpeedValue.text()),
                               self.long_Continuous.isChecked(),
                               self.long_Freespace.isChecked(),
                               float(self.long_MaxAccel.text()),
                               float(self.long_MaxDecel.text()),
                               float(self.long_MaxSpeed.text())])
        self._long_man_layer.dataProvider().addFeature(feature)

        message = "Maneuver added"
        iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)

    def save_lateral_attributes(self):
        """
        Gets lateral maneuver attributes and saves into QGIS attributes table.
        """
        feature = QgsFeature()
        feature.setAttributes([self._man_id,
                               self.lateral_Type.currentText(),
                               self.lateral_LaneTarget.currentText(),
                               self.lateral_RefEntity.currentText(),
                               self.lateral_DynamicsShape.currentText(),
                               self.lateral_DynamicsDim.currentText(),
                               float(self.lateral_DynamicsValue.text()),
                               self.lateral_LaneTargetValue.text(),
                               float(self.lateral_MaxLatAccel.text()),
                               float(self.lateral_MaxAccel.text()),
                               float(self.lateral_MaxDecel.text()),
                               float(self.lateral_MaxSpeed.text())])
        self._lat_man_layer.dataProvider().addFeature(feature)

        message = "Maneuver added"
        iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)

#pylint: disable=missing-function-docstring
class PointTool(QgsMapTool):
    """Enables Point Addition"""

    def __init__(self, canvas, layer, entity_attributes, layer_type, parent=None):
        QgsMapTool.__init__(self, canvas)
        self._canvas = canvas
        self._type = layer_type
        self._layer = layer
        self._data_input = layer.dataProvider()
        self._canvas.setCursor(Qt.CrossCursor)
        self._entity_attributes = entity_attributes
        self._parent = parent
        if self._entity_attributes["Orientation"] is None:
            self._use_lane_heading = True
        else:
            self._use_lane_heading = False
        iface.setActiveLayer(self._layer)

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        # Get the click
        x = event.pos().x()
        y = event.pos().y()
        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # Converting to ENU points
        geopoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=0)
        enupoint = ad.map.point.toENU(geopoint)
        add_entity_attr = AddManeuverAttributes()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._entity_attributes["Orientation"] = add_entity_attr.get_entity_heading(geopoint)

        # If point type is waypoint, spawn points, else pass click parameters
        if self._type == "Waypoints":
            # Add points only if user clicks within lane boundaries (Orientation is not None)
            if self._entity_attributes["Orientation"] is not None:
                processed_attrs = add_entity_attr.get_entity_waypoint_attributes(self._layer, self._entity_attributes)

                # Set attributes
                feature = QgsFeature()
                feature.setAttributes([processed_attrs["Maneuver ID"],
                                      processed_attrs["Entity"],
                                      int(processed_attrs["Waypoint No"]),
                                      float(processed_attrs["Orientation"]),
                                      float(enupoint.x),
                                      float(enupoint.y),
                                      processed_attrs["Route Strat"]])
                feature.setGeometry(QgsGeometry.fromPointXY(point))
                self._data_input.addFeature(feature)
        elif self._type == "Position":
            heading = add_entity_attr.get_entity_heading(geopoint)
            self._parent.entityPositionX.setText(str(enupoint.x))
            self._parent.entityPositionY.setText(str(enupoint.y))
            self._parent.entityHeading.setText(str(heading))
            self._canvas.unsetMapTool(self)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()

    def activate(self):
        pass

    def deactivate(self):
        pass

    def isZoomTool(self):
        return False

    def isTransient(self):
        return True

    def isEditTool(self):
        return True
#pylint: enable=missing-function-docstring

class AddManeuverAttributes():
    """
    Handles processing of maneuver attributes.
    """
    def get_entity_heading(self, geopoint):
        """
        Acquires heading based on spawn position in map.
        Prompts user to select lane if multiple lanes exist at spawn position.
        Throws error if spawn position is not on lane.

        Args:
            geopoint: [AD Map GEOPoint] point of click event

        Returns:
            lane_heading: [float] heading of click point at selected lane ID
            lane_heading: [None] if click point is not valid
        """
        dist = ad.physics.Distance(0.025)
        admap_matched_points = ad.map.match.AdMapMatching.findLanes(geopoint, dist)

        lanes_detected = 0
        for point in admap_matched_points:
            lanes_detected += 1

        if lanes_detected == 0:
            message = "Click point is too far from valid lane"
            iface.messageBar().pushMessage("Error", message, level=Qgis.Critical)
            QgsMessageLog.logMessage(message, level=Qgis.Critical)
            return None
        elif lanes_detected == 1:
            for point in admap_matched_points:
                lane_id = point.lanePoint.paraPoint.laneId
                para_offset = point.lanePoint.paraPoint.parametricOffset
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading
        else:
            lane_ids_to_match = []
            lane_ids = []
            para_offsets = []
            for point in admap_matched_points:
                lane_ids_to_match.append(str(point.lanePoint.paraPoint.laneId))
                lane_ids.append(point.lanePoint.paraPoint.laneId)
                para_offsets.append(point.lanePoint.paraPoint.parametricOffset)

            lane_id_selected, ok_pressed = QInputDialog.getItem(
                QInputDialog(),
                "Choose Lane ID",
                "Lane ID",
                tuple(lane_ids_to_match),
                current=0,
                editable=False)

            if ok_pressed:
                i = lane_ids_to_match.index(lane_id_selected)
                lane_id = lane_ids[i]
                para_offset = para_offsets[i]
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading

    def get_entity_waypoint_attributes(self, layer, attributes):
        """
        Processes waypoint attributes to be inserted into table

        Args:
            layer: [QGIS layer] waypoints layer
            attributes: [dict] attributes to be processed

        Returns:
            entity_attributes: [dict] attributes to be saved into layer
        """
        query = f'"Entity" = \'{attributes["Entity"]}\''
        entity_features = layer.getFeatures(query)
        waypoint_list = []
        for feat in entity_features:
            waypoint_list.append(feat["Waypoint No"])

        if waypoint_list:
            largest_waypoint_number = max(waypoint_list)
            waypoint_number = largest_waypoint_number + 1
        else:
            waypoint_number = 1

        entity_attributes = {"Maneuver ID": attributes["Maneuver ID"],
                             "Entity": attributes["Entity"],
                             "Waypoint No": waypoint_number,
                             "Orientation": attributes["Orientation"],
                             "Route Strat": attributes["Route Strat"]}
        return entity_attributes
