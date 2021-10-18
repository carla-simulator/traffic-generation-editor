# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Helper Functions

A collection of helper functions used throughout the plugin
"""
import os
# pylint: disable=no-name-in-module, no-member
from PyQt5.QtWidgets import QInputDialog
from qgis.core import (Qgis, QgsProject, QgsMessageLog, QgsVectorLayer,
                       QgsField, QgsPalLayerSettings, QgsVectorLayerSimpleLabeling, QgsFeatureRequest,
                       QgsSpatialIndex, QgsFeature, edit)
from qgis.utils import iface
from qgis.PyQt.QtCore import QVariant

import ad_map_access as ad


def resolve(name, basepath=None):
    """
    Resolves file path

    Args:
        name ([str]): File name to be resolved for path
        basepath ([str], optional): Specify the basepath for resolving. Defaults to None.

    Returns:
        [str]: Fully resolved filepath
    """
    if not basepath:
        basepath = os.path.dirname(os.path.realpath(__file__))
    return os.path.join(basepath, name)


def display_message(message, level):
    """
    Presents status messages on UI

    Args:
        message (str): Status message to display
        level (str): 3 levels -> Info, Warning, Critical
    """
    status = level

    # Convert into QGIS message levels
    if level == "Info":
        level = Qgis.Info
    elif level == "Warning":
        level = Qgis.Warning
    elif level == "Critical":
        level = Qgis.Critical

    iface.messageBar().pushMessage(status, message, level=level)
    QgsMessageLog.logMessage(message, level=level)


def layer_setup_metadata():
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
        display_message(message, level="Info")


def set_metadata(rev_major=None,
                 rev_minor=None,
                 description=None,
                 author=None,
                 road_network_filepath=None,
                 scene_graph_filepath=None):
    """
    Set/Replace the metadata
    """
    if not QgsProject.instance().mapLayersByName("Metadata"):
        layer_setup_metadata()

    metadata_layer = QgsProject.instance().mapLayersByName("Metadata")[0]

    if metadata_layer.featureCount() == 0:
        # initialize feature with default values
        feature = QgsFeature()
        feature.setAttributes([
            1,
            0,
            "Generated OpenSCENARIO File",
            "QGIS OSCGenerator Plugin",
            "",
            ""
        ])
        metadata_layer.dataProvider().addFeature(feature)

    with edit(metadata_layer):
        feature = metadata_layer.getFeature(1)
        if rev_major:
            feature["Rev Major"] = int(rev_major)
        if rev_minor:
            feature["Rev Minor"] = int(rev_minor)
        if description:
            feature["Description"] = description
        if author:
            feature["Author"] = author
        if road_network_filepath:
            feature["Road Network"] = road_network_filepath
        if scene_graph_filepath:
            feature["Scene Graph File"] = scene_graph_filepath
        metadata_layer.updateFeature(feature)


def layer_setup_end_eval():
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
        display_message(message, level="Info")


def layer_setup_environment():
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
        display_message(message, level="Info")


def layer_setup_walker():
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
        display_message(message, level="Info")


def layer_setup_vehicle():
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
        display_message(message, level="Info")


def layer_setup_props():
    """
    Set up static objects layer
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Static Objects"):
        props_layer = QgsVectorLayer("Polygon", "Static Objects", "memory")
        QgsProject.instance().addMapLayer(props_layer, False)
        osc_layer.addLayer(props_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("id", QVariant.Int),
            QgsField("Prop", QVariant.String),
            QgsField("Prop Type", QVariant.String),
            QgsField("Orientation", QVariant.Double),
            QgsField("Mass", QVariant.String),
            QgsField("Pos X", QVariant.Double),
            QgsField("Pos Y", QVariant.Double),
            QgsField("Pos Z", QVariant.Double),
            QgsField("Physics", QVariant.Bool)
        ]
        props_layer.dataProvider().addAttributes(data_attributes)
        props_layer.updateFields()

        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_settings.fieldName = "concat('Prop_', \"id\")"
        props_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        props_layer.setLabelsEnabled(True)

        message = "Static objects layer added"
        display_message(message, level="Info")


