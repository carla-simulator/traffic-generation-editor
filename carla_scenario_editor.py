# -*- coding: utf-8 -*-

# Copyright (c) 2020-2021 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.
"""
OpenSCENARIO Generator
A QGIS 3+ plugin

Enables faster and easier generation of OpenSCENARIO XOSC files.
"""
import os.path

# pylint: disable=no-name-in-module
from qgis.PyQt.QtCore import QSettings, QTranslator, QCoreApplication, Qt
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction
from qgis.core import QgsProject, Qgis, QgsMessageLog

# pylint: disable=relative-beyond-top-level
from .osc_generator.add_vehicles import AddVehiclesDockWidget
from .osc_generator.add_pedestrians import AddPedestriansDockWidget
from .osc_generator.add_static_objects import AddPropsDockWidget
from .osc_generator.export_xosc import ExportXOSCDialog
from .osc_generator.import_xosc import ImportXOSCDialog
from .osc_generator.edit_environment import EditEnvironmentDockWidget
from .osc_generator.end_eval_criteria import EndEvalCriteriaDialog
from .osc_generator.add_maneuvers import AddManeuversDockWidget
from .osc_generator.parameter_declarations import ParameterDeclarationsDockWidget

try:
    # test import here to avoid exception later
    import carla    # pylint: disable=unused-import
    from .carla_connect.mapupdate import MapUpdate
    from .carla_connect.addcam import CameraDockWidget
    from .carla_connect.carla_connect_dockwidget import CarlaConnectDockWidget
    from .carla_connect.carla_connect_to_host import CarlaConnectToHostDialog
    carla_available = True  # pylint: disable=invalid-name
except:     # pylint: disable=bare-except
    carla_available = False  # pylint: disable=invalid-name


