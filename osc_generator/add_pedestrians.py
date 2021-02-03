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
from PyQt5.QtWidgets import QInputDialog
from qgis.core import (Qgis, QgsFeature, QgsField, QgsGeometry, QgsMessageLog,
                       QgsPalLayerSettings, QgsPointXY, QgsProject,
                       QgsVectorLayer, QgsVectorLayerSimpleLabeling)
from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.utils import iface

# AD Map plugin
import ad_map_access as ad

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
        self.addWalker_Button.pressed.connect(self.insert_pedestrian)
        self.walkerUseRandom.stateChanged.connect(self.random_walkers)
        self.walkerOrientation_useLane.stateChanged.connect(self.override_orientation)
        self.walkerLabels_Button.pressed.connect(self.toggle_labels)

        self._labels_on = True
        self._walker_layer = None
        self.layer_setup()

    def layer_setup(self):
        """
        Sets up layer for pedestrians
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Pedestrians"):
            walker_layer = QgsVectorLayer("Polygon", "Pedestrians", "memory")
            QgsProject.instance().addMapLayer(walker_layer, False)
            osc_layer.addLayer(walker_layer)
            # Setup layer attributes
            data_attributes = [QgsField("id", QVariant.Int),
                              QgsField("Walker", QVariant.String),
                              QgsField("Orientation", QVariant.Double),
                              QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double),
                              QgsField("Init Speed", QVariant.Double)]
            data_input = walker_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            walker_layer.updateFields()

            label_settings = QgsPalLayerSettings()
            label_settings.isExpression = True
            label_settings.fieldName = "concat('Pedestrian_', \"id\")"
            walker_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            walker_layer.setLabelsEnabled(True)

            iface.messageBar().pushMessage("Info", "Pedestrian layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Pedestrian layer added", level=Qgis.Info)

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

    def closeEvent(self, event):
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
        if self.walkerOrientation_useLane.isChecked():
            walker_orientation = None
        else:
            walker_orientation = float(self.walkerOrientation.text())
            walker_orientation = math.radians(walker_orientation)
        # Walker selection
        if self.walkerUseRandom.isChecked():
            walker_type = None
        else:
            walker_type = self.walkerSelection.currentText()
        walker_attributes = {"Walker Type": walker_type,
                             "Orientation": walker_orientation,
                             "Init Speed": self.walkerInitSpeed.text()}
        tool = PointTool(canvas, layer, walker_attributes)
        canvas.setMapTool(tool)

    def random_walkers(self):
        """
        Use random pedestrian entities instead of user specified
        """
        if self.walkerUseRandom.isChecked():
            self.walkerSelection.setDisabled(True)
        else:
            self.walkerSelection.setEnabled(True)

    def override_orientation(self):
        """
        Toggles user input for walker orientation on/off
        """
        if self.walkerOrientation_useLane.isChecked():
            self.walkerOrientation.setDisabled(True)
        else:
            self.walkerOrientation.setEnabled(True)

#pylint: disable=missing-function-docstring
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
        add_walker = AddPedestrianAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._pedestrian_attributes["Orientation"] = add_walker.get_pedestrian_heading(geopoint)

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
                                   pedestrian_attr["Init Speed"]])
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


class AddPedestrianAttribute():
    """
    Class for processing / acquiring pedestrian attributes.
    """
    def get_pedestrian_heading(self, geopoint):
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
            bot_right_y =  float(enupoint.y) + (-0.3 * math.sin(angle) - 0.35 * math.cos(angle))
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
        walker_dict={"Walker 0001": "walker.pedestrian.0001",
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
            random_walker = random.choice(walker_entries)
            walker_type = random_walker[1]
        else:
            walker_type = walker_dict[attributes["Walker Type"]]

        orientation = float(attributes["Orientation"])
        init_speed = float(attributes["Init Speed"])

        walker_attributes = {"id": ped_id,
                             "Walker": walker_type,
                             "Orientation": orientation,
                             "Init Speed": init_speed}

        return walker_attributes