def layer_setup_maneuvers_waypoint():
    """
    Set up waypoint maneuvers layer
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Waypoint Maneuvers"):
        waypoint_layer = QgsVectorLayer("Point", "Waypoint Maneuvers", "memory")
        QgsProject.instance().addMapLayer(waypoint_layer, False)
        osc_layer.addLayer(waypoint_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("Maneuver ID", QVariant.Int),
            QgsField("Entity", QVariant.String),
            QgsField("Waypoint No", QVariant.Int),
            QgsField("Orientation", QVariant.Double),
            QgsField("Pos X", QVariant.Double),
            QgsField("Pos Y", QVariant.Double),
            QgsField("Pos Z", QVariant.Double),
            QgsField("Route Strategy", QVariant.String)
        ]
        waypoint_layer.dataProvider().addAttributes(data_attributes)
        waypoint_layer.updateFields()

        label_settings = QgsPalLayerSettings()
        label_settings.isExpression = True
        label_name = "concat('ManID: ', \"Maneuver ID\", ' ', \"Entity\", ' - ', \"Waypoint No\")"
        label_settings.fieldName = label_name
        waypoint_layer.setLabeling(QgsVectorLayerSimpleLabeling(label_settings))
        waypoint_layer.setLabelsEnabled(True)

        message = "Waypoint maneuvers layer added"
        display_message(message, level="Info")
    else:
        message = "Using existing waypoint maneuver layer"
        display_message(message, level="Info")


def layer_setup_maneuvers_and_triggers():
    """
    Set up maneuvers layer (including start and stop triggers)
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Maneuvers"):
        maneuver_layer = QgsVectorLayer("None", "Maneuvers", "memory")
        QgsProject.instance().addMapLayer(maneuver_layer, False)
        osc_layer.addLayer(maneuver_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("id", QVariant.Int),
            QgsField("Maneuver Type", QVariant.String),
            QgsField("Entity", QVariant.String),
            QgsField("Entity: Maneuver Type", QVariant.String),
            # Global Actions
            QgsField("Global: Act Type", QVariant.String),
            QgsField("Infra: Traffic Light ID", QVariant.Int),
            QgsField("Infra: Traffic Light State", QVariant.String),
            # Start Triggers
            QgsField("Start Trigger", QVariant.String),
            QgsField("Start - Entity: Condition", QVariant.String),
            QgsField("Start - Entity: Ref Entity", QVariant.String),
            QgsField("Start - Entity: Duration", QVariant.Double),
            QgsField("Start - Entity: Value", QVariant.Double),
            QgsField("Start - Entity: Rule", QVariant.String),
            QgsField("Start - Entity: RelDistType", QVariant.String),
            QgsField("Start - Entity: Freespace", QVariant.Bool),
            QgsField("Start - Entity: Along Route", QVariant.Bool),
            QgsField("Start - Value: Condition", QVariant.String),
            QgsField("Start - Value: Param Ref", QVariant.String),
            QgsField("Start - Value: Name", QVariant.String),
            QgsField("Start - Value: DateTime", QVariant.String),
            QgsField("Start - Value: Value", QVariant.Double),
            QgsField("Start - Value: Rule", QVariant.String),
            QgsField("Start - Value: State", QVariant.String),
            QgsField("Start - Value: Sboard Type", QVariant.String),
            QgsField("Start - Value: Sboard Element", QVariant.String),
            QgsField("Start - Value: Sboard State", QVariant.String),
            QgsField("Start - Value: TController Ref", QVariant.String),
            QgsField("Start - Value: TController Phase", QVariant.String),
            QgsField("Start - WorldPos: Tolerance", QVariant.Double),
            QgsField("Start - WorldPos: X", QVariant.Double),
            QgsField("Start - WorldPos: Y", QVariant.Double),
            QgsField("Start - WorldPos: Z", QVariant.Double),
            QgsField("Start - WorldPos: Heading", QVariant.Double),
            # Stop Triggers
            QgsField("Stop Trigger Enabled", QVariant.Bool),
            QgsField("Stop Trigger", QVariant.String),
            QgsField("Stop - Entity: Condition", QVariant.String),
            QgsField("Stop - Entity: Ref Entity", QVariant.String),
            QgsField("Stop - Entity: Duration", QVariant.Double),
            QgsField("Stop - Entity: Value", QVariant.Double),
            QgsField("Stop - Entity: Rule", QVariant.String),
            QgsField("Stop - Entity: RelDistType", QVariant.String),
            QgsField("Stop - Entity: Freespace", QVariant.Bool),
            QgsField("Stop - Entity: Along Route", QVariant.Bool),
            QgsField("Stop - Value: Condition", QVariant.String),
            QgsField("Stop - Value: Param Ref", QVariant.String),
            QgsField("Stop - Value: Name", QVariant.String),
            QgsField("Stop - Value: DateTime", QVariant.String),
            QgsField("Stop - Value: Value", QVariant.Double),
            QgsField("Stop - Value: Rule", QVariant.String),
            QgsField("Stop - Value: State", QVariant.String),
            QgsField("Stop - Value: Sboard Type", QVariant.String),
            QgsField("Stop - Value: Sboard Element", QVariant.String),
            QgsField("Stop - Value: Sboard State", QVariant.String),
            QgsField("Stop - Value: TController Ref", QVariant.String),
            QgsField("Stop - Value: TController Phase", QVariant.String),
            QgsField("Stop - WorldPos: Tolerance", QVariant.Double),
            QgsField("Stop - WorldPos: X", QVariant.Double),
            QgsField("Stop - WorldPos: Y", QVariant.Double),
            QgsField("Stop - WorldPos: Z", QVariant.Double),
            QgsField("Stop - WorldPos: Heading", QVariant.Double)
        ]
        maneuver_layer.dataProvider().addAttributes(data_attributes)
        maneuver_layer.updateFields()

        message = "Maneuvers layer added"
        display_message(message, level="Info")
    else:
        message = "Using existing maneuvers layer"
        display_message(message, level="Info")