class OSC_Generator:    # pylint: disable=invalid-name
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)

        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'OSC_Generator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&OSC Generator')
        self.toolbar = self.iface.addToolBar(u'OSC_Generator')
        self.toolbar.setObjectName(u'OSC_Generator')
        self.pluginIsActive = False
        self._plugin_is_active_vehicles = False
        self._plugin_is_active_pedestrians = False
        self._plugin_is_active_props = False
        self._plugin_is_active_environment = False
        self._plugin_is_active_maneuvers = False
        self._plugin_is_active_parameters = False
        self._dockwidget_vehicles = None
        self._dockwidget_pedestrians = None
        self._dockwidget_props = None
        self._dockwidget_environment = None
        self._dockwidget_maneuvers = None
        self._dockwidget_parameters = None
        self._root_layer = QgsProject.instance().layerTreeRoot()
        self.ui = QGISUI(self.iface, "OSC_Generator", True)
        self.action_tool = {}
        self.host = None
        self.port = None
        self.update_map = None
        self.dockwidget = None
        self.camera_dock_widget = None

    # noinspection PyMethodMayBeStatic

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('OSC_Generator', message)

    def add_action(
            self,
            icon_path,
            text,
            callback,
            enabled_flag=True,
            add_to_menu=True,
            add_to_toolbar=True,
            status_tip=None,
            whats_this=None,
            parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)
        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""
        weather = "icon_weather"
        weather_info = "Edit Environment"
        vehicle = "icon_vehicle"
        vehicle_info = "Add Vehicles"
        pedestrians = "icon_pedestrian"
        pedestrians_info = "Add Pedestrians"
        static = "icon_static"
        static_info = "Add static objects"
        maneuver = "icon_maneuver"
        maneuver_info = "Add maneuvers"
        parameter = "icon_parameter"
        parameter_info = "Add Parameters"
        endeval = "icon_endEval"
        endeval_info = "End evaluation KPI's"
        code_export = "icon_code"
        code_export_info = "Export OpenSCENARIO file"
        code_import = "icon_import"
        code_import_info = "Import OpenSCENARIO file"
        carla_logo = "carla_logo"
        carla_info = "Connect to CARLA"
        cam = "video_cam"
        cam_info = "Add bird eye camera"

        self.__add_action__(weather, weather_info, self.edit_environment)
        self.__add_action__(vehicle, vehicle_info, self.add_vehicles)
        self.__add_action__(pedestrians, pedestrians_info, self.add_pedestrians)
        self.__add_action__(static, static_info, self.add_props)
        self.__add_action__(maneuver, maneuver_info, self.add_maneuver)
        self.__add_action__(parameter, parameter_info, self.add_parameters)
        self.__add_action__(endeval, endeval_info, self.end_evaluation)
        self.__add_action__(code_export, code_export_info, self.export_xosc)
        self.__add_action__(code_import, code_import_info, self.import_xosc)
        self.__add_action__(carla_logo, carla_info, self.run_scenario)
        self.__add_action__(cam, cam_info, self.add_camera_position)

    def __add_action__(self, icon_file, info, callback):
        """
        Adds action to QGIS toolbar

        Args:
            icon_file (str): Icon file name (without file extension)
            info (str): Tooltip information
            callback (function): Callback function for button
        """
        action = self.ui.add_action(icon_file, info, callback)
        self.action_tool[icon_file] = (action, None)

    # --------------------------------------------------------------------------

    def onClosePlugin(self):
        """Cleanup necessary items here when plugin dockwidget is closed"""
        self.pluginIsActive = False
        if self._plugin_is_active_vehicles:
            self._dockwidget_vehicles.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_vehicles = False

        if self._plugin_is_active_pedestrians:
            self._dockwidget_pedestrians.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_pedestrians = False

        if self._plugin_is_active_environment:
            self._dockwidget_environment.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_environment = False

        if self._plugin_is_active_maneuvers:
            self._dockwidget_maneuvers.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_maneuvers = False

        if self._plugin_is_active_props:
            self._dockwidget_props.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_props = False

        if self._plugin_is_active_parameters:
            self._dockwidget_parameters.closingPlugin.disconnect(self.onClosePlugin)
            self._plugin_is_active_parameters = False

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&OSC Generator'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    # --------------------------------------------------------------------------

    def add_vehicles(self):
        """
        Adds "Add Vehicle" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugins
        if not self._plugin_is_active_vehicles:
            self._plugin_is_active_vehicles = True

            # dockwidget may not exist if:
            #    first run of plugin
            #    removed on close (see self.onClosePlugin method)
            if self._dockwidget_vehicles is None:
                self._dockwidget_vehicles = AddVehiclesDockWidget()

            # connect to provide cleanup on closing of dockwidget
            self._dockwidget_vehicles.closingPlugin.connect(self.onClosePlugin)

            # show the dockwidget
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self._dockwidget_vehicles)
            self._dockwidget_vehicles.show()

    def add_pedestrians(self):
        """
        Adds "Add Pedestrians" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugin
        if not self._plugin_is_active_pedestrians:
            self._plugin_is_active_pedestrians = True

            if self._dockwidget_pedestrians is None:
                self._dockwidget_pedestrians = AddPedestriansDockWidget()

            self._dockwidget_pedestrians.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self._dockwidget_pedestrians)
            self._dockwidget_pedestrians.show()

    def get_carla_host_and_port(self):
        """
        Opens "Connect to CARLA" dialog.
        """
        dlg = CarlaConnectToHostDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            self.host, self.port = CarlaConnectToHostDialog.get_host_and_port(dlg)
            return True
        else:
            return False

    def export_xosc(self):
        """
        Opens "Export OpenSCENARIO" dialog.
        """
        dlg = ExportXOSCDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            ExportXOSCDialog.save_file(dlg)

    def import_xosc(self):
        """
        Opens "Import OpenSCENARIO" dialog.
        """
        dlg = ImportXOSCDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            ImportXOSCDialog.open_file(dlg)

    def edit_environment(self):
        """
        Adds "Edit Environment" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugin
        if not self._plugin_is_active_environment:
            self._plugin_is_active_environment = True

            if self._dockwidget_environment is None:
                self._dockwidget_environment = EditEnvironmentDockWidget()

            self._dockwidget_environment.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self._dockwidget_environment)
            self._dockwidget_environment.show()

    def add_maneuver(self):
        """
        Adds "Add Maneuvers" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugin
        if not self._plugin_is_active_maneuvers:
            self._plugin_is_active_maneuvers = True

            if self._dockwidget_maneuvers is None:
                self._dockwidget_maneuvers = AddManeuversDockWidget()

            self._dockwidget_maneuvers.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.RightDockWidgetArea, self._dockwidget_maneuvers)
            self._dockwidget_maneuvers.show()

    def add_props(self):
        """
        Adds "Add Static Objects" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugin
        if not self._plugin_is_active_props:
            self._plugin_is_active_props = True

            if self._dockwidget_props is None:
                self._dockwidget_props = AddPropsDockWidget()

            self._dockwidget_props.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self._dockwidget_props)
            self._dockwidget_props.show()

    def add_parameters(self):
        """
        Adds "Add Parameters" dock widget.
        Creates OpenSCENARIO layer group if it does not exist.
        """
        # Add temporary scratch layer to QGIS (if not yet created)
        if self._root_layer.findGroup("OpenSCENARIO") is None:
            self._root_layer.addGroup("OpenSCENARIO")

        # Load plugin
        if not self._plugin_is_active_parameters:
            self._plugin_is_active_parameters = True

            if self._dockwidget_parameters is None:
                self._dockwidget_parameters = ParameterDeclarationsDockWidget()

            self._dockwidget_parameters.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.BottomDockWidgetArea, self._dockwidget_parameters)
            self._dockwidget_parameters.show()

    def end_evaluation(self):
        """
        Opens "End Evaluation" dialog.
        """
        dlg = EndEvalCriteriaDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            EndEvalCriteriaDialog.save_end_eval_kpis(dlg)

    def run_scenario(self):
        '''
        Opens the Carla-Connect widget
        '''
        if not carla_available:
            message = "No CARLA module available"
            self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
            return

        if not self.get_carla_host_and_port():
            message = "Did not specify CARLA host and port"
            self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
            return

        message = "Loading Map"
        self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)
        self.update_map = MapUpdate(self.host, self.port)
        self.update_map.read_map()
        self.update_map.map_init()
        self.update_map.map_update()
        message = "Map Loaded"
        self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
        QgsMessageLog.logMessage(message, level=Qgis.Info)
        if not self.pluginIsActive:
            self.dockwidget = CarlaConnectDockWidget(host=self.host, port=self.port)
            self.dockwidget.closingPlugin.connect(self.onClosePlugin)
            self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.dockwidget)
            self.dockwidget.show()
            self.pluginIsActive = True
        action = self.action_tool['carla_logo'][0]
        action.setDisabled(True)

    def add_camera_position(self):
        '''
        Opens the camera placement widget
        '''
        if not carla_available:
            message = "No CARLA module available"
            self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
            return

        if not self.get_carla_host_and_port():
            message = "Did not specify CARLA host and port"
            self.iface.messageBar().pushMessage("Info", message, level=Qgis.Info)
            QgsMessageLog.logMessage(message, level=Qgis.Info)
            return

        self.camera_dock_widget = CameraDockWidget(host=self.host, port=self.port)
        self.iface.addDockWidget(Qt.LeftDockWidgetArea, self.camera_dock_widget)
        self.camera_dock_widget.show()


class QGISUI(object):
    "..."

    def __init__(self, iface, title, toolbar_too=False):
        "..."
        self.iface = iface
        self.menu = title
        self.actions = {}
        self.separators = []
        self.toolbar = None
        if toolbar_too:
            self.toolbar = self.iface.addToolBar(title)
            self.toolbar.setObjectName(title)

    def add_action(self, icon_file, info, callback):
        "..."
        parent = self.iface.mainWindow()
        icon = self.__icon__(icon_file)
        action = QAction(icon, info, parent)
        action.triggered.connect(callback)
        self.iface.addPluginToDatabaseMenu(self.menu, action)
        if self.toolbar is not None:
            self.toolbar.addAction(action)
        self.actions[icon_file] = action
        return action

    def __icon__(self, text):
        "..."
        name = os.path.dirname(__file__) + "/icons/"
        for char in text:
            name = name + char
        name = name + ".png"
        if os.path.exists(name):
            icon = QIcon(name)
            if icon is not None:
                return icon
        return QIcon()
