# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add Maneuvers
"""
import os
import math
# pylint: disable=no-name-in-module, no-member
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, pyqtSignal, QVariant
from qgis.gui import QgsMapTool
from qgis.utils import iface
from qgis.core import (QgsProject, QgsVectorLayer, QgsMessageLog, Qgis, QgsField,
    QgsFeature, QgsGeometry, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling,
    QgsTextFormat, QgsTextBackgroundSettings)
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import QInputDialog

# AD Map plugin
import ad_map_access as ad

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'AddManeuvers.ui'))


class AddManeuversDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to add scenario maneuvers.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Initialization of AddManeuversDockWidget"""
        super(AddManeuversDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.refreshEntity_Button.pressed.connect(self.RefreshEntity)
        self.addManeuver_Button.pressed.connect(self.AddManeuvers)
        self.entityManeuverType.currentTextChanged.connect(self.ChangeManeuver)
        self.waypointOrientation_useLane.stateChanged.connect(self.OverrideOrientation)
        self.ConditionType.currentTextChanged.connect(self.UpdateStartTriggerCondition)
        self.ValueCond.currentTextChanged.connect(self.UpdateValueConditionParameter)
        self.EntityCond.currentTextChanged.connect(self.UpdateEntityConditionParameter)
        self.entitySelection.currentTextChanged.connect(self.UpdateRefEntity)

        self.toggleTrafficLightLabels_Button.pressed.connect(self.ToggleTrafficLightLabels)
        self.refreshTrafficLights_Button.pressed.connect(self.UpdateTrafficLights)
        self.entityChoosePosition_Button.pressed.connect(self.GetWorldPosition)

        self._waypointLayer = None
        self._maneuverLayer = None
        self.ManID = None
        self.trafficLabelsOn = False
        self.trafficLabelsSetup = False
        self.trafficLightsLayer = None
        self.LayerSetup()
        self.RefreshEntity()
        self.UpdateTrafficLights()

    def LayerSetup(self):
        """
        Sets up layers for maneuvers
        """
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")

        # Waypoint maneuvers
        if not QgsProject.instance().mapLayersByName("Waypoint Maneuvers"):
            waypointLayer = QgsVectorLayer("Point", "Waypoint Maneuvers", "memory")
            QgsProject.instance().addMapLayer(waypointLayer, False)
            OSCLayer.addLayer(waypointLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("Maneuver ID", QVariant.Int),
                              QgsField("Entity", QVariant.String),
                              QgsField("Waypoint No", QVariant.Int),
                              QgsField("Orientation", QVariant.Double),
                              QgsField("Pos X", QVariant.Double),
                              QgsField("Pos Y", QVariant.Double),
                              QgsField("Route Strategy", QVariant.String)]
            dataInput = waypointLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            waypointLayer.updateFields()

            iface.messageBar().pushMessage("Info", "Waypoint maneuvers layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Waypoint maneuvers layer added", level=Qgis.Info)
        else:
            iface.messageBar().pushMessage("Info", "Using existing waypoint maneuver layer", level=Qgis.Info)
            QgsMessageLog.logMessage("Using existing waypoint maneuver layer", level=Qgis.Info)

        self._waypointLayer = QgsProject.instance().mapLayersByName("Waypoint Maneuvers")[0]
        labelSettings = QgsPalLayerSettings()
        labelSettings.isExpression = True
        labelSettings.fieldName = "concat('ManID: ', \"Maneuver ID\", ' ', \"Entity\", ' - ', \"Waypoint No\")"
        self._waypointLayer.setLabeling(QgsVectorLayerSimpleLabeling(labelSettings))
        self._waypointLayer.setLabelsEnabled(True)

        # Maneuvers
        if not QgsProject.instance().mapLayersByName("Maneuvers"):
            maneuverLayer = QgsVectorLayer("None", "Maneuvers", "memory")
            QgsProject.instance().addMapLayer(maneuverLayer, False)
            OSCLayer.addLayer(maneuverLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("id", QVariant.Int),
                              QgsField("Maneuver Type", QVariant.String),
                              QgsField("Entity", QVariant.String),
                              QgsField("Entity: Maneuver Type", QVariant.String),
                              QgsField("Start Trigger", QVariant.String),
                              QgsField("Entity: Condition", QVariant.String),
                              QgsField("Entity: Ref Entity", QVariant.String),
                              QgsField("Entity: Duration", QVariant.Double),
                              QgsField("Entity: Value", QVariant.Double),
                              QgsField("Entity: Rule", QVariant.String),
                              QgsField("Entity: RelDistType", QVariant.String),
                              QgsField("Entity: Freespace", QVariant.Bool),
                              QgsField("Entity: Along Route", QVariant.Bool),
                              QgsField("Value: Condition", QVariant.String),
                              QgsField("Value: Param Ref", QVariant.String),
                              QgsField("Value: Name", QVariant.String),
                              QgsField("Value: DateTime", QVariant.String),
                              QgsField("Value: Value", QVariant.Double),
                              QgsField("Value: Rule", QVariant.String),
                              QgsField("Value: State", QVariant.String),
                              QgsField("Value: Sboard Type", QVariant.String),
                              QgsField("Value: Sboard Element", QVariant.String),
                              QgsField("Value: Sboard State", QVariant.String),
                              QgsField("Value: TController Ref", QVariant.String),
                              QgsField("Value: TController Phase", QVariant.String),
                              QgsField("Global: Act Type", QVariant.String),
                              QgsField("Infra: Traffic Light ID", QVariant.Int),
                              QgsField("Infra: Traffic Light State", QVariant.String),
                              QgsField("WorldPos: Tolerance", QVariant.Double),
                              QgsField("WorldPos: X", QVariant.Double),
                              QgsField("WorldPos: Y", QVariant.Double),
                              QgsField("WorldPos: Heading", QVariant.Double)]
            dataInput = maneuverLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            maneuverLayer.updateFields()

            iface.messageBar().pushMessage("Info", "Maneuvers layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Maneuvers layer added", level=Qgis.Info)
        else:
            iface.messageBar().pushMessage("Info", "Using existing maneuvers layer", level=Qgis.Info)
            QgsMessageLog.logMessage("Using existing maneuvers layer", level=Qgis.Info)

        self._maneuverLayer = QgsProject.instance().mapLayersByName("Maneuvers")[0]

    def RefreshEntity(self):
        """
        Gets list of entities spawned on map and populates drop down
        """
        self.entitySelection.clear()
        self.refEntitySelection.clear()
        entities = []
        if QgsProject.instance().mapLayersByName("Vehicles - Ego"):
            layer = QgsProject.instance().mapLayersByName("Vehicles - Ego")[0]
            for feature in layer.getFeatures():
                vehID = "Ego_" + str(feature["id"])
                entities.append(vehID)

        if QgsProject.instance().mapLayersByName("Vehicles"):
            layer = QgsProject.instance().mapLayersByName("Vehicles")[0]
            for feature in layer.getFeatures():
                vehID = "Vehicle_" + str(feature["id"])
                entities.append(vehID)

        if QgsProject.instance().mapLayersByName("Pedestrians"):
            layer = QgsProject.instance().mapLayersByName("Pedestrians")[0]
            for feature in layer.getFeatures():
                pedID = "Pedestrian_" + str(feature["id"])
                entities.append(pedID)

        self.entitySelection.addItems(entities)
        self.refEntitySelection.addItems(entities)

    def UpdateRefEntity(self):
        """
        Updates start trigger reference entity to match selected entity by default.
        """
        selectedEntity = self.entitySelection.currentText()
        index = self.refEntitySelection.findText(selectedEntity)
        self.refEntitySelection.setCurrentIndex(index)

    def OverrideOrientation(self):
        """
        Toggles orientation field on and off
        """
        if self.waypointOrientation_useLane.isChecked():
            self.waypointOrientation.setDisabled(True)
        else:
            self.waypointOrientation.setEnabled(True)

    def ToggleTrafficLightLabels(self):
        """
        Toggles labels for traffic light IDs
        """
        if self.trafficLabelsSetup is False:
            self.trafficLightsLayer = QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT")[0]
            labelSettings = QgsPalLayerSettings()
            labelSettings.isExpression = True
            labelSettings.fieldName = "\"Id\""
            textFormat = QgsTextFormat()
            textBackground = QgsTextBackgroundSettings()
            textBackground.setFillColor(QColor('white'))
            textBackground.setEnabled(True)
            textBackground.setType(QgsTextBackgroundSettings.ShapeCircle)
            textFormat.setBackground(textBackground)
            labelSettings.setFormat(textFormat)
            self.trafficLightsLayer.setLabeling(QgsVectorLayerSimpleLabeling(labelSettings))
            self.trafficLightsLayer.setLabelsEnabled(True)

        if self.trafficLabelsOn:
            self.trafficLightsLayer.setLabelsEnabled(False)
            self.trafficLabelsOn = False
        else:
            self.trafficLightsLayer.setLabelsEnabled(True)
            self.trafficLabelsOn = True

        self.trafficLightsLayer.triggerRepaint()

    def UpdateTrafficLights(self):
        """
        Gets list of traffic light IDs spawned on map and populates drop down
        """
        self.trafficLightID.clear()
        trafficLightIDs = []
        if QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT"):
            layer = QgsProject.instance().mapLayersByName("TRAFFIC_LIGHT")[0]
            for feature in layer.getFeatures():
                tLightID = str(feature["Id"])
                trafficLightIDs.append(tLightID)

        self.trafficLightID.addItems(trafficLightIDs)

    def closeEvent(self, event):
        """
        Dockwidget closing event
        """
        self.closingPlugin.emit()
        event.accept()

    def AddManeuvers(self):
        """
        Spawn waypoints on the map.
        """
        self.GetManeuverID()

        canvas = iface.mapCanvas()

        if self.maneuverType.currentText() == "Entity Maneuvers":
            entity = self.entitySelection.currentText()
            if self.waypointOrientation_useLane.isChecked():
                entityOrientation = None
            else:
                entityOrientation = math.radians(self.waypointOrientation.text())

            entityAttributes = {"Maneuver ID": self.ManID,
                                "Entity":entity,
                                "Orientation":entityOrientation,
                                "Route Strat":self.waypointStrategy.currentText()}
            tool = PointTool(canvas, self._waypointLayer, entityAttributes, layerType="Waypoints")
            canvas.setMapTool(tool)
        elif self.maneuverType.currentText() == "Global Actions":
            pass

        self.SaveManeuverAttributes()

    def ChangeManeuver(self):
        """
        Enables / disables group boxes depending on type of maneuver selected.
        """
        if self.entityManeuverType.currentText() == "Waypoint":
            self.waypointGroup.setEnabled(True)
            self.actorMoveGroup.setDisabled(True)
        elif self.entityManeuverType.currentText() == "Move on Condition":
            self.waypointGroup.setDisabled(True)
            self.actorMoveGroup.setEnabled(True)

    def GetWorldPosition(self):
        """
        Gets world position from map
        """
        canvas = iface.mapCanvas()
        entityAttributes = {"Orientation": None}
        tool = PointTool(canvas, self._maneuverLayer, entityAttributes, layerType="Position", parent=self)
        canvas.setMapTool(tool)

    def UpdateValueConditionParameter(self):
        """
        Enables / disables parameters for Value Conditions based on condition selected.
        """
        # Parameter Reference
        if self.ValueCond.currentText() == "ParameterCondition":
            self.Value_ParamRef.setEnabled(True)
        else:
            self.Value_ParamRef.setDisabled(True)

        # Name
        if (self.ValueCond.currentText() == "UserDefinedValueCondition"
            or self.ValueCond.currentText() == "TrafficSignalCondition"):
            self.Value_Name.setEnabled(True)
        else:
            self.Value_Name.setDisabled(True)

        # DateTime
        if self.ValueCond.currentText() == "TimeOfDayCondition":
            self.Value_DateTime.setEnabled(True)
        else:
            self.Value_DateTime.setDisabled(True)

        # Value
        if (self.ValueCond.currentText() == "ParameterCondition"
            or self.ValueCond.currentText() == "SimulationTimeCondition"
            or self.ValueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Value.setEnabled(True)
        else:
            self.Value_Value.setDisabled(True)

        # Rule
        if (self.ValueCond.currentText() == "ParameterCondition"
            or self.ValueCond.currentText() == "TimeOfDayCondition"
            or self.ValueCond.currentText() == "SimulationTimeCondition"
            or self.ValueCond.currentText() == "UserDefinedValueCondition"):
            self.Value_Rule.setEnabled(True)
        else:
            self.Value_Rule.setDisabled(True)

        # State
        if self.ValueCond.currentText() == "TrafficSignalCondition":
            self.Value_State.setEnabled(True)
        else:
            self.Value_State.setDisabled(True)

        # Storyboard elements
        if self.ValueCond.currentText() == "StoryboardElementStateCondition":
            self.StoryboardGroup.setEnabled(True)
        else:
            self.StoryboardGroup.setDisabled(True)

        # Traffic signal controller
        if self.ValueCond.currentText() == "TrafficSignalControllerCondition":
            self.TrafficSignalGroup.setEnabled(True)
        else:
            self.TrafficSignalGroup.setDisabled(True)

    def UpdateEntityConditionParameter(self):
        """
        Enables / disables parameters for Entity Conditions based on condition selected.
        """
        # Entity Ref
        if (self.EntityCond.currentText() == "TimeHeadwayCondition"
            or self.EntityCond.currentText() == "RelativeSpeedCondition"
            or self.EntityCond.currentText() == "RelativeDistanceCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"):
            self.refEntitySelection.setEnabled(True)
        else:
            self.refEntitySelection.setDisabled(True)

        # Duration
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "StandStillCondition"):
            self.Entity_Duration.setEnabled(True)
        else:
            self.Entity_Duration.setDisabled(True)

        # Value (setting disabled)
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "CollisionCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "TimeToCollisionCondition"
            or self.EntityCond.currentText() == "StandStillCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"
            or self.EntityCond.currentText() == "DistanceCondition"):
            self.Entity_Value.setDisabled(True)
        else:
            self.Entity_Value.setEnabled(True)

        # Rule (setting disabled)
        if (self.EntityCond.currentText() == "EndOfRoadCondition"
            or self.EntityCond.currentText() == "OffroadCondition"
            or self.EntityCond.currentText() == "StandStillCondition"
            or self.EntityCond.currentText() == "TraveledDistanceCondition"
            or self.EntityCond.currentText() == "ReachPositionCondition"):
            self.Entity_Rule.setDisabled(True)
        else:
            self.Entity_Rule.setEnabled(True)

        # Relative Distance
        if self.EntityCond.currentText() == "RelativeDistanceCondition":
            self.Entity_RelDistType.setEnabled(True)
        else:
            self.Entity_RelDistType.setDisabled(True)

        # Freespace
        if (self.EntityCond.currentText() == "TimeHeadwayCondition"
            or self.EntityCond.currentText() == "RelativeDistanceCondition"):
            self.Entity_Freespace.setEnabled(True)
        else:
            self.Entity_Freespace.setDisabled(True)

        # Along Route
        if self.EntityCond.currentText() == "TimeHeadwayCondition":
            self.Entity_AlongRoute.setEnabled(True)
        else:
            self.Entity_AlongRoute.setDisabled(True)

        # Position
        if self.EntityCond.currentText() == "ReachPositionCondition":
            self.Entity_PositionGroup.setEnabled(True)
        else:
            self.Entity_PositionGroup.setDisabled(True)

    def UpdateStartTriggerCondition(self):
        """
        Enables / disables groups based on trigger condition selected.
        """
        if self.ConditionType.currentText() == "by Entity":
            self.EntityConditionGroup.setEnabled(True)
            self.ValueConditionGroup.setDisabled(True)
        else:
            self.EntityConditionGroup.setDisabled(True)
            self.ValueConditionGroup.setEnabled(True)

    def GetManeuverID(self):
        """
        Generates maneuver ID
        """
        if self._maneuverLayer.featureCount() != 0:
            idx = self._maneuverLayer.fields().indexFromName("id")
            largestManID = self._maneuverLayer.maximumValue(idx)
            self.ManID = largestManID + 1
        else:
            self.ManID = 1

    def SaveManeuverAttributes(self):
        """
        Gets maneuver attributes and saves into QGIS attributes table.
        """
        feature = QgsFeature()
        feature.setAttributes([self.ManID,
                               self.maneuverType.currentText(),
                               self.entitySelection.currentText(),
                               self.entityManeuverType.currentText(),
                               self.ConditionType.currentText(),
                               self.EntityCond.currentText(),
                               self.refEntitySelection.currentText(),
                               float(self.Entity_Duration.text()),
                               float(self.Entity_Value.text()),
                               self.Entity_Rule.currentText(),
                               self.Entity_RelDistType.currentText(),
                               self.Entity_Freespace.isChecked(),
                               self.Entity_AlongRoute.isChecked(),
                               self.ValueCond.currentText(),
                               self.Value_ParamRef.text(),
                               self.Value_Name.text(),
                               self.Value_DateTime.dateTime().toString("yyyy-MM-ddThh:mm:ss"),
                               float(self.Value_Value.text()),
                               self.Value_Rule.currentText(),
                               self.Value_State.text(),
                               self.Storyboard_Type.currentText(),
                               self.Storyboard_Element.text(),
                               self.Storyboard_State.currentText(),
                               self.TrafficSignal_ControllerRef.text(),
                               self.TrafficSignal_Phase.text(),
                               self.globalActType.currentText(),
                               int(self.trafficLightID.currentText()),
                               self.trafficLightState.currentText(),
                               float(self.entityTolerance.text()),
                               float(self.entityPositionX.text()),
                               float(self.entityPositionY.text()),
                               float(self.entityHeading.text())])
        self._maneuverLayer.dataProvider().addFeature(feature)

