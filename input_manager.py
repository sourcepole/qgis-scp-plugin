# -*- coding: utf-8 -*-

"""
Module managing the input part of the SCP plugin.
"""

from PyQt4.QtCore import *
from PyQt4.QtGui import *
from qgis.core import *
import json
import os


def setComboItemEnabled(combo, id, enabled):
    row = combo.findData(id)
    if row > -1:
        item = combo.model().item(row)
        if not enabled:
            item.setFlags(item.flags() & ~(Qt.ItemIsSelectable | Qt.ItemIsEnabled))
        else:
            item.setFlags(item.flags() | Qt.ItemIsSelectable | Qt.ItemIsEnabled)


class ComboItemDelegate(QItemDelegate):
    valueChanged = pyqtSignal()

    def __init__(self, combo, table):
        super(ComboItemDelegate, self).__init__()
        self.combo = combo
        self.table = table

    def createEditor(self, parent, option, index):
        combo = QComboBox(parent)
        combo.setModel(self.combo.model())
        return combo

    def setEditorData(self, editor, index):
        id = index.model().data(index, Qt.UserRole)
        editor.setCurrentIndex(editor.findData(id))

    def setModelData(self, editor, model, index):
        row = editor.currentIndex()
        if row > -1:
            if model.data(index, Qt.UserRole) != editor.itemData(row):
                setComboItemEnabled(self.combo, model.data(index, Qt.UserRole), True)
                setComboItemEnabled(self.combo, editor.itemData(row), False)
                self.valueChanged.emit()
                self.table.item(index.row(), 0).setBackground(QBrush())
            model.setData(index, editor.itemData(row), Qt.UserRole)
            model.setData(index, editor.itemText(row), Qt.DisplayRole)


class PointComboItemDelegate(ComboItemDelegate):
    def setModelData(self, editor, model, index):
        super(PointComboItemDelegate, self).setModelData(editor, model, index)
        row = editor.currentIndex()
        fieldCombo = self.table.cellWidget(index.row(), 2)
        fieldCombo.clear()
        if row > -1:
            layer = QgsMapLayerRegistry.instance().mapLayer(editor.itemData(row))
            for field in layer.dataProvider().fields():
                if not field.name() == "id":
                    fieldCombo.addItem(field.name())
        if fieldCombo.count() < 1:
            self.table.item(index.row(), 0).setBackground(Qt.red)


