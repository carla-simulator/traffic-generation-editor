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
    os.path.dirname(__file__), 'AddStaticObjects.ui'))


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
        self.addPropsButton.pressed.connect(self.InsertProps)
        self.propsOrientation_useLane.stateChanged.connect(self.OverrideOrientation)
        self.propsLabels.pressed.connect(self.ToggleLabels)

        self.LabelsOn = True
        self.propsLayer = None
        self.LayerSetup()

    def LayerSetup(self):
        """
        Sets up layer for pedestrians
        """
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Static Objects"):
            propsLayer = QgsVectorLayer("Polygon", "Static Objects", "memory")
            QgsProject.instance().addMapLayer(propsLayer, False)
            OSCLayer.addLayer(propsLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("id", QVariant.Int),
                              QgsField("Prop", QVariant.String),
                              QgsField("Prop Type", QVariant.String),
                              QgsField("Orientation", QVariant.Double),
                              QgsField("Mass", QVariant.Double),
                              QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double),
                              QgsField("Physics", QVariant.Bool)]
            dataInput = propsLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            propsLayer.updateFields()

            labelSettings = QgsPalLayerSettings()
            labelSettings.isExpression = True
            labelSettings.fieldName = "concat('Prop_', \"id\")"
            propsLayer.setLabeling(QgsVectorLayerSimpleLabeling(labelSettings))
            propsLayer.setLabelsEnabled(True)

            iface.messageBar().pushMessage("Info", "Static objects layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Static objects layer added", level=Qgis.Info)

        self.propsLayer = QgsProject.instance().mapLayersByName("Static Objects")[0]

    def ToggleLabels(self):
        """
        Toggles labels for static objects on/off
        """
        if self.LabelsOn:
            self.propsLayer.setLabelsEnabled(False)
            self.LabelsOn = False
        else:
            self.propsLayer.setLabelsEnabled(True)
            self.LabelsOn = True

        self.propsLayer.triggerRepaint()

    def closeEvent(self, event):
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def InsertProps(self):
        """
        Spawn static objects on map with mouse click.
        """
        iface.setActiveLayer(self.propsLayer)

        # UI Information
        iface.messageBar().pushMessage("Info", "Using existing static objects layer", level=Qgis.Info)
        QgsMessageLog.logMessage("Using existing static objects layer", level=Qgis.Info)

        # Set map tool to point tool
        canvas = iface.mapCanvas()
        layer = iface.mapCanvas().currentLayer()

        # Static objects orientation
        if self.propsOrientation_useLane.isChecked():
            propsOrientation = None
        else:
            propsOrientation = float(self.propsOrientation.text())
            propsOrientation = math.radians(propsOrientation)

        propAttributes = {"Prop": self.propsSelection.currentText(),
                          "Prop Type": self.propsObjectType.currentText(),
                          "Orientation": propsOrientation,
                          "Mass": float(self.propsMass.text()),
                          "Physics": str(self.propsPhysics.isChecked())}
        tool = PointTool(canvas, layer, propAttributes)
        canvas.setMapTool(tool)

    def OverrideOrientation(self):
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

    def __init__(self, canvas, layer, propAttributes):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self.layer = layer
        self.dataInput = layer.dataProvider()
        self.canvas.setCursor(Qt.CrossCursor)
        self.propAttributes = propAttributes
        if self.propAttributes["Orientation"] is None:
            self.useLaneHeading = True
        else:
            self.useLaneHeading = False

    def canvasReleaseEvent(self, event):
        """
        Function when map canvas is clicked
        """
        # Get the click
        x = event.pos().x()
        y = event.pos().y()

        point = self.canvas.getCoordinateTransform().toMapCoordinates(x, y)

        # Converting to ENU points
        GeoPoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=0)
        EnuPoint = ad.map.point.toENU(GeoPoint)
        AddProp = AddPropAttribute()

        # Get lane heading and save attribute (when not manually specified)
        if self.useLaneHeading is True:
            self.propAttributes["Orientation"] = AddProp.getPropHeading(GeoPoint)

        # Add points only if user clicks within lane boundaries (Orientation is not None)
        if self.propAttributes["Orientation"] is not None:
            PolygonPoints = AddProp.spawnProps(EnuPoint, self.propAttributes["Orientation"])
            # Pass attributes to process
            PropAttr = AddProp.getPropAttributes(self.layer, self.propAttributes)

            # Set pedestrian attributes
            feature = QgsFeature()
            feature.setAttributes([PropAttr["id"],
                                   PropAttr["Prop"],
                                   PropAttr["Prop Type"],
                                   PropAttr["Orientation"],
                                   PropAttr["Mass"],
                                   float(EnuPoint.x),
                                   float(EnuPoint.y),
                                   PropAttr["Physics"]])
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


