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
from qgis.core import QgsFeature, QgsProject
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from .helper_functions import layer_setup_environment, display_message

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
        self.AddEnvironment_Button.pressed.connect(self.add_environment)

        self._layer = None
        self._data_provider = None

        layer_setup_environment()
        self.set_layer()

    def closeEvent(self, event):    # pylint: disable=invalid-name
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

    def add_environment(self):
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

        message = "Environment variables added!"
        display_message(message, level="Info")
