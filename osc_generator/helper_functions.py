# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Helper Functions
"""

from qgis.core import (Qgis, QgsProject, QgsMessageLog, QgsVectorLayer, QgsFeature,
    QgsField, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant

class HelperFunctions():
    """
    A collection of helper functions used throughout the plugin
    """
    def display_message(self, message, level):
        """
        Presents status messages on UI

        Args:
            message (str): Status message to display
            level (str): 3 levels -> Info, Warning, Critical
        """
        status = level

        # Convert into QGIS message levels
        if level is "Info":
            level = Qgis.Info
        elif level is "Warning":
            level = Qgis.Warning
        elif level is "Critical":
            level = Qgis.Critical

        iface.messageBar().pushMessage(status, message, level=level)
        QgsMessageLog.logMessage(message, level=level)

    def layer_setup_metadata(self):
        """
        Set up OpenSCENARIO metadata layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")

        metadata_layer = QgsVectorLayer("None", "Metadata", "memory")
        QgsProject.instance().addMapLayer(metadata_layer, False)
        osc_layer.addLayer(metadata_layer)

        # Setup layer attributes
        data_attibutes = [
            QgsField("Rev Major", QVariant.Int),
            QgsField("Rev Minor", QVariant.Int),
            QgsField("Description", QVariant.String),
            QgsField("Author", QVariant.String),
            QgsField("Road Network", QVariant.String),
            QgsField("Scene Graph File", QVariant.String)
        ]
        metadata_layer.dataProvider().addAttributes(data_attibutes)
        metadata_layer.updateFields()

        message = "Metadata layer added"
        self.display_message(message, level="Info")
    
    def layer_setup_environment(self):
        """
        Set up environment layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")

        env_layer = QgsVectorLayer("None", "Environment", "memory")
        QgsProject.instance().addMapLayer(env_layer, False)
        osc_layer.addLayer(env_layer)
        
        # Setup layer attributes
        data_attributes = [
            QgsField("Datetime", QVariant.String),
            QgsField("Datetime Animation", QVariant.Bool),
            QgsField("Cloud State", QVariant.String),
            QgsField("Fog Visual Range", QVariant.Double),
            QgsField("Sun Intensity", QVariant.Double),
            QgsField("Sun Azimuth", QVariant.Double),
            QgsField("Sun Elevation", QVariant.Double),
            QgsField("Precipitation Type", QVariant.String),
            QgsField("Precipitation Intensity", QVariant.Double)
        ]
        env_layer.dataProvider().addAttributes(data_attributes)
        env_layer.updateFields()

        message = "Environment layer added"
        self.display_message(message, level="Info")

    def layer_setup_walker(self):
        """
        Set up pedestrian layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")

        walker_layer = QgsVectorLayer("Polygon", "Pedestrians", "memory")
        QgsProject.instance().addMapLayer(walker_layer, False)
        osc_layer.addLayer(walker_layer)
        
        # Setup layer attributes
        data_attributes = [
            QgsField("id", QVariant.Int),
            QgsField("Walker", QVariant.String),
            QgsField("Orientation", QVariant.Double),
            QgsField("Pos X", QVariant.Double),
            QgsField("Pos Y", QVariant.Double),
            QgsField("Pos Z", QVariant.Double),
            QgsField("Init Speed", QVariant.String)
        ]
        walker_layer.dataProvider().addAttributes(data_attributes)
        walker_layer.updateFields()

        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_settings.fieldName = "concat('Pedestrian_', \"id\")"
        walker_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        walker_layer.setLabelsEnabled(True)

        message = "Pedestrian layer added"
        self.display_message(message, level="Info")