class AddPropAttribute():
    """
    Class for processing / acquiring static object attributes.
    """
    def getPropHeading(self, GeoPoint):
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

    def spawnProps(self, EnuPoint, angle):
        """
        Spawns static objects on the map and draws bounding boxes

        Args:
            EnuPoint: [AD Map ENUPoint] point of click event, as spawn center
            angle: [float] angle to rotate object (in radians)
        """
        if angle is not None:
            BotLeftX = float(EnuPoint.x) + (-0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            BotLeftY = float(EnuPoint.y) + (-0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            BotRightX = float(EnuPoint.x) + (-0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            BotRightY =  float(EnuPoint.y) + (-0.5 * math.sin(angle) - 0.5 * math.cos(angle))
            TopLeftX = float(EnuPoint.x) + (0.5 * math.cos(angle) - 0.5 * math.sin(angle))
            TopLeftY = float(EnuPoint.y) + (0.5 * math.sin(angle) + 0.5 * math.cos(angle))
            TopRightX = float(EnuPoint.x) + (0.5 * math.cos(angle) + 0.5 * math.sin(angle))
            TopRightY = float(EnuPoint.y) + (0.5 * math.sin(angle) - 0.5 * math.cos(angle))

            # Create ENU points for polygon
            BotLeft = ad.map.point.createENUPoint(x=BotLeftX, y=BotLeftY, z=0)
            BotRight = ad.map.point.createENUPoint(x=BotRightX, y=BotRightY, z=0)
            TopLeft = ad.map.point.createENUPoint(x=TopLeftX, y=TopLeftY, z=0)
            TopRight = ad.map.point.createENUPoint(x=TopRightX, y=TopRightY, z=0)

            # Convert back to Geo points
            BotLeft = ad.map.point.toGeo(BotLeft)
            BotRight = ad.map.point.toGeo(BotRight)
            TopLeft = ad.map.point.toGeo(TopLeft)
            TopRight = ad.map.point.toGeo(TopRight)

            # Create polygon
            PolygonPoints = [QgsPointXY(BotLeft.longitude, BotLeft.latitude),
                            QgsPointXY(BotRight.longitude, BotRight.latitude),
                            QgsPointXY(TopRight.longitude, TopRight.latitude),
                            QgsPointXY(TopLeft.longitude, TopLeft.latitude)]

            return PolygonPoints

    def getPropAttributes(self, layer, attributes):
        """
        Inputs static objects attributes into table
        """
        # Get largest static objects ID from attribute table
        # If no static objects has been added, start at 1
        if layer.featureCount() != 0:
            idx = layer.fields().indexFromName("id")
            largestPropID = layer.maximumValue(idx)
            propID = largestPropID + 1
        else:
            propID = 1

        prop = "static.prop." + attributes["Prop"]

        Orientation = float(attributes["Orientation"])

        propAttributes = {"id": propID,
                          "Prop": prop,
                          "Prop Type": attributes["Prop Type"],
                          "Mass": attributes["Mass"],
                          "Orientation": Orientation,
                          "Physics": attributes["Physics"]}

        return propAttributes
