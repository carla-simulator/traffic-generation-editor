# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Vehicles
"""
import math
import os

# pylint: disable=no-name-in-module, no-member
from PyQt5.QtWidgets import QInputDialog
from qgis.core import (Qgis, QgsFeature, QgsGeometry, QgsMessageLog, QgsPointXY,
                       QgsProject, QgsFeatureRequest)
from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal
from qgis.utils import iface
import ad_map_access as ad

from .helper_functions import layer_setup_vehicle, get_geo_point

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'add_vehicles_widget.ui'))


class AddVehiclesDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to spawn vehicles on map.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Initialization of AddVehicles"""
        super(AddVehiclesDockWidget, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.add_vehicle_button.pressed.connect(self.insert_vehicle)
        self.vehicle_orientation_use_lane.stateChanged.connect(self.override_orientation)
        self.agent_selection.currentTextChanged.connect(self.agent_camera_selection)
        self.agent_selection.currentTextChanged.connect(self.agent_use_user_defined)
        self.vehicle_labels.pressed.connect(self.toggle_labels)

        self._labels_on = True
        self._vehicle_layer_ego = None
        self._vehicle_layer = None
        layer_setup_vehicle()

        self._vehicle_layer_ego = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
        self._vehicle_layer = QgsProject.instance().mapLayersByName("Vehicles")[0]

    def toggle_labels(self):
        """
        Toggles labels for vehicles on/off
        """
        if self._labels_on:
            self._vehicle_layer.setLabelsEnabled(False)
            self._vehicle_layer_ego.setLabelsEnabled(False)
            self._labels_on = False
        else:
            self._vehicle_layer.setLabelsEnabled(True)
            self._vehicle_layer_ego.setLabelsEnabled(True)
            self._labels_on = True

        self._vehicle_layer.triggerRepaint()
        self._vehicle_layer_ego.triggerRepaint()

    def closeEvent(self, event):    # pylint: disable=invalid-name
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def insert_vehicle(self):
        """
        Spawn vehicles on map with mouse click.
        User needs to select whether vehicle is ego before pressing button.
        """
        if self.vehicle_is_hero.isChecked():
            iface.setActiveLayer(self._vehicle_layer_ego)

            # UI Information
            message = "Using existing ego vehicle layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        else:
            iface.setActiveLayer(self._vehicle_layer)

            # UI Information
            message = "Using existing vehicle layer"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        # Check value entry
        orientation = None
        if self.vehicle_orientation_use_lane.isChecked():
            orientation = None
        else:
            if self.is_float(self.vehicle_orientation.text()):
                orientation = float(self.vehicle_orientation.text())
                orientation = math.radians(orientation)
            else:
                verification = self.verify_parameters(param=self.vehicle_orientation.text())
                if len(verification) == 0:
                    # UI Information
                    message = f"Parameter {self.vehicle_orientation.text()} does not exist!"
                    iface.messageBar().pushMessage("Info", message, level=Qgis.Critical)
                    QgsMessageLog.logMessage(message, level=Qgis.Critical)
                else:
                    orientation = float(verification["Value"])
                    orientation = math.radians(orientation)

        init_speed = None
        if self.is_float(self.vehicle_init_speed.text()):
            init_speed = float(self.vehicle_init_speed.text())
        else:
            verification = self.verify_parameters(param=self.vehicle_init_speed.text())
            if len(verification) == 0:
                # UI Information
                message = f"Parameter {self.vehicle_init_speed.text()} does not exist!"
                iface.messageBar().pushMessage("Info", message, level=Qgis.Critical)
                QgsMessageLog.logMessage(message, level=Qgis.Critical)
            else:
                init_speed = self.vehicle_init_speed.text()

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()

        if self.agent_selection.currentText() == "User Defined":
            agent = self.agent_user_defined.text()
        else:
            agent = self.agent_selection.currentText()

        vehicle_attributes = {"Model": self.vehicle_selection.currentText(),
                              "Orientation": orientation,
                              "InitSpeed": init_speed,
                              "Agent": agent,
                              "Agent Camera": self.agent_attach_camera.isChecked()}
        tool = PointTool(canvas, layer, vehicle_attributes)
        canvas.setMapTool(tool)

    def override_orientation(self):
        """
        Toggles user input for orientation based on "Use lane heading" setting.
        """
        if self.vehicle_orientation_use_lane.isChecked():
            self.vehicle_orientation.setDisabled(True)
        else:
            self.vehicle_orientation.setEnabled(True)

    def agent_camera_selection(self):
        """
        Toggles 'attach_camera' to be user-selectable if agent is 'simple_vehicle_control'
        """
        if self.agent_selection.currentText() == "simple_vehicle_control":
            self.agent_attach_camera.setEnabled(True)
        else:
            self.agent_attach_camera.setDisabled(True)

    def agent_use_user_defined(self):
        """
        Enables / Disable uesr defined agent text entry
        """
        if self.agent_selection.currentText() == "User Defined":
            self.agent_user_defined.setEnabled(True)
        else:
            self.agent_user_defined.setDisabled(True)

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

# pylint: disable=missing-function-docstring


class PointTool(QgsMapTool):
    """Enables Point Addition"""

    def __init__(self, canvas, layer, vehicle_attributes):
        QgsMapTool.__init__(self, canvas)
        self._canvas = canvas
        self._layer = layer
        self._data_input = layer.dataProvider()
        self._canvas.setCursor(Qt.CrossCursor)
        self._vehicle_attributes = vehicle_attributes
        if self._vehicle_attributes["Orientation"] is None:
            self._use_lane_heading = True
        else:
            self._use_lane_heading = False

    def canvasReleaseEvent(self, event):    # pylint: disable=invalid-name
        # Get the click
        x = event.pos().x()  # pylint: disable=invalid-name
        y = event.pos().y()  # pylint: disable=invalid-name

        point = self._canvas.getCoordinateTransform().toMapCoordinates(x, y)
        geopoint = get_geo_point(point)
        # Converting to ENU point
        enupoint = ad.map.point.toENU(geopoint)

        add_veh = AddVehicleAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._vehicle_attributes["Orientation"] = add_veh.get_vehicle_heading(geopoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self._vehicle_attributes["Orientation"] is not None:
            polygon_points = add_veh.spawn_vehicle(enupoint, self._vehicle_attributes["Orientation"])
            # Pass attributes to process
            veh_attr = add_veh.get_vehicle_attributes(self._layer, self._vehicle_attributes)

            # Set vehicle attributes
            feature = QgsFeature()
            feature.setAttributes([
                veh_attr["id"],
                veh_attr["Model"],
                veh_attr["Orientation"],
                float(enupoint.x),
                float(enupoint.y),
                float(enupoint.z) + 0.2,  # Avoid ground collision
                veh_attr["InitSpeed"],
                veh_attr["Agent"],
                veh_attr["Agent Camera"],
            ])
            feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
            self._data_input.addFeature(feature)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()
        self._canvas.unsetMapTool(self)

# pylint: enable=missing-function-docstring


class AddVehicleAttribute():
    """
    Handles processing of vehicle attributes.
    """

    def get_vehicle_heading(self, geopoint):
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
                para_offset = para_offsets[i]
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading
        return None

    def spawn_vehicle(self, enupoint, angle):
        """
        Spawns vehicle on the map and draws bounding boxes

        Args:
            enupoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """
        if angle is not None:
            bot_left_x = float(enupoint.x) + (-2 * math.cos(angle) - 1 * math.sin(angle))
            bot_left_y = float(enupoint.y) + (-2 * math.sin(angle) + 1 * math.cos(angle))
            bot_right_x = float(enupoint.x) + (-2 * math.cos(angle) + 1 * math.sin(angle))
            bot_right_y = float(enupoint.y) + (-2 * math.sin(angle) - 1 * math.cos(angle))
            top_left_x = float(enupoint.x) + (2 * math.cos(angle) - 1 * math.sin(angle))
            top_left_y = float(enupoint.y) + (2 * math.sin(angle) + 1 * math.cos(angle))
            top_center_x = float(enupoint.x) + 2.5 * math.cos(angle)
            top_center_y = float(enupoint.y) + 2.5 * math.sin(angle)
            top_right_x = float(enupoint.x) + (2 * math.cos(angle) + 1 * math.sin(angle))
            top_right_y = float(enupoint.y) + (2 * math.sin(angle) - 1 * math.cos(angle))

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

    def get_vehicle_attributes(self, layer, attributes):
        """
        Process vehicle attributes to be placed in attributes table

        Args:
            layer: [QGIS layer] layer that contains vehicle data
            attributes: [dict] vehicle attributes from GUI to be processed
        """
        # Get largest Vehicle ID from attribute table
        # If no vehicles has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largest_veh_id = layer.maximumValue(idx)
            veh_id = largest_veh_id + 1
        else:
            veh_id = 1

        # Match vehicle model
        vehicle_dict = {"Audi A2": "vehicle.audi.a2",
                        "Audi eTron": "vehicle.audi.etron",
                        "Audi TT": "vehicle.audi.tt",
                        "BH Crossbike": "vehicle.bh.crossbike",
                        "BMW Grandtourer": "vehicle.bmw.grandtourer",
                        "BMW iSetta (CARLA 0.9.12)": "vehicle.micro.microlino",
                        "BMW iSetta (CARLA 0.9.11)": "vehicle.bmw.isetta",
                        "Carla Cola Truck": "vehicle.carlamotors.carlacola",
                        "Chevrolet Impala": "vehicle.chevrolet.impala",
                        "Citroen C3": "vehicle.citroen.c3",
                        "Diamondback Century": "vehicle.diamondback.century",
                        "Dodge Charger Police (CARLA 0.9.12)": "vehicle.dodge.charger_police",
                        "Dodge Charger Police (CARLA 0.9.11)": "vehicle.dodge_charger.police",
                        "Gazelle Omafiets": "vehicle.gazelle.omafiets",
                        "Harley Davidson Low Rider": "vehicle.harley-davidson.low_rider",
                        "Jeep Wrangler": "vehicle.jeep.wrangler_rubicon",
                        "Kawasaki Ninja": "vehicle.kawasaki.ninja",
                        "Lincoln MKZ 2017 (CARLA 0.9.12)": "vehicle.lincoln.mkz_2017",
                        "Lincoln MKZ 2017 (CARLA 0.9.11)": "vehicle.lincoln.mkz2017",
                        "Lincoln MKZ 2020 (CARLA 0.9.12)": "vehicle.lincoln.mkz_2020",
                        "Lincoln MKZ 2020 (CARLA 0.9.11)": "vehicle.lincoln2020.mkz2020",
                        "Mercedes Benz Coupe (CARLA 0.9.12)": "vehicle.mercedes.coupe",
                        "Mercedes Benz Coupe (CARLA 0.9.11)": "vehicle.mercedes-benz.coupe",
                        "Mini Cooper ST (CARLA 0.9.12)": "vehicle.mini.cooper_s",
                        "Mini Cooper ST (CARLA 0.9.11)": "vehicle.mini.cooperst",
                        "Ford Mustang (CARLA 0.9.12)": "vehicle.ford.mustang",
                        "Ford Mustang (CARLA 0.9.11)": "vehicle.mustang.mustang",
                        "Nissan Micra": "vehicle.nissan.micra",
                        "Nissan Patrol": "vehicle.nissan.patrol",
                        "Seat Leon": "vehicle.seat.leon",
                        "Tesla Cybertruck": "vehicle.tesla.cybertruck",
                        "Tesla Model 3": "vehicle.tesla.model3",
                        "Toyota Prius": "vehicle.toyota.prius",
                        "Volkswagen T2": "vehicle.volkswagen.t2",
                        "Yamaha YZF": "vehicle.yamaha.yzf",
                        "Firetruck (CARLA 0.9.12)": "vehicle.carlamotors.firetruck",
                        "Mini Cooper 2021 (CARLA 0.9.12)": "vehicle.mini.cooper_s_2021",
                        "Nissan Patrol 2021 (CARLA 0.9.12)": "vehicle.nissan.patrol_2021",
                        "Ambulance (CARLA 0.9.12)": "vehicle.ford.ambulance",
                        "Mercedes Sprinter (CARLA 0.9.12)": "vehicle.mercedes.sprinter"}
        vehicle_model = vehicle_dict[attributes["Model"]]
        orientation = float(attributes["Orientation"])

        vehicle_attributes = {"id": veh_id,
                              "Model": vehicle_model,
                              "Orientation": orientation,
                              "InitSpeed": attributes["InitSpeed"],
                              "Agent": attributes["Agent"],
                              "Agent Camera": attributes["Agent Camera"]}
        return vehicle_attributes
