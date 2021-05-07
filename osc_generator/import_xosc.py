# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator - Import XOSC
"""
import os
import math
from qgis.PyQt import QtWidgets, uic
from PyQt5.QtWidgets import QFileDialog
from qgis.utils import iface
from qgis.core import Qgis, QgsMessageLog, QgsProject, QgsFeature, QgsPointXY, QgsGeometry

from defusedxml import ElementTree as etree
# import xml.etree.ElementTree as etree

import ad_map_access as ad

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_xosc_dialog.ui'))

class ImportXOSCDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Dialog class for importing OpenSCENARIO XML files.
    """
    def __init__(self, parent=None):
        """Initialization of ExportXMLDialog"""
        super(ImportXOSCDialog, self).__init__(parent)
        self.setupUi(self)
        # UI element signals
        self.import_path_button.pressed.connect(self.select_input)

    def select_input(self):
        """Prompts user to select file to import"""
        filename, _filter = QFileDialog.getOpenFileName(
            self,
            caption="Select OpenSCENARIO file to import",
            filter="OpenSCENARIO (*.xosc)")
        # Update text field only if user press 'OK'
        if filename:
            self.import_path.setText(filename)

    def open_file(self):
        """Opens OpenSCENARIO file and start parsing into QGIS layers"""
        if self.import_path.text() is not "":
            filepath = self.import_path.text()
            read_xosc = ImportXOSC(filepath)
            read_xosc.import_xosc()
        else:
            message = "No file path was given for importing"
            iface.messageBar().pushMessage("Critical", message, level=Qgis.Critical)
            QgsMessageLog.logMessage(message, level=Qgis.Critical)


class ImportXOSC():
    def __init__(self, filepath):
        self._filepath = filepath

    def import_xosc(self):
        print("Ready to import")


