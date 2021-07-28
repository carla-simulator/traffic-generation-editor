# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Parameter Declarations
"""
import os
# pylint: disable=no-name-in-module, no-member
from qgis.core import QgsFeature, QgsProject, QgsFeatureRequest
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox
from .helper_functions import layer_setup_parameters, display_message

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'parameter_declarations.ui'))


class ParameterDeclarationsDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    """
    Dockwidget to add parameters declarations.
    """
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        """
        Initialization of ParameterDeclarationsDockWidget
        """
        super(ParameterDeclarationsDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.add_param_button.pressed.connect(self.add_parameters)

        self._canvas = iface.mapCanvas()

        layer_setup_parameters()
        self._param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
        self._param_layer_data_input = self._param_layer.dataProvider()

    def closeEvent(self, event):    # pylint: disable=invalid-name
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def add_parameters(self):
        """
        Adds parameters into layer
        """
        check_result = self.check_existing_parameters()

        param_name = self.param_name.text()
        param_type = self.param_type.currentText()
        param_value = self.param_value.text()

        if check_result is False:
            self.insert_parameters(param_name, param_type, param_value)
        else:
            message = f"Parameter '{param_name}' exists!"
            display_message(message, level="Warning")

            query = f'"Parameter Name" = \'{param_name}\''
            request = QgsFeatureRequest().setFilterExpression(query)
            for feature in self._param_layer.getFeatures(request):
                exist_param_type = feature["Type"]
                exist_param_value = feature["Value"]

            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Question)
            text_display = (f"Parameter '{param_name}' already exists!\n"
                            "Existing parameters:\n"
                            f"Type: {exist_param_type}\nValue: {exist_param_value}\n\n"
                            "New parameters:\n"
                            f"Type: {param_type}\nValue: {param_value}\n\n"
                            "Replace existing parameter with new?")
            msg_box.setText(text_display)
            msg_box.setWindowTitle("Parameter exists")
            msg_box.setStandardButtons(QMessageBox.No | QMessageBox.Yes)
            return_value = msg_box.exec()

            if return_value == QMessageBox.Yes:
                self.delete_existing_parameter(param_name)
                self.insert_parameters(param_name, param_type, param_value)

        self._canvas.refreshAllLayers()

    def check_existing_parameters(self):
        """
        Checks attribute tables for existing parameters with the same name

        Returns:
            False: if no existing parameters are found
            True: if there is an existing parameter
        """
        query = f'"Parameter Name" = \'{self.param_name.text()}\''
        feature_request = QgsFeatureRequest().setFilterExpression(query)
        features = self._param_layer.getFeatures(feature_request)
        count = len(list(features))

        if count == 0:
            return False
        else:
            return True

    def insert_parameters(self, param_name, param_type, param_value):
        """
        Inserts parameters into attributes table

        Args:
            param_name (string): Parameter name
            param_type (string): Parameter type
            param_value (string): Parameter value
        """
        feature = QgsFeature()
        feature.setAttributes([param_name,
                               param_type,
                               param_value])
        self._param_layer_data_input.addFeature(feature)

        message = f"Parameter '{param_name}' added!"
        display_message(message, level="Info")

    def delete_existing_parameter(self, param_name):
        """
        Delete existing parameter from attributes table

        Args:
            param_name (string): Parameter name to be deleted
        """
        query = f'"Parameter Name" = \'{param_name}\''
        feature_request = QgsFeatureRequest().setFilterExpression(query)
        features_to_delete = self._param_layer.getFeatures(feature_request)

        feat_ids = []
        for feature in features_to_delete:
            feat_ids.append(feature.id())

        self._param_layer_data_input.deleteFeatures(feat_ids)
