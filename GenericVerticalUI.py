#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This file is part of manageR

Copyright (C) 2008-9 Carson J. Q. Farmer

This program is free software; you can redistribute it and/or modify it under
the terms of the GNU General Public Licence as published by the Free Software
Foundation; either version 2 of the Licence, or (at your option) any later
version.

This program is distributed in the hope that it will be useful, but WITHOUT
ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
FOR A PARTICULAR PURPOSE.  See the GNU General Public Licence for more 
details.

You should have received a copy of the GNU General Public Licence along with
this program (see LICENSE file in install directory); if not, write to the Free 
Software Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

Portions of the console and EditR window, as well as several background 
funtions are based on the Sandbox python gui of Mark Summerfield.
  Copyright (C) 2007-9 Mark Summerfield. All rights reserved.
  Released under the terms of the GNU General Public License.
The plugins functinality is based largely on the PostGisTools plugin of Mauricio de Paulo.
  Copyright (C) 2009 Mauricio de Paulo. All rights reserved.
  Released under the terms of the GNU General Public License.
manageR makes extensive use of rpy2 (Laurent Gautier) to communicate with R.
  Copyright (C) 2008-9 Laurent Gautier.
  Rpy2 may be used under the terms of the GNU General Public License.
'''

from PyQt4 import QtCore, QtGui
import rpy2.robjects as robjects

VECTORTYPES = ["SpatialPointsDataFrame",
               "SpatialPolygonsDataFrame", 
               "SpatialLinesDataFrame"]
RASTERTYPES = ["SpatialGridDataFrame",
               "SpatialPixelsDataFrame"]

"""Usage:
from PyQt4 import QtCore, QtGui 
from GenericVerticalUI import GenericVerticalUI
class GenericNewDialog(QtGui.QDialog):
    def __init__(self): 
        QtGui.QDialog.__init__(self) 
        # Set up the user interface from Designer. 
        self.ui = GenericVerticalUI ()
        interface=[["label combobox","comboBox","a;b;c;d","false"   ] , ["label spinbox","doubleSpinBox","10","false"   ] ]
        self.ui.setupUi(self,interface) 
"""

class SpComboBox(QtGui.QComboBox):
    def __init__(self, parent=None, types=QtCore.QStringList()):
        super(SpComboBox, self).__init__(parent)
        self.types = types
        
    def spTypes(self):
        return self.types
        
class SpListWidget(QtGui.QListWidget):
    def __init__(self, parent=None, 
        types=QtCore.QStringList(), delimiter=','):
        super(SpListWidget, self).__init__(parent)
        self.types = types
        self.delimiter = delimiter
        
    def spTypes(self):
        return self.types
        
    def spDelimiter(self):
        return self.delimiter
        
class GenericVerticalUI(object):
    """Generic class of user interface"""
    def addGuiItem(self, ParentClass, parameters, width):
        """Defines a new set of Label and a box that can be a 
        ComboBox, spComboBox, LineEdit, TextEdit or DoubleSpinBox."""
        widgetType=parameters[1]
        #check if there are default values:
        if len(parameters)>2:
            default=parameters[2]
        else:
            default=""
        skip = False
        notnull=parameters[3]
        #setting the right type of widget
        if widgetType=="comboBox":
            widget = QtGui.QComboBox(ParentClass)
            widget.addItems(default.split(';'))
            widget.setFixedHeight(26)
        elif widgetType=="spComboBox":
            widget = SpComboBox(ParentClass, default.split(';'))
            widget.setFixedHeight(26)
            self.hasSpComboBox = True
            widget.setEditable(True)
        elif widgetType=="spListWidget":
            widget = SpListWidget(ParentClass, 
            default.split(';'), notnull)
            widget.setMinimumHeight(116)
            self.hasSpComboBox = True
            widget.setSelectionMode(
            QtGui.QAbstractItemView.ExtendedSelection)
        elif widgetType=="doubleSpinBox":
            widget = QtGui.QDoubleSpinBox(ParentClass)
            widget.setValue(float(default))
            widget.setFixedHeight(26)
            widget.setMaximum(999999.9999)
            widget.setDecimals(4)
        elif widgetType=="textEdit":
            widget = QtGui.QTextEdit(ParentClass)
            widget.setPlainText(default)
            widget.setMinimumHeight(116)
        elif widgetType=="helpString":
            self.helpString = default
            skip = True
        else:
            #if unknown assumes lineEdit
            widget = QtGui.QLineEdit(ParentClass)
            widget.setText(default)
            widget.setFixedHeight(26)
        if not skip:
            hbox = QtGui.QHBoxLayout()
            name="widget"+str(self.widgetCounter)
            widget.setObjectName(name)
            widget.setMinimumWidth(250)
            self.widgets.append(widget)
            name="label"+str(self.widgetCounter)
            self.widgetCounter += 1
            label = QtGui.QLabel(ParentClass)
            label.setObjectName(name)
            label.setFixedWidth(width*8)
            label.setText(parameters[0])
            hbox.addWidget(label)
            hbox.addWidget(widget)
            self.vbox.addLayout(hbox)
        
    def isSpatial(self):
        return self.hasSpComboBox
        
    def updateRObjects(self):
        splayers = currentRObjects()
        for widget in self.widgets:
            if isinstance(widget, SpComboBox) \
            or isinstance(widget, SpListWidget):
                sptypes = widget.spTypes()
                for sptype in sptypes:
                    for layer in splayers.keys():
                        if splayers[layer] == sptype.strip() \
                        or sptype.strip() == "all":
                            value = layer
                            widget.addItem(value)
                        if splayers[layer] in VECTORTYPES \
                        and (sptype.strip() == "data.frame" \
                        or sptype.strip() == "all"):
                            value = layer+"@data"
                            widget.addItem(value)
                        if splayers[layer] in VECTORTYPES \
                        or splayers[layer] == "data.frame":
                            for item in list(robjects.r('names(%s)' % (layer))):
                                if splayers[layer] == "data.frame":
                                    value = layer+"$"+item
                                else:
                                    value = layer+"@data$"+item
                                if str(robjects.r('class(%s)' % (value))[0]) == sptype.strip() \
                                or sptype.strip() == "all":
                                    widget.addItem(value)
                            
                                        

    def setupUi(self, ParentClass, itemlist):
        self.ParentClass = ParentClass
        self.ParentClass.setObjectName("ParentClass")
        self.exists={"spComboBox":0, "comboBox":0, "textEdit":0, 
                     "doubleSpinBox":0, "lineEdit":0,  "label":0}
        self.helpString = "There is no help available for this plugin"
        self.widgetCounter = 0
        self.widgets = []
        width = 0
        self.hasSpComboBox = False
        self.vbox = QtGui.QVBoxLayout(self.ParentClass)
        for item in itemlist:
            if len(item[0]) > width:
                width = len(item[0])
        # Draw a label/widget pair for every item in the list
        for item in itemlist:
            self.addGuiItem(self.ParentClass, item, width)
        self.showCommands = QtGui.QCheckBox("Append commands to console",self.ParentClass)
        self.buttonBox = QtGui.QDialogButtonBox(self.ParentClass)
        self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
        self.buttonBox.setStandardButtons(
        QtGui.QDialogButtonBox.Help|QtGui.QDialogButtonBox.Close|QtGui.QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.vbox.addWidget(self.showCommands)
        self.vbox.addWidget(self.buttonBox)
        # accept gets connected in the plugin manager
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), self.ParentClass.reject)
        QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("helpRequested()"), self.help)
        QtCore.QMetaObject.connectSlotsByName(self.ParentClass)

    def help(self):
        if QtCore.QString(self.helpString).startsWith("topic:"):
            topic = QtCore.QString(self.helpString).remove("topic:")
            self.ParentClass.parent().editor.moveToEnd()
            self.ParentClass.parent().editor.cursor.movePosition(
            QtGui.QTextCursor.StartOfBlock, QtGui.QTextCursor.KeepAnchor)
            self.ParentClass.parent().editor.cursor.removeSelectedText()
            self.ParentClass.parent().editor.cursor.insertText(
            "%shelp(%s)" % (
            self.ParentClass.parent().editor.currentPrompt,
            str(topic)))
            self.ParentClass.parent().editor.execute(
            QtCore.QString("help('%s')" % (str(topic))))
        else:
            HelpForm(self.ParentClass, self.helpString).show()
    
class HelpForm(QtGui.QDialog):

    def __init__(self, parent=None, text=""):
        super(HelpForm, self).__init__(parent)
        self.setAttribute(QtCore.Qt.WA_GroupLeader)
        self.setAttribute(QtCore.Qt.WA_DeleteOnClose)
        browser = QtGui.QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(text)
        layout = QtGui.QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(browser)
        self.setLayout(layout)
        self.resize(400, 200)
        QtGui.QShortcut(QtGui.QKeySequence("Escape"), self, self.close)
        self.setWindowTitle("R plugin - Help")

# This is used whenever we check for sp objects in manageR
def currentRObjects():
    ls_ = robjects.conversion.ri2py(
    robjects.rinterface.globalEnv.get('ls',wantFun=True))
    class_ = robjects.conversion.ri2py(
    robjects.rinterface.globalEnv.get('class',wantFun=True))
    dev_list_ = robjects.conversion.ri2py(
    robjects.rinterface.globalEnv.get('dev.list',wantFun=True))
    getwd_ = robjects.conversion.ri2py(
    robjects.rinterface.globalEnv.get('getwd',wantFun=True))
    layers = {}
    graphics = {}
    for item in ls_():
        check = class_(robjects.r[item])[0]
        layers[unicode(item)] = check
    return layers