def layer_setup_maneuvers_longitudinal():
    """
    Set up longitudinal maneuvers layer
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Longitudinal Maneuvers"):
        long_man_layer = QgsVectorLayer("None", "Longitudinal Maneuvers", "memory")
        QgsProject.instance().addMapLayer(long_man_layer, False)
        osc_layer.addLayer(long_man_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("Maneuver ID", QVariant.Int),
            QgsField("Type", QVariant.String),
            QgsField("Speed Target", QVariant.String),
            QgsField("Ref Entity", QVariant.String),
            QgsField("Dynamics Shape", QVariant.String),
            QgsField("Dynamics Dimension", QVariant.String),
            QgsField("Dynamics Value", QVariant.String),
            QgsField("Target Type", QVariant.String),
            QgsField("Target Speed", QVariant.String),
            QgsField("Continuous", QVariant.Bool),
            QgsField("Freespace", QVariant.Bool),
            QgsField("Max Acceleration", QVariant.String),
            QgsField("Max Deceleration", QVariant.String),
            QgsField("Max Speed", QVariant.String)
        ]
        long_man_layer.dataProvider().addAttributes(data_attributes)
        long_man_layer.updateFields()

        message = "Longitudinal maneuvers layer added"
        display_message(message, level="Info")
    else:
        message = "Using existing longitudinal maneuvers layer"
        display_message(message, level="Info")


def layer_setup_maneuvers_lateral():
    """
    Set up lateral maneuvers layer
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Lateral Maneuvers"):
        lat_man_layer = QgsVectorLayer("None", "Lateral Maneuvers", "memory")
        QgsProject.instance().addMapLayer(lat_man_layer, False)
        osc_layer.addLayer(lat_man_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("Maneuver ID", QVariant.Int),
            QgsField("Type", QVariant.String),
            QgsField("Lane Target", QVariant.String),
            QgsField("Ref Entity", QVariant.String),
            QgsField("Dynamics Shape", QVariant.String),
            QgsField("Dynamics Dimension", QVariant.String),
            QgsField("Dynamics Value", QVariant.String),
            QgsField("Lane Target Value", QVariant.String),
            QgsField("Max Lateral Acceleration", QVariant.String),
            QgsField("Max Acceleration", QVariant.String),
            QgsField("Max Deceleration", QVariant.String),
            QgsField("Max Speed", QVariant.String)
        ]
        lat_man_layer.dataProvider().addAttributes(data_attributes)
        lat_man_layer.updateFields()

        message = "Lateral maneuvers layer added"
        display_message(message, level="Info")
    else:
        message = "Using existing lateral maneuvers layer"
        display_message(message, level="Info")


