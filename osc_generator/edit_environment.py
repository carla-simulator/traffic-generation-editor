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
    os.path.dirname(__file__), 'edit_environment_widget.ui'))


class EditEnvironmentDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to insert environment variables.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialization of EditEnvironmentDockWidget
        """
        super(EditEnvironmentDockWidget, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.AddEnvironment_Button.pressed.connect(self.AddEnvironment)

        self._layer = None
        self._data_provider = None

        self.layer_setup()
        self.set_layer()

    def layer_setup(self):
        """
        Sets up layer for environment
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Environment"):
            env_layer = QgsVectorLayer("None", "Environment", "memory")
            QgsProject.instance().addMapLayer(env_layer, False)
            osc_layer.addLayer(env_layer)
            # Setup layer attributes
            data_attributes = [QgsField("Datetime", QVariant.String),
                               QgsField("Datetime Animation", QVariant.Bool),
                               QgsField("Cloud State", QVariant.String),
                               QgsField("Fog Visual Range", QVariant.Double),
                               QgsField("Sun Intensity", QVariant.Double),
                               QgsField("Sun Azimuth", QVariant.Double),
                               QgsField("Sun Elevation", QVariant.Double),
                               QgsField("Precipitation Type", QVariant.String),
                               QgsField("Precipitation Intensity", QVariant.Double)]
            data_input = env_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            env_layer.updateFields()
            # UI Information
            message = "Environment layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

    def closeEvent(self, event):
        """QtDockWidget signals for closing"""
        self.closingPlugin.emit()
        event.accept()

    def set_layer(self):
        """
        Sets environment layer as active and clears all attributes
        """
        self._layer = QgsProject.instance().mapLayersByName("Environment")[0]
        iface.setActiveLayer(self._layer)

        self.clear_existing_attributes()

    def clear_existing_attributes(self):
        """
        Clears all existing attribues in layer
        """
        current_features = [feat.id() for feat in self._layer.getFeatures()]
        self._data_provider = self._layer.dataProvider()
        self._data_provider.deleteFeatures(current_features)

    def AddEnvironment(self):
        """
        Inserts environment variables into dimensionless QGIS layer.
        """
        self.clear_existing_attributes()

        datetime = self.TimeofDay.dateTime().toString("yyyy-MM-ddThh:mm:ss")
        datatime_animation = self.TimeAnimation.isChecked()
        cloud = self.CloudState.currentText()
        fog_range = self.Fog_VisualRange.text()
        sun_intensity = self.Sun_Intensity.text()
        sun_azimuth = self.Sun_Azimuth.text()
        sun_elevation = self.Sun_Elevation.text()
        percip_type = self.Precip_Type.currentText()
        percip_intensity = self.Precip_Intensity.text()

        feature = QgsFeature()
        feature.setAttributes([datetime, datatime_animation,
                               cloud, fog_range,
                               sun_intensity, sun_azimuth, sun_elevation,
                               percip_type, percip_intensity])
        self._data_provider.addFeature(feature)
