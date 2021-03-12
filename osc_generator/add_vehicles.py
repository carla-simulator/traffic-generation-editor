# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Static Objects
"""
import math
import os

# pylint: disable=no-name-in-module, no-member
import ad_map_access as ad
from PyQt5.QtWidgets import QInputDialog
from qgis.core import (Qgis, QgsFeature, QgsField, QgsGeometry, QgsMessageLog, QgsPointXY,
    QgsProject, QgsVectorLayer, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.utils import iface

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
        self.AddVehicleButton.pressed.connect(self.insert_vehicle)
        self.vehicleOrientation_useLane.stateChanged.connect(self.override_orientation)
        self.agentSelection.currentTextChanged.connect(self.agent_camera_selection)
        self.vehicleLabels.pressed.connect(self.toggle_labels)

        self._labels_on = True
        self._vehicle_layer_ego = None
        self._vehicle_layer = None
        self.layer_setup()

    def layer_setup(self):
        """
        Sets up layer for vehicles
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if (not QgsProject.instance().mapLayersByName("Vehicles") or
            not QgsProject.instance().mapLayersByName("Vehicles - Ego")):
            vehicle_layer_ego = QgsVectorLayer("Polygon", "Vehicles - Ego", "memory")
            vehicle_layer = QgsVectorLayer("Polygon", "Vehicles", "memory")
            QgsProject.instance().addMapLayer(vehicle_layer_ego, False)
            QgsProject.instance().addMapLayer(vehicle_layer, False)
            osc_layer.addLayer(vehicle_layer_ego)
            osc_layer.addLayer(vehicle_layer)
            # Setup layer attributes
            data_attributes = [QgsField("id", QVariant.Int),
                               QgsField("Vehicle Model", QVariant.String),
                               QgsField("Orientation", QVariant.Double),
                               QgsField("Pos X", QVariant.Double),
                               QgsField("Pos Y", QVariant.Double),
                               QgsField("Init Speed", QVariant.Double),
                               QgsField("Agent", QVariant.String),
                               QgsField("Agent Camera", QVariant.Bool)]
            data_input_ego = vehicle_layer_ego.dataProvider()
            data_input = vehicle_layer.dataProvider()
            data_input_ego.addAttributes(data_attributes)
            data_input.addAttributes(data_attributes)
            vehicle_layer_ego.updateFields()
            vehicle_layer.updateFields()

            label_settings_ego = QgsPalLayerSettings()
            label_settings_ego.isExpression = True
            label_settings_ego.fieldName = "concat('Ego_', \"id\")"
            vehicle_layer_ego.setLabeling(QgsVectorLayerSimpleLabeling(label_settings_ego))
            vehicle_layer_ego.setLabelsEnabled(True)
            label_settings = QgsPalLayerSettings()
            label_settings.isExpression = True
            label_settings.fieldName = "concat('Vehicle_', \"id\")"
            vehicle_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            vehicle_layer.setLabelsEnabled(True)

            iface.messageBar().pushMessage("Info", "Vehicle layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Vehicle layer added", level=Qgis.Info)

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

    def closeEvent(self, event):
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
        if self.vehicleIsHero.isChecked():
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

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()
        if self.vehicleOrientation_useLane.isChecked():
            vehicle_orientation = None
        else:
            vehicle_orientation = float(self.vehicleOrientation.text())
            vehicle_orientation = math.radians(vehicle_orientation)
        vehicle_attributes = {"Model":self.vehicleSelection.currentText(),
                              "Orientation":vehicle_orientation,
                              "InitSpeed":self.vehicleInitSpeed.text(),
                              "Agent": self.agentSelection.currentText(),
                              "Agent Camera": self.agent_AttachCamera.isChecked()}
        tool = PointTool(canvas, layer, vehicle_attributes)
        canvas.setMapTool(tool)

    def override_orientation(self):
        """
        Toggles user input for orientation based on "Use lane heading" setting.
        """
        if self.vehicleOrientation_useLane.isChecked():
            self.vehicleOrientation.setDisabled(True)
        else:
            self.vehicleOrientation.setEnabled(True)

    def agent_camera_selection(self):
        """
        Toggles 'attach_camera' to be user-selectable if agent is 'simple_vehicle_control'
        """
        if self.agentSelection.currentText() == "simple_vehicle_control":
            self.agent_AttachCamera.setEnabled(True)
        else:
            self.agent_AttachCamera.setDisabled(True)