#pylint: disable=missing-function-docstring
class PointTool(QgsMapTool):
    """Enables Point Addition"""

    def __init__(self, canvas, layer, entityAttributes, layerType, parent=None):
        QgsMapTool.__init__(self, canvas)
        self.canvas = canvas
        self._type = layerType
        self.layer = layer
        self.dataInput = layer.dataProvider()
        self.canvas.setCursor(Qt.CrossCursor)
        self.entityAttributes = entityAttributes
        self._parent = parent
        if self.entityAttributes["Orientation"] is None:
            self.useLaneHeading = True
        else:
            self.useLaneHeading = False
        iface.setActiveLayer(self.layer)

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
        AddEntityAttr = AddManeuverAttributes()

        # Get lane heading and save attribute (when not manually specified)
        if self.useLaneHeading is True:
            self.entityAttributes["Orientation"] = AddEntityAttr.getEntityHeading(GeoPoint)

        # If point type is waypoint, spawn points, else pass click parameters
        if self._type == "Waypoints":
            # Add points only if user clicks within lane boundaries (Orientation is not None)
            if self.entityAttributes["Orientation"] is not None:
                processedAttrs = AddEntityAttr.getEntityWaypointAttributes(self.layer, self.entityAttributes)

                # Set attributes
                feature = QgsFeature()
                feature.setAttributes([processedAttrs["Maneuver ID"],
                                    processedAttrs["Entity"],
                                    int(processedAttrs["Waypoint No"]),
                                    float(processedAttrs["Orientation"]),
                                    float(EnuPoint.x),
                                    float(EnuPoint.y),
                                    processedAttrs["Route Strat"]])
                feature.setGeometry(QgsGeometry.fromPointXY(point))
                self.dataInput.addFeature(feature)
        elif self._type == "Position":
            heading = AddEntityAttr.getEntityHeading(GeoPoint)
            self._parent.entityPositionX.setText(str(EnuPoint.x))
            self._parent.entityPositionY.setText(str(EnuPoint.y))
            self._parent.entityHeading.setText(str(heading))
            self.canvas.unsetMapTool(self)

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

class AddManeuverAttributes():
    """
    Handles processing of maneuver attributes.
    """
    def getEntityHeading(self, GeoPoint):
        """
        Acquires entity heading based on spawn position in map.
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

    def getEntityWaypointAttributes(self, layer, attributes):
        """
        Processes waypoint attributes to be inserted into table
        """
        query = f'"Entity" = \'{attributes["Entity"]}\''
        entityFeatures = layer.getFeatures(query)
        waypointList = []
        for feat in entityFeatures:
            waypointList.append(feat["Waypoint No"])

        if waypointList:
            largestVal = max(waypointList)
            waypointNo = largestVal + 1
        else:
            waypointNo = 1

        entityAttributes = {"Maneuver ID": attributes["Maneuver ID"],
                            "Entity": attributes["Entity"],
                            "Waypoint No": waypointNo,
                            "Orientation": attributes["Orientation"],
                            "Route Strat": attributes["Route Strat"]}

        return entityAttributes