def layer_setup_parameters():
    """
    Set up parameter declarations layer
    """
    root_layer = QgsProject.instance().layerTreeRoot()
    osc_layer = root_layer.findGroup("OpenSCENARIO")
    if osc_layer is None:
        osc_layer = root_layer.addGroup("OpenSCENARIO")

    if not QgsProject.instance().mapLayersByName("Parameter Declarations"):
        param_layer = QgsVectorLayer("None", "Parameter Declarations", "memory")
        QgsProject.instance().addMapLayer(param_layer, False)
        osc_layer.addLayer(param_layer)
        # Setup layer attributes
        data_attributes = [
            QgsField("Parameter Name", QVariant.String),
            QgsField("Type", QVariant.String),
            QgsField("Value", QVariant.String)
        ]
        param_layer.dataProvider().addAttributes(data_attributes)
        param_layer.updateFields()

        message = "Parameter declarations layer added"
        display_message(message, level="Info")


def verify_parameters(param):
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


def is_float(value):
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


def get_entity_heading(geopoint):
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

    return None


def get_geo_point(point):
    """
    Acquires hight based on position in map.
    Prompts user to select hight if multiple lanes with significant different heights exist at the position.
    Throws error if spawn position is not on lane.

    Args:
        point: [QgsPointXY] point of click event

    Returns:
        geo_point: [AD Map GEOPoint] geo point including (selected) altitude
        geo_point: [None] if click point is not valid
    """

    pt_geo = ad.map.point.createGeoPoint(point.x(), point.y(), ad.map.point.AltitudeUnknown)
    dist = ad.physics.Distance(1.)
    mmpts = ad.map.match.AdMapMatching.findLanes(pt_geo, dist)
    z_values = set()
    if len(mmpts) == 0:
        # fallback calculation
        lane_edge_layer = QgsProject.instance().mapLayersByName("Lane Edge")[0]
        lane_edge_data_provider = lane_edge_layer.dataProvider()
        spatial_index = QgsSpatialIndex()
        spatial_feature = QgsFeature()
        lane_edge_features = lane_edge_data_provider.getFeatures()

        while lane_edge_features.nextFeature(spatial_feature):
            spatial_index.addFeature(spatial_feature)

        nearest_ids = spatial_index.nearestNeighbor(point, 5)

        for feat in lane_edge_layer.getFeatures(QgsFeatureRequest().setFilterFids(nearest_ids)):
            feature_coordinates = feat.geometry().vertexAt(1)
            z_values.add(round(feature_coordinates.z(), ndigits=4))
    else:
        for mmpt in mmpts:
            if mmpt.type == ad.map.match.MapMatchedPositionType.LANE_IN:
                geo_matched_point = ad.map.point.toGeo(mmpt.matchedPoint)
                z_values.add(float(geo_matched_point.altitude))
        if len(z_values) == 0:
            # take all matches into account if no in line match found
            for mmpt in mmpts:
                geo_matched_point = ad.map.point.toGeo(mmpt.matchedPoint)
                z_values.add(float(geo_matched_point.altitude))

    if len(z_values) == 0:
        message = "Click point is too far from valid lane"
        iface.messageBar().pushMessage("Error", message, level=Qgis.Critical)
        QgsMessageLog.logMessage(message, level=Qgis.Critical)
        return None

    # sort the values
    z_values = sorted(z_values, reverse=True)

    # fallback: use max
    altitude = max(z_values)
    if max(z_values) - min(z_values) > 0.1:
        stringified_z_values = [str(z_value) for z_value in z_values]
        z_value_selected, ok_pressed = QInputDialog.getItem(
            QInputDialog(),
            "Choose Elevation",
            "Elevation (meters)",
            tuple(stringified_z_values),
            current=0,
            editable=False)

        if ok_pressed:
            altitude = float(z_value_selected)

    geopoint = ad.map.point.createGeoPoint(longitude=point.x(), latitude=point.y(), altitude=altitude)
    return geopoint
