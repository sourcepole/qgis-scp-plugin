# -*- coding: utf-8 -*-

"""
Module managing the result part of the SCP plugin.
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *

import os


def features(layer):
    it = layer.getFeatures()
    feature = QgsFeature()
    while it.nextFeature(feature):
        yield feature


class ResultManager:
    def __init__(self, ui, iface):
        self.iface = iface
        self.ui = ui

        self.ui.tabWidget.setTabEnabled(1, False)

        self.pointTable = self.ui.tableWidget_pointLayersResult
        self.polyTable = self.ui.tableWidget_polygonLayersResult
        self.pointTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.polyTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)

        self.resetSymbologyBtn = self.ui.buttonBox_resultTab.addButton(u"Reset symbology", QDialogButtonBox.ActionRole)
        self.resetSymbologyBtn.clicked.connect(self.__resetSymbology)
        self.resetSymbologyBtn.setEnabled(False)

        self.ui.buttonBox_resultTab.button(QDialogButtonBox.Save).clicked.connect(self.__save)
        self.orgSymbology = dict()

    def clear(self):
        self.orgSymbology = dict()
        self.pointTable.setRowCount(0)
        self.polyTable.setRowCount(0)
        self.ui.tabWidget.setTabEnabled(1, False)
        self.ui.tabWidget.setCurrentWidget(self.ui.tab_input)

    def __resetSymbology(self):
        for layerid in self.orgSymbology:
            layer = QgsMapLayerRegistry.instance().mapLayer(layerid)
            layer.rendererV2().setSymbol(self.orgSymbology[layerid])
        self.resetSymbologyBtn.setEnabled(False)
        self.iface.mapCanvas().refresh()
        self.orgSymbology = dict()

    def __areaString(self, da, area):
        # Try to convert area to square kilometers
        cm = da.convertMeasurement(area, self.iface.mapCanvas().mapUnits(), QGis.Meters, True)
        if cm[1] == QGis.Meters:
            return u"%.3f km\u00B2" % (cm[0] / 1000000.)
        elif cm[1] == QGis.Feet:
            return u"%.3f ft\u00B2" % cm[0]
        elif cm[1] == QGis.Degrees:
            return u"%.5f deg\u00B2" % cm[0]
        else:
            return u"???"

    def computeResult(self, pointLayerInput, polygonLayerInput, MPALayerId, landLayerId):
        self.pointTable.setRowCount(0)
        self.polyTable.setRowCount(0)

        # Set up projection
        da = QgsDistanceArea()
        da.setEllipsoidalMode(self.iface.mapCanvas().hasCrsTransformEnabled())
        ellipsoid = QgsProject.instance().readEntry("Measure", "/Ellipsoid", "NONE")[0]
        da.setEllipsoid(ellipsoid)

        # Collect MPA layer geometries
        MPALayer = QgsMapLayerRegistry.instance().mapLayer(MPALayerId)
        assert(MPALayer.geometryType() == QGis.Polygon)

        MPAGeometries = []
        for MPAFeature in features(MPALayer):
            MPAGeometries += [MPAFeature.geometry()]

        # Clip MPA layer with land layer, if one is specified
        if landLayerId:
            landLayer = QgsMapLayerRegistry.instance().mapLayer(landLayerId)
            assert(landLayer.geometryType() == QGis.Polygon)
            assert(landLayer.featureCount() > 0)

            for i in range(0, len(MPAGeometries)):
                for landFeature in features(landLayer):
                    MPAGeometries[i] = MPAGeometries[i].difference(landFeature.geometry())
            self.ui.label_mpaClipped.show()
        else:
            self.ui.label_mpaClipped.hide()

        crsName = MPALayer.crs().authid()

        # Compute point layer coverage with MPA
        for layerInput in pointLayerInput:
            layer = QgsMapLayerRegistry.instance().mapLayer(layerInput[0])
            assert(layer.geometryType() == QGis.Point)

            if layer.crs().authid() != crsName:
                crsName = None

            outside = 0.0
            total = 0.0
            for feature in features(layer):
                attribValue = feature.attribute(layerInput[2])
                total += attribValue
                for MPAGeometry in MPAGeometries:
                    if not MPAGeometry.contains(feature.geometry().asPoint()):
                        outside += attribValue
            actualOut = round(outside / total * 10000) / 100

            insRow = self.pointTable.rowCount()
            self.pointTable.insertRow(insRow)
            self.pointTable.setItem(insRow, 0, QTableWidgetItem(layer.name()))
            self.pointTable.setItem(insRow, 1, QTableWidgetItem("%.2f" % total))
            if layerInput[3] == True: # Invert
                actualIn = 100. - actualOut
                self.pointTable.setItem(insRow, 2, QTableWidgetItem(QTableWidgetItem("%.2f %% inside" % layerInput[1])))
                self.pointTable.setItem(insRow, 3, QTableWidgetItem(QTableWidgetItem("%.2f %% inside" % actualIn)))
                self.pointTable.setItem(insRow, 4, QTableWidgetItem(QTableWidgetItem("%.2f %%" % (actualIn - layerInput[1]))))
                bg = Qt.red if actualOut >= layerInput[1] else Qt.green
            else:
                self.pointTable.setItem(insRow, 2, QTableWidgetItem(QTableWidgetItem("%.2f %% outside" % layerInput[1])))
                self.pointTable.setItem(insRow, 3, QTableWidgetItem(QTableWidgetItem("%.2f %% outside" % actualOut)))
                self.pointTable.setItem(insRow, 4, QTableWidgetItem(QTableWidgetItem("%.2f %%" % (actualOut - layerInput[1]))))
                bg = Qt.green if actualOut >= layerInput[1] else Qt.red

            for i in range(0, 5):
                self.pointTable.item(insRow, i).setBackground(bg)
            layer.rendererV2().symbol().symbolLayer(0).setBorderColor(bg)
            layer.rendererV2().symbol().symbolLayer(0).properties()["outline_width"] = u"10"

            col = QColor(bg)
            props = layer.rendererV2().symbol().symbolLayer(0).properties()
            if not layerInput[0] in self.orgSymbology:
                self.orgSymbology[layerInput[0]] = layer.rendererV2().symbol().clone()
            props["outline_width"] = u"2"
            props["color_border"] = u"%d, %d, %d, %d" % (col.red(), col.green(), col.blue(), col.alpha())
            props["outline_width_unit"] = u"MM"
            layer.rendererV2().setSymbol(QgsMarkerSymbolV2.createSimple(props))

        # Compute polygon layer coverage with MPA
        for layerInput in polygonLayerInput:
            layer = QgsMapLayerRegistry.instance().mapLayer(layerInput[0])
            assert(layer.geometryType() == QGis.Polygon)
            assert(layer.featureCount() > 0)

            if layer.crs().authid() != crsName:
                crsName = None

            da.setSourceCrs(layer.crs().srsid())

            intersectionArea = 0.0
            layerArea = 0.0
            for feature in features(layer):
                layerArea += da.measure(feature.geometry())
                for MPAGeometry in MPAGeometries:
                    intersectionArea += da.measure(feature.geometry().intersection(MPAGeometry))
            actualIn = round(intersectionArea / layerArea * 10000.) / 100.

            insRow = self.polyTable.rowCount()
            self.polyTable.insertRow(insRow)
            self.polyTable.setItem(insRow, 0, QTableWidgetItem(layer.name()))
            self.polyTable.setItem(insRow, 1, QTableWidgetItem(self.__areaString(da, layerArea)))
            if layerInput[2] == True: # Invert
                actualOut = 100. - actualIn
                self.polyTable.setItem(insRow, 2, QTableWidgetItem(QTableWidgetItem("%.2f %% outside MPA" % layerInput[1])))
                self.polyTable.setItem(insRow, 3, QTableWidgetItem(QTableWidgetItem("%.2f %% outside MPA" % actualOut)))
                self.polyTable.setItem(insRow, 4, QTableWidgetItem(QTableWidgetItem("%.2f %%" % (actualOut - layerInput[1]))))
                bg = Qt.red if actualIn >= layerInput[1] else Qt.green
            else:
                self.polyTable.setItem(insRow, 2, QTableWidgetItem(QTableWidgetItem("%.2f %% inside MPA" % layerInput[1])))
                self.polyTable.setItem(insRow, 3, QTableWidgetItem(QTableWidgetItem("%.2f %% inside MPA" % actualIn)))
                self.polyTable.setItem(insRow, 4, QTableWidgetItem(QTableWidgetItem("%.2f %%" % (actualIn - layerInput[1]))))
                bg = Qt.green if actualIn >= layerInput[1] else Qt.red

            for i in range(0, 5):
                self.polyTable.item(insRow, i).setBackground(bg)

            col = QColor(bg)
            props = layer.rendererV2().symbol().symbolLayer(0).properties()
            if not layerInput[0] in self.orgSymbology:
                self.orgSymbology[layerInput[0]] = layer.rendererV2().symbol().clone()
            props["width_border"] = u"2"
            props["color_border"] = u"%d, %d, %d, %d" % (col.red(), col.green(), col.blue(), col.alpha())
            props["border_width_unit"] = u"MM"
            layer.rendererV2().setSymbol(QgsFillSymbolV2.createSimple(props))

        da.setSourceCrs(MPALayer.crs().srsid())
        self.ui.label_MPAAreaValue.setText(self.__areaString(da, da.measure(MPAGeometry)))

        self.ui.label_crsWarning.setVisible(not crsName and not self.iface.mapCanvas().hasCrsTransformEnabled())
        self.ui.label_unitsWarning.setVisible(not self.iface.mapCanvas().hasCrsTransformEnabled() or ellipsoid == "NONE")

        self.resetSymbologyBtn.setEnabled(True)
        self.ui.tabWidget.setTabEnabled(1, True)
        self.ui.tabWidget.setCurrentWidget(self.ui.tab_result)
        self.iface.mapCanvas().refresh()

    def __save(self):
        dir = os.path.join(QDesktopServices.storageLocation(QDesktopServices.DocumentsLocation), "scp_result.csv")
        filename = QFileDialog.getSaveFileName(self.ui, u"Save SCP result", dir, u"CSV files (*.csv)")
        if filename:
            try:
                fh = open(filename, "w")
                for row in range(0, self.pointTable.rowCount()):
                    name = self.pointTable.item(row, 0).text()
                    target = self.pointTable.item(row, 1).text()
                    actual = self.pointTable.item(row, 2).text()
                    fh.write("%s,%s,%s\n" % (name, target, actual))
                for row in range(0, self.polyTable.rowCount()):
                    name = self.polyTable.item(row, 0).text()
                    target = self.polyTable.item(row, 1).text()
                    actual = self.polyTable.item(row, 2).text()
                    fh.write("%s,%s,%s\n" % (name, target, actual))
            except Exception, e:
                QMessageBox.critical(self.ui, u"Failed to save SCP result", "The SCP result could not be saved:\n%s" % e)
