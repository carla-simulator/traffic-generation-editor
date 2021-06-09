# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Helper Functions
"""
from PyQt5.QtWidgets import QInputDialog
from qgis.core import (Qgis, QgsProject, QgsMessageLog, QgsVectorLayer, QgsFeature,
    QgsField, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling)
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant

import ad_map_access as ad

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
        if osc_layer is None:
            osc_layer = root_layer.addGroup("OpenSCENARIO")

        if not QgsProject.instance().mapLayersByName("Metadata"):
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
    
    def layer_setup_end_eval(self):
        """
        Set up OpenSCENARIO end evaluation KPIs layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if osc_layer is None:
            osc_layer = root_layer.addGroup("OpenSCENARIO")
        
        if not QgsProject.instance().mapLayersByName("End Evaluation KPIs"):
            end_eval_layer = QgsVectorLayer("None", "End Evaluation KPIs", "memory")
            QgsProject.instance().addMapLayer(end_eval_layer, False)
            osc_layer.addLayer(end_eval_layer)
            # Setup layer attributes
            data_attributes = [
                QgsField("Condition Name", QVariant.String),
                QgsField("Delay", QVariant.Double),
                QgsField("Condition Edge", QVariant.String),
                QgsField("Parameter Ref", QVariant.String),
                QgsField("Value", QVariant.Double),
                QgsField("Rule", QVariant.String)
            ]

            end_eval_layer.dataProvider().addAttributes(data_attributes)
            end_eval_layer.updateFields()

            message = "End evaluation KPIs layer added"
            self.display_message(message, level="Info")

    def layer_setup_environment(self):
        """
        Set up environment layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if osc_layer is None:
            osc_layer = root_layer.addGroup("OpenSCENARIO")

        if not QgsProject.instance().mapLayersByName("Environment"):
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
        if osc_layer is None:
            osc_layer = root_layer.addGroup("OpenSCENARIO")

        if not QgsProject.instance().mapLayersByName("Pedestrians"):
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
    
    def layer_setup_vehicle(self):
        """
        Set up vehicle layer
        """
        root_layer = QgsProject.instance().layerTreeRoot()
        osc_layer = root_layer.findGroup("OpenSCENARIO")
        if osc_layer is None:
            osc_layer = root_layer.addGroup("OpenSCENARIO")

        if (not QgsProject.instance().mapLayersByName("Vehicles") or
            not QgsProject.instance().mapLayersByName("Vehicles - Ego")):
            vehicle_layer_ego = QgsVectorLayer("Polygon", "Vehicles - Ego", "memory")
            vehicle_layer = QgsVectorLayer("Polygon", "Vehicles", "memory")
            QgsProject.instance().addMapLayer(vehicle_layer_ego, False)
            QgsProject.instance().addMapLayer(vehicle_layer, False)
            osc_layer.addLayer(vehicle_layer_ego)
            osc_layer.addLayer(vehicle_layer)
            
            # Setup layer attributes
            data_attributes = [QgsField("id", QVariant.Int),
                               QgsField("Vehicle Model", QVariant.String),
                               QgsField("Orientation", QVariant.Double),
                               QgsField("Pos X", QVariant.Double),
                               QgsField("Pos Y", QVariant.Double),
                               QgsField("Pos Z", QVariant.Double),
                               QgsField("Init Speed", QVariant.String),
                               QgsField("Agent", QVariant.String),
                               QgsField("Agent Camera", QVariant.Bool)]

            vehicle_layer_ego.dataProvider().addAttributes(data_attributes)
            vehicle_layer.dataProvider().addAttributes(data_attributes)
            vehicle_layer_ego.updateFields()
            vehicle_layer.updateFields()

            label_settings_ego = QgsPalLayerSettings()
            label_settings_ego.isExpression = True
            label_settings_ego.fieldName = "concat('Ego_', \"id\")"
            vehicle_layer_ego.setLabeling(QgsVectorLayerSimpleLabeling(label_settings_ego))
            vehicle_layer_ego.setLabelsEnabled(True)
            label_settings = QgsPalLayerSettings()
            label_settings.isExpression = True
            label_settings.fieldName = "concat('Vehicle_', \"id\")"
            vehicle_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
            vehicle_layer.setLabelsEnabled(True)

            message = "Vehicle layer added"
            self.display_message(message, level="Info")

    def verify_parameters(self, param):
        """
        Checks Parameter Declarations attribute table to verify parameter exists

        Args:
            param (string): name of parameter to check against

        Returns:
            feature (dict): parameter definitions
        """
        param_layer = QgsProject.instance().mapLayersByName("Parameter Declarations")[0]
        query = f'"Parameter Name" = \'{param}\''
        feature_request = QgsFeatureRequest().setFilterExpression(query)
        features = param_layer.getFeatures(feature_request)
        feature = {}

        for feat in features:
            feature["Type"] = feat["Type"]
            feature["Value"] = feat["Value"]

        return feature
    
    def is_float(self, value):
        """
        Checks value if it can be converted to float.

        Args:
            value (string): value to check if can be converted to float

        Returns:
            bool: True if float, False if not
        """
        try:
            float(value)
            return True
        except ValueError:
            return False

    def get_entity_heading(self, geopoint):
        """
        Acquires heading based on spawn position in map.
        Prompts user to select lane if multiple lanes exist at spawn position.
        Throws error if spawn position is not on lane.

        Args:
            geopoint: [AD Map GEOPoint] point of click event

        Returns:
            lane_heading: [float] heading of click point at selected lane ID
            lane_heading: [None] if click point is not valid
        """
        dist = ad.physics.Distance(1)
        admap_matched_points = ad.map.match.AdMapMatching.findLanes(geopoint, dist)

        lanes_detected = 0
        for point in admap_matched_points:
            lanes_detected += 1

        if lanes_detected == 0:
            message = "Click point is too far from valid lane"
            iface.messageBar().pushMessage("Error", message, level=Qgis.Critical)
            QgsMessageLog.logMessage(message, level=Qgis.Critical)
            return None
        elif lanes_detected == 1:
            for point in admap_matched_points:
                lane_id = point.lanePoint.paraPoint.laneId
                para_offset = point.lanePoint.paraPoint.parametricOffset
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading
        else:
            lane_ids_to_match = []
            lane_id = []
            para_offsets = []
            for point in admap_matched_points:
                lane_ids_to_match.append(str(point.lanePoint.paraPoint.laneId))
                lane_id.append(point.lanePoint.paraPoint.laneId)
                para_offsets.append(point.lanePoint.paraPoint.parametricOffset)

            lane_id_selected, ok_pressed = QInputDialog.getItem(
                QInputDialog(),
                "Choose Lane ID",
                "Lane ID",
                tuple(lane_ids_to_match),
                current=0,
                editable=False)

            if ok_pressed:
                i = lane_ids_to_match.index(lane_id_selected)
                lane_id = lane_id[i]
                para_offset = para_offsets[i]
                parapoint = ad.map.point.createParaPoint(lane_id, para_offset)
                lane_heading = ad.map.lane.getLaneENUHeading(parapoint)
                return lane_heading
