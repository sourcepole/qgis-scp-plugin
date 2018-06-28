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
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    # load ScpPlugin class from file ScpPlugin
    from .scpplugin import ScpPlugin
    return ScpPlugin(iface)
