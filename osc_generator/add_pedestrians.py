# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Pedestrians
"""
import math
import os
import random
# pylint: disable=no-name-in-module, no-member
from qgis.core import (Qgis, QgsFeature, QgsGeometry, QgsMessageLog, QgsPointXY,
                       QgsProject)
from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.utils import iface
# AD Map plugin
import ad_map_access as ad

from .helper_functions import (layer_setup_walker, get_entity_heading, is_float,
                               verify_parameters, get_geo_point)

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'add_pedestrians_widget.ui'))


class AddPedestriansDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to spawn pedestrians on map.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialization of AddPedestriansDockWidget
        """
        super(AddPedestriansDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.add_walker_button.pressed.connect(self.insert_pedestrian)
        self.walker_selection_use_random.stateChanged.connect(self.random_walkers)
        self.walker_orientation_use_lane.stateChanged.connect(self.override_orientation)
        self.walker_labels_button.pressed.connect(self.toggle_labels)

        self._labels_on = True
        layer_setup_walker()
        self._walker_layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]

    def toggle_labels(self):
        """
        Toggles labels for pedestrians on/off
        """
        if self._labels_on:
            self._walker_layer.setLabelsEnabled(False)
            self._labels_on = False
        else:
            self._walker_layer.setLabelsEnabled(True)
            self._labels_on = True

        self._walker_layer.triggerRepaint()

    def closeEvent(self, event):    # pylint: disable=invalid-name
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def insert_pedestrian(self):
        """
        Spawn pedestrians on map with mouse click.
        """
        iface.setActiveLayer(self._walker_layer)

        # UI Information
        iface.messageBar().pushMessage("Info", "Using existing pedestrian layer", level=Qgis.Info)
        QgsMessageLog.logMessage("Using existing pedestrian layer", level=Qgis.Info)

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()

        # Walker Orientation
        orientation = None
        if self.walker_orientation_use_lane.isChecked():
            orientation = None
        else:
            if is_float(self.walker_orientation.text()):
                walker_orientation = float(self.walker_orientation.text())
                walker_orientation = math.radians(walker_orientation)
            else:
                verification = verify_parameters(param=self.walker_orientation.text())
                if len(verification) == 0:
                    # UI Information
                    message = f"Parameter {self.walker_orientation.text()} does not exist!"
                    iface.messageBar().pushMessage("Info", message, level=Qgis.Critical)
                    QgsMessageLog.logMessage(message, level=Qgis.Critical)
                else:
                    orientation = float(verification["Value"])
                    orientation = math.radians(orientation)

        init_speed = None
        if is_float(self.walker_init_speed.text()):
            init_speed = float(self.walker_init_speed.text())
        else:
            verification = verify_parameters(param=self.walker_init_speed.text())
            if len(verification) == 0:
                # UI Information
                message = f"Parameter {self.walker_init_speed.text()} does not exist!"
                iface.messageBar().pushMessage("Info", message, level=Qgis.Critical)
                QgsMessageLog.logMessage(message, level=Qgis.Critical)
            else:
                init_speed = self.walker_init_speed.text()

        # Walker selection
        if self.walker_selection_use_random.isChecked():
            walker_type = None
        else:
            walker_type = self.walker_selection.currentText()
        walker_attributes = {"Walker Type": walker_type,
                             "Orientation": orientation,
                             "Init Speed": init_speed}
        tool = PointTool(canvas, layer, walker_attributes)
        canvas.setMapTool(tool)

    def random_walkers(self):
        """
        Use random pedestrian entities instead of user specified
        """
        if self.walker_selection_use_random.isChecked():
            self.walker_selection.setDisabled(True)
        else:
            self.walker_selection.setEnabled(True)

    def override_orientation(self):
        """
        Toggles user input for walker orientation on/off
        """
        if self.walker_orientation_use_lane.isChecked():
            self.walker_orientation.setDisabled(True)
        else:
            self.walker_orientation.setEnabled(True)

# pylint: disable=missing-function-docstring


