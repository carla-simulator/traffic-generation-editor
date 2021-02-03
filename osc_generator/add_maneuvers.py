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
        self.ConditionType.currentTextChanged.connect(self.update_start_trigger_condition)
        self.ValueCond.currentTextChanged.connect(self.update_value_condition_parameters)
        self.EntityCond.currentTextChanged.connect(self.update_entity_condition_parameters)
        self.entitySelection.currentTextChanged.connect(self.update_ref_entity)

        self.toggleTrafficLightLabels_Button.pressed.connect(self.toggle_traffic_light_labels)
        self.refreshTrafficLights_Button.pressed.connect(self.refresh_traffic_lights)
        self.entityChoosePosition_Button.pressed.connect(self.get_world_position)

        self._waypoint_layer = None
        self._maneuver_layer = None
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
        label_settings.fieldName = "concat('ManID: ', \"Maneuver ID\", ' ', \"Entity\", ' - ', \"Waypoint No\")"
        self._waypoint_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        self._waypoint_layer.setLabelsEnabled(True)

        # Maneuvers
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
                               QgsField("Entity: Condition", QVariant.String),
                               QgsField("Entity: Ref Entity", QVariant.String),
                               QgsField("Entity: Duration", QVariant.Double),
                               QgsField("Entity: Value", QVariant.Double),
                               QgsField("Entity: Rule", QVariant.String),
                               QgsField("Entity: RelDistType", QVariant.String),
                               QgsField("Entity: Freespace", QVariant.Bool),
                               QgsField("Entity: Along Route", QVariant.Bool),
                               QgsField("Value: Condition", QVariant.String),
                               QgsField("Value: Param Ref", QVariant.String),
                               QgsField("Value: Name", QVariant.String),
                               QgsField("Value: DateTime", QVariant.String),
                               QgsField("Value: Value", QVariant.Double),
                               QgsField("Value: Rule", QVariant.String),
                               QgsField("Value: State", QVariant.String),
                               QgsField("Value: Sboard Type", QVariant.String),
                               QgsField("Value: Sboard Element", QVariant.String),
                               QgsField("Value: Sboard State", QVariant.String),
                               QgsField("Value: TController Ref", QVariant.String),
                               QgsField("Value: TController Phase", QVariant.String),
                               QgsField("Global: Act Type", QVariant.String),
                               QgsField("Infra: Traffic Light ID", QVariant.Int),
                               QgsField("Infra: Traffic Light State", QVariant.String),
                               QgsField("WorldPos: Tolerance", QVariant.Double),
                               QgsField("WorldPos: X", QVariant.Double),
                               QgsField("WorldPos: Y", QVariant.Double),
                               QgsField("WorldPos: Heading", QVariant.Double)]
            data_input = maneuver_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            maneuver_layer.updateFields()

            message = "Maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            message = "Using existing maneuvers layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._maneuver_layer = QgsProject.instance().mapLayersByName("Maneuvers")[0]

    def refresh_entity(self):
        """
        Gets list of entities spawned on map and populates drop down
        """
        self.entitySelection.clear()
        self.refEntitySelection.clear()
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
        self.refEntitySelection.addItems(entities)

    def update_ref_entity(self):
        """
        Updates start trigger reference entity to match selected entity by default.
        """
        selected_entity = self.entitySelection.currentText()
        index = self.refEntitySelection.findText(selected_entity)
        self.refEntitySelection.setCurrentIndex(index)

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
        Spawn waypoints on the map.
        """
        self.get_maneuver_id()

        canvas = iface.mapCanvas()

        if self.maneuverType.currentText() == "Entity Maneuvers":
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
        elif self.maneuverType.currentText() == "Global Actions":
            pass

        self.save_maneuver_attributes()

    def change_maneuver(self):
        """
        Enables / disables group boxes depending on type of maneuver selected.
        """
        if self.entityManeuverType.currentText() == "Waypoint":
            self.waypointGroup.setEnabled(True)
            self.actorMoveGroup.setDisabled(True)
        elif self.entityManeuverType.currentText() == "Move on Condition":
            self.waypointGroup.setDisabled(True)
            self.actorMoveGroup.setEnabled(True)

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
        if self.ValueCond.currentText() == "ParameterCondition":
            self.Value_ParamRef.setEnabled(True)
        else:
            self.Value_ParamRef.setDisabled(True)

        # Name
        if (self.ValueCond.currentText() == "UserDefinedValueCondition"
            or self.ValueCond.currentText() == "TrafficSignalCondition"):
            self.Value_Name.setEnabled(True)
        else:
            self.Value_Name.setDisabled(True)

        # DateTime
        if self.ValueCond.currentText() == "TimeOfDayCondition":
            self.Value_DateTime.setEnabled(True)
        else:
            self.Value_DateTime.setDisabled(True)

        # Value
        if (self.ValueCond.currentText() == "ParameterCondition"
            or self.ValueCond.currentText() == "SimulationTimeCondition"
            or self.ValueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Value.setEnabled(True)
        else:
            self.Value_Value.setDisabled(True)

        # Rule
        if (self.ValueCond.currentText() == "ParameterCondition"
            or self.ValueCond.currentText() == "TimeOfDayCondition"
            or self.ValueCond.currentText() == "SimulationTimeCondition"
            or self.ValueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Rule.setEnabled(True)
        else:
            self.Value_Rule.setDisabled(True)

        # State
        if self.ValueCond.currentText() == "TrafficSignalCondition":
            self.Value_State.setEnabled(True)
        else:
            self.Value_State.setDisabled(True)

        # Storyboard elements
        if self.ValueCond.currentText() == "StoryboardElementStateCondition":
            self.StoryboardGroup.setEnabled(True)
        else:
            self.StoryboardGroup.setDisabled(True)

        # Traffic signal controller
        if self.ValueCond.currentText() == "TrafficSignalControllerCondition":
            self.TrafficSignalGroup.setEnabled(True)
        else:
            self.TrafficSignalGroup.setDisabled(True)

    def update_entity_condition_parameters(self):
        """
        Enables / disables parameters for Entity Conditions based on condition selected.
        """
        # Entity Ref
        if (self.EntityCond.currentText() == "TimeHeadwayCondition"
            or self.EntityCond.currentText() == "RelativeSpeedCondition"
            or self.EntityCond.currentText() == "RelativeDistanceCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"):
            self.refEntitySelection.setEnabled(True)
        else:
            self.refEntitySelection.setDisabled(True)

        # Duration
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "StandStillCondition"):
            self.Entity_Duration.setEnabled(True)
        else:
            self.Entity_Duration.setDisabled(True)

        # Value (setting disabled)
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "CollisionCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "TimeToCollisionCondition"
            or self.EntityCond.currentText() == "StandStillCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"
            or self.EntityCond.currentText() == "DistanceCondition"):
            self.Entity_Value.setDisabled(True)
        else:
            self.Entity_Value.setEnabled(True)

        # Rule (setting disabled)
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "StandStillCondition"
            or self.EntityCond.currentText() == "TraveledDistanceCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"):
            self.Entity_Rule.setDisabled(True)
        else:
            self.Entity_Rule.setEnabled(True)

        # Relative Distance
        if self.EntityCond.currentText() == "RelativeDistanceCondition":
            self.Entity_RelDistType.setEnabled(True)
        else:
            self.Entity_RelDistType.setDisabled(True)

        # Freespace
        if (self.EntityCond.currentText() == "TimeHeadwayCondition"
            or self.EntityCond.currentText() == "RelativeDistanceCondition"):
            self.Entity_Freespace.setEnabled(True)
        else:
            self.Entity_Freespace.setDisabled(True)

        # Along Route
        if self.EntityCond.currentText() == "TimeHeadwayCondition":
            self.Entity_AlongRoute.setEnabled(True)
        else:
            self.Entity_AlongRoute.setDisabled(True)

        # Position
        if self.EntityCond.currentText() == "ReachPositionCondition":
            self.Entity_PositionGroup.setEnabled(True)
        else:
            self.Entity_PositionGroup.setDisabled(True)

    def update_start_trigger_condition(self):
        """
        Enables / disables groups based on trigger condition selected.
        """
        if self.ConditionType.currentText() == "by Entity":
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
                               self.ConditionType.currentText(),
                               self.EntityCond.currentText(),
                               self.refEntitySelection.currentText(),
                               float(self.Entity_Duration.text()),
                               float(self.Entity_Value.text()),
                               self.Entity_Rule.currentText(),
                               self.Entity_RelDistType.currentText(),
                               self.Entity_Freespace.isChecked(),
                               self.Entity_AlongRoute.isChecked(),
                               self.ValueCond.currentText(),
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
                               float(self.entityHeading.text())])
        self._maneuver_layer.dataProvider().addFeature(feature)

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
