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

# Import the PyQt and QGIS libraries
from PyQt4.QtCore import * 
from PyQt4.QtGui import *
#from PyQt4.QtSql import *
from qgis.core import *
import os, resources
from xml.dom import minidom

from GenericVerticalUI import GenericVerticalUI, SpListWidget, SpComboBox

class PluginManager: 
    def __init__(self, parent):#, iface):
        ## Save reference to the QGIS interface
        #self.iface = iface
        self.tools= os.path.join(os.path.dirname( __file__ ),"tools.xml")
        self.parent = parent

    def makeCaller(self, n):
        return lambda: self.run(n)
    
    def createActions(self, pluginsMenu):  
        self.actionlist=[] #list of actions
        self.callerlist=[] #list of funcions to call run() with id parameter
        self.sublist=[]
        #starting xml file reading
        if not self.tools is None:
            xmlfile=open(self.tools)
            dom=minidom.parse(xmlfile)
            tool=dom.firstChild.firstChild
            
            #loads every tool in the file
            while tool:
                if isinstance(tool, minidom.Element):
                    add = False
                    name = tool.getAttribute("name")
                    category = tool.getAttribute("category")
                    if not category == "":
                        sub = QMenu(category, self.parent)
                        sub.setIcon(QIcon(":mActionAnalysisMenu.png"))
                        add = True
                    else:
                        sub = pluginsMenu
                        add = False
                    for item in self.sublist:
                        if category == item.title():
                            sub = item
                            add = False
                            break
                    if add:
                        self.sublist.append(sub)
                        pluginsMenu.addMenu(sub)
                    # Create action that will start plugin configuration
                    self.actionlist.append(QAction(
                    QIcon(":mActionAnalysisTool"), name, self.parent))
                    #create a new funcion that calls run() with the id parameter
                    self.callerlist.append(self.makeCaller(len(self.actionlist)-1)) 
                    # connect the action to the run method
                    QObject.connect(self.actionlist[-1], 
                    SIGNAL("activated()"), self.callerlist[-1]) 
                    # Add toolbar button and menu item
                    self.parent.addActions(sub, (self.actionlist[-1],))
                tool=tool.nextSibling
            xmlfile.close()

    def runCommand(self, command):
        mime = QMimeData()
        self.parent.editor.moveToEnd()
        self.parent.editor.cursor.movePosition(
        QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        self.parent.editor.cursor.removeSelectedText()
        self.parent.editor.cursor.insertText(
        self.parent.editor.currentPrompt)
        if self.dlg.ui.showCommands.isChecked():
            mime.setText("# manageR '%s' tool\n%s" % (self.name,command))
            self.parent.editor.insertFromMimeData(mime)
            self.parent.editor.entered()
        else:
            mime.setText("# manageR '%s' tool" % (self.name))
            self.parent.editor.insertFromMimeData(mime)
            self.parent.editor.execute(QString(command))
    
    def start(self):
        #reads the info in the widgets and calls the sql command
        command = self.command
        for i,item in enumerate(self.dlg.ui.widgets):
            if type(item)==type(QTextEdit()):
                text=str(item.toPlainText())
            elif type(item)==type(QLineEdit()):
                text=str(item.text())
            elif type(item)==type(QDoubleSpinBox()):
                text=str(item.value())
            elif type(item)==type(QComboBox()):
                text=str(item.currentText())
            elif isinstance(item, SpListWidget):
                items=item.selectedItems()
                text=QString()
                for j in items:
                    text.append(j.text()+item.spDelimiter())
                text.remove(-1,1)
            else:
                try:
                    text=str(item.currentText())
                except:
                    text="Error loading widget."
            command = command.replace("|"+str(i+1)+"|",text)
        self.runCommand(command)

    def getTool(self,toolid):
        """Reads the xml file looking for the tool with toolid 
        and returns it's commands and the parameters double list."""
        xmlfile=open(self.tools)
        dom=minidom.parse(xmlfile)
        tools=dom.firstChild
        count = 0
        for tool in tools.childNodes:
            if isinstance(tool, minidom.Element):
                if count == toolid:
                    break
                count += 1
        query=tool.getAttribute("query")
        name= tool.getAttribute("name")
        lines=[]
        parm=tool.firstChild
        while parm:
            if isinstance(parm, minidom.Element):
                line = [
                parm.attributes.getNamedItem("label").value,
                parm.attributes.getNamedItem("type").value,
                parm.attributes.getNamedItem("default").value,
                parm.attributes.getNamedItem("notnull").value]
                lines.append(line)
            parm=parm.nextSibling
        xmlfile.close()
        return name, query, lines

    # run method that performs all the real work
    def run(self, actionid): 
        #reads the xml file
        self.name, self.command, parameters = self.getTool(actionid)
        # create and show the dialog 
        self.dlg = PluginsDialog(self.parent, parameters)
        self.dlg.setWindowTitle(self.name)
        if self.dlg.ui.isSpatial():
            self.dlg.ui.updateRObjects()
        #connect the slots
        QObject.connect(self.dlg.ui.buttonBox, SIGNAL("accepted()"), self.start)
        #self.helpString = QString(parameters[actionid][-1])
        # show the dialog
        self.dlg.show()
        result = self.dlg.exec_() 
        # See if OK was pressed
        if result == 1: 
            # do something useful (delete the line containing pass and
            # substitute with your code
            print "ok pressed"
            
class PluginsDialog(QDialog):
    def __init__(self, parent, interface): 
        QDialog.__init__(self, parent) 
        self.ui = GenericVerticalUI()
        self.ui.setupUi(self, interface)
