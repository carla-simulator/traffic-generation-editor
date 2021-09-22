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
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.gui import QgsMapTool
from qgis.utils import iface
from qgis.core import QgsProject, QgsFeature, QgsGeometry, QgsPointXY
from PyQt5.QtWidgets import QInputDialog
# AD Map plugin
import ad_map_access as ad

from .helper_functions import (layer_setup_props, display_message, is_float,
                               verify_parameters, get_geo_point)

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
        self.add_props_button.pressed.connect(self.insert_props)
        self.props_orientation_use_lane.stateChanged.connect(self.override_orientation)
        self.props_labels_button.pressed.connect(self.toggle_labels)

        self._labels_on = True
        layer_setup_props()
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

    def closeEvent(self, event):    # pylint: disable=invalid-name
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
        display_message(message, level="Info")

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()

        # Static objects orientation
        orientation = None
        if self.props_orientation_use_lane.isChecked():
            orientation = None
        else:
            if is_float(self.props_orientation.text()):
                orientation = float(self.props_orientation.text())
                orientation = math.radians(orientation)
            else:
                verification = verify_parameters(param=self.props_orientation.text())
                if len(verification) == 0:
                    # UI Information
                    message = f"Parameter {self.props_orientation.text()} does not exist!"
                    display_message(message, level="Critical")
                else:
                    orientation = float(verification["Value"])
                    orientation = math.radians(orientation)

        mass = None
        if is_float(self.props_mass.text()):
            mass = float(self.props_mass.text())
        else:
            verification = verify_parameters(param=self.props_mass.text())
            if len(verification) == 0:
                # UI Information
                message = f"Parameter {self.props_mass.text()} does not exist!"
                display_message(message, level="Critical")
            else:
                mass = self.props_mass.text()

        prop_attributes = {"Prop": self.props_selection.currentText(),
                           "Prop Type": self.props_object_type.currentText(),
                           "Orientation": orientation,
                           "Mass": mass,
                           "Physics": str(self.props_physics.isChecked())}
        tool = PointTool(canvas, layer, prop_attributes)
        canvas.setMapTool(tool)

    def override_orientation(self):
        """
        Toggles user input for walker orientation on/off
        """
        if self.props_orientation_use_lane.isChecked():
            self.props_orientation.setDisabled(True)
        else:
            self.props_orientation.setEnabled(True)


# pylint: disable=missing-function-docstring
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

    def canvasReleaseEvent(self, event):    # pylint: disable=invalid-name
        """
        Function when map canvas is clicked
        """
        # Get the click
        x = event.pos().x()  # pylint: disable=invalid-name
        y = event.pos().y()  # pylint: disable=invalid-name

        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)
        geopoint = get_geo_point(point)
        # Converting to ENU points
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
                                   float(enupoint.z) + 0.2,  # Avoid ground collision
                                   prop_attr["Physics"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
            self._data_input.addFeature(feature)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()
# pylint: enable=missing-function-docstring


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
            lane_id = []
            para_offsets = []
            for point in admap_matched_points:
                lane_ids_to_match.append(str(point.lanePoint.paraPoint.laneId))
                lane_id.append(point.lanePoint.paraPoint.laneId)
                para_offsets.append(point.lanePoint.paraPoint.parametricOffset)

            lane_id_selected, ok_pressed = QInputDialog.getItem(QInputDialog(), "Choose Lane ID",
                                                                "Lane ID", tuple(lane_ids_to_match),
                                                                current=0, editable=False)

            if ok_pressed:
                i = lane_ids_to_match.index(lane_id_selected)
                lane_id = lane_id[i]
                para_offset = para_offsets[i]
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading

        return None

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
            bot_right_y = float(enupoint.y) + (-0.5 * math.sin(angle) - 0.5 * math.cos(angle))
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
        return None

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
