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
    os.path.dirname(__file__), 'AddPedestriansWidget.ui'))


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
        self.addWalkerButton.pressed.connect(self.InsertPedestrian)
        self.walkerUseRandom.stateChanged.connect(self.RandomWalkers)
        self.walkerOrientation_useLane.stateChanged.connect(self.OverrideOrientation)
        self.walkerLabels.pressed.connect(self.ToggleLabels)

        self.LabelsOn = True
        self.walkerLayer = None
        self.LayerSetup()

    def LayerSetup(self):
        """
        Sets up layer for pedestrians
        """
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Pedestrians"):
            walkerLayer = QgsVectorLayer("Polygon", "Pedestrians", "memory")
            QgsProject.instance().addMapLayer(walkerLayer, False)
            OSCLayer.addLayer(walkerLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("id", QVariant.Int),
                              QgsField("Walker", QVariant.String),
                              QgsField("Orientation", QVariant.Double),
                              QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double),
                              QgsField("Init Speed", QVariant.Double)]
            dataInput = walkerLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            walkerLayer.updateFields()

            labelSettings = QgsPalLayerSettings()
            labelSettings.isExpression = True
            labelSettings.fieldName = "concat('Pedestrian_', \"id\")"
            walkerLayer.setLabeling(QgsVectorLayerSimpleLabeling(labelSettings))
            walkerLayer.setLabelsEnabled(True)

            iface.messageBar().pushMessage("Info", "Pedestrian layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Pedestrian layer added", level=Qgis.Info)

        self.walkerLayer = QgsProject.instance().mapLayersByName("Pedestrians")[0]

    def ToggleLabels(self):
        """
        Toggles labels for pedestrians on/off
        """
        if self.LabelsOn:
            self.walkerLayer.setLabelsEnabled(False)
            self.LabelsOn = False
        else:
            self.walkerLayer.setLabelsEnabled(True)
            self.LabelsOn = True

        self.walkerLayer.triggerRepaint()

    def closeEvent(self, event):
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def InsertPedestrian(self):
        """
        Spawn pedestrians on map with mouse click.
        """
        iface.setActiveLayer(self.walkerLayer)

        # UI Information
        iface.messageBar().pushMessage("Info", "Using existing pedestrian layer", level=Qgis.Info)
        QgsMessageLog.logMessage("Using existing pedestrian layer", level=Qgis.Info)

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()
        # Walker Orientation
        if self.walkerOrientation_useLane.isChecked():
            walkerOrientation = None
        else:
            walkerOrientation = float(self.walkerOrientation.text())
            walkerOrientation = math.radians(walkerOrientation)
        # Walker selection
        if self.walkerUseRandom.isChecked():
            walkerType = None
        else:
            walkerType = self.walkerSelection.currentText()
        pedestrianAttributes = {"Walker Type": walkerType,
                             "Orientation": walkerOrientation,
                             "Init Speed": self.walkerInitSpeed.text()}
        tool = PointTool(canvas, layer, pedestrianAttributes)
        canvas.setMapTool(tool)

    def RandomWalkers(self):
        """
        Use random pedestrian entities instead of user specified
        """
        if self.walkerUseRandom.isChecked():
            self.walkerSelection.setDisabled(True)
        else:
            self.walkerSelection.setEnabled(True)

    def OverrideOrientation(self):
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

    def __init__(self, canvas, layer, pedestrianAttributes):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.dataInput = layer.dataProvider()
        self.canvas.setCursor(Qt.CrossCursor)
        self.pedestrianAttributes = pedestrianAttributes
        if self.pedestrianAttributes["Orientation"] is None:
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
        AddWalker = AddPedestrianAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self.useLaneHeading is True:
            self.pedestrianAttributes["Orientation"] = AddWalker.getPedestrianHeading(GeoPoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self.pedestrianAttributes["Orientation"] is not None:
            PolygonPoints = AddWalker.spawnPedestrian(EnuPoint, self.pedestrianAttributes["Orientation"])
            # Pass attributes to process
            PedAttr = AddWalker.getPedestrianAttributes(self.layer, self.pedestrianAttributes)

            # Set pedestrian attributes
            feature = QgsFeature()
            feature.setAttributes([PedAttr["id"],
                                   PedAttr["Walker"],
                                   PedAttr["Orientation"],
                                   float(EnuPoint.x),
                                   float(EnuPoint.y),
                                   PedAttr["Init Speed"]])
            feature.setGeometry(QgsGeometry.fromPolygonXY([PolygonPoints]))
            self.dataInput.addFeature(feature)

        self.layer.updateExtents()
        self.canvas.refreshAllLayers()

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
    def getPedestrianHeading(self, GeoPoint):
        """
        Acquires heading based on spawn position in map.
        Prompts user to select lane if multiple lanes exist at spawn position.
        Throws error if spawn position is not on lane.
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

    def spawnPedestrian(self, EnuPoint, angle):
        """
        Spawns pedestrian on the map and draws bounding boxes

        Args:
            EnuPoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """
        if angle is not None:
            BotLeftX = float(EnuPoint.x) + (-0.3 * math.cos(angle) - 0.35 * math.sin(angle))
            BotLeftY = float(EnuPoint.y) + (-0.3 * math.sin(angle) + 0.35 * math.cos(angle))
            BotRightX = float(EnuPoint.x) + (-0.3 * math.cos(angle) + 0.35 * math.sin(angle))
            BotRightY =  float(EnuPoint.y) + (-0.3 * math.sin(angle) - 0.35 * math.cos(angle))
            TopLeftX = float(EnuPoint.x) + (0.3 * math.cos(angle) - 0.35 * math.sin(angle))
            TopLeftY = float(EnuPoint.y) + (0.3 * math.sin(angle) + 0.35 * math.cos(angle))
            TopCenterX = float(EnuPoint.x) + 0.4 * math.cos(angle)
            TopCenterY = float(EnuPoint.y) + 0.4 * math.sin(angle)
            TopRightX = float(EnuPoint.x) + (0.3 * math.cos(angle) + 0.35 * math.sin(angle))
            TopRightY = float(EnuPoint.y) + (0.3 * math.sin(angle) - 0.35 * math.cos(angle))

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

    def getPedestrianAttributes(self, layer, attributes):
        """
        Inputs pedestrian attributes into table
        """
        # Get largest pedestrian ID from attribute table
        # If no pedestrians has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largestPedID = layer.maximumValue(idx)
            PedID = largestPedID + 1
        else:
            PedID = 1
        # Match pedestrian model
        WalkerDict={"Walker 0001": "walker.pedestrian.0001",
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
            WalkerEntries = list(WalkerDict.items())
            RandomWalker = random.choice(WalkerEntries)
            WalkerType = RandomWalker[1]
        else:
            WalkerType = attributes["Walker Type"]

        Orientation = float(attributes["Orientation"])
        InitSpeed = float(attributes["Init Speed"])

        WalkerAttributes = {"id": PedID,
                            "Walker": WalkerType,
                            "Orientation": Orientation,
                            "Init Speed": InitSpeed}

        return WalkerAttributes
