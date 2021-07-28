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
from qgis.core import QgsProject

# pylint: disable=relative-beyond-top-level
from .add_vehicles import AddVehiclesDockWidget
from .add_pedestrians import AddPedestriansDockWidget
from .add_static_objects import AddPropsDockWidget
from .export_xosc import ExportXOSCDialog
from .edit_environment import EditEnvironmentDockWidget
from .end_eval_criteria import EndEvalCriteriaDialog
from .add_maneuvers import AddManeuversDockWidget


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

        self._plugin_is_active_vehicles = False
        self._plugin_is_active_pedestrians = False
        self._plugin_is_active_props = False
        self._plugin_is_active_environment = False
        self._plugin_is_active_maneuvers = False
        self._dockwidget_vehicles = None
        self._dockwidget_pedestrians = None
        self._dockwidget_props = None
        self._dockwidget_environment = None
        self._dockwidget_maneuvers = None
        self._root_layer = QgsProject.instance().layerTreeRoot()

    # noinspection PyMethodMayBeStatic

    def tr(self, message):  # pylint: disable=invalid-name
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

    def initGui(self):  # pylint: disable=invalid-name
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_weather.png',
            text=self.tr(u'Edit Environment'),
            callback=self.edit_environment,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_vehicle.png',
            text=self.tr(u'Add Vehicles'),
            callback=self.add_vehicles,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_pedestrian.png',
            text=self.tr(u'Add Pedestrians'),
            callback=self.add_pedestrians,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_static.png',
            text=self.tr(u'Add Static Objects'),
            callback=self.add_props,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_maneuver.png',
            text=self.tr(u'Add Maneuvers'),
            callback=self.add_maneuver,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_endEval.png',
            text=self.tr(u'End Evaluation KPIs'),
            callback=self.end_evaluation,
            parent=self.iface.mainWindow())

        self.add_action(
            icon_path=':/plugins/OSC_Generator/icon_code.png',
            text=self.tr(u'Export to OpenSCENARIO'),
            callback=self.export_xosc,
            parent=self.iface.mainWindow())

    # --------------------------------------------------------------------------

    def onClosePlugin(self):    # pylint: disable=invalid-name
        """Cleanup necessary items here when plugin dockwidget is closed"""
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

    def unload(self):   # pylint: disable=invalid-name
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

    def export_xosc(self):
        """
        Opens "Export OpenSCENARIO" dialog.
        """
        dlg = ExportXOSCDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            ExportXOSCDialog.save_file(dlg)

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

    def end_evaluation(self):
        """
        Opens "End Evaluation" dialog.
        """
        dlg = EndEvalCriteriaDialog()
        dlg.show()
        return_value = dlg.exec_()
        if return_value:
            EndEvalCriteriaDialog.save_end_eval_kpis(dlg)