class PointTool(QgsMapTool):
    """Enables Point Addition"""

    def __init__(self, canvas, layer, pedestrian_attributes):
        QgsMapTool.__init__(self, canvas)
        self._canvas = canvas
        self._layer = layer
        self._data_input = layer.dataProvider()
        self._canvas.setCursor(Qt.CrossCursor)
        self._pedestrian_attributes = pedestrian_attributes
        if self._pedestrian_attributes["Orientation"] is None:
            self._use_lane_heading = True
        else:
            self._use_lane_heading = False

    def canvasReleaseEvent(self, event):    # pylint: disable=invalid-name
        # Get the click
        x = event.pos().x()  # pylint: disable=invalid-name
        y = event.pos().y()  # pylint: disable=invalid-name

        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)
        geopoint = get_geo_point(point)
        # Converting to ENU points
        enupoint = ad.map.point.toENU(geopoint)

        add_walker = AddPedestrianAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._pedestrian_attributes["Orientation"] = get_entity_heading(geopoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self._pedestrian_attributes["Orientation"] is not None:
            polygon_points = add_walker.spawn_pedestrian(enupoint,
                                                         self._pedestrian_attributes["Orientation"])
            # Pass attributes to process
            pedestrian_attr = add_walker.get_pedestrian_attributes(self._layer,
                                                                   self._pedestrian_attributes)

            # Set pedestrian attributes
            feature = QgsFeature()
            feature.setAttributes([pedestrian_attr["id"],
                                   pedestrian_attr["Walker"],
                                   pedestrian_attr["Orientation"],
                                   float(enupoint.x),
                                   float(enupoint.y),
                                   float(enupoint.z) + 0.2,  # Avoid ground collision
                                   pedestrian_attr["Init Speed"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
            self._data_input.addFeature(feature)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()

# pylint: enable=missing-function-docstring


class AddPedestrianAttribute():
    """
    Class for processing / acquiring pedestrian attributes.
    """

    def spawn_pedestrian(self, enupoint, angle):
        """
        Spawns pedestrian on the map and draws bounding boxes

        Args:
            enupoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """
        if angle is not None:
            bot_left_x = float(enupoint.x) + (-0.3 * math.cos(angle) - 0.35 * math.sin(angle))
            bot_left_y = float(enupoint.y) + (-0.3 * math.sin(angle) + 0.35 * math.cos(angle))
            bot_right_x = float(enupoint.x) + (-0.3 * math.cos(angle) + 0.35 * math.sin(angle))
            bot_right_y = float(enupoint.y) + (-0.3 * math.sin(angle) - 0.35 * math.cos(angle))
            top_left_x = float(enupoint.x) + (0.3 * math.cos(angle) - 0.35 * math.sin(angle))
            top_left_y = float(enupoint.y) + (0.3 * math.sin(angle) + 0.35 * math.cos(angle))
            top_center_x = float(enupoint.x) + 0.4 * math.cos(angle)
            top_center_y = float(enupoint.y) + 0.4 * math.sin(angle)
            top_right_x = float(enupoint.x) + (0.3 * math.cos(angle) + 0.35 * math.sin(angle))
            top_right_y = float(enupoint.y) + (0.3 * math.sin(angle) - 0.35 * math.cos(angle))

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
        return None

    def get_pedestrian_attributes(self, layer, attributes):
        """
        Inputs pedestrian attributes into table

        Args:
            layer: [QGIS layer] layer that contains pedestrian data
            attributes: [dict] pedestrians attributes from GUI to be processed
        """
        # Get largest pedestrian ID from attribute table
        # If no pedestrians has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largest_ped_id = layer.maximumValue(idx)
            ped_id = largest_ped_id + 1
        else:
            ped_id = 1
        # Match pedestrian model
        walker_dict = {"Walker 0001": "walker.pedestrian.0001",
                       "Walker 0002": "walker.pedestrian.0002",
                       "Walker 0003": "walker.pedestrian.0003",
                       "Walker 0004": "walker.pedestrian.0004",
                       "Walker 0005": "walker.pedestrian.0005",
                       "Walker 0006": "walker.pedestrian.0006",
                       "Walker 0007": "walker.pedestrian.0007",
                       "Walker 0008": "walker.pedestrian.0008",
                       "Walker 0009": "walker.pedestrian.0009",
                       "Walker 0010": "walker.pedestrian.0010",
                       "Walker 0011": "walker.pedestrian.0011",
                       "Walker 0012": "walker.pedestrian.0012",
                       "Walker 0013": "walker.pedestrian.0013",
                       "Walker 0014": "walker.pedestrian.0014",
                       "Walker 0015": "walker.pedestrian.0015"}
        if attributes["Walker Type"] is None:
            walker_entries = list(walker_dict.items())
            random_walker = random.choice(walker_entries)   # nosec
            walker_type = random_walker[1]
        else:
            walker_type = walker_dict[attributes["Walker Type"]]

        walker_attributes = {"id": ped_id,
                             "Walker": walker_type,
                             "Orientation": float(attributes["Orientation"]),
                             "Init Speed": attributes["Init Speed"]}

        return walker_attributes
