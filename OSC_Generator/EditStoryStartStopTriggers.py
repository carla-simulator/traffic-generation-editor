# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

import os

from PyQt5.QtWidgets import QMessageBox
from qgis.core import (Qgis, QgsFeature, QgsField, QgsMessageLog,
                       QgsProject, QgsVectorLayer)
from qgis.PyQt import QtGui, QtWidgets, uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'EditStoryStartStopTriggers.ui'))


class EditStoryStartStopTriggersDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    OpenSCENARIO Generator - QGIS Plugin - Edit Story Start and Stop Triggers

    Creates a dockwidget in QGIS for changing story start and stop triggers.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Initialization of EditEnvironmentDockWidget"""
        super(EditStoryStartStopTriggersDockWidget, self).__init__(parent)
        self.setupUi(self)

        self.layer = None
        self.dataProvider = None

        self.CreateLayer()
        self.SetLayer()

    def CreateLayer(self):
        """Create environment QGIS layer to save all attributes"""
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Story Start Stop Triggers"):
            storyTriggersLayer = QgsVectorLayer("None", "Story Start Stop Triggers", "memory")
            QgsProject.instance().addMapLayer(storyTriggersLayer, False)
            OSCLayer.addLayer(storyTriggersLayer)
            # Setup layer attributes
            dataAttributes = [QgsField("Datetime", QVariant.String),
                              QgsField("Datetime Animation", QVariant.Bool),
                              QgsField("Cloud State", QVariant.String),
                              QgsField("Fog Visual Range", QVariant.Double),
                              QgsField("Sun Intensity", QVariant.Double),
                              QgsField("Sun Azimuth", QVariant.Double),
                              QgsField("Sun Elevation", QVariant.Double),
                              QgsField("Precipitation Type", QVariant.String),
                              QgsField("Precipitation Intensity", QVariant.Double)]
            dataInput = storyTriggersLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            storyTriggersLayer.updateFields()
            # UI Information
            iface.messageBar().pushMessage("Info", "Environment layer added", level=Qgis.Info)
            QgsMessageLog.logMessage("Environment layer added", level=Qgis.Info)
        
    def closeEvent(self, event):
        """QtDockWidget signals for closing"""
        self.closingPlugin.emit()
        event.accept()

    def SetLayer(self):
        """Sets environment layer as active and clears all attributes"""
        self.layer = QgsProject.instance().mapLayersByName("Environment")[0]
        iface.setActiveLayer(self.layer)

        self.ClearExistingAttributes()

    def ClearExistingAttributes(self):
        """Clears all existing attribues in layer"""
        currFeat = [feat.id() for feat in self.layer.getFeatures()]
        self.dataProvider = self.layer.dataProvider()
        self.dataProvider.deleteFeatures(currFeat)

    def AddEnvironment(self):
        """Inserts environment variables into dimensionless QGIS layer."""
        self.ClearExistingAttributes()

        datetime = self.TimeofDay.dateTime().toString("yyyy-MM-ddThh:mm:ss")
        datetimeAnim = self.TimeAnimation.isChecked()
        cloud = self.CloudState.currentText()
        fogRange = self.Fog_VisualRange.text()
        sunIntensity = self.Sun_Intensity.text()
        sunAzimuth = self.Sun_Azimuth.text()
        sunElevation = self.Sun_Elevation.text()
        percipType = self.Precip_Type.currentText()
        percipIntensity = self.Precip_Intensity.text()

        feature = QgsFeature()
        feature.setAttributes([datetime, datetimeAnim,
                               cloud, fogRange,
                               sunIntensity, sunAzimuth, sunElevation,
                               percipType, percipIntensity])
        self.dataProvider.addFeature(feature)
