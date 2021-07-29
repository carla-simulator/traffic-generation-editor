# -*- coding: utf-8 -*-
# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

'''
Carla_connect - Docker_Widget
'''
import os
from subprocess import Popen    # nosec
from os import environ
import pathlib
# pylint: disable=no-name-in-module
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal
from qgis.utils import iface
from qgis.core import Qgis
# pylint: disable=import-error
from .mapupdate import MapUpdate
from .export_xosc import Exportxosc
from .addcam import ImageProcessor

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'carla_connect_dockwidget_base.ui'))


class CarlaConnectDockWidget(QtWidgets.QDockWidget, FORM_CLASS):
    '''
    Handels UI/widget for carla connection and play scenario
    '''
    closingPlugin = pyqtSignal()

    def __init__(self, parent=None, host='localhost', port=2000):
        """Constructor."""
        super(CarlaConnectDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.combo_box.clear()
        self.iface = iface
        self.host = host
        self.port = port
        self.update_map = MapUpdate(self.host, self.port)
        self.maps = self._get_maps()
        self.combo_box.addItems(self.maps)
        self.combo_box.currentTextChanged.connect(self._change_town)
        self.connection_stat.setText("Connected to carla")
        self.iface.messageBar().pushMessage("Info", "Connected to CARLA", level=Qgis.Info)
        self.play_button.pressed.connect(self._play_scenario)
        self.stop_button.pressed.connect(self._destroy_all)
        self.change_map.pressed.connect(self._get_town)
        self.selected_town = None
        self._scenario_runner_process = None
        self.world = self.update_map.get_world()

    def _get_maps(self):
        self.maps_available = self.update_map.get_available_map()
        maps_avail = []
        for maps in self.maps_available:
            maps_avail.append(maps[17:])
        return maps_avail

    def closeEvent(self, event):    # pylint: disable=invalid-name
        '''
        close plugin
        '''
        self.closingPlugin.emit()
        event.accept()

    def _change_town(self):
        self.selected_town = self.combo_box.currentText()

    def _get_changed_town(self):
        self.selected_town = self.combo_box.currentText()
        return self.selected_town

    def _get_town(self):
        '''
        method to read avaialble maps and change map
        '''
        update_town = self._get_changed_town()
        print("Changing map")
        iface.messageBar().pushMessage("Info", "Changing Map", level=Qgis.Info)
        self.update_map.map_unload()
        self.update_map.change_map(update_town)
        self.update_map.read_map()
        self.update_map.map_init()
        self.update_map.map_update()
        print("Map changed")
        iface.messageBar().pushMessage("Info", "Map Changed", level=Qgis.Info)

    def _play_scenario(self):
        '''
        connect to the senerio runner
        Open py game window for visualization
        '''
        road_network = str(self.world.get_map())
        export_file = Exportxosc(road_network[9:15])
        export_file.save_file()
        ImageProcessor.py_game_setup()
        if environ.get('SCENARIO_RUNNER_ROOT') is not None:
            scenario_runner_file = "/scenario_runner.py"
            scenario_path = os.environ['SCENARIO_RUNNER_ROOT']
            scenario_runner_path = scenario_path + scenario_runner_file
            file = pathlib.Path(scenario_runner_path)
            if file.exists():
                try:
                    self._scenario_runner_process = Popen(['python3', scenario_runner_path,     # nosec
                                                           '--openscenario', '/tmp/scenariogenerator1.xosc',
                                                           '--host', self.host,
                                                           '--port', str(self.port)])
                except RuntimeError as error:
                    print('RuntimeError: {}'.format(error))
                    print(' Could not run the scenario.')
                    print(' Make sure the Carla 0.9.10 or greater in running.')
            else:
                print("Invalid path-> SCENARIO_RUNNER_ROOT")
        else:
            print("Path to scenario runner(SCENARIO_RUNNER_ROOT) not set")

    def _destroy_all(self):
        '''
        Method to destroy all actors
        '''
        ImageProcessor.destroy_all_window()
        if self._scenario_runner_process.poll() is None:
            self._scenario_runner_process.communicate()
            self._scenario_runner_process.kill()
            self._scenario_runner_process.communicate()
