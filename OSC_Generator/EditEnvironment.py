# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Edit Environment
"""
import os
# pylint: disable=no-name-in-module, no-member
from qgis.core import (Qgis, QgsFeature, QgsField, QgsMessageLog,
                       QgsProject, QgsVectorLayer)
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import QVariant, pyqtSignal
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'EditEnvironmentWidget.ui'))


class EditEnvironmentDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    OpenSCENARIO Generator - QGIS Plugin - Edit Environment

    Creates a dockwidget in QGIS for changing environment variables.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """Initialization of EditEnvironmentDockWidget"""
        super(EditEnvironmentDockWidget, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.AddEnvironment_Button.pressed.connect(self.AddEnvironment)

        self.layer = None
        self.dataProvider = None

        self.CreateLayer()
        self.SetLayer()

    def CreateLayer(self):
        """Create environment QGIS layer to save all attributes"""
        rootLayer = QgsProject.instance().layerTreeRoot()
        OSCLayer = rootLayer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Environment"):
            environmentLayer = QgsVectorLayer("None", "Environment", "memory")
            QgsProject.instance().addMapLayer(environmentLayer, False)
            OSCLayer.addLayer(environmentLayer)
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
            dataInput = environmentLayer.dataProvider()
            dataInput.addAttributes(dataAttributes)
            environmentLayer.updateFields()
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
