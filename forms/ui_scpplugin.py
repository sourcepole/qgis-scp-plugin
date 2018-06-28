# -*- coding: utf-8 -*-

"""
Module implementing ScpPluginDialog.
"""

from qgis.PyQt.QtWidgets import *
from .Ui_ui_scpplugin import Ui_ScpPlugin

import os
import subprocess
import sys


class ScpPluginDialog(QDialog, Ui_ScpPlugin):
    def __init__(self, parent=None):
        QDialog.__init__(self, parent)
        self.setupUi(self)
        self.setModal(True)
        self.buttonBox.button(QDialogButtonBox.Close).clicked.connect(
            self.accept)
        self.buttonBox.button(QDialogButtonBox.Help).clicked.connect(
            self.__showHelp)

    def __showHelp(self):
        filepath = os.path.join(
            os.path.dirname(
                os.path.dirname(__file__)),
            "documentation", "documentation.pdf")
        if sys.platform.startswith('darwin'):
            subprocess.call(('open', filepath))
        elif os.name == 'nt':
            os.startfile(filepath)
        elif os.name == 'posix':
            subprocess.call(('xdg-open', filepath))
