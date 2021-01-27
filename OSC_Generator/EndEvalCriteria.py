# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Add End Evaluation KPIs
"""
import os.path

# pylint: disable=no-name-in-module, no-member
from qgis.core import Qgis, QgsFeature, QgsField, QgsMessageLog, QgsProject, QgsVectorLayer
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QVariant
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'EndEvalCriteria.ui'))

class EndEvalCriteriaDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Class for post-scenario evaluation criteria
    """
    def __init__(self, parent=None):
        """Initialization of class and Qt UI element connect signals"""
        super(EndEvalCriteriaDialog, self).__init__(parent)
        self.setupUi(self)
        self.useDefault.stateChanged.connect(self.DefaultTriggers)
        self.dataProvider = None

    def DefaultTriggers(self):
        """Toggles default triggers"""
        if self.useDefault.isChecked():
            self.collisionGroup.setDisabled(True)
            self.drivenDistanceGroup.setDisabled(True)
            self.keepLaneGroup.setDisabled(True)
            self.onSidewalkGroup.setDisabled(True)
            self.runningRedGroup.setDisabled(True)
            self.runningStopGroup.setDisabled(True)
            self.wrongLaneGroup.setDisabled(True)

            self.collisionGroup.setChecked(True)
            self.drivenDistanceGroup.setChecked(True)
            self.keepLaneGroup.setChecked(True)
            self.onSidewalkGroup.setChecked(True)
            self.runningRedGroup.setChecked(True)
            self.runningStopGroup.setChecked(True)
            self.wrongLaneGroup.setChecked(True)
        else:
            self.collisionGroup.setEnabled(True)
            self.drivenDistanceGroup.setEnabled(True)
            self.keepLaneGroup.setEnabled(True)
            self.onSidewalkGroup.setEnabled(True)
            self.runningRedGroup.setEnabled(True)
            self.runningStopGroup.setEnabled(True)
            self.wrongLaneGroup.setEnabled(True)

    def SaveStopTriggers(self):
        """Executes ingestion of dialog form data into QGIS layer"""
        self.CreateLayer()
        layer = QgsProject.instance().mapLayersByName("End Evaluation KPIs")[0]
        self.dataProvider = layer.dataProvider()
        currFeat = [feat.id() for feat in layer.getFeatures()]
        self.dataProvider.deleteFeatures(currFeat)
        iface.setActiveLayer(layer)

        self.GetCollision()
        self.GetDrivenDistance()
        self.GetKeepLane()
        self.GetOnSidewalk()
        self.GetRunningRed()
        self.GetRunningStop()
        self.GetWrongLane()

    def GetCollision(self):
        """Sets attribute for collision check"""
        if self.collisionGroup.isChecked():
            condName = self.collision_CondName.text()
            delay = self.collision_Delay.text()
            condEdge = self.collision_CondEdge.currentText()
            paramRef = self.collision_ParamRef.text()
            value = self.collision_Value.text()
            rule = self.collision_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetDrivenDistance(self):
        """Sets attribute for driven distance"""
        if self.drivenDistanceGroup.isChecked():
            condName = self.drivenDistance_CondName.text()
            delay = self.drivenDistance_Delay.text()
            condEdge = self.drivenDistance_CondEdge.currentText()
            paramRef = self.drivenDistance_ParamRef.text()
            value = self.drivenDistance_Value.text()
            rule = self.drivenDistance_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetKeepLane(self):
        """Sets attribute for keeping lane"""
        if self.keepLaneGroup.isChecked():
            condName = self.keepLane_CondName.text()
            delay = self.keepLane_Delay.text()
            condEdge = self.keepLane_CondEdge.currentText()
            paramRef = self.keepLane_ParamRef.text()
            value = self.keepLane_Value.text()
            rule = self.keepLane_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetOnSidewalk(self):
        """Sets attribute for sidewalk check"""
        if self.onSidewalkGroup.isChecked():
            condName = self.onSidewalk_CondName.text()
            delay = self.onSidewalk_Delay.text()
            condEdge = self.onSidewalk_CondEdge.currentText()
            paramRef = self.onSidewalk_ParamRef.text()
            value = self.onSidewalk_Value.text()
            rule = self.onSidewalk_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetRunningRed(self):
        """Sets attribute for running red light check"""
        if self.runningRedGroup.isChecked():
            condName = self.runningRed_CondName.text()
            delay = self.runningRed_Delay.text()
            condEdge = self.runningRed_CondEdge.currentText()
            paramRef = self.runningRed_ParamRef.text()
            value = self.runningRed_Value.text()
            rule = self.runningRed_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetRunningStop(self):
        """Sets attribute for running stop signs check"""
        if self.runningStopGroup.isChecked():
            condName = self.runningStop_CondName.text()
            delay = self.runningStop_Delay.text()
            condEdge = self.runningStop_CondEdge.currentText()
            paramRef = self.runningStop_ParamRef.text()
            value = self.runningStop_Value.text()
            rule = self.runningStop_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def GetWrongLane(self):
        """Sets attribute for wrong lane check"""
        if self.wrongLaneGroup.isChecked():
            condName = self.wrongLane_CondName.text()
            delay = self.wrongLane_Delay.text()
            condEdge = self.wrongLane_CondEdge.currentText()
            paramRef = self.wrongLane_ParamRef.text()
            value = self.wrongLane_Value.text()
            rule = self.wrongLane_Rule.currentText()
            self.WriteAttributes(condName, delay, condEdge, paramRef, value, rule)

    def CreateLayer(self):
        """Create no geometry layer in QGIS to save End Evaluation KPIs."""
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("End Evaluation KPIs"):
            stopTriggersLayer = QgsVectorLayer("None", "End Evaluation KPIs", "memory")
            QgsProject.instance().addMapLayer(stopTriggersLayer, False)
            OSCLayer.addLayer(stopTriggersLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("Condition Name", QVariant.String),
                              QgsField("Delay", QVariant.Double),
                              QgsField("Condition Edge", QVariant.String),
                              QgsField("Parameter Ref", QVariant.String),
                              QgsField("Value", QVariant.Double),
                              QgsField("Rule", QVariant.String)]
            self.dataProvider = stopTriggersLayer.dataProvider()
            self.dataProvider.addAttributes(dataAttributes)
            stopTriggersLayer.updateFields()
            # UI Information
            iface.messageBar().pushMessage("Info", "End evaluation KPIs layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("End evaluation KPIs layer added", level=Qgis.Info)

    def WriteAttributes(self, condName, delay, condEdge, paramRef, value, rule):
        """
        Writes stop trigger attributes into QGIS attributes table.

        Args:
            condName: [str] Condition Name
            delay: [str] Delay for condition
            condEdge: [str] Condition Edge (rising, falling, risingOrFalling, None)
            paramRef: [str] Parameter Reference (user-defined)
            value: [str] Value for condition
            rule: [str] Comparator for value (lessThan, equalTo, greaterThan)
        """
        feature = QgsFeature()
        feature.setAttributes([condName, float(delay), condEdge, paramRef, float(value), rule])
        self.dataProvider.addFeature(feature)
