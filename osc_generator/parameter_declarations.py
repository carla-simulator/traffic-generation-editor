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
from qgis.core import (Qgis, QgsFeature, QgsField, QgsMessageLog, QgsProject,
                       QgsVectorLayer, QgsExpression, QgsFeatureRequest)
from qgis.gui import QgsMapTool
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import Qt, QVariant, pyqtSignal
from qgis.utils import iface
from PyQt5.QtWidgets import QMessageBox

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

        self._param_layer = None
        self._param_layer_data_input = None
        self._canvas = iface.mapCanvas()

        self.layer_setup()

    def closeEvent(self, event):
        """
        Closes dockwidget
        """
        self.closingPlugin.emit()
        event.accept()

    def layer_setup(self):
        """
        Sets up layer for storing parameter declarations
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if not QgsProject.instance().mapLayersByName("Parameter Declarations"):
            param_layer = QgsVectorLayer("None", "Parameter Declarations", "memory")
            QgsProject.instance().addMapLayer(param_layer, False)
            osc_layer.addLayer(param_layer)
            # Setup layer attributes
            data_attributes = [QgsField("Parameter Name", QVariant.String),
                               QgsField("Type", QVariant.String),
                               QgsField("Value", QVariant.String)]
            data_input = param_layer.dataProvider()
            data_input.addAttributes(data_attributes)
            param_layer.updateFields()

            message = "Parameter declarations layer added"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)

        self._param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
        self._param_layer_data_input = self._param_layer.dataProvider()

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
            iface.messageBar().pushMessage("Info", message, level=Qgis.Warning)
            QgsMessageLog.logMessage(message, level=Qgis.Warning)

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
            param_name ([string]): Parameter name
            param_type ([string]): Parameter type
            param_value ([string]): Parameter value
        """
        feature = QgsFeature()
        feature.setAttributes([param_name,
                               param_type,
                               param_value])
        self._param_layer_data_input.addFeature(feature)

        message = f"Parameter '{param_name}' added!"
        iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)

    def delete_existing_parameter(self, param_name):
        query = f'"Parameter Name" = \'{param_name}\''
        feature_request = QgsFeatureRequest().setFilterExpression(query)
        features_to_delete = self._param_layer.getFeatures(feature_request)

        feat_ids = []
        for feature in features_to_delete:
            feat_ids.append(feature.id())

        self._param_layer_data_input.deleteFeatures(feat_ids)
