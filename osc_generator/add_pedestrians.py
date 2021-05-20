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
    QgsPalLayerSettings, QgsPointXY, QgsProject, QgsVectorLayer,
    QgsVectorLayerSimpleLabeling, QgsFeatureRequest, QgsRectangle)
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
        self.add_walker_button.pressed.connect(self.insert_pedestrian)
        self.walker_selection_use_random.stateChanged.connect(self.random_walkers)
        self.walker_orientation_use_lane.stateChanged.connect(self.override_orientation)
        self.walker_labels_button.pressed.connect(self.toggle_labels)

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
                               QgsField("Pos Z", QVariant.Double),
                               QgsField("Init Speed", QVariant.String)]
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
        orientation = None
        if self.walker_orientation_use_lane.isChecked():
            orientation = None
        else:
            if self.is_float(self.walker_orientation.text()):
                walker_orientation = float(self.walker_orientation.text())
                walker_orientation = math.radians(walker_orientation)
            else:
                verification = self.verify_parameters(param=self.walker_orientation.text())
                if len(verification) == 0:
                    # UI Information
                    message = f"Parameter {self.walker_orientation.text()} does not exist!"
                    iface.messageBar().pushMessage("Info", message, level=Qgis.Critical)
                    QgsMessageLog.logMessage(message, level=Qgis.Critical)
                else:
                    orientation = float(verification["Value"])
                    orientation = math.radians(orientation)

        init_speed = None
        if self.is_float(self.walker_init_speed.text()):
            init_speed = float(self.walker_init_speed.text())
        else:
            verification = self.verify_parameters(param=self.walker_init_speed.text())
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

    def verify_parameters(self, param):
        """
        Checks Parameter Declarations attribute table to verify parameter exists

        Args:
            param (string): name of parameter to check against

        Returns:
            feature (dict): parameter definitions
        """
        param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
        query = f'"Parameter Name" = \'{param}\''
        feature_request = QgsFeatureRequest().setFilterExpression(query)
        features = param_layer.getFeatures(feature_request)
        feature = {}

        for feat in features:
            feature["Type"] = feat["Type"]
            feature["Value"] = feat["Value"]

        return feature

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

        lane_id = self.find_lane_id_at_point(event.pos())
        lane_id_t = int(lane_id)
        
        if lane_id_t is not None:
            lla_left = self.GetLaneEdgeLeft(lane_id_t)

            if lla_left is not None:
                altitude_sum = 0
                for lla in lla_left:
                    altitude_sum = altitude_sum + float(lla.altitude)
                altitude = altitude_sum / len(lla_left)
                print("The lane altitude is... " + str(altitude))

        # Converting to ENU points
        geopoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=altitude)
        print(geopoint)
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
                                   float(enupoint.z),
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

    def find_lane_id_at_point(self, pos):
        "..."
        registry = QgsProject.instance()
        layers = registry.mapLayers()
        for layer_name in layers:
            layer = layers[layer_name]
            point = self.toLayerCoordinates(layer, pos)
            request = QgsFeatureRequest()
            rect = QgsRectangle(point[0], point[1], point[0], point[1])
            request.setFilterRect(rect)
            try:
                layer_attrs = layer.attributeList()
                if layer_attrs is not None:
                    attr0_name = layer.attributeDisplayName(0)
                    attr2_name = layer.attributeDisplayName(2)
                    if attr0_name == "Id" and attr2_name == "HOV":
                        feats = layer.getFeatures(request)
                        for feat in feats:
                            attrs = feat.attributes()
                            return attrs[0]
            except AttributeError:
                pass
        return None
    
    def GetLaneEdge(self, lane_id, tf):
        lane_t = ad.map.lane.getLane(lane_id)
        geom = lane_t.edgeLeft if tf else lane_t.edgeRight
        geos = ad.map.point.GeoEdge()
        mCoordinateTransform = ad.map.point.CoordinateTransform()
        mCoordinateTransform.convert(geom.ecefEdge, geos)
        return geos
    
    def GetLaneEdgeLeft(self, lane_id):
        return self.GetLaneEdge(lane_id, True)

    def GetLaneEdgeRight(self, lane_id):
        return self.GetLaneEdge(lane_id, False)
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

        Returns:
            lane_heading: [float] heading of click point at selected lane ID
            lane_heading: [None] if click point is not valid
        """
        # dist = ad.physics.Distance(0.025)
        dist = ad.physics.Distance(5)
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
                # lane = ad.map.lane.getLane(lane_id)
                # altitude_range = ad.map.lane.calcLaneAltitudeRange(lane)
                # print("Altitude Max: " + str(altitude_range.maximum.mAltitude) + " Min:" + str(altitude_range.minimum.mAltitude))
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

            lane_id_selected, ok_pressed = QInputDialog.getItem(
                QInputDialog(),
                "Choose Lane ID",
                "Lane ID",
                tuple(lane_ids_to_match),
                current=0,
                editable=False)

            if ok_pressed:
                i = lane_ids_to_match.index(lane_id_selected)
                lane_id = lane_id[i]
                # lane = ad.map.lane.getLane(lane_id)
                # altitude_range = ad.map.lane.calcLaneAltitudeRange(lane)
                # print("Altitude Max: " + str(altitude_range.maximum.mAltitude) + " Min:" + str(altitude_range.minimum.mAltitude))
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

        walker_attributes = {"id": ped_id,
                             "Walker": walker_type,
                             "Orientation": float(attributes["Orientation"]),
                             "Init Speed": attributes["Init Speed"]}

        return walker_attributes
