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
    os.path.dirname(__file__), 'AddVehiclesWidget.ui'))


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
        self.AddVehicleButton.pressed.connect(self.InsertVehicle)
        self.vehicleOrientation_useLane.stateChanged.connect(self.OverrideOrientation)
        self.vehicleIsHero.stateChanged.connect(self.EgoAgentSelection)
        self.agentSelection.currentTextChanged.connect(self.AgentCameraSelection)
        self.vehicleLabels.pressed.connect(self.ToggleLabels)

        self.LabelsOn = True
        self.vehicleLayerEgo = None
        self.vehicleLayer = None
        self.LayerSetup()

    def LayerSetup(self):
        """
        Sets up layer for vehicles
        """
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if (not QgsProject.instance().mapLayersByName("Vehicles") or
            not QgsProject.instance().mapLayersByName("Vehicles - Ego")):
            vehicleLayerEgo = QgsVectorLayer("Polygon", "Vehicles - Ego", "memory")
            vehicleLayer = QgsVectorLayer("Polygon", "Vehicles", "memory")
            QgsProject.instance().addMapLayer(vehicleLayerEgo, False)
            QgsProject.instance().addMapLayer(vehicleLayer, False)
            OSCLayer.addLayer(vehicleLayerEgo)
            OSCLayer.addLayer(vehicleLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("id", QVariant.Int),
                              QgsField("Vehicle Model", QVariant.String),
                              QgsField("Orientation", QVariant.Double),
                              QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double),
                              QgsField("Init Speed", QVariant.Double),
                              QgsField("Agent", QVariant.String),
                              QgsField("Agent Camera", QVariant.Bool)]
            dataInputEgo = vehicleLayerEgo.dataProvider()
            dataInput = vehicleLayer.dataProvider()
            dataInputEgo.addAttributes(dataAttributes)
            dataInput.addAttributes(dataAttributes)
            vehicleLayerEgo.updateFields()
            vehicleLayer.updateFields()

            labelSettingsEgo = QgsPalLayerSettings()
            labelSettingsEgo.isExpression = True
            labelSettingsEgo.fieldName = "concat('Ego_', \"id\")"
            vehicleLayerEgo.setLabeling(QgsVectorLayerSimpleLabeling(labelSettingsEgo))
            vehicleLayerEgo.setLabelsEnabled(True)
            labelSettings = QgsPalLayerSettings()
            labelSettings.isExpression = True
            labelSettings.fieldName = "concat('Vehicle_', \"id\")"
            vehicleLayer.setLabeling(QgsVectorLayerSimpleLabeling(labelSettings))
            vehicleLayer.setLabelsEnabled(True)

            iface.messageBar().pushMessage("Info", "Vehicle layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Vehicle layer added", level=Qgis.Info)

        self.vehicleLayerEgo = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
        self.vehicleLayer = QgsProject.instance().mapLayersByName("Vehicles")[0]

    def ToggleLabels(self):
        """
        Toggles labels for vehicles on/off
        """
        if self.LabelsOn:
            self.vehicleLayer.setLabelsEnabled(False)
            self.vehicleLayerEgo.setLabelsEnabled(False)
            self.LabelsOn = False
        else:
            self.vehicleLayer.setLabelsEnabled(True)
            self.vehicleLayerEgo.setLabelsEnabled(True)
            self.LabelsOn = True

        self.vehicleLayer.triggerRepaint()
        self.vehicleLayerEgo.triggerRepaint()

    def closeEvent(self, event):
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def InsertVehicle(self):
        """
        Spawn vehicles on map with mouse click.
        User needs to select whether vehicle is ego before pressing button.
        """
        if self.vehicleIsHero.isChecked():
            # Indexing ego vehicle layer and set as active
            vehicleLayer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            iface.setActiveLayer(vehicleLayer)

            # UI Information
            iface.messageBar().pushMessage("Info", "Using existing vehicle layer", level=Qgis.Info)
            QgsMessageLog.logMessage("Using existing vehicle layer", level=Qgis.Info)
        else:
            # Indexing vehicle layer and set as active
            vehicleLayer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            iface.setActiveLayer(vehicleLayer)

            # UI Information
            iface.messageBar().pushMessage("Info", "Using existing vehicle layer", level=Qgis.Info)
            QgsMessageLog.logMessage("Using existing vehicle layer", level=Qgis.Info)

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()
        if self.vehicleOrientation_useLane.isChecked():
            vehicleOrientation = None
        else:
            vehicleOrientation = float(self.vehicleOrientation.text())
            vehicleOrientation = math.radians(vehicleOrientation)
        VehicleAttributes = {"Model":self.vehicleSelection.currentText(),
                             "Orientation":vehicleOrientation,
                             "InitSpeed":self.vehicleInitSpeed.text(),
                             "Agent": self.agentSelection.currentText(),
                             "Agent Camera": self.agent_AttachCamera.isChecked()}
        tool = PointTool(canvas, layer, VehicleAttributes)
        canvas.setMapTool(tool)

    def OverrideOrientation(self):
        """
        Toggles user input for orientation based on "Use lane heading" setting.
        """
        if self.vehicleOrientation_useLane.isChecked():
            self.vehicleOrientation.setDisabled(True)
        else:
            self.vehicleOrientation.setEnabled(True)

    def EgoAgentSelection(self):
        """
        Toggles agent selection group depending on whether vehicle is ego.
        """
        if self.vehicleIsHero.isChecked():
            self.agentGroup.setEnabled(True)
        else:
            self.agentGroup.setDisabled(True)

    def AgentCameraSelection(self):
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

    def __init__(self, canvas, layer, VehicleAttributes):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.dataInput = layer.dataProvider()
        self.canvas.setCursor(Qt.CrossCursor)
        self.VehicleAttributes = VehicleAttributes
        if self.VehicleAttributes["Orientation"] is None:
            self.useLaneHeading = True
        else:
            self.useLaneHeading = False

    def canvasPressEvent(self, event):
        pass

    def canvasMoveEvent(self, event):
        pass

    def canvasReleaseEvent(self, event):
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # Converting to ENU points
        GeoPoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=0)
        EnuPoint = ad.map.point.toENU(GeoPoint)
        AddVeh = AddVehicleAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self.useLaneHeading is True:
            self.VehicleAttributes["Orientation"] = AddVeh.getVehicleHeading(GeoPoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self.VehicleAttributes["Orientation"] is not None:
            PolygonPoints = AddVeh.spawnVehicle(EnuPoint, self.VehicleAttributes["Orientation"])
            # Pass attributes to process
            VehAttr = AddVeh.getVehicleAttributes(self.layer, self.VehicleAttributes)

            # Set vehicle attributes
            feature = QgsFeature()
            feature.setAttributes([VehAttr["id"],
                                   VehAttr["Model"],
                                   VehAttr["Orientation"],
                                   float(EnuPoint.x),
                                   float(EnuPoint.y),
                                   VehAttr["InitSpeed"],
                                   VehAttr["Agent"],
                                   VehAttr["Agent Camera"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([PolygonPoints]))
            self.dataInput.addFeature(feature)

        self.layer.updateExtents()
        self.canvas.refreshAllLayers()
        self.canvas.unsetMapTool(self)

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
    def getVehicleHeading(self, GeoPoint):
        """
        Acquires vehicle heading based on spawn position in map.
        Throws error if spawn position is >0.1 m from lane.
        """
        dist = ad.physics.Distance(0.025)
        adMapMatchedPoints = ad.map.match.AdMapMatching.findLanes(GeoPoint, dist)

        lanesDetected = 0
        for point in adMapMatchedPoints:
            lanesDetected += 1

        if lanesDetected == 0:
            iface.messageBar().pushMessage("Error", "Click point is too far from valid lane", level=Qgis.Critical)
            QgsMessageLog.logMessage("Click point is too far from valid lane", level=Qgis.Critical)
            return None
        elif lanesDetected == 1:
            for point in adMapMatchedPoints:
                laneID = point.lanePoint.paraPoint.laneId
                paraOffset = point.lanePoint.paraPoint.parametricOffset
                paraPoint = ad.map.point.createParaPoint(laneID, paraOffset)
                laneHeading = ad.map.lane.getLaneENUHeading(paraPoint)
                return laneHeading
        else:
            laneIDsToMatch = []
            laneIDs = []
            paraOffsets = []
            for point in adMapMatchedPoints:
                laneIDsToMatch.append(str(point.lanePoint.paraPoint.laneId))
                laneIDs.append(point.lanePoint.paraPoint.laneId)
                paraOffsets.append(point.lanePoint.paraPoint.parametricOffset)

            laneIDMatched, okPressed = QInputDialog.getItem(QInputDialog(), "Choose Lane ID",
                "Lane ID", tuple(laneIDsToMatch), current=0, editable=False)

            if okPressed:
                i = laneIDsToMatch.index(laneIDMatched)
                laneID = laneIDs[i]
                paraOffset = paraOffsets[i]
                paraPoint = ad.map.point.createParaPoint(laneID, paraOffset)
                laneHeading = ad.map.lane.getLaneENUHeading(paraPoint)
                return laneHeading

    def spawnVehicle(self, EnuPoint, angle):
        """
        Spawns vehicle on the map and draws bounding boxes

        Args:
            EnuPoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """

        if angle is not None:
            BotLeftX = float(EnuPoint.x) + (-2 * math.cos(angle) - 1 * math.sin(angle))
            BotLeftY = float(EnuPoint.y) + (-2 * math.sin(angle) + 1 * math.cos(angle))
            BotRightX = float(EnuPoint.x) + (-2 * math.cos(angle) + 1 * math.sin(angle))
            BotRightY =  float(EnuPoint.y) + (-2 * math.sin(angle) - 1 * math.cos(angle))
            TopLeftX = float(EnuPoint.x) + (2 * math.cos(angle) - 1 * math.sin(angle))
            TopLeftY = float(EnuPoint.y) + (2 * math.sin(angle) + 1 * math.cos(angle))
            TopCenterX = float(EnuPoint.x) + 2.5 * math.cos(angle)
            TopCenterY = float(EnuPoint.y) + 2.5 * math.sin(angle)
            TopRightX = float(EnuPoint.x) + (2 * math.cos(angle) + 1 * math.sin(angle))
            TopRightY = float(EnuPoint.y) + (2 * math.sin(angle) - 1 * math.cos(angle))

            # Create ENU points for polygon
            BotLeft = ad.map.point.createENUPoint(x=BotLeftX, y=BotLeftY, z=0)
            BotRight = ad.map.point.createENUPoint(x=BotRightX, y=BotRightY, z=0)
            TopLeft = ad.map.point.createENUPoint(x=TopLeftX, y=TopLeftY, z=0)
            TopCenter = ad.map.point.createENUPoint(x=TopCenterX, y=TopCenterY, z=0)
            TopRight = ad.map.point.createENUPoint(x=TopRightX, y=TopRightY, z=0)

            # Convert back to Geo points
            BotLeft = ad.map.point.toGeo(BotLeft)
            BotRight = ad.map.point.toGeo(BotRight)
            TopLeft = ad.map.point.toGeo(TopLeft)
            TopCenter = ad.map.point.toGeo(TopCenter)
            TopRight = ad.map.point.toGeo(TopRight)

            # Create polygon
            PolygonPoints = [QgsPointXY(BotLeft.longitude, BotLeft.latitude),
                            QgsPointXY(BotRight.longitude, BotRight.latitude),
                            QgsPointXY(TopRight.longitude, TopRight.latitude),
                            QgsPointXY(TopCenter.longitude, TopCenter.latitude),
                            QgsPointXY(TopLeft.longitude, TopLeft.latitude)]

            return PolygonPoints

    def getVehicleAttributes(self, layer, attributes):
        """
        Process vehicle attributes to be placed in attributes table
        """
        # Get largest Vehicle ID from attribute table
        # If no vehicles has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largestVehID = layer.maximumValue(idx)
            VehID = largestVehID + 1
        else:
            VehID = 1

        # Match vehicle model
        VehicleDict={"Audi A2": "vehicle.audi.a2",
                     "Audi eTron": "vehicle.audi.etron",
                     "Audi TT": "vehicle.audi.tt",
                     "BH Crossbike": "vehicle.bh.crossbike",
                     "BMW Grandtourer": "vehicle.bmw.grandtourer",
                     "BMW iSetta": "vehicle.bmw.isetta",
                     "Carla Cola Truck": "vehicle.arlamotors.carlacola",
                     "Chevrolet Impala": "vehicle.chevrolet.impala",
                     "Citroen C3": "vehicle.citroen.c3",
                     "Diamondback Century": "vehicle.diamondback.century",
                     "Dodge Charger Police": "vehicle.dodge_charger.police",
                     "Gazelle Omafiets": "vehicle.gazelle.omafiets",
                     "Harley Davidson Low Rider": "vehicle.harley-davidson.low_rider",
                     "Jeep Wrangler": "vehicle.jeep.wrangler_rubicon",
                     "Kawasaki Ninja": "vehicle.kawasaki.ninja",
                     "Lincoln MKZ 2017": "vehicle.lincoln.mkz2017",
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
        VehicleModel = VehicleDict[attributes["Model"]]
        Orientation = float(attributes["Orientation"])
        InitSpeed = float(attributes["InitSpeed"])

        VehicleAttributes = {"id": VehID,
                             "Model": VehicleModel,
                             "Orientation": Orientation,
                             "InitSpeed": InitSpeed,
                             "Agent": attributes["Agent"],
                             "Agent Camera": attributes["Agent Camera"]}
        return VehicleAttributes
