# -*- coding: utf-8 -*-

# Copyright (c) 2021 FZI Forschungszentrum Informatik
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
Carla_connect - Connect to CARLA
"""
import os.path
# pylint: disable=no-name-in-module,no-member
from qgis.core import Qgis, QgsMessageLog
from qgis.PyQt import QtWidgets, uic
from qgis.utils import iface

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'carla_connect_to_host_dialog.ui'))


class CarlaConnectToHostDialog(QtWidgets.QDialog, FORM_CLASS):
    """
    Dialog class for connecting to CARLA.
    """

    def __init__(self, parent=None):
        """Initialization of CarlaConnectToHostDialog"""
        super(CarlaConnectToHostDialog, self).__init__(parent)
        self.setupUi(self)

    def get_host_and_port(self):
        """Returns host and port selection from GUI"""
        host = "localhost"
        port = 2000
        if self.host_selection.text() != "":
            host = str(self.host_selection.text())
        else:
            message = "No CARLA host was selected, defaulting to 'localhost'"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        if self.port_selection.text() != "":
            port = int(self.port_selection.text())
        else:
            message = "No CARLA port was selected, defaulting to 2000"
            iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
        return [host, port]
