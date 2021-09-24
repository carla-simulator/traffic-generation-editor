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
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapTool
from qgis.utils import iface
from qgis.core import (QgsProject, QgsFeature, QgsGeometry,
                       QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsTextFormat,
                       QgsTextBackgroundSettings)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QInputDialog
# AD Map plugin
import ad_map_access as ad

from .helper_functions import (layer_setup_maneuvers_waypoint, layer_setup_maneuvers_and_triggers,
                               layer_setup_maneuvers_longitudinal, layer_setup_maneuvers_lateral,
                               verify_parameters, is_float, display_message, get_geo_point)


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
        self.refresh_entity_button.pressed.connect(self.refresh_entity)
        self.entity_selection.currentTextChanged.connect(self.update_ref_entity)
        self.add_maneuver_button.pressed.connect(self.add_maneuvers)
        self.entity_maneuver_type.currentTextChanged.connect(self.change_maneuver)
        self.waypoint_orientation_use_lane.stateChanged.connect(self.override_orientation)
        self.lateral_type.currentTextChanged.connect(self.change_lateral_type)
        self.long_type.currentTextChanged.connect(self.change_longitudinal_type)
        self.long_speed_target.currentTextChanged.connect(self.change_longitudinal_speed_target)

        self.start_condition_type.currentTextChanged.connect(self.update_start_trigger_condition)
        self.start_value_cond.currentTextChanged.connect(self.update_start_value_cond_parameters)
        self.start_entity_cond.currentTextChanged.connect(self.update_start_entity_cond_parameters)

        self.stop_condition_type.currentTextChanged.connect(self.update_stop_trigger_condition)
        self.stop_value_cond.currentTextChanged.connect(self.update_stop_value_cond_parameters)
        self.stop_entity_cond.currentTextChanged.connect(self.update_stop_entity_cond_parameters)

        self.toggle_traffic_light_labels_button.pressed.connect(self.toggle_traffic_light_labels)
        self.refresh_traffic_light_ids_button.pressed.connect(self.refresh_traffic_lights)
        self.start_entity_choose_position_button.pressed.connect(self.get_world_position)
        self.stop_entity_choose_position_button.pressed.connect(self.get_world_position)

        layer_setup_maneuvers_waypoint()
        layer_setup_maneuvers_and_triggers()
        layer_setup_maneuvers_longitudinal()
        layer_setup_maneuvers_lateral()
        self._waypoint_layer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]
        self._maneuver_layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]
        self._long_man_layer = QgsProject.instance().mapLayersByName("Longitudinal Maneuvers")[0]
        self._lat_man_layer = QgsProject.instance().mapLayersByName("Lateral Maneuvers")[0]
        self._man_id = None
        self._traffic_labels_on = False
        self._traffic_labels_setup = False
        self._traffic_lights_layer = None

        self.refresh_entity()
        self.refresh_traffic_lights()

    def refresh_entity(self):
        """
        Gets list of entities spawned on map and populates drop down
        """
        self.entity_selection.clear()
        self.long_ref_entity.clear()
        self.lateral_ref_entity.clear()
        self.start_entity_ref_entity.clear()
        self.stop_entity_ref_entity.clear()

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

        self.entity_selection.addItems(entities)
        self.long_ref_entity.addItems(entities)
        self.lateral_ref_entity.addItems(entities)
        self.start_entity_ref_entity.addItems(entities)
        self.stop_entity_ref_entity.addItems(entities)

    def update_ref_entity(self):
        """
        Updates start trigger reference entity to match selected entity by default.
        """
        selected_entity = self.entity_selection.currentText()
        # Start Trigger (Ref Entity)
        index = self.start_entity_ref_entity.findText(selected_entity)
        self.start_entity_ref_entity.setCurrentIndex(index)

        # Stop Trigger (Ref Entity)
        index = self.stop_entity_ref_entity.findText(selected_entity)
        self.stop_entity_ref_entity.setCurrentIndex(index)

        # Lateral reference entity
        index = self.lateral_ref_entity.findText(selected_entity)
        self.lateral_ref_entity.setCurrentIndex(index)

        # Longitudinal reference entity
        index = self.long_ref_entity.findText(selected_entity)
        self.long_ref_entity.setCurrentIndex(index)

    def override_orientation(self):
        """
        Toggles waypoint orientation field on and off
        """
        if self.waypoint_orientation_use_lane.isChecked():
            self.waypoint_orientation.setDisabled(True)
        else:
            self.waypoint_orientation.setEnabled(True)

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
        self.traffic_light_id.clear()
        traffic_light_ids = []
        if QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT"):
            layer = QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT")[0]
            for feature in layer.getFeatures():
                loaded_traffic_light_ids = str(feature["Id"])
                traffic_light_ids.append(loaded_traffic_light_ids)

            if len(traffic_light_ids) == 0:
                traffic_light_ids.append("0")

        self.traffic_light_id.addItems(traffic_light_ids)

    def closeEvent(self, event):    # pylint: disable=invalid-name
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

        if self.maneuver_type.currentText() == "Entity Maneuvers":
            if self.entity_maneuver_type.currentText() == "Waypoint":
                entity = self.entity_selection.currentText()
                if self.waypoint_orientation_use_lane.isChecked():
                    entity_orientation = None
                else:
                    entity_orientation = math.radians(float(self.waypoint_orientation.text()))

                entity_attributes = {"Maneuver ID": self._man_id,
                                     "Entity": entity,
                                     "Orientation": entity_orientation,
                                     "Route Strat": self.waypoint_strategy.currentText()}
                tool = PointTool(canvas, self._waypoint_layer, entity_attributes, layer_type="Waypoints")
                canvas.setMapTool(tool)
            elif self.entity_maneuver_type.currentText() == "Longitudinal":
                self.save_longitudinal_attributes()
            elif self.entity_maneuver_type.currentText() == "Lateral":
                self.save_lateral_attributes()
        elif self.maneuver_type.currentText() == "Global Actions":
            # Infrastructure actions are saved inside Maneuvers layer
            pass

        self.save_maneuver_attributes()

    def change_maneuver(self):
        """
        Enables / disables group boxes depending on type of maneuver selected.
        """
        if self.entity_maneuver_type.currentText() == "Waypoint":
            self.waypoint_group.setEnabled(True)
            self.lateral_group.setDisabled(True)
            self.longitudinal_group.setDisabled(True)
        elif self.entity_maneuver_type.currentText() == "Longitudinal":
            self.waypoint_group.setDisabled(True)
            self.lateral_group.setDisabled(True)
            self.longitudinal_group.setEnabled(True)
        elif self.entity_maneuver_type.currentText() == "Lateral":
            self.waypoint_group.setDisabled(True)
            self.lateral_group.setEnabled(True)
            self.longitudinal_group.setDisabled(True)

    def change_lateral_type(self):
        """
        Enables / disables fields for lateral maneuvers based on type of lateral maneuvers.
        """
        if self.lateral_type.currentText() == "LaneChangeAction":
            self.lateral_dynamics_dim.setEnabled(True)
            self.lateral_dynamics_shape.setEnabled(True)
            self.lateral_dynamics_value.setEnabled(True)
            self.lateral_lane_target_value.setEnabled(True)
            self.lateral_ref_entity.setEnabled(True)
            self.lateral_lane_target.setEnabled(True)
            self.lateral_max_lat_accel.setDisabled(True)
            self.lateral_max_accel.setDisabled(True)
            self.lateral_max_decel.setDisabled(True)
            self.lateral_max_speed.setDisabled(True)
            lane_targets = ["RelativeTargetLane", "AbsoluteTargetLane"]
            self.lateral_lane_target.clear()
            self.lateral_lane_target.addItems(lane_targets)

        elif self.lateral_type.currentText() == "LaneOffsetAction":
            self.lateral_max_lat_accel.setEnabled(True)
            self.lateral_dynamics_shape.setEnabled(True)
            self.lateral_lane_target_value.setEnabled(True)
            self.lateral_ref_entity.setEnabled(True)
            self.lateral_lane_target.setEnabled(True)
            self.lateral_max_accel.setDisabled(True)
            self.lateral_max_decel.setDisabled(True)
            self.lateral_max_speed.setDisabled(True)
            self.lateral_dynamics_dim.setDisabled(True)
            self.lateral_dynamics_value.setDisabled(True)
            lane_targets = ["RelativeTargetLaneOffset", "AbsoluteTargetLaneOffset"]
            self.lateral_lane_target.clear()
            self.lateral_lane_target.addItems(lane_targets)

        elif self.lateral_type.currentText() == "LateralDistanceAction":
            self.lateral_max_accel.setEnabled(True)
            self.lateral_max_decel.setEnabled(True)
            self.lateral_max_speed.setEnabled(True)
            self.lateral_max_lat_accel.setDisabled(True)
            self.lateral_lane_target_value.setDisabled(True)
            self.lateral_dynamics_dim.setDisabled(True)
            self.lateral_dynamics_shape.setDisabled(True)
            self.lateral_dynamics_value.setDisabled(True)
            self.lateral_ref_entity.setDisabled(True)
            self.lateral_lane_target.setDisabled(True)

    def change_longitudinal_type(self):
        """
        Enables / disables fields for longitudinal maneuvers based on type.
        """
        if self.long_type.currentText() == "SpeedAction":
            self.long_ref_entity.setEnabled(True)
            self.long_speed_target.setEnabled(True)
            self.long_dynamics_shape.setEnabled(True)
            self.long_dynamics_dim.setEnabled(True)
            self.long_dynamics_value.setEnabled(True)
            self.long_target_type.setEnabled(True)
            self.long_target_speed_value.setEnabled(True)
            self.long_continuous.setEnabled(True)
            self.long_max_accel.setDisabled(True)
            self.long_max_decel.setDisabled(True)
            self.long_max_speed.setDisabled(True)
            self.long_freespace.setDisabled(True)
        elif self.long_type.currentText() == "LongitudinalDistanceAction":
            self.long_max_accel.setEnabled(True)
            self.long_max_decel.setEnabled(True)
            self.long_max_speed.setEnabled(True)
            self.long_ref_entity.setEnabled(True)
            self.long_continuous.setEnabled(True)
            self.long_freespace.setEnabled(True)
            self.long_speed_target.setDisabled(True)
            self.long_dynamics_shape.setDisabled(True)
            self.long_dynamics_dim.setDisabled(True)
            self.long_dynamics_value.setDisabled(True)
            self.long_target_type.setDisabled(True)
            self.long_target_speed_value.setDisabled(True)

    def change_longitudinal_speed_target(self):
        """
        Enables / disables fields for longitudinal maneuvers based on type.
        """
        if self.long_speed_target.currentText() == "RelativeTargetSpeed":
            self.long_ref_entity.setEnabled(True)
            self.long_target_speed_value.setEnabled(True)
            self.long_target_type.setEnabled(True)
            self.long_continuous.setEnabled(True)
        elif self.long_speed_target.currentText() == "AbsoluteTargetSpeed":
            self.long_target_speed_value.setEnabled(True)
            self.long_ref_entity.setDisabled(True)
            self.long_target_type.setDisabled(True)
            self.long_continuous.setDisabled(True)

    def get_world_position(self):
        """
        Gets world position from map for triggers
        """
        canvas = iface.mapCanvas()
        entity_attributes = {"Orientation": None}
        tool = PointTool(canvas, self._maneuver_layer, entity_attributes, layer_type="Position", parent=self)
        canvas.setMapTool(tool)

    def update_start_value_cond_parameters(self):
        """
        Enables / disables parameters for Value Conditions
        (Start Trigger) based on condition selected.
        """
        # Parameter Reference
        if self.start_value_cond.currentText() == "ParameterCondition":
            self.start_value_param_ref.setEnabled(True)
        else:
            self.start_value_param_ref.setDisabled(True)

        # Name
        if (self.start_value_cond.currentText() == "UserDefinedValueCondition"
                or self.start_value_cond.currentText() == "TrafficSignalCondition"):
            self.start_value_name.setEnabled(True)
        else:
            self.start_value_name.setDisabled(True)

        # DateTime
        if self.start_value_cond.currentText() == "TimeOfDayCondition":
            self.start_value_datetime.setEnabled(True)
        else:
            self.start_value_datetime.setDisabled(True)

        # Value
        if (self.start_value_cond.currentText() == "ParameterCondition"
            or self.start_value_cond.currentText() == "SimulationTimeCondition"
                or self.start_value_cond.currentText() == "UserDefinedValueCondition"):
            self.start_value_value.setEnabled(True)
        else:
            self.start_value_value.setDisabled(True)

        # Rule
        if (self.start_value_cond.currentText() == "ParameterCondition"
            or self.start_value_cond.currentText() == "TimeOfDayCondition"
            or self.start_value_cond.currentText() == "SimulationTimeCondition"
                or self.start_value_cond.currentText() == "UserDefinedValueCondition"):
            self.start_value_rule.setEnabled(True)
        else:
            self.start_value_rule.setDisabled(True)

        # State
        if self.start_value_cond.currentText() == "TrafficSignalCondition":
            self.start_value_state.setEnabled(True)
        else:
            self.start_value_state.setDisabled(True)

        # Storyboard elements
        if self.start_value_cond.currentText() == "StoryboardElementStateCondition":
            self.start_storyboard_group.setEnabled(True)
        else:
            self.start_storyboard_group.setDisabled(True)

        # Traffic signal controller
        if self.start_value_cond.currentText() == "TrafficSignalControllerCondition":
            self.start_traffic_signal_group.setEnabled(True)
        else:
            self.start_traffic_signal_group.setDisabled(True)

    def update_stop_value_cond_parameters(self):
        """
        Enables / disables parameters for Value Conditions
        (Stop Trigger) based on condition selected.
        """
        # Parameter Reference
        if self.stop_value_cond.currentText() == "ParameterCondition":
            self.stop_value_param_ref.setEnabled(True)
        else:
            self.stop_value_param_ref.setDisabled(True)

        # Name
        if (self.stop_value_cond.currentText() == "UserDefinedValueCondition"
                or self.stop_value_cond.currentText() == "TrafficSignalCondition"):
            self.stop_value_name.setEnabled(True)
        else:
            self.stop_value_name.setDisabled(True)

        # DateTime
        if self.stop_value_cond.currentText() == "TimeOfDayCondition":
            self.stop_value_datetime.setEnabled(True)
        else:
            self.stop_value_datetime.setDisabled(True)

        # Value
        if (self.stop_value_cond.currentText() == "ParameterCondition"
            or self.stop_value_cond.currentText() == "SimulationTimeCondition"
                or self.stop_value_cond.currentText() == "UserDefinedValueCondition"):
            self.stop_value_value.setEnabled(True)
        else:
            self.stop_value_value.setDisabled(True)

        # Rule
        if (self.stop_value_cond.currentText() == "ParameterCondition"
            or self.stop_value_cond.currentText() == "TimeOfDayCondition"
            or self.stop_value_cond.currentText() == "SimulationTimeCondition"
                or self.stop_value_cond.currentText() == "UserDefinedValueCondition"):
            self.stop_value_rule.setEnabled(True)
        else:
            self.stop_value_rule.setDisabled(True)

        # State
        if self.stop_value_cond.currentText() == "TrafficSignalCondition":
            self.stop_value_state.setEnabled(True)
        else:
            self.stop_value_state.setDisabled(True)

        # Storyboard elements
        if self.stop_value_cond.currentText() == "StoryboardElementStateCondition":
            self.stop_storyboard_group.setEnabled(True)
        else:
            self.stop_storyboard_group.setDisabled(True)

        # Traffic signal controller
        if self.stop_value_cond.currentText() == "TrafficSignalControllerCondition":
            self.stop_traffic_signal_group.setEnabled(True)
        else:
            self.stop_traffic_signal_group.setDisabled(True)

    def update_start_entity_cond_parameters(self):
        """
        Enables / disables parameters for Entity Conditions
        (Start Trigger) based on condition selected.
        """
        # Entity Ref
        if (self.start_entity_cond.currentText() == "TimeHeadwayCondition"
            or self.start_entity_cond.currentText() == "RelativeSpeedCondition"
            or self.start_entity_cond.currentText() == "RelativeDistanceCondition"
                or self.start_entity_cond.currentText() == "ReachPositionCondition"):
            self.start_entity_ref_entity.setEnabled(True)
        else:
            self.start_entity_ref_entity.setDisabled(True)

        # Duration
        if (self.start_entity_cond.currentText() == "EndOfRoadCondition"
            or self.start_entity_cond.currentText() == "OffroadCondition"
                or self.start_entity_cond.currentText() == "StandStillCondition"):
            self.start_entity_duration.setEnabled(True)
        else:
            self.start_entity_duration.setDisabled(True)

        # Value (setting disabled)
        if (self.start_entity_cond.currentText() == "EndOfRoadCondition"
            or self.start_entity_cond.currentText() == "CollisionCondition"
            or self.start_entity_cond.currentText() == "OffroadCondition"
            or self.start_entity_cond.currentText() == "TimeToCollisionCondition"
            or self.start_entity_cond.currentText() == "StandStillCondition"
            or self.start_entity_cond.currentText() == "ReachPositionCondition"
                or self.start_entity_cond.currentText() == "DistanceCondition"):
            self.start_entity_value.setDisabled(True)
        else:
            self.start_entity_value.setEnabled(True)

        # Rule (setting disabled)
        if (self.start_entity_cond.currentText() == "EndOfRoadCondition"
            or self.start_entity_cond.currentText() == "OffroadCondition"
            or self.start_entity_cond.currentText() == "StandStillCondition"
            or self.start_entity_cond.currentText() == "TraveledDistanceCondition"
                or self.start_entity_cond.currentText() == "ReachPositionCondition"):
            self.start_entity_rule.setDisabled(True)
        else:
            self.start_entity_rule.setEnabled(True)

        # Relative Distance
        if self.start_entity_cond.currentText() == "RelativeDistanceCondition":
            self.start_entity_rel_dist_type.setEnabled(True)
        else:
            self.start_entity_rel_dist_type.setDisabled(True)

        # Freespace
        if (self.start_entity_cond.currentText() == "TimeHeadwayCondition"
                or self.start_entity_cond.currentText() == "RelativeDistanceCondition"):
            self.start_entity_freespace.setEnabled(True)
        else:
            self.start_entity_freespace.setDisabled(True)

        # Along Route
        if self.start_entity_cond.currentText() == "TimeHeadwayCondition":
            self.start_entity_along_route.setEnabled(True)
        else:
            self.start_entity_along_route.setDisabled(True)

        # Position
        if self.start_entity_cond.currentText() == "ReachPositionCondition":
            self.start_entity_position_group.setEnabled(True)
        else:
            self.start_entity_position_group.setDisabled(True)

    def update_stop_entity_cond_parameters(self):
        """
        Enables / disables parameters for Entity Conditions
        (Stop Trigger) based on condition selected.
        """
        # Entity Ref
        if (self.stop_entity_cond.currentText() == "TimeHeadwayCondition"
            or self.stop_entity_cond.currentText() == "RelativeSpeedCondition"
            or self.stop_entity_cond.currentText() == "RelativeDistanceCondition"
                or self.stop_entity_cond.currentText() == "ReachPositionCondition"):
            self.stop_entity_ref_entity.setEnabled(True)
        else:
            self.stop_entity_ref_entity.setDisabled(True)

        # Duration
        if (self.stop_entity_cond.currentText() == "EndOfRoadCondition"
            or self.stop_entity_cond.currentText() == "OffroadCondition"
                or self.stop_entity_cond.currentText() == "StandStillCondition"):
            self.stop_entity_duration.setEnabled(True)
        else:
            self.stop_entity_duration.setDisabled(True)

        # Value (setting disabled)
        if (self.stop_entity_cond.currentText() == "EndOfRoadCondition"
            or self.stop_entity_cond.currentText() == "CollisionCondition"
            or self.stop_entity_cond.currentText() == "OffroadCondition"
            or self.stop_entity_cond.currentText() == "TimeToCollisionCondition"
            or self.stop_entity_cond.currentText() == "StandStillCondition"
            or self.stop_entity_cond.currentText() == "ReachPositionCondition"
                or self.stop_entity_cond.currentText() == "DistanceCondition"):
            self.stop_entity_value.setDisabled(True)
        else:
            self.stop_entity_value.setEnabled(True)

        # Rule (setting disabled)
        if (self.stop_entity_cond.currentText() == "EndOfRoadCondition"
            or self.stop_entity_cond.currentText() == "OffroadCondition"
            or self.stop_entity_cond.currentText() == "StandStillCondition"
            or self.stop_entity_cond.currentText() == "TraveledDistanceCondition"
                or self.stop_entity_cond.currentText() == "ReachPositionCondition"):
            self.stop_entity_rule.setDisabled(True)
        else:
            self.stop_entity_rule.setEnabled(True)

        # Relative Distance
        if self.stop_entity_cond.currentText() == "RelativeDistanceCondition":
            self.stop_entity_rel_dist_type.setEnabled(True)
        else:
            self.stop_entity_rel_dist_type.setDisabled(True)

        # Freespace
        if (self.stop_entity_cond.currentText() == "TimeHeadwayCondition"
                or self.stop_entity_cond.currentText() == "RelativeDistanceCondition"):
            self.stop_entity_freespace.setEnabled(True)
        else:
            self.stop_entity_freespace.setDisabled(True)

        # Along Route
        if self.stop_entity_cond.currentText() == "TimeHeadwayCondition":
            self.stop_entity_along_route.setEnabled(True)
        else:
            self.stop_entity_along_route.setDisabled(True)

        # Position
        if self.stop_entity_cond.currentText() == "ReachPositionCondition":
            self.stop_entity_position_group.setEnabled(True)
        else:
            self.stop_entity_position_group.setDisabled(True)

    def update_start_trigger_condition(self):
        """
        Enables / disables groups based on start trigger condition selected.
        """
        if self.start_condition_type.currentText() == "by Entity":
            self.start_entity_condition_group.setEnabled(True)
            self.start_value_condition_group.setDisabled(True)
        else:
            self.start_entity_condition_group.setDisabled(True)
            self.start_value_condition_group.setEnabled(True)

    def update_stop_trigger_condition(self):
        """
        Enables / disables groups based on stop trigger condition selected.
        """
        if self.stop_condition_type.currentText() == "by Entity":
            self.stop_entity_condition_group.setEnabled(True)
            self.stop_value_condition_group.setDisabled(True)
        else:
            self.stop_entity_condition_group.setDisabled(True)
            self.stop_value_condition_group.setEnabled(True)

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
                               self.maneuver_type.currentText(),
                               self.entity_selection.currentText(),
                               self.entity_maneuver_type.currentText(),
                               # Global Actions
                               self.global_act_type.currentText(),
                               int(self.traffic_light_id.currentText()),
                               self.traffic_light_state.currentText(),
                               # Start Triggers
                               self.start_condition_type.currentText(),
                               self.start_entity_cond.currentText(),
                               self.start_entity_ref_entity.currentText(),
                               float(self.start_entity_duration.text()),
                               float(self.start_entity_value.text()),
                               self.start_entity_rule.currentText(),
                               self.start_entity_rel_dist_type.currentText(),
                               self.start_entity_freespace.isChecked(),
                               self.start_entity_along_route.isChecked(),
                               self.start_value_cond.currentText(),
                               self.start_value_param_ref.text(),
                               self.start_value_name.text(),
                               self.start_value_datetime.dateTime().toString("yyyy-MM-ddThh:mm:ss"),
                               float(self.start_value_value.text()),
                               self.start_value_rule.currentText(),
                               self.start_value_state.text(),
                               self.start_storyboard_type.currentText(),
                               self.start_storyboard_element.text(),
                               self.start_storyboard_state.currentText(),
                               self.start_traffic_controller_ref.text(),
                               self.start_traffic_phase.text(),
                               float(self.start_entity_tolerance.text()),
                               float(self.start_entity_position_x.text()),
                               float(self.start_entity_position_y.text()),
                               float(self.start_entity_position_z.text()),
                               float(self.start_entity_heading.text()),
                               # Stop Triggers
                               self.stop_triggers_group.isChecked(),
                               self.stop_condition_type.currentText(),
                               self.stop_entity_cond.currentText(),
                               self.stop_entity_ref_entity.currentText(),
                               self.stop_entity_duration.text(),
                               self.stop_entity_value.text(),
                               self.stop_entity_rule.currentText(),
                               self.stop_entity_rel_dist_type.currentText(),
                               self.stop_entity_freespace.isChecked(),
                               self.stop_entity_along_route.isChecked(),
                               self.stop_value_cond.currentText(),
                               self.stop_value_param_ref.text(),
                               self.stop_value_name.text(),
                               self.stop_value_datetime.dateTime().toString("yyyy-MM-ddThh:mm:ss"),
                               float(self.stop_value_value.text()),
                               self.stop_value_rule.currentText(),
                               self.stop_value_state.text(),
                               self.stop_storyboard_type.currentText(),
                               self.stop_storyboard_element.text(),
                               self.stop_storyboard_state.currentText(),
                               self.stop_traffic_controller_ref.text(),
                               self.stop_traffic_phase.text(),
                               float(self.stop_entity_tolerance.text()),
                               float(self.stop_entity_position_x.text()),
                               float(self.stop_entity_position_y.text()),
                               float(self.stop_entity_position_z.text()),
                               float(self.stop_entity_heading.text())])
        self._maneuver_layer.dataProvider().addFeature(feature)

        message = "Maneuver added"
        display_message(message, level="Info")

    def save_longitudinal_attributes(self):
        """
        Gets longudinal maneuver attributes and saves into QGIS attributes table.
        """
        if is_float(self.long_dynamics_value.text()):
            long_dynamics_value = float(self.long_dynamics_value.text())
        else:
            verification = verify_parameters(self.long_dynamics_value.text())
            if len(verification) == 0:
                message = f"Parameter {self.long_dynamics_value.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                long_dynamics_value = self.long_dynamics_value.text()

        if is_float(self.long_target_speed_value.text()):
            long_target_speed_value = float(self.long_target_speed_value.text())
        else:
            verification = verify_parameters(self.long_target_speed_value.text())
            if len(verification) == 0:
                message = f"Parameter {self.long_target_speed_value.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                long_target_speed_value = self.long_target_speed_value.text()

        if is_float(self.long_max_accel.text()):
            long_max_accel = float(self.long_max_accel.text())
        else:
            verification = verify_parameters(self.long_max_accel.text())
            if len(verification) == 0:
                message = f"Parameter {self.long_max_accel.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                long_max_accel = self.long_max_accel.text()

        if is_float(self.long_max_decel.text()):
            long_max_decel = float(self.long_max_decel.text())
        else:
            verification = verify_parameters(self.long_max_decel.text())
            if len(verification) == 0:
                message = f"Parameter {self.long_max_decel.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                long_max_decel = self.long_max_decel.text()

        if is_float(self.long_max_speed.text()):
            long_max_speed = float(self.long_max_speed.text())
        else:
            verification = verify_parameters(self.long_max_speed.text())
            if len(verification) == 0:
                message = f"Parameter {self.long_max_speed.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                long_max_speed = self.long_max_speed.text()

        feature = QgsFeature()
        feature.setAttributes([self._man_id,
                               self.long_type.currentText(),
                               self.long_speed_target.currentText(),
                               self.long_ref_entity.currentText(),
                               self.long_dynamics_shape.currentText(),
                               self.long_dynamics_dim.currentText(),
                               long_dynamics_value,
                               self.long_target_type.currentText(),
                               long_target_speed_value,
                               self.long_continuous.isChecked(),
                               self.long_freespace.isChecked(),
                               long_max_accel,
                               long_max_decel,
                               long_max_speed])
        self._long_man_layer.dataProvider().addFeature(feature)

        message = "Maneuver added"
        display_message(message, level="Info")

    def save_lateral_attributes(self):
        """
        Gets lateral maneuver attributes and saves into QGIS attributes table.
        """
        if is_float(self.lateral_dynamics_value.text()):
            lateral_dynamics_value = float(self.lateral_dynamics_value.text())
        else:
            verification = verify_parameters(self.lateral_dynamics_value.text())
            if len(verification) == 0:
                message = f"Parameter {self.lateral_dynamics_value.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                lateral_dynamics_value = self.lateral_dynamics_value.text()

        if is_float(self.lateral_max_lat_accel.text()):
            lateral_max_lat_accel = float(self.lateral_max_lat_accel.text())
        else:
            verification = verify_parameters(self.lateral_max_lat_accel.text())
            if len(verification) == 0:
                message = f"Parameter {self.lateral_max_lat_accel.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                lateral_max_lat_accel = self.lateral_max_lat_accel.text()

        if is_float(self.lateral_max_accel.text()):
            lateral_max_accel = float(self.lateral_max_accel.text())
        else:
            verification = verify_parameters(self.lateral_max_accel.text())
            if len(verification) == 0:
                message = f"Parameter {self.lateral_max_accel.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                lateral_max_accel = self.lateral_max_accel.text()

        if is_float(self.lateral_max_decel.text()):
            lateral_max_decel = float(self.lateral_max_decel.text())
        else:
            verification = verify_parameters(self.lateral_max_decel.text())
            if len(verification) == 0:
                message = f"Parameter {self.lateral_max_decel.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                lateral_max_decel = self.lateral_max_decel.text()

        if is_float(self.lateral_max_speed.text()):
            lateral_max_speed = float(self.lateral_max_speed.text())
        else:
            verification = verify_parameters(self.lateral_max_speed.text())
            if len(verification) == 0:
                message = f"Parameter {self.lateral_max_speed.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                lateral_max_speed = self.lateral_max_speed.text()

        feature = QgsFeature()
        feature.setAttributes([self._man_id,
                               self.lateral_type.currentText(),
                               self.lateral_lane_target.currentText(),
                               self.lateral_ref_entity.currentText(),
                               self.lateral_dynamics_shape.currentText(),
                               self.lateral_dynamics_dim.currentText(),
                               lateral_dynamics_value,
                               self.lateral_lane_target_value.text(),
                               lateral_max_lat_accel,
                               lateral_max_accel,
                               lateral_max_decel,
                               lateral_max_speed])
        self._lat_man_layer.dataProvider().addFeature(feature)

        message = "Maneuver added"
        display_message(message, level="Info")