#pylint: disable=missing-function-docstring
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
        add_veh = AddVehicleAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self._use_lane_heading is True:
            self._vehicle_attributes["Orientation"] = add_veh.get_vehicle_heading(geopoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self._vehicle_attributes["Orientation"] is not None:
            polygon_points = add_veh.spawnVehicle(enupoint, self._vehicle_attributes["Orientation"])
            # Pass attributes to process
            veh_attr = add_veh.get_vehicle_attributes(self._layer, self._vehicle_attributes)

            # Set vehicle attributes
            feature = QgsFeature()
            feature.setAttributes([veh_attr["id"],
                                   veh_attr["Model"],
                                   veh_attr["Orientation"],
                                   float(enupoint.x),
                                   float(enupoint.y),
                                   veh_attr["InitSpeed"],
                                   veh_attr["Agent"],
                                   veh_attr["Agent Camera"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([polygon_points]))
            self._data_input.addFeature(feature)

        self._layer.updateExtents()
        self._canvas.refreshAllLayers()
        self._canvas.unsetMapTool(self)

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

    def spawnVehicle(self, enupoint, angle):
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
            bot_right_y =  float(enupoint.y) + (-2 * math.sin(angle) - 1 * math.cos(angle))
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
        vehicle_dict={"Audi A2": "vehicle.audi.a2",
                      "Audi eTron": "vehicle.audi.etron",
                       "Audi TT": "vehicle.audi.tt",
                      "BH Crossbike": "vehicle.bh.crossbike",
                      "BMW Grandtourer": "vehicle.bmw.grandtourer",
                      "BMW iSetta": "vehicle.bmw.isetta",
                      "Carla Cola Truck": "vehicle.carlamotors.carlacola",
                      "Chevrolet Impala": "vehicle.chevrolet.impala",
                      "Citroen C3": "vehicle.citroen.c3",
                      "Diamondback Century": "vehicle.diamondback.century",
                      "Dodge Charger Police": "vehicle.dodge_charger.police",
                      "Gazelle Omafiets": "vehicle.gazelle.omafiets",
                      "Harley Davidson Low Rider": "vehicle.harley-davidson.low_rider",
                      "Jeep Wrangler": "vehicle.jeep.wrangler_rubicon",
                      "Kawasaki Ninja": "vehicle.kawasaki.ninja",
                      "Lincoln MKZ 2017": "vehicle.lincoln.mkz2017",
                      "Lincoln MKZ 2020": "vehicle.lincoln2020.mkz2020",
                      "Mercedes Benz Coupe": "vehicle.mercedes-benz.coupe",
                      "Mini Cooper ST": "vehicle.mini.cooperst",
                      "Ford Mustang": "vehicle.mustang.mustang",
                      "Nissan Micra": "vehicle.nissan.micra",
                      "Nissan Patrol": "vehicle.nissan.patrol",
                      "Seat Leon": "vehicle.seat.leon",
                      "Tesla Cybertruck": "vehicle.tesla.cybertruck",
                      "Tesla Model 3": "vehicle.tesla.model3",
                      "Toyota Prius": "vehicle.toyota.prius",
                      "Volkswagen T2": "vehicle.volkswagen.t2",
                      "Yamaha YZF": "vehicle.yamaha.yzf"}
        vehicle_model = vehicle_dict[attributes["Model"]]
        orientation = float(attributes["Orientation"])
        init_speed = float(attributes["InitSpeed"])

        vehicle_attributes = {"id": veh_id,
                              "Model": vehicle_model,
                              "Orientation": orientation,
                              "InitSpeed": init_speed,
                              "Agent": attributes["Agent"],
                              "Agent Camera": attributes["Agent Camera"]}
        return vehicle_attributes