class InputManager(QObject):
    run = pyqtSignal(list, list, str, str, name="run")

    def __init__(self, ui, iface):
        super(InputManager, self).__init__()
        self.iface = iface
        self.ui = ui

        self.inputFile = None
        self.inputChanged = False

        self.pointTable = self.ui.tableWidget_pointLayers
        self.polyTable = self.ui.tableWidget_polygonLayers
        self.pointCombo = self.ui.comboBox_addPointLayer
        self.polyCombo = self.ui.comboBox_addPolygonLayer

        self.mpaCombo = self.ui.comboBox_selectMPA
        self.mpaCombo.curId = None
        self.mpaCombo.setModel(self.polyCombo.model())
        self.mpaCombo.currentIndexChanged.connect(lambda: self.__singleLayerSelected(self.mpaCombo))

        self.landCombo = self.ui.comboBox_selectLand
        self.landCombo.curId = None
        self.landCombo.setModel(self.polyCombo.model())
        self.landCombo.currentIndexChanged.connect(lambda: self.__singleLayerSelected(self.landCombo))

        self.ui.checkBox_land.toggled.connect(self.__enableLandLayer)

        self.analyzeBtn = self.ui.buttonBox_inputTab.addButton(u"Run analysis", QDialogButtonBox.ApplyRole)
        self.analyzeBtn.clicked.connect(lambda: self.run.emit(self.getPointLayerInput(), self.getPolygonLayerInput(), self.mpaCombo.curId, self.landCombo.curId))
        self.analyzeBtn.setEnabled(False)

        self.pointCombo.setEditable(True)
        self.pointCombo.lineEdit().setPlaceholderText(u"Select point layer to add")
        self.pointCombo.lineEdit().setFocusPolicy(Qt.NoFocus)
        self.pointCombo.activated.connect(lambda idx: self.__addLayerSelected(idx, self.pointCombo, self.__addPointLayer))
        self.pointTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.pointTable.horizontalHeader().setResizeMode(3, QHeaderView.Fixed)
        self.pointTable.setColumnWidth(3, 24)
        self.pointTable.horizontalHeader().setResizeMode(4, QHeaderView.Fixed)
        self.pointTable.setColumnWidth(4, 24)
        self.pointTableCol0Delegate = PointComboItemDelegate(self.pointCombo, self.pointTable)
        self.pointTable.setItemDelegateForColumn(0, self.pointTableCol0Delegate)
        self.pointTable.itemDelegateForColumn(0).valueChanged.connect(self.__layerChanged)

        self.polyCombo.setEditable(True)
        self.polyCombo.lineEdit().setPlaceholderText(u"Select polygon layer to add")
        self.polyCombo.lineEdit().setFocusPolicy(Qt.NoFocus)
        self.polyCombo.activated.connect(lambda idx: self.__addLayerSelected(idx, self.polyCombo, self.__addPolygonLayer))
        self.polyTable.horizontalHeader().setResizeMode(QHeaderView.Stretch)
        self.polyTable.horizontalHeader().setResizeMode(2, QHeaderView.Fixed)
        self.polyTable.setColumnWidth(2, 24)
        self.polyTable.horizontalHeader().setResizeMode(3, QHeaderView.Fixed)
        self.polyTable.setColumnWidth(3, 24)
        self.polyTableCol0Delegate = ComboItemDelegate(self.polyCombo, self.polyTable)
        self.polyTable.setItemDelegateForColumn(0, self.polyTableCol0Delegate)
        self.polyTable.itemDelegateForColumn(0).valueChanged.connect(self.__layerChanged)

        self.ui.buttonBox_inputTab.button(QDialogButtonBox.Save).clicked.connect(self.__save)
        self.ui.buttonBox_inputTab.button(QDialogButtonBox.Open).clicked.connect(self.__open)
        self.ui.buttonBox_inputTab.button(QDialogButtonBox.Reset).clicked.connect(self.clear)

    def __layerChanged(self):
        self.inputChanged = True
        self.__validateInput()

    def __setInputChanged(self):
        self.inputChanged = True

    def __addLayerSelected(self, idx, combo, addFz):
        addFz(combo.itemData(idx))
        self.inputChanged = True
        self.__validateInput()
        combo.setCurrentIndex(-1)

    def __singleLayerSelected(self, combo):
        combo.setEditable(False) # Clear error state from __open
        if combo.curId:
            setComboItemEnabled(combo, combo.curId, True)
        idx = combo.currentIndex()
        if idx > -1:
            if combo.curId != combo.itemData(idx):
                self.inputChanged = True
                combo.curId = combo.itemData(idx)
            setComboItemEnabled(combo, combo.curId, False)
            self.__validateInput()
        else:
            combo.curId = None

    def __enableLandLayer(self, checked):
        self.landCombo.setEnabled(checked)
        if not checked:
            self.landCombo.setCurrentIndex(-1)
            self.landCombo.curId = None
        self.__validateInput()

    def __setSpinBoxSuffix(self, spinBox, inside):
        spinBox.setSuffix(u"% inside MPA" if inside else u"% outside MPA")

    def __addPointLayer(self, layerId, targetPerc=None, fieldName=None, invert=False):
        layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        layerName = layer.name() if layer else layerId

        setComboItemEnabled(self.pointCombo, layerId, False)

        insRow = self.pointTable.rowCount()
        self.pointTable.insertRow(insRow)

        nameItem = QTableWidgetItem(layerName)
        nameItem.setData(Qt.UserRole, layerId)
        self.pointTable.setItem(insRow, 0, nameItem)
        self.pointTable.scrollToItem(nameItem)

        spinBox = QDoubleSpinBox()
        spinBox.setRange(0, 100)
        spinBox.setSingleStep(0.1)
        spinBox.setDecimals(2)
        spinBox.setSuffix(u" % outside MPA")
        if targetPerc is not None:
            spinBox.setValue(targetPerc)
        spinBox.valueChanged.connect(self.__setInputChanged)
        self.pointTable.setCellWidget(insRow, 1, spinBox)

        fieldCombo = QComboBox()
        if layer:
            for field in layer.dataProvider().fields():
                if not field.name() == "id":
                    fieldCombo.addItem(field.name())
        if fieldCombo.count() < 1:
            nameItem.setBackground(Qt.red)
        fieldCombo.setCurrentIndex(max(0, fieldCombo.findText(fieldName)))
        self.pointTable.setCellWidget(insRow, 2, fieldCombo)
        fieldCombo.currentIndexChanged.connect(self.__setInputChanged)

        invertCbx = QCheckBox()
        invertCbx.setChecked(invert)
        invertCbx.clicked.connect(self.__setInputChanged)
        invertCbx.clicked.connect(lambda: self.__setSpinBoxSuffix(spinBox, invertCbx.isChecked()))
        self.__setSpinBoxSuffix(spinBox, invertCbx.isChecked())
        self.pointTable.setCellWidget(insRow, 3, invertCbx)

        removeBtn = QPushButton()
        removeBtn.setFlat(True)
        removeBtn.setIcon(QIcon(":/plugins/scpplugin/icons/list-remove.png"))
        removeBtn.clicked.connect(lambda: self.__removeItem(self.pointTable, nameItem, self.pointCombo))
        self.pointTable.setCellWidget(insRow, 4, removeBtn)

    def __addPolygonLayer(self, layerId, targetPerc=None, invert=False):
        layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
        layerName = layer.name() if layer else layerId

        setComboItemEnabled(self.polyCombo, layerId, False)

        insRow = self.polyTable.rowCount()
        self.polyTable.insertRow(insRow)

        nameItem = QTableWidgetItem(layerName)
        nameItem.setData(Qt.UserRole, layerId)
        self.polyTable.setItem(insRow, 0, nameItem)
        self.polyTable.scrollToItem(nameItem)

        spinBox = QDoubleSpinBox()
        spinBox.setRange(0, 100)
        spinBox.setSingleStep(0.1)
        spinBox.setDecimals(2)
        spinBox.setSuffix(u" % inside MPA")
        if targetPerc is not None:
            spinBox.setValue(targetPerc)
        spinBox.valueChanged.connect(self.__setInputChanged)
        self.polyTable.setCellWidget(insRow, 1, spinBox)

        invertCbx = QCheckBox()
        invertCbx.setChecked(invert)
        invertCbx.clicked.connect(self.__setInputChanged)
        invertCbx.clicked.connect(lambda: self.__setSpinBoxSuffix(spinBox, not invertCbx.isChecked()))
        self.__setSpinBoxSuffix(spinBox, not invertCbx.isChecked())
        self.polyTable.setCellWidget(insRow, 2, invertCbx)

        removeBtn = QPushButton()
        removeBtn.setFlat(True)
        removeBtn.setIcon(QIcon(":/plugins/scpplugin/icons/list-remove.png"))
        removeBtn.clicked.connect(lambda: self.__removeItem(self.polyTable, nameItem, self.polyCombo))
        self.polyTable.setCellWidget(insRow, 3, removeBtn)

    def __removeItem(self, table, item, combo):
        row = table.row(item)
        layerId = table.item(row, 0).data(Qt.UserRole)
        table.removeRow(row)
        self.inputChanged = True
        self.__validateInput()
        setComboItemEnabled(combo, layerId, True)

    def updateLayers(self):
        """
        Updates the list of layers selectable in the input dialog and ensures the selected ones are valid
        """
        # Block signals to avoid setting the dirty flag when populating the combobox
        self.mpaCombo.blockSignals(True)
        self.landCombo.blockSignals(True)
        self.pointCombo.clear()
        self.polyCombo.clear()
        layers = QgsMapLayerRegistry.instance().mapLayers().iteritems()
        for (id, layer) in layers:
            if layer.type() == QgsMapLayer.VectorLayer:
                geomType = layer.geometryType()
                if geomType == QGis.Point:
                    self.pointCombo.addItem(layer.name(), id)
                elif geomType == QGis.Polygon and layer.featureCount() > 0:
                    self.polyCombo.addItem(layer.name(), id)
        self.pointCombo.setCurrentIndex(-1)
        self.polyCombo.setCurrentIndex(-1)
        self.mpaCombo.setCurrentIndex(self.mpaCombo.findData(self.mpaCombo.curId))
        self.landCombo.setCurrentIndex(self.landCombo.findData(self.landCombo.curId))
        self.mpaCombo.blockSignals(False)
        self.landCombo.blockSignals(False)

        self.__validateCombo(self.mpaCombo)
        self.__validateCombo(self.landCombo)
        self.__validateTable(self.pointTable, self.pointCombo)
        self.__validateTable(self.polyTable, self.polyCombo)
        self.__validateInput()

    def __validateInput(self):
        valid = (self.pointTable.rowCount() > 0 or self.polyTable.rowCount() > 0)
        valid &= self.mpaCombo.curId is not None
        valid &= (not self.ui.checkBox_land.isChecked() or self.landCombo.curId is not None)
        for row in range(0, self.pointTable.rowCount()):
            valid &= (self.pointTable.item(row, 0).background() != Qt.red)
        for row in range(0, self.polyTable.rowCount()):
            valid &= (self.polyTable.item(row, 0).background() != Qt.red)
        self.analyzeBtn.setEnabled(valid)

    def __validateCombo(self, combo):
        if combo.currentIndex() == -1:
            if combo.curId:
                combo.setEditable(True)
                combo.lineEdit().setFocusPolicy(Qt.NoFocus)
                combo.lineEdit().setText(combo.curId)
                combo.lineEdit().setStyleSheet("QLineEdit { background-color: red; }")
        else:
            setComboItemEnabled(combo, combo.curId, False)

    def __validateTable(self, table, combo):
        row = 0
        for row in range(0, table.rowCount()):
            layerId = table.item(row, 0).data(Qt.UserRole)
            layer = QgsMapLayerRegistry.instance().mapLayer(layerId)
            if not layer:
                table.item(row, 0).setText(layerId)
                table.item(row, 0).setBackground(Qt.red)
            else:
                setComboItemEnabled(combo, layerId, False)

    def __save(self, filename):
        if not filename:
            filename = self.inputFile
            if not filename:
                filename = QSettings().value("ScpPlugin/lastLocation", QDesktopServices.storageLocation(QDesktopServices.DocumentsLocation) + os.sep)
            filename = QFileDialog.getSaveFileName(self.ui, u"Save SCP plan", filename, u"JSON files (*.json)")
        if filename:
            base, ext = os.path.splitext(filename)
            if ext.lower() != '.json':
                filename = base + ext + ".json"

            try:
                fh = open(filename, "w")
                data = {"PointLayers": self.getPointLayerInput(),
                        "PolygonLayers": self.getPolygonLayerInput(),
                        "MPALayer": self.mpaCombo.curId,
                        "LandLayer": self.landCombo.curId}
                fh.write(json.dumps(data))
                self.inputChanged = False
                self.inputFile = filename
                QSettings().setValue("ScpPlugin/lastLocation", os.path.dirname(filename))
                return True
            except Exception, e:
                QMessageBox.critical(self.ui, u"Failed to save SCP plan", "The SCP plan could not be saved:\n%s" % e)
        return False

    def __open(self, filename):
        if self.clear():
            dir = QSettings().value("ScpPlugin/lastLocation", QDesktopServices.storageLocation(QDesktopServices.DocumentsLocation) + os.sep)
            filename = QFileDialog.getOpenFileName(self.ui, u"Open SCP plan", dir, u"JSON files (*.json)")
            if filename:
                try:
                    fh = open(filename, "r")
                    data = json.loads(fh.read())
                    for layer in data["PointLayers"]:
                        self.__addPointLayer(layer[0], layer[1], layer[2], layer[3])
                    for layer in data["PolygonLayers"]:
                        self.__addPolygonLayer(layer[0], layer[1], layer[2])
                    self.mpaCombo.curId = data["MPALayer"]
                    self.mpaCombo.setCurrentIndex(self.mpaCombo.findData(self.mpaCombo.curId))
                    self.landCombo.curId = data["LandLayer"]
                    self.landCombo.setCurrentIndex(self.landCombo.findData(self.landCombo.curId))
                    self.ui.checkBox_land.setChecked(self.landCombo.curId is not None)
                    self.inputFile = filename
                    QSettings().setValue("ScpPlugin/lastLocation", os.path.dirname(filename) + os.sep)
                    self.inputChanged = False
                    self.__validateCombo(self.mpaCombo)
                    self.__validateCombo(self.landCombo)
                    self.__validateTable(self.pointTable, self.pointCombo)
                    self.__validateTable(self.polyTable, self.polyCombo)
                    self.__validateInput()
                except Exception, e:
                    QMessageBox.critical(self.ui, u"Failed to load SCP plan", "The SCP plan could not be loaded:\n%s" % e)

    def clear(self):
        if self.__saveIfChanged():
            while self.pointTable.rowCount() > 0:
                self.__removeItem(self.pointTable, self.pointTable.item(0, 0), self.pointCombo)
            while self.polyTable.rowCount() > 0:
                self.__removeItem(self.polyTable, self.polyTable.item(0, 0), self.polyCombo)
            self.mpaCombo.setCurrentIndex(-1)
            self.mpaCombo.setEditable(False)
            self.mpaCombo.curId = None
            self.landCombo.setCurrentIndex(-1)
            self.landCombo.setEditable(False)
            self.landCombo.curId = None
            self.ui.checkBox_land.setChecked(False)
            self.inputFile = None
            self.inputChanged = False
            self.analyzeBtn.setEnabled(False)
            return True
        return False

    def getPointLayerInput(self):
        """
        Returns a list of input point layer data tuples:
            [(layerId1, targetPerc1, quantField1, invert1), (layerId2, targetPerc2, quantField2, invert2), ...]
        """
        list = []
        for row in range(0, self.pointTable.rowCount()):
            layerId = self.pointTable.item(row, 0).data(Qt.UserRole)
            targetPerc = self.pointTable.cellWidget(row, 1).value()
            combo = self.pointTable.cellWidget(row, 2)
            quantField = combo.itemText(combo.currentIndex())
            invert = self.pointTable.cellWidget(row, 3).isChecked()
            list.append((layerId, targetPerc, quantField, invert))
        return list

    def getPolygonLayerInput(self):
        """
        Returns a list of input polygon layer data tuples:
            [(layerId1, targetPerc1, invert1), (layerId2, targetPerc2, invert2), ...]
        """
        list = []
        for row in range(0, self.polyTable.rowCount()):
            layerId = self.polyTable.item(row, 0).data(Qt.UserRole)
            targetPerc = self.polyTable.cellWidget(row, 1).value()
            invert = self.polyTable.cellWidget(row, 2).isChecked()
            list.append((layerId, targetPerc, invert))
        return list

    def __saveIfChanged(self):
        if self.inputChanged is True:
            if QMessageBox.question(self.ui, u"SCP Input Modified", \
               u"The SCP input dialog has unsaved changes. Do you want to save them?", \
               QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes) == QMessageBox.Yes:
                return self.__save(self.inputFile)
        return True
