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
from qgis.core import QgsFeature, QgsProject
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface
from .helper_functions import layer_setup_end_eval


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'end_eval_criteria_dialog.ui'))


class EndEvalCriteriaDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Class for post-scenario evaluation criteria
    """

    def __init__(self, parent=None):
        """Initialization of class and Qt UI element connect signals"""
        super(EndEvalCriteriaDialog, self).__init__(parent)
        self.setupUi(self)
        self.useDefault.stateChanged.connect(self.default_triggers)
        self._data_provider = None

    def default_triggers(self):
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

    def save_end_eval_kpis(self):
        """Executes ingestion of dialog form data into QGIS layer"""
        layer_setup_end_eval()
        layer = QgsProject.instance().mapLayersByName("End Evaluation KPIs")[0]
        self._data_provider = layer.dataProvider()
        # Clear existing attributes
        current_features = [feat.id() for feat in layer.getFeatures()]
        self._data_provider.deleteFeatures(current_features)
        iface.setActiveLayer(layer)

        self.get_collision()
        self.get_driven_distance()
        self.get_keep_lane()
        self.get_on_sidewalk()
        self.get_running_red()
        self.get_running_stop()
        self.get_wrong_lane()

    def get_collision(self):
        """Sets attribute for collision check"""
        if self.collisionGroup.isChecked():
            cond_name = self.collision_CondName.text()
            delay = self.collision_Delay.text()
            cond_edge = self.collision_CondEdge.currentText()
            param_ref = self.collision_ParamRef.text()
            value = self.collision_Value.text()
            rule = self.collision_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_driven_distance(self):
        """Sets attribute for driven distance"""
        if self.drivenDistanceGroup.isChecked():
            cond_name = self.drivenDistance_CondName.text()
            delay = self.drivenDistance_Delay.text()
            cond_edge = self.drivenDistance_CondEdge.currentText()
            param_ref = self.drivenDistance_ParamRef.text()
            value = self.drivenDistance_Value.text()
            rule = self.drivenDistance_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_keep_lane(self):
        """Sets attribute for keeping lane"""
        if self.keepLaneGroup.isChecked():
            cond_name = self.keepLane_CondName.text()
            delay = self.keepLane_Delay.text()
            cond_edge = self.keepLane_CondEdge.currentText()
            param_ref = self.keepLane_ParamRef.text()
            value = self.keepLane_Value.text()
            rule = self.keepLane_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_on_sidewalk(self):
        """Sets attribute for sidewalk check"""
        if self.onSidewalkGroup.isChecked():
            cond_name = self.onSidewalk_CondName.text()
            delay = self.onSidewalk_Delay.text()
            cond_edge = self.onSidewalk_CondEdge.currentText()
            param_ref = self.onSidewalk_ParamRef.text()
            value = self.onSidewalk_Value.text()
            rule = self.onSidewalk_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_running_red(self):
        """Sets attribute for running red light check"""
        if self.runningRedGroup.isChecked():
            cond_name = self.runningRed_CondName.text()
            delay = self.runningRed_Delay.text()
            cond_edge = self.runningRed_CondEdge.currentText()
            param_ref = self.runningRed_ParamRef.text()
            value = self.runningRed_Value.text()
            rule = self.runningRed_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_running_stop(self):
        """Sets attribute for running stop signs check"""
        if self.runningStopGroup.isChecked():
            cond_name = self.runningStop_CondName.text()
            delay = self.runningStop_Delay.text()
            cond_edge = self.runningStop_CondEdge.currentText()
            param_ref = self.runningStop_ParamRef.text()
            value = self.runningStop_Value.text()
            rule = self.runningStop_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def get_wrong_lane(self):
        """Sets attribute for wrong lane check"""
        if self.wrongLaneGroup.isChecked():
            cond_name = self.wrongLane_CondName.text()
            delay = self.wrongLane_Delay.text()
            cond_edge = self.wrongLane_CondEdge.currentText()
            param_ref = self.wrongLane_ParamRef.text()
            value = self.wrongLane_Value.text()
            rule = self.wrongLane_Rule.currentText()
            self.write_attributes(cond_name, delay, cond_edge, param_ref, value, rule)

    def write_attributes(self, cond_name, delay, cond_edge, param_ref, value, rule):
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
        feature.setAttributes([cond_name, float(delay), cond_edge,
                               param_ref, float(value), rule])
        self._data_provider.addFeature(feature)
