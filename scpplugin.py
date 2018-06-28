# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ScpPlugin
                                 A QGIS plugin
 SCP Plugin
                              -------------------
        begin                : 2014-03-03
        copyright            : (C) 2014 by Sandro Mani / Sourcepole AG
        email                : smani@sourcepole.ch
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
# Import the PyQt and QGIS libraries
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import *
from qgis.PyQt.QtWidgets import *
from qgis.core import *
from qgis.utils import home_plugin_path
# Initialize Qt resources from file resources.py
from . import resources_rc
# Import the code for the dialog
from .forms.ui_scpplugin import ScpPluginDialog
from .about.doAbout import DlgAbout
from .input_manager import InputManager
from .result_manager import ResultManager
import os.path
import shutil
import platform


class ScpPlugin:

    def __init__(self, iface):
        # Remove old scp plugin (except on case sensitive platforms)
        if not platform.system() is "Windows":
            try:
                shutil.rmtree(os.path.join(home_plugin_path, "ScpPlugin"))
            except:
                pass

        # Save reference to the QGIS interface
        self.iface = iface

        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value("locale/userLocale")[0:2]
        localePath = os.path.join(self.plugin_dir,
                                  'i18n', 'scpplugin_{}.qm'.format(locale))

        if os.path.exists(localePath):
            self.translator = QTranslator()
            self.translator.load(localePath)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)

        # Create the dialog (after translation) and keep reference
        self.dlg = ScpPluginDialog()
        self.inputManager = InputManager(self.dlg, iface)
        self.resultManager = ResultManager(self.dlg, iface)
        self.inputManager.run.connect(self.resultManager.computeResult)
        # FIXME: QGIS should expose a signal which is emitted when a project
        # is closed
        QgsProject().instance().removeAll.connect(self.inputManager.clear)
        QgsProject().instance().removeAll.connect(self.resultManager.clear)

    def initGui(self):
        # Create action that will start plugin configuration
        self.action = QAction(
            QIcon(":/plugins/scpplugin/icons/icon.png"),
            u"SCP Plugin", self.iface.mainWindow())

        self.actionAbout = QAction(
            QIcon(""), u"About", self.iface.mainWindow())

        # connect the action to the run method
        self.action.triggered.connect(self.run)
        self.actionAbout.triggered.connect(self.doAbout)

        # Add toolbar button and menu item
        self.iface.addToolBarIcon(self.action)
        self.iface.addPluginToMenu(u"&SCP-Plugin", self.action)
        self.iface.addPluginToMenu(u"&SCP-Plugin", self.actionAbout)

    def unload(self):
        # Remove the plugin menu item and icon
        self.iface.removePluginMenu(u"&SCP-Plugin", self.action)
        self.iface.removePluginMenu(u"&SCP-Plugin", self.actionAbout)
        self.iface.removeToolBarIcon(self.action)

    # run method that performs all the real work
    def run(self):
        self.inputManager.updateLayers()
        self.dlg.exec_()

    def doAbout(self):
        self.dlgAbout = DlgAbout(self.plugin_dir)
        self.dlgAbout.show()