# pylint: disable=missing-function-docstring
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

    def canvasReleaseEvent(self, event):    # pylint: disable=invalid-name
        # Get the click
        x = event.pos().x()  # pylint: disable=invalid-name
        y = event.pos().y()  # pylint: disable=invalid-name

        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)
        geopoint = get_geo_point(point)
        # Converting to ENU points
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
                                       float(enupoint.z),
                                       processed_attrs["Route Strat"]])
                feature.setGeometry(QgsGeometry.fromPointXY(point))
                self._data_input.addFeature(feature)
        elif self._type == "Position":
            heading = add_entity_attr.get_entity_heading(geopoint)
            self._parent.start_entity_position_x.setText(str(enupoint.x))
            self._parent.start_entity_position_y.setText(str(enupoint.y))
            self._parent.start_entity_position_z.setText(str(enupoint.z))
            self._parent.start_entity_heading.setText(str(heading))
            self._parent.stop_entity_position_x.setText(str(enupoint.x))
            self._parent.stop_entity_position_y.setText(str(enupoint.y))
            self._parent.stop_entity_position_z.setText(str(enupoint.z))
            self._parent.stop_entity_heading.setText(str(heading))
            self._canvas.unsetMapTool(self)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()

# pylint: enable=missing-function-docstring


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
        dist = ad.physics.Distance(1)
        admap_matched_points = ad.map.match.AdMapMatching.findLanes(geopoint, dist)

        lanes_detected = 0
        for point in admap_matched_points:
            lanes_detected += 1

        if lanes_detected == 0:
            message = "Click point is too far from valid lane"
            display_message(message, level="Critical")
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
        return None

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
