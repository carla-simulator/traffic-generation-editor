# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Static Objects
"""
import os
import math
# pylint: disable=no-name-in-module, no-member
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.gui import QgsMapTool
from qgis.utils import iface
from qgis.core import (QgsProject, QgsVectorLayer, QgsMessageLog, Qgis, QgsField,
    QgsFeature, QgsGeometry, QgsPointXY, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from PyQt5.QtWidgets import QInputDialog

# AD Map plugin
import ad_map_access as ad

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'add_static_objects_widget.ui'))


class AddPropsDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to spawn props / static objects on map.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialization of AddPropsDockWidget
        """
        super(AddPropsDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.addProps_Button.pressed.connect(self.insert_props)
        self.propsOrientation_useLane.stateChanged.connect(self.override_orientation)
        self.propsLabels_Button.pressed.connect(self.toggle_labels)

        self._labels_on = True
        self._props_layer = None
        self.layer_setup()

    def layer_setup(self):
        """
        Sets up layer for pedestrians
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Static Objects"):
            props_layer = QgsVectorLayer("Polygon", "Static Objects", "memory")
            QgsProject.instance().addMapLayer(props_layer, False)
            osc_layer.addLayer(props_layer)
            # Setup layer attributes
            data_attributes = [QgsField("id", QVariant.Int),
                               QgsField("Prop", QVariant.String),
                               QgsField("Prop Type", QVariant.String),
                               QgsField("Orientation", QVariant.Double),
                               QgsField("Mass", QVariant.Double),
                               QgsField("Pos X", QVariant.Double),
                               QgsField("Pos Y", QVariant.Double),
                               QgsField("Physics", QVariant.Bool)]
            data_input = props_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            props_layer.updateFields()

            label_settings = QgsPalLayerSettings()
            label_settings.isExpression = True
            label_settings.fieldName = "concat('Prop_', \"id\")"
            props_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            props_layer.setLabelsEnabled(True)

            message = "Static objects layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._props_layer = QgsProject.instance().mapLayersByName("Static Objects")[0]

    def toggle_labels(self):
        """
        Toggles labels for static objects on/off
        """
        if self._labels_on:
            self._props_layer.setLabelsEnabled(False)
            self._labels_on = False
        else:
            self._props_layer.setLabelsEnabled(True)
            self._labels_on = True

        self._props_layer.triggerRepaint()

    def closeEvent(self, event):
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def insert_props(self):
        """
        Spawn static objects on map with mouse click.
        """
        iface.setActiveLayer(self._props_layer)

        # UI Information
        message = "Using existing static objects layer"
        iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()

        # Static objects orientation
        if self.propsOrientation_useLane.isChecked():
            props_orientation = None
        else:
            props_orientation = float(self.propsOrientation.text())
            props_orientation = math.radians(props_orientation)

        prop_attributes = {"Prop": self.propsSelection.currentText(),
                           "Prop Type": self.propsObjectType.currentText(),
                           "Orientation": props_orientation,
                           "Mass": float(self.propsMass.text()),
                           "Physics": str(self.propsPhysics.isChecked())}
        tool = PointTool(canvas, layer, prop_attributes)
        canvas.setMapTool(tool)

    def override_orientation(self):
        """
        Toggles user input for walker orientation on/off
        """
        if self.propsOrientation_useLane.isChecked():
            self.propsOrientation.setDisabled(True)
        else:
            self.propsOrientation.setEnabled(True)

#pylint: disable=missing-function-docstring
class PointTool(QgsMapTool):
    """Enables Point Addition"""

    def __init__(self, canvas, layer, prop_attributes):
        QgsMapTool.__init__(self, canvas)
        self._canvas = canvas
        self._layer = layer
        self._data_input = layer.dataProvider()
        self._canvas.setCursor(Qt.CrossCursor)
        self._prop_attributes = prop_attributes
        if self._prop_attributes["Orientation"] is None:
            self._use_lane_heading = True
        else:
            self._use_lane_heading = False

    def canvasReleaseEvent(self, event):
        """
        Function when map canvas is clicked
        """
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # Converting to ENU points
        geopoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=0)
        enupoint = ad.map.point.toENU(geopoint)
        add_props = AddPropAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._prop_attributes["Orientation"] = add_props.get_prop_heading(geopoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self._prop_attributes["Orientation"] is not None:
            polygon_points = add_props.spawn_props(enupoint,
                                                   self._prop_attributes["Orientation"])
            # Pass attributes to process
            prop_attr = add_props.get_prop_attributes(self._layer,
                                                      self._prop_attributes)

            # Set pedestrian attributes
            feature = QgsFeature()
            feature.setAttributes([prop_attr["id"],
                                   prop_attr["Prop"],
                                   prop_attr["Prop Type"],
                                   prop_attr["Orientation"],
                                   prop_attr["Mass"],
                                   float(enupoint.x),
                                   float(enupoint.y),
                                   prop_attr["Physics"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
            self._data_input.addFeature(feature)

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


class AddPropAttribute():
    """
    Class for processing / acquiring static object attributes.
    """
    def get_prop_heading(self, geopoint):
        """
        Acquires heading based on spawn position in map.
        Prompts user to select lane if multiple lanes exist at spawn position.
        Throws error if spawn position is not on lane.

        Args:
            geopoint: [AD Map GEOPoint] point of click event
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
            lane_id = []
            para_offsets = []
            for point in admap_matched_points:
                lane_ids_to_match.append(str(point.lanePoint.paraPoint.laneId))
                lane_id.append(point.lanePoint.paraPoint.laneId)
                para_offsets.append(point.lanePoint.paraPoint.parametricOffset)

            lane_id_selected, ok_pressed = QInputDialog.getItem(QInputDialog(), "Choose Lane ID",
                "Lane ID", tuple(lane_ids_to_match), current=0, editable=False)

            if ok_pressed:
                i = lane_ids_to_match.index(lane_id_selected)
                lane_id = lane_id[i]
                para_offset = para_offsets[i]
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading

    def spawn_props(self, enupoint, angle):
        """
        Spawns static objects on the map and draws bounding boxes

        Args:
            enupoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """
        if angle is not None:
            bot_left_x = float(enupoint.x) + (-0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            bot_left_y = float(enupoint.y) + (-0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            bot_right_x = float(enupoint.x) + (-0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            bot_right_y =  float(enupoint.y) + (-0.5 * math.sin(angle) - 0.5 * math.cos(angle))
            top_left_x = float(enupoint.x) + (0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            top_left_y = float(enupoint.y) + (0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            top_right_x = float(enupoint.x) + (0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            top_right_y = float(enupoint.y) + (0.5 * math.sin(angle) - 0.5 * math.cos(angle))

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

    def get_prop_attributes(self, layer, attributes):
        """
        Inputs static objects attributes into table

        Args:
            layer: [QGIS layer] layer that contains static object data
            attributes: [dict] static object attributes from GUI to be processed
        """
        # Get largest static objects ID from attribute table
        # If no static objects has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largest_prop_id = layer.maximumValue(idx)
            prop_id = largest_prop_id + 1
        else:
            prop_id = 1

        prop = "static.prop." + attributes["Prop"]

        orientation = float(attributes["Orientation"])

        prop_attributes = {"id": prop_id,
                           "Prop": prop,
                           "Prop Type": attributes["Prop Type"],
                           "Mass": attributes["Mass"],
                           "Orientation": orientation,
                           "Physics": attributes["Physics"]}

        return prop_attributes
