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

import base64
import os, re, sys, platform

from qgis.core import *

import resources
from QLayerConverter import QVectorLayerConverter, QRasterLayerConverter
from RLayerWriter import RVectorLayerWriter, RRasterLayerWriter, RVectorLayerConverter
from pluginManager import PluginManager

from PyQt4.QtCore import (PYQT_VERSION_STR, QByteArray, QDir, QEvent,
        QFile, QFileInfo, QIODevice, QPoint, QProcess, QRegExp, QObject,
        QSettings, QString, QT_VERSION_STR, QTextStream, QThread,
        QTimer, QUrl, QVariant, Qt, SIGNAL, QStringList, QMimeData)
from PyQt4.QtGui import (QAction, QApplication, QButtonGroup, QCheckBox,
        QColor, QColorDialog, QComboBox, QCursor, QDesktopServices,
        QDialog, QDialogButtonBox, QFileDialog, QFont, QFontComboBox,
        QFontMetrics, QGridLayout, QHBoxLayout, QIcon, QInputDialog,
        QKeySequence, QLabel, QLineEdit, QListWidget, QMainWindow,QMouseEvent,
        QMessageBox, QPixmap, QPushButton, QRadioButton, QGroupBox,
        QRegExpValidator, QShortcut, QSpinBox, QSplitter, QDirModel,
        QSyntaxHighlighter, QTabWidget, QTextBrowser, QTextCharFormat,
        QTextCursor, QTextDocument, QTextEdit, QToolTip, QVBoxLayout,
        QWidget, QDockWidget, QToolButton, QSpacerItem, QSizePolicy,
        QPalette, QSplashScreen, QTreeWidget, QTreeWidgetItem, QFrame,
        QListView, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, 
        QAbstractItemView, QTextBlockUserData, QTextFormat, QClipboard)

try:
  import rpy2.robjects as robjects
#  import rpy2.rinterface as rinterface
except ImportError:
  QMessageBox.warning(None , "manageR", "Unable to load manageR: Unable to load required package rpy2."
  + "\nPlease ensure that both R, and the corresponding version of Rpy2 are correctly installed.")

__license__ = """<font color=green>\
Copyright &copy; 2008-9 Carson J. Q. Farmer. All rights reserved.</font>

This program is free software: you can redistribute it and/or modify it
under the terms of the GNU General Public License as published by the Free
Software Foundation, version 2 of the License, or version 3 of the
License or (at your option) any later version.

This program is distributed in the hope that it will be useful, but
<i>without any warranty</i>; without even the implied warranty of
<i>merchantability</i> or <i>fitness for a particular purpose</i>. 
See the <a href="http://www.gnu.org/licenses/">GNU General Public
License</a> for more details."""

KEYWORDS = ["break", "else", "for", "if", "in", "next", "repeat", 
            "return", "switch", "try", "while", "print", "return",
            "not", "library", "attach", "detach", "ls", "as", "summary",
            "plot", "hist", "lines", "points"]

BUILTINS = ["array", "character", "complex", "data.frame", "double", 
            "factor", "function", "integer", "list", "logical", 
            "matrix", "numeric", "vector"] 

CONSTANTS = ["Inf", "NA", "NaN", "NULL", "TRUE", "FALSE"]

VECTORTYPES = ["SpatialPointsDataFrame",
               "SpatialPolygonsDataFrame", 
               "SpatialLinesDataFrame"]

RASTERTYPES = ["SpatialGridDataFrame",
               "SpatialPixelsDataFrame"]

Config = {}
CAT = QStringList() # Completions And Tooltips
Libraries = []

def welcomeString(version):
    string = """Welcome to manageR %s
QGIS interface to the R statistical analysis program
Copyright (C) 2009  Carson Farmer 
Licensed under the terms of GNU GPL 2\nmanageR is free software; 
you can redistribute it and/or modify it under the terms of 
the GNU General Public License as published by the Free Software Foundation; 
either version 2 of the License, or (at your option) any later version.
Currently running %s""" % (version,robjects.r.version[12][0])
    return string

def loadConfig():
    def setDefaultString(name, default):
        value = settings.value("manageR/%s" % (name)).toString()
        if value.isEmpty():
            value = default
        Config[name] = value

    settings = QSettings()
    for name in ("window", "console"):
        Config["%swidth" % name] = settings.value("manageR/%swidth" % name,
                QVariant(QApplication.desktop()
                         .availableGeometry().width() / 2)).toInt()[0]
        Config["%sheight" % name] = settings.value("manageR/%sheight" % name,
                QVariant(QApplication.desktop()
                         .availableGeometry().height() / 2)).toInt()[0]
        Config["%sy" % name] = settings.value("manageR/%sy" % name,
                QVariant(0)).toInt()[0]
    Config["toolbars"] = settings.value("manageR/toolbars").toByteArray()
    Config["consolex"] = settings.value("manageR/consolex",
                                      QVariant(0)).toInt()[0]
    Config["windowx"] = settings.value("manageR/windowx",
            QVariant(QApplication.desktop()
                            .availableGeometry().width() / 2)).toInt()[0]
    Config["remembergeometry"] = settings.value("manageR/remembergeometry",
            QVariant(True)).toBool()
    setDefaultString("newfile", "")
    setDefaultString("consolestartup", "")
    Config["backupsuffix"] = settings.value("manageR/backupsuffix",
            QVariant(".bak")).toString()
    Config["beforeinput"] = settings.value("manageR/beforeinput",
            QVariant(">")).toString()
    Config["afteroutput"] = settings.value("manageR/afteroutput",
            QVariant("+")).toString()
    Config["setwd"] = settings.value("manageR/setwd", QVariant(".")).toString()
    Config["findcasesensitive"] = settings.value("manageR/findcasesensitive",
            QVariant(False)).toBool()
    Config["findwholewords"] = settings.value("manageR/findwholewords",
            QVariant(False)).toBool()
    Config["tabwidth"] = settings.value("manageR/tabwidth",
            QVariant(4)).toInt()[0]
    Config["fontfamily"] = settings.value("manageR/fontfamily",
            QVariant("Bitstream Vera Sans Mono")).toString()
    Config["fontsize"] = settings.value("manageR/fontsize",
            QVariant(10)).toInt()[0]
    for name, color, bold, italic in (
            ("normal", "#000000", False, False),
            ("keyword", "#000080", True, False),
            ("builtin", "#0000A0", False, False),
            ("constant", "#0000C0", False, False),
            ("delimiter", "#0000E0", False, False),
            ("comment", "#007F00", False, True),
            ("string", "#808000", False, False),
            ("number", "#924900", False, False),
            ("error", "#FF0000", False, False),
            ("assignment", "#50621A", False, False)):
        Config["%sfontcolor" % name] = settings.value(
                "manageR/%sfontcolor" % name, QVariant(color)).toString()
        Config["%sfontbold" % name] = settings.value(
                "manageR/%sfontbold" % name, QVariant(bold)).toBool()
        Config["%sfontitalic" % name] = settings.value(
                "manageR/%sfontitalic" % name, QVariant(italic)).toBool()
    Config["backgroundcolor"] = settings.value("manageR/backgroundcolor",
            QVariant("#FFFFFF")).toString()
    Config["delay"] = settings.value("manageR/delay",
            QVariant(500)).toInt()[0]
    Config["minimumchars"] = settings.value("manageR/minimumchars",
            QVariant(3)).toInt()[0]
    Config["enablehighlighting"] = settings.value("manageR/enablehighlighting",
            QVariant(True)).toBool()
    Config["enableautocomplete"] = settings.value("manageR/enableautocomplete",
            QVariant(True)).toBool()

def saveConfig():
    settings = QSettings()
    for key, value in Config.items():
        settings.setValue("manageR/%s" % (key), QVariant(value))

def addLibraryCommands(library):
    if not library in Libraries:
        Libraries.append(library)
        info = robjects.r('lsf.str("package:%s")' % (library))
        info = QString(str(info)).replace(", \n    ", ", ")
        items = info.split('\n')
        for item in items:
            CAT.append(item)
            
def isLibraryLoaded(package="sp"):
    return robjects.r("require(%s)" % (package))[0]
    
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
        if not unicode(item) in CAT:
            CAT.append(unicode(item))
    try:
        graphics = dict(zip(list(dev_list_()),
        list(dev_list_().names)))
    except:
        graphics = {}
    cwd = getwd_()[0]
    return (layers, graphics, cwd)

class HelpForm(QDialog):

    def __init__(self, version, parent=None):
        super(HelpForm, self).__init__(parent)
        self.setAttribute(Qt.WA_GroupLeader)
        self.setAttribute(Qt.WA_DeleteOnClose)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(
u"""
<center><h2>manageR %s documentation</h2>
<h3>Interface to the R statistical programming environment</h3>
<h4>Copyright &copy; 2009 Carson J.Q. Farmer
<br/>carson.farmer@gmail.com
<br/><a href='http://www.ftools.ca/manageR'>www.ftools.ca/manageR</a></h4></center>
<h4>Description:</h4>
<b>manageR</b> adds comprehensive statistical capabilities to <b>Quantum GIS</b> by 
loosely coupling <b>QGIS</b> with the R statistical programming environment.
<h4>Features:</h4>
<ul><li>Perform complex statistical analysis functions on raster, vector and spatial database formats</li>
<li>Use the R statistical environment to graph, plot, and map spatial and aspatial data from within <b>QGIS</b></li>
<li>Export R (sp) vector layers directly to <b>QGIS</b> map canvas as <b>QGIS</b> vector layers</li>
<li>Read <b>QGIS</b> vector layers directly from map canvas as R (sp) vector layers, allowing analysis to be carried out on any vector format supported by <b>QGIS</b></li>
<li>Perform all available R commands from within <b>QGIS</b>, including multi-line commands</li>
<li>Visualise R commands clearly and cleanly using any one of the four included syntax highlighting themes</li>
<li>Create, edit, and save R scripts for complex statistical and computational operations</li></ul>
<h4>Usage:</h4>
<ul><li><tt>Ctrl+L</tt> : Import selected <b>l</b>ayer</li>
<li><tt>Ctrl+T</tt> : Import attribute <b>t</b>able of selected layer</li>
<li><tt>Ctrl+M</tt> : Export R layer to <b>m</b>ap canvas</li>
<li><tt>Ctrl+D</tt> : Export R layer to <b>d</b>isk</li>
<li><tt>Ctrl+Return</tt> : Send (selected) commands from <b>EditR</b> window to 
<b>manageR</b> console</li></ul>
<h4>Details:</h4>
<p>
Use <tt>Ctrl+L</tt> to import the currently selected layer in the <b>QGIS</b> 
layer list into the <b>manageR</b> environment. To import only the attribute 
table of the selected layer, use <tt>Ctrl+T</tt>. Exporting R layers 
from the <b>manageR</b> environment is done via <tt>Ctrl-M</tt> and <tt>Ctrl-D</tt>, 
where M signifies exporting to the map canvas, and D signifies exporting to disk. Each 
of these commands are also available via the <b>Actions</b> toolbar in the <b>manageR</b> 
console.
</p>
<p>
The <b>manageR</b> console is also equipped with several additional tools to help manage the R 
environment. These tools include a <b>Workspace</b> manager, a <b>Graphic Devices</b> manager, 
a <b>Command History</b> manager, and a <b>Working Directory</b> manager.
</p>
<p>
Use <tt>Ctrl+R</tt> to send commands from an <b>EditR</b> window to the <b>manageR</b> 
console. If an <b>EditR</b> window contains selected text, only this text will be sent 
to the <b>manageR</b> console, otherwise, all text is sent. The <b>EditR</b> window 
also contains tools for creating, loading, editing, and saving R scripts. The suite of  
available tools is outlined in detail in the <b>Key bindings</b> section.
</p>
<h4>Additional tools:</h4>
<p>
<i>Autocompletion</i><br>
If enabled, command completion suggestions are automatically shown after %d seconds 
based on the current work. This can also be manually activated using <b>Ctrl+Space</b>. 
In addition, a tooltip will appear if one is available for the selected command.
Autocompletion and tooltips are available for R functions and commands within 
libraries that are automatically loaded by R, or <b>manageR</b>, 
as well as any additional libraries loaded after the <b>manageR</b> session has started.
(This makes loading libraries with many built-in functions or additional libraries slightly 
longer than in a normal R session). It is possible to turn off autocompletion (and tooltips) 
by unchecking File\N{RIGHTWARDS ARROW}Configure\N{RIGHTWARDS ARROW}
General tab\N{RIGHTWARDS ARROW}Enable autocompletion.
</p>
<p>
<i>Find and Replace</i><br>
A Find and Replace toolbar is available for both the <b>manageR</b> console and <b>EditR</b> 
window (the replace functionality is only available in <b>EditR</b>). When activated (see 
<b>Key Bindings</b> section below), if any text is selected in the parent dialog, this text 
will be placed in the 'Find toolbar' for searching. To search for 
the next occurrence of the text or phrase in the toolbar, type <tt>Enter</tt> 
or click the 'Next' button. Conversely, click the 'Previous' button to search backwards. To 
replace text as it is found, simply type the replacement text in the 'Replace' line edit and  
click 'Replace'. To replace all occurrences of the found text, click 'Replace all'. All 
searches can be refined by using the 'Case sensitive' and 'Whole words' check boxes.
</p>
<p>
<i>Workspace Manager</i></i><br>
The variables table stores the name and type of all currently loaded variables in your global 
R environment (globalEnv). From here, it is possible to remove, save, and load R variables, as 
well as export R variables to file, or the <b>QGIS</b> map canvas (when a Spatial*Data Frames is selected).
</p>
<p>
<i>Graphic Device Manager</i><br>
The graphic devices table stores the ID and device type of all current R graphic devices. From here, 
it is possible to refresh the list of graphic devices, create a new empty graphic window, and remove 
existing devices. In addition, it is possible to export the selected graphic device to file in both raster 
and vector formats.
</p>
<p>
<i>Command History Manager</i><br>
The command history stores a list of all previously executed commands (including commands loaded from a 
.RHistory file). From here it is possible to insert a command into the <b>manageR</b> console by 
right clicking and selecting 'insert' in the popup menu. Similarly, multiple commands can be selected, 
copied, or cleared using the popup menu. Individual commands can be selected or unselected simply by 
clicking on them using the left mouse button. To run all selected commands, right click anywhere within 
the command history widget, and select run from the popup menu. Each of these actions are also available 
via the icons at the top of the command history widget.
</p>
<p>
<i>Working Directory Manager</i><br>
The working directory widget is a simple toolbar to help browse to different working directories, making it 
relatively simple to change the current R working directory.
</p>
<p>
<i>Startup and New Script Commands</i><br>
Additional tools include the ability to specify startup commands to be run whenever <b>manageR</b> 
is started (see File\N{RIGHTWARDS ARROW}Configure\N{RIGHTWARDS ARROW}At Startup), 
as well as a tab to specify the text/commands to be included at the top of all new R scripts (see 
File\N{RIGHTWARDS ARROW}Configure\N{RIGHTWARDS ARROW}On New File).
</p>
<p>
<i>Analysis</i><br>
<b>manageR</b> supports simple plugins which help to streamline tedious R functions by providing a 
plugin framework for creating simple graphical user interfaces (GUI) to commonly used R functions. 
These functions can be specified using an XML ('tools.xml') file stored in the <b>manageR</b> 
installation folder (%s). The format of the XML file should be as follows:
<font color=green><i>
<pre>&lt;?xml version="1.0"?&gt;
&lt;manageRTools&gt;
  &lt;RTool name="Insert random R commands" query="|1|"&gt;
    &lt;Parameter label="R commands:" type="textEdit" default="ls()" notnull="true"/&gt;
  &lt;/RTool&gt;
&lt;manageRTools&gt;</i></font>
</pre>
where each RTool specifies a unique R function. In the above example, the GUI will consist of a simple 
dialog with a text editing region to input user-defined R commands, and an OK and CANCEL button. When 
OK is clicked, the R commands in the text editing region will be run, and when CANCEL is clicked, 
the dialog will be closed. In the example above, query is set to <tt>|1|</tt>, which means take the 
output from the first parameter, and place here. In other words, in this case the entire query is 
equal to whatever is input into the text editing region (default here is <tt>ls()</tt>). Other GUI 
parameters that may be entered include:
<ul>
<li>comboBox: Drop-down list box</li>
<li>doubleSpinBox: Widget for entering numerical values</li>
<li>textEdit: Text editing region</li>
<li>spComboBox: comboBox containing only the specified Spatial*DataFrame types</li>
<li>helpString: A non-graphical parameter that is linked to the help button on the dialog</li>
</ul>
Default values for all of the above GUI parameters can be specified in the XML file, using semi-colons 
to separate multiple options. For the spComboBox, the default string should specify the type(s) of 
Spatial*DataFrame to display (e.g. SpatialPointsDataFrame;SpatialLinesDataFrame).
<b>manageR</b> comes with several default R GUI functions which can be used as examples for creating
custom R GUI functions.
</p>
<h4>Key bindings:</h4>
<ul>
<li><tt>\N{UPWARDS ARROW}</tt> : In the <b>manageR</b> console, show the previous command
from the command history. In the <b>EditR</b> windows, move up one line.
<li><tt>\N{DOWNWARDS ARROW}</tt> : In the <b>manageR</b> console, show the next command
from the command history. In the <b>EditR</b> windows, move down one line.
<li><tt>\N{LEFTWARDS ARROW}</tt> : Move the cursor left one character
<li><tt>Ctrl+\N{LEFTWARDS ARROW}</tt> : Move the cursor left one word
<li><tt>\N{RIGHTWARDS ARROW}</tt> : Move the cursor right one character
<li><tt>Ctrl+\N{RIGHTWARDS ARROW}</tt> : Move the cursor right one word
<li><tt>Ctrl+]</tt> : Indent the selected text (or the current line) by %d spaces
<li><tt>Ctrl+[</tt> : Unindent the selected text (or the current line) by %d spaces
<li><tt>Ctrl+A</tt> : Select all the text
<li><tt>Backspace</tt> : Delete the character to the left of the cursor
<li><tt>Ctrl+C</tt> : In the <b>manageR</b> console, if the cursor is in the command line, clear
current command(s), otherwise copy the selected text to the clipboard (same for <b>EditR</b> 
windows.
<li><tt>Delete</tt> : Delete the character to the right of the cursor
<li><tt>End</tt> : Move the cursor to the end of the line
<li><tt>Ctrl+End</tt> : Move the cursor to the end of the file
<li><tt>Ctrl+Return</tt> : In an <b>EditR</b> window, execute the (selected) code/text
<li><tt>Ctrl+F</tt> : Pop up the Find toolbar
<li><tt>Ctrl+R</tt> : In an <b>EditR</b> window, pop up the Find and Replace toolbar
<li><tt>Home</tt> : Move the cursor to the beginning of the line
<li><tt>Ctrl+Home</tt> : Move the cursor to the beginning of the file
<li><tt>Ctrl+K</tt> : Delete to the end of the line
<li><tt>Ctrl+H</tt> : Pop up the 'Goto line' dialog
<li><tt>Ctrl+N</tt> : Open a new editor window
<li><tt>Ctrl+O</tt> : Open a file open dialog to open an R script
<li><tt>Ctrl+Space</tt> : Pop up a list of possible completions for
the current word. Use the up and down arrow keys and the page up and page
up keys (or the mouse) to navigate; click <tt>Enter</tt> to accept a
completion or <tt>Esc</tt> to cancel.
<li><tt>PageUp</tt> : Move up one screen
<li><tt>PageDown</tt> : Move down one screen
<li><tt>Ctrl+Q</tt> : Terminate manageR; prompting to save any unsaved changes
for every <b>EditR</b> window for which this is necessary. If the user cancels
any save unsaved changes message box, manageR will not terminate.
<li><tt>Ctrl+S</tt> : Save the current file
<li><tt>Ctrl+V</tt> : Paste the clipboard's text
<li><tt>Ctrl+W</tt> : Close the current file; prompting to save any unsaved
changes if necessary
<li><tt>Ctrl+X</tt> : Cut the selected text to the clipboard
<li><tt>Ctrl+Z</tt> : Undo the last editing action
<li><tt>Ctrl+Shift+Z</tt> : Redo the last editing action
<li><tt>Ctrl+L</tt> : Import selected <b>l</b>ayer</li>
<li><tt>Ctrl+T</tt> : Import attribute <b>t</b>able of selected layer</li>
<li><tt>Ctrl+M</tt> : Export R layer to <b>m</b>ap canvas</li>
<li><tt>Ctrl+D</tt> : Export R layer to <b>d</b>isk</li>
<li><tt>Ctrl+Return</tt> : Send (selected) commands from <b>EditR</b> window to 
<b>manageR</b> console</li>
</ul>
Hold down <tt>Shift</tt> when pressing movement keys to select the text moved over.
<br>
Thanks to Agustin Lobo for extensive testing and bug reporting.
Press <tt>Esc</tt> to close this window.
""" % (version, Config["delay"], str(os.path.dirname( __file__ )),
      Config["tabwidth"], Config["tabwidth"]))
        layout = QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(browser)
        self.setLayout(layout)
        self.resize(500, 500)
        QShortcut(QKeySequence("Escape"), self, self.close)
        self.setWindowTitle("manageR - Help")

def RLibraryError(library):
    message = QString("Error: Unable to find R package '%s'.\n" % (library))
    message.append("Please manually install the '%s' package in R via " % (library))
    message.append("install.packages()")
    return message

class RFinder(QWidget):

    def __init__(self, parent, document):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.document = document
        grid = QGridLayout(self)
        self.edit = QLineEdit(self)
        font = QFont(Config["fontfamily"], Config["fontsize"])
        font.setFixedPitch(True)
        find_label = QLabel("Find:")
        find_label.setMaximumWidth(50)
        self.edit.setFont(font)
        self.edit.setToolTip("Find text")
        self.next = QToolButton(self)
        self.next.setText("Next")
        self.next.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.next.setIcon(QIcon(":mActionNext.png"))
        self.next.setToolTip("Find next")
        self.previous = QToolButton(self)
        self.previous.setToolTip("Find previous")
        self.previous.setText("Previous")
        self.previous.setIcon(QIcon(":mActionPrevious.png"))
        self.previous.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.whole_words = QCheckBox()
        self.whole_words.setText("Whole words")
        self.case_sensitive = QCheckBox()
        self.case_sensitive.setText("Case sensitive")
        #find_horiz = QHBoxLayout()
        grid.addWidget(find_label,1,0,1,1)
        #find_horiz.addWidget(find_label)
        grid.addWidget(self.edit, 1,1,1,2)
        #find_horiz.addWidget(self.edit)
        grid.addWidget(self.next, 1,3,1,1)
        #find_horiz.addWidget(self.previous)
        grid.addWidget(self.previous, 1,4,1,1)
        #find_horiz.addWidget(self.next)
        grid.addWidget(self.whole_words, 0,3,1,1)
        grid.addWidget(self.case_sensitive, 0,4,1,1)
        #grid.addLayout(find_horiz, 1, 0, 1, 3)
        self.replace_label = QLabel("Replace:")
        self.replace_label.setMaximumWidth(50)
        self.replace_edit = QLineEdit(self)
        self.replace_edit.setFont(font)
        self.replace_edit.setToolTip("Replace text")
        self.replace = QToolButton(self)
        self.replace.setText("Replace")
        self.replace.setToolTip("Replace text")
        self.replace_all = QToolButton(self)
        self.replace_all.setToolTip("Replace all")
        self.replace_all.setText("Replace all")
        #replace_horiz = QHBoxLayout()
        grid.addWidget(self.replace_label, 2, 0, 1, 1)
        #replace_horiz.addWidget(self.replace_label)
        grid.addWidget(self.replace_edit, 2, 1, 1, 2)
        #replace_horiz.addWidget(self.replace_edit)
        grid.addWidget(self.replace, 2, 3, 1, 1)
        #replace_horiz.addWidget(self.replace)
        grid.addWidget(self.replace_all, 2, 4, 1, 1)
        #replace_horiz.addWidget(self.replace_all)
        #grid.addLayout(replace_horiz, 2, 0, 1, 3)
        self.setFocusProxy(self.edit)
        self.setVisible(False)
        
        self.connect(self.next, SIGNAL("clicked()"), self.findNext)
        self.connect(self.previous, SIGNAL("clicked()"), self.findPrevious)
        self.connect(self.replace, SIGNAL("clicked()"), self.replaceNext)
        self.connect(self.edit, SIGNAL("returnPressed()"), self.findNext)
        self.connect(self.replace_all, SIGNAL("clicked()"), self.replaceAll)
    
    def find(self, forward):
        if not self.document:
            return False
        text = QString(self.edit.text())
        found = False
        if text == "":
            return False
        else:
            flags = QTextDocument.FindFlag()
            if self.whole_words.isChecked():
                flags = (flags|QTextDocument.FindWholeWords)
            if self.case_sensitive.isChecked():
                flags = (flags|QTextDocument.FindCaseSensitively)
            if not forward:
                flags = (flags|QTextDocument.FindBackward)
                fromPos = self.document.toPlainText().length() - 1
            else:
                fromPos = 0
            if not self.document.find(text, flags):
                cursor = QTextCursor(self.document.textCursor())
                selection = cursor.hasSelection()
                if selection:
                    start = cursor.selectionStart()
                    end = cursor.selectionEnd()
                else:
                    pos = cursor.position()
                cursor.setPosition(fromPos)
                self.document.setTextCursor(cursor)
                if not self.document.find(text, flags):
                    if selection:
                        cursor.setPosition(start, QTextCursor.MoveAnchor)
                        cursor.setPosition(end, QTextCursor.KeepAnchor)
                    else:
                        cursor.setPosition(pos)
                    self.document.setTextCursor(cursor)
                    return False
                elif selection:
                    cursor = QTextCursor(self.document.textCursor())
                    if start == cursor.selectionStart():
                        return False
        return True
          
    def findNext(self):
        return self.find(True)
      
    def findPrevious(self):
        return self.find(False)
          
    def showReplace(self):
        self.replace_edit.setVisible(True)
        self.replace.setVisible(True)
        self.replace_all.setVisible(True)
        self.replace_label.setVisible(True)

    def hideReplace(self):
        self.replace_edit.setVisible(False)
        self.replace.setVisible(False)
        self.replace_all.setVisible(False)
        self.replace_label.setVisible(False)

    def replaceNext(self):
        cursor = QTextCursor(self.document.textCursor())
        selection = cursor.hasSelection()
        if selection:
            text = QString(cursor.selectedText())
            current = QString(self.edit.text())
            replace = QString(self.replace_edit.text())
            if text == current:
                cursor.insertText(replace)
                cursor.select(QTextCursor.WordUnderCursor)
        else:
            return self.findNext()
        self.findNext()
        return True

    def replaceAll(self):
        while self.findNext():
            self.replaceNext()
        self.replaceNext()
        
    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape:
            self.document.setFocus()


class RHighlighter(QSyntaxHighlighter):

    Rules = []
    Formats = {}

    def __init__(self, parent=None, isConsole=False):
        super(RHighlighter, self).__init__(parent)
        self.parent = parent
        self.initializeFormats()
        self.isConsole = isConsole
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % keyword for keyword in KEYWORDS])),
                "keyword"))
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % builtin for builtin in BUILTINS])),
                "builtin"))
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % constant
                for constant in CONSTANTS])), "constant"))
        RHighlighter.Rules.append((QRegExp(
                r"\b[+-]?[0-9]+[lL]?\b"
                r"|\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b"
                r"|\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"),
                "number"))
        RHighlighter.Rules.append((QRegExp(
                r"(<){1,2}-"), "assignment"))
        RHighlighter.Rules.append((QRegExp(r"[\)\(]+|[\{\}]+|[][]+"),
                "delimiter"))
        RHighlighter.Rules.append((QRegExp(r"#.*"), "comment"))
        self.stringRe = QRegExp("(\'[^\']*\'|\"[^\"]*\")")
        self.stringRe.setMinimal(True)
        RHighlighter.Rules.append((self.stringRe, "string"))
        self.multilineSingleStringRe = QRegExp(r"""'(?!")""")
        self.multilineDoubleStringRe = QRegExp(r'''"(?!')''')

    @staticmethod
    def initializeFormats():
        baseFormat = QTextCharFormat()
        baseFormat.setFontFamily(Config["fontfamily"])
        baseFormat.setFontPointSize(Config["fontsize"])
        for name in ("normal", "keyword", "builtin", "constant",
                "delimiter", "comment", "string", "number", "error",
                "assignment"):
            format = QTextCharFormat(baseFormat)
            format.setForeground(
                            QColor(Config["%sfontcolor" % name]))
            if Config["%sfontbold" % name]:
                format.setFontWeight(QFont.Bold)
            format.setFontItalic(Config["%sfontitalic" % name])
            RHighlighter.Formats[name] = format

    def highlightBlock(self, text):
        NORMAL, MULTILINESINGLE, MULTILINEDOUBLE, ERROR = range(4)

        textLength = text.length()
        prevState = self.previousBlockState()

        self.setFormat(0, textLength,
                       RHighlighter.Formats["normal"])

        if text.startsWith("Error") and self.isConsole:
            self.setCurrentBlockState(ERROR)
            self.setFormat(0, textLength, RHighlighter.Formats["error"])
            return
        if (prevState == ERROR and self.isConsole and \
            not (text.startsWith(Config["beforeinput"]) or text.startsWith("#"))):
            self.setCurrentBlockState(ERROR)
            self.setFormat(0, textLength, RHighlighter.Formats["error"])
            return

        for regex, format in RHighlighter.Rules:
            i = regex.indexIn(text)
            while i >= 0:
                length = regex.matchedLength()
                self.setFormat(i, length, RHighlighter.Formats[format])
                i = regex.indexIn(text, i + length)
            
        self.setCurrentBlockState(NORMAL)

        if text.indexOf(self.stringRe) != -1:
            return
        for i, state in ((text.indexOf(self.multilineSingleStringRe),
                          MULTILINESINGLE),
                         (text.indexOf(self.multilineDoubleStringRe),
                          MULTILINEDOUBLE)):
            if self.previousBlockState() == state:
                if i == -1:
                    i = text.length()
                    self.setCurrentBlockState(state)
                if text.startsWith(Config["afteroutput"]) and self.isConsole:
                    self.setFormat(self.parent.currentPromptLength, i + 1,
                    RHighlighter.Formats["string"])
                else:
                    self.setFormat(0, i + 1, RHighlighter.Formats["string"])
            elif i > -1:
                self.setCurrentBlockState(state)
                self.setFormat(i, text.length(), RHighlighter.Formats["string"])

    def rehighlight(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        QSyntaxHighlighter.rehighlight(self)
        QApplication.restoreOverrideCursor()       

class RCompleter(QObject):

    def __init__(self, parent, delay=500):
        QObject.__init__(self, parent)
        self.editor = parent
        self.popup = QTreeWidget()
        self.popup.setColumnCount(1)
        self.popup.setUniformRowHeights(True)
        self.popup.setRootIsDecorated(False)
        self.popup.setEditTriggers(QTreeWidget.NoEditTriggers)
        self.popup.setSelectionBehavior(QTreeWidget.SelectRows)
        self.popup.setFrameStyle(QFrame.Box|QFrame.Plain)
        self.popup.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.popup.header().hide()
        self.popup.installEventFilter(self)
        self.popup.setMouseTracking(True)
        self.connect(self.popup,\
        SIGNAL("itemClicked(QTreeWidgetItem*, int)"),\
        self.doneCompletion)
        self.popup.setWindowFlags(Qt.Popup)
        self.popup.setFocusPolicy(Qt.NoFocus)
        self.popup.setFocusProxy(self.editor)
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        if isinstance(delay,int):
            self.timer.setInterval(delay)
        else:
            self.timer.setInterval(500)
        self.connect(self.timer, SIGNAL("timeout()"), self.suggest, Config["minimumchars"])
        self.connect(self.editor, SIGNAL("textChanged()"), self.startTimer)

    def startTimer(self):
        self.timer.start()

    def eventFilter(self, obj, ev):
        if not obj == self.popup:
            return False
        if ev.type() == QEvent.MouseButtonPress:
            self.popup.hide()
            self.editor.setFocus()
            return True
        if ev.type() == QEvent.KeyPress:
            consumed = False
            key = ev.key()
            if key == Qt.Key_Enter or \
            key == Qt.Key_Return:
                self.doneCompletion()
                consumed = True
            elif key == Qt.Key_Escape:
                self.editor.setFocus()
                self.popup.hide()
                consumed = True
            elif key == Qt.Key_Up or \
            key == Qt.Key_Down or \
            key == Qt.Key_Home or \
            key == Qt.Key_End or \
            key == Qt.Key_PageUp or \
            key == Qt.Key_PageDown:
                pass
            else:
                self.editor.setFocus()
                self.editor.event(ev)
                self.popup.hide()
            return consumed
        return False

    def showCompletion(self, choices):
        if choices.isEmpty():
            return

        pal = self.editor.palette()
        color = pal.color(QPalette.Disabled, 
                          QPalette.WindowText)
        self.popup.setUpdatesEnabled(False)
        self.popup.clear()
        for i in choices:
            item = QTreeWidgetItem(self.popup)
            item.setText(0, i.split(":")[0].simplified())
            try:
                item.setData(0, Qt.StatusTipRole, 
                QVariant(i.split(":")[1].simplified()))
            except:
                pass
        self.popup.setCurrentItem(self.popup.topLevelItem(0))
        self.popup.resizeColumnToContents(0)
        self.popup.adjustSize()
        self.popup.setUpdatesEnabled(True)

        h = self.popup.sizeHintForRow(0) * min([7, choices.count()]) + 3
        self.popup.resize(self.popup.width(), h)

        self.popup.move(self.editor.mapToGlobal(self.editor.cursorRect().bottomRight()))
        self.popup.setFocus()
        self.popup.show()

    def doneCompletion(self):
        self.timer.stop()
        self.popup.hide()
        self.editor.setFocus()
        item = self.popup.currentItem()
        self.editor.parent.statusBar().showMessage(
        item.data(0, Qt.StatusTipRole).toString().\
        replace("function", item.text(0)))
        # TODO: Figure out if it's possible the word wrap the statusBar
        if item:
            self.replaceCurrentWord(item.text(0))
            self.preventSuggest()

    def preventSuggest(self):
        self.timer.stop()

    def suggest(self,minchars=3):
        text = self.getCurrentWord()
        if text.contains(QRegExp("\\b.{%d,}" % (minchars))):
            self.showCompletion(CAT.filter(QRegExp("^%s" % (text))))
        
    def getCurrentWord(self):
        textCursor = self.editor.textCursor()
        textCursor.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        currentWord = textCursor.selectedText()
        textCursor.setPosition(textCursor.anchor(), QTextCursor.MoveAnchor)
        return currentWord
        
    def replaceCurrentWord(self, word):
        textCursor = self.editor.textCursor()
        textCursor.movePosition(QTextCursor.StartOfWord, QTextCursor.KeepAnchor)
        textCursor.insertText(word)


class REditor(QTextEdit):
    def __init__(self, parent, tabwidth=4):
        super(REditor, self).__init__(parent)
        self.setLineWrapMode(QTextEdit.NoWrap)
        self.indent = 0
        self.tabwidth = tabwidth
        self.parent = parent
        self.oldfrmt = QTextCharFormat()
        self.oldpos = None
        self.connect(self, SIGNAL("cursorPositionChanged()"),
        self.positionChanged)

    def event(self, event):
        indent = " " * self.tabwidth
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Tab:
                if not self.tabChangesFocus():
                    cursor = self.textCursor()
                    if not cursor.hasSelection():
                        cursor.insertText(indent)
                    else:
                        self.indentRegion()
                    return True
                # else leave for base class to handle
            elif event.key() in (Qt.Key_Enter,
                                 Qt.Key_Return):
                userCursor = self.textCursor()
                cursor = QTextCursor(userCursor)
                cursor.movePosition(QTextCursor.End)
                insert = "\n"
                cursor = QTextCursor(userCursor)
                cursor.movePosition(QTextCursor.StartOfLine)
                cursor.movePosition(QTextCursor.EndOfLine,
                                    QTextCursor.KeepAnchor)
                line = cursor.selectedText()
                if line.startsWith(indent):
                    for c in line:
                        if c == " ":
                            insert += " "
                        else:
                            break
                userCursor.insertText(insert)
                return True
                # Fall through to let the base class handle the movement
        return QTextEdit.event(self, event)
        
    def positionChanged(self):
        self.highlight()

    def gotoLine(self):
        cursor = self.textCursor()
        lino, ok = QInputDialog.getInteger(self,
                            "editR - Goto line",
                            "Goto line:", cursor.blockNumber() + 1,
                            1, self.document().blockCount())
        if ok:
            cursor.movePosition(QTextCursor.Start)
            cursor.movePosition(QTextCursor.Down,
                    QTextCursor.MoveAnchor, lino - 1)
            self.setTextCursor(cursor)
            self.ensureCursorVisible()

    def highlight(self):
        extraSelections = []
        self.setExtraSelections(extraSelections)
        format = QTextCharFormat()
        format.setBackground(QColor(Config["backgroundcolor"]).darker(110))
        format.setProperty(QTextFormat.FullWidthSelection, QVariant(True))
        selection = QTextEdit.ExtraSelection()
        selection.format = format
        cursor = self.textCursor()
        selection.cursor = cursor
        selection.cursor.clearSelection()
        extraSelections.append(selection)
        self.setExtraSelections(extraSelections)
        
        format = QTextCharFormat()
        format.setForeground(QColor(Config["delimiterfontcolor"]))
        format.setBackground(QColor(Qt.yellow).lighter(160)) #QColor(Config["bracketcolor"])?
        selection = QTextEdit.ExtraSelection()
        selection.format = format

        doc = self.document()
        cursor = self.textCursor()
        beforeCursor = QTextCursor(cursor)

        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        brace = cursor.selectedText()

        beforeCursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
        beforeBrace = beforeCursor.selectedText()

        if ((brace != "{") and \
            (brace != "}") and \
            (brace != "[") and \
            (brace != "]") and \
            (brace != "(") and \
            (brace != ")")):
            if ((beforeBrace == "{") or \
                (beforeBrace == "}") or \
                (beforeBrace == "[") or \
                (beforeBrace == "]") or \
                (beforeBrace == "(") or \
                (beforeBrace == ")")):
                cursor = beforeCursor
                brace = cursor.selectedText();
            else:
                return

        #format = QTextCharFormat()
        #format.setForeground(Qt.red)
        #format.setFontWeight(QFont.Bold)

        if ((brace == "{") or (brace == "}")):
            openBrace = "{"
            closeBrace = "}"
        elif ((brace == "[") or (brace == "]")):
            openBrace = "["
            closeBrace = "]"
        elif ((brace == "(") or (brace == ")")):
            openBrace = "("
            closeBrace = ")"
            
        if (brace == openBrace):
            cursor1 = doc.find(closeBrace, cursor)
            cursor2 = doc.find(openBrace, cursor)
            if (cursor2.isNull()):
                selection.cursor = cursor
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
                selection.cursor = cursor1
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
            else:
                while (cursor1.position() > cursor2.position()):
                    cursor1 = doc.find(closeBrace, cursor1)
                    cursor2 = doc.find(openBrace, cursor2)
                    if (cursor2.isNull()):
                        break
                selection.cursor = cursor
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
                selection.cursor = cursor1
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
        else:
            if (brace == closeBrace):
                cursor1 = doc.find(openBrace, cursor, QTextDocument.FindBackward)
                cursor2 = doc.find(closeBrace, cursor, QTextDocument.FindBackward)
                if (cursor2.isNull()):
                    selection.cursor = cursor
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                    selection.cursor = cursor1
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                else:
                    while (cursor1.position() < cursor2.position()):
                        cursor1 = doc.find(openBrace, cursor1, QTextDocument.FindBackward)
                        cursor2 = doc.find(closeBrace, cursor2, QTextDocument.FindBackward)
                        if (cursor2.isNull()):
                            break
                    selection.cursor = cursor
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                    selection.cursor = cursor1
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)

    def execute(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            commands = cursor.selectedText().replace(u"\u2029", "\n")
        else:
            commands = self.toPlainText()
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            MainWindow.Console.editor.moveToEnd()
            MainWindow.Console.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            MainWindow.Console.editor.cursor.removeSelectedText()
            MainWindow.Console.editor.cursor.insertText(
            MainWindow.Console.editor.currentPrompt)
            MainWindow.Console.editor.insertFromMimeData(mime)
            MainWindow.Console.editor.entered()

    def indentRegion(self):
        self._walkTheLines(True, " " * self.tabwidth)

    def unindentRegion(self):
        self._walkTheLines(False, " " * self.tabwidth)

    def commentRegion(self):
        self._walkTheLines(True, "# ")

    def uncommentRegion(self):
        self._walkTheLines(False, "# ")

    def _walkTheLines(self, insert, text):
        userCursor = self.textCursor()
        userCursor.beginEditBlock()
        start = userCursor.position()
        end = userCursor.anchor()
        if start > end:
            start, end = end, start
        block = self.document().findBlock(start)
        while block.isValid():
            cursor = QTextCursor(block)
            cursor.movePosition(QTextCursor.StartOfBlock)
            if insert:
                cursor.clearSelection()
                cursor.insertText(text)
            else:
                cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor, len(text))
                if cursor.selectedText() == text:
                    cursor.removeSelectedText()
            block = block.next()
            if block.position() > end:
                break
        userCursor.endEditBlock()

class RConsole(QTextEdit):
    def __init__(self, parent):
        super(RConsole, self).__init__(parent)
        # initialise standard settings
        self.setTextInteractionFlags(Qt.TextEditorInteraction)
        self.setAcceptDrops(False)
        self.setMinimumSize(30, 30)
        self.parent = parent
        self.setUndoRedoEnabled(False)
        self.setAcceptRichText(False)
        monofont = QFont(Config["fontfamily"], Config["fontsize"])
        self.setFont(monofont)
        # initialise required variables
        self.history = QStringList()
        self.historyIndex = 0
        self.runningCommand = QString()
        # prepare prompt
        self.reset()
        self.setPrompt(Config["beforeinput"]+" ", Config["afteroutput"]+" ")
        self.cursor = self.textCursor()
        self.connect(self, SIGNAL("cursorPositionChanged()"),
        self.positionChanged)

    def loadRHistory(self):
        success = True
        try:
            fileInfo = QFileInfo()
            fileInfo.setFile(QDir(robjects.r['getwd']()[0]), ".Rhistory")
            fileFile = QFile(fileInfo.absoluteFilePath())
            if not fileFile.open(QIODevice.ReadOnly):
                return False
            inFile = QTextStream(fileFile)
            while not inFile.atEnd():
                line = QString(inFile.readLine())
                self.updateHistory(line)
        except:
            success = False
        return success
      
    def saveRHistory(self):
        success = True
        try:
            fileInfo = QFileInfo()
            fileInfo.setFile(QDir(robjects.r['getwd']()[0]), ".Rhistory")
            outFile = open(fileInfo.filePath(), "w")
            for line in self.history:
                outFile.write(line+"\n")
            outFile.flush()
        except:
            success = False
        return success

    def reset(self):
        # clear all contents
        self.clear()
        # init attributes
        self.runningCommand.clear()
        self.historyIndex = 0
        self.history.clear()

    def setPrompt(self, newPrompt = "> ", 
        alternatePrompt = "+ ", display = False):
        self.defaultPrompt = newPrompt
        self.alternatePrompt = alternatePrompt
        self.currentPrompt = self.defaultPrompt
        self.currentPromptLength = len(self.currentPrompt)
        if display:
            self.displayPrompt()

    def switchPrompt(self, default = True):
        if default:
            self.currentPrompt = self.defaultPrompt
        else:
            self.currentPrompt = self.alternatePrompt
        self.currentPromptLength = len(self.currentPrompt)

    def displayPrompt(self):
        self.runningCommand.clear()
        self.append(self.currentPrompt)
        self.moveCursor(QTextCursor.End, QTextCursor.MoveAnchor)

    def positionChanged(self):
        self.highlight()

    def keyPressEvent(self, e):
        self.cursor = self.textCursor()
        # if the cursor isn't in the edition zone, don't do anything except Ctrl+C
        if not self.isCursorInEditionZone():
            if e.modifiers() == Qt.ControlModifier or \
                e.modifiers() == Qt.MetaModifier:
                if e.key() == Qt.Key_C or e.key() == Qt.Key_A:
                    QTextEdit.keyPressEvent(self, e)
            else:
                # all other keystrokes get sent to the input line
                self.cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        else:
            # if Ctrl + C is pressed, then undo the current command
            if e.key() == Qt.Key_C and (e.modifiers() == Qt.ControlModifier or \
                e.modifiers() == Qt.MetaModifier) and not self.cursor.hasSelection():
                self.runningCommand.clear()
                self.switchPrompt(True)
                self.displayPrompt()
                MainWindow.Console.statusBar().clearMessage()
            elif e.key() == Qt.Key_Tab:
                indent = " " * int(Config["tabwidth"])
                self.cursor.insertText(indent)
              # if Return is pressed, then perform the commands
            elif e.key() == Qt.Key_Return:
                self.entered()
              # if Up or Down is pressed
            elif e.key() == Qt.Key_Down:
                self.showPrevious()
            elif e.key() == Qt.Key_Up:
                self.showNext()
              # if backspace is pressed, delete until we get to the prompt
            elif e.key() == Qt.Key_Backspace:
                if not self.cursor.hasSelection() and \
                    self.cursor.columnNumber() == self.currentPromptLength:
                    return
                QTextEdit.keyPressEvent(self, e)
              # if the left key is pressed, move left until we get to the prompt
            elif e.key() == Qt.Key_Left and \
                self.cursor.position() > self.document().lastBlock().position() + \
                self.currentPromptLength:
                if e.modifiers() == Qt.ShiftModifier:
                    anchor = QTextCursor.KeepAnchor
                else:
                    anchor = QTextCursor.MoveAnchor
                if (e.modifiers() == Qt.ControlModifier or \
                e.modifiers() == Qt.MetaModifier):
                    self.cursor.movePosition(QTextCursor.WordLeft, anchor)
                else:
                    self.cursor.movePosition(QTextCursor.Left, anchor)
              # use normal operation for right key
            elif e.key() == Qt.Key_Right:
                if e.modifiers() == Qt.ShiftModifier:
                    anchor = QTextCursor.KeepAnchor
                else:
                    anchor = QTextCursor.MoveAnchor
                if (e.modifiers() == Qt.ControlModifier or \
                e.modifiers() == Qt.MetaModifier):
                    self.cursor.movePosition(QTextCursor.WordRight, anchor)
                else:
                    self.cursor.movePosition(QTextCursor.Right, anchor)
              # if home is pressed, move cursor to right of prompt
            elif e.key() == Qt.Key_Home:
                if e.modifiers() == Qt.ShiftModifier:
                    anchor = QTextCursor.KeepAnchor
                else:
                    anchor = QTextCursor.MoveAnchor
                self.cursor.movePosition(QTextCursor.StartOfBlock, anchor, 1)
                self.cursor.movePosition(QTextCursor.Right, anchor, self.currentPromptLength)
              # use normal operation for end key
            elif e.key() == Qt.Key_End:
                if e.modifiers() == Qt.ShiftModifier:
                    anchor = QTextCursor.KeepAnchor
                else:
                    anchor = QTextCursor.MoveAnchor
                self.cursor.movePosition(
                QTextCursor.EndOfBlock, anchor, 1)
                # use normal operation for all remaining keys
            else:
                QTextEdit.keyPressEvent(self, e)
        self.setTextCursor(self.cursor)
        self.ensureCursorVisible()
        
    def entered(self):
        command = self.currentCommand()
        check = self.runningCommand.split("\n").last()
        if not self.runningCommand.isEmpty():
            if not command == check:
                self.runningCommand.append(command)
                self.updateHistory(command)
        else:
            if not command.isEmpty():
                self.runningCommand = command
                self.updateHistory(command)
            else:
                self.switchPrompt(True)
                self.displayPrompt()
        if not self.checkBrackets(self.runningCommand):
            self.switchPrompt(False)
            self.cursor.insertText("\n" + self.currentPrompt)
            self.runningCommand.append("\n")
        else:
            if not self.runningCommand.isEmpty():
                command=self.runningCommand
            self.execute(command)
            self.runningCommand.clear()
            self.switchPrompt(True)
        #self.displayPrompt()
        self.cursor.movePosition(QTextCursor.End, 
        QTextCursor.MoveAnchor)
        self.moveToEnd()

    def showPrevious(self):
        if self.historyIndex < len(self.history) and not self.history.isEmpty():
            self.cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.MoveAnchor)
            self.cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            self.cursor.removeSelectedText()
            self.cursor.insertText(self.currentPrompt)
            self.historyIndex += 1
            if self.historyIndex == len(self.history):
                self.insertPlainText("")
            else:
                self.insertPlainText(self.history[self.historyIndex])

    def showNext(self):
        if  self.historyIndex > 0 and not self.history.isEmpty():
            self.cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.MoveAnchor)
            self.cursor.movePosition(QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            self.cursor.removeSelectedText()
            self.cursor.insertText(self.currentPrompt)
            self.historyIndex -= 1
            if self.historyIndex == len(self.history):
                self.insertPlainText("")
            else:
                self.insertPlainText(self.history[self.historyIndex])


    def checkBrackets(self, command):
        s = str(command)
        s = filter(lambda x: x in '()[]{}"\'', s)
        s = s.replace ("'''", "'")
        s = s.replace ('"""', '"')
        instring = False
        brackets = {'(':')', '[':']', '{':'}', '"':'"', '\'':'\''}
        stack = []
        
        while len(s):
            if not instring:
                if s[0] in ')]}':
                    if stack and brackets[stack[-1]]==s[0]:
                        del stack[-1]
                    else:
                        return False
                elif s[0] in '"\'':
                    if stack and brackets[stack[-1]]==s[0]:
                        del stack[-1]
                        instring = False
                    else:
                        stack.append(s[0])
                        instring = True
                else:
                    stack.append(s[0])
            else:
                if s[0] in '"\'' and stack and brackets[stack[-1]] == s[0]:
                    del stack[-1]
                    instring = False
            s = s[1:]
        return len(stack)==0

    def mousePressEvent(self, e):
        self.cursor = self.textCursor()
        if e.button() == Qt.LeftButton:
            QTextEdit.mousePressEvent(self, e)
        elif (not self.isCursorInEditionZone() or \
            (self.isCursorInEditionZone() and \
            not self.isAnchorInEditionZone())) and \
            e.button() == Qt.RightButton:
            QTextEdit.mousePressEvent(self, e)
            menu = self.createStandardContextMenu()
            actions = menu.actions()
            keep = [3,6,12]
            count = 0
            for action in keep:
                menu.removeAction(actions[action])
            menu.exec_(e.globalPos())
        else:
            QTextEdit.mousePressEvent(self, e)
        
    def moveToEnd(self):
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End, 
        QTextCursor.MoveAnchor)
        self.setTextCursor(cursor)
        self.emit(SIGNAL("textChanged()"))

    def highlight(self):
        extraSelections = []
        self.setExtraSelections(extraSelections)
        format = QTextCharFormat()
        format.setForeground(QColor(Config["delimiterfontcolor"]))
        format.setBackground(QColor(Qt.yellow).lighter(160)) #QColor(Config["bracketcolor"])?
        selection = QTextEdit.ExtraSelection()
        selection.format = format

        doc = self.document()
        cursor = self.textCursor()
        beforeCursor = QTextCursor(cursor)

        cursor.movePosition(QTextCursor.NextCharacter, QTextCursor.KeepAnchor)
        brace = cursor.selectedText()

        beforeCursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.KeepAnchor)
        beforeBrace = beforeCursor.selectedText()

        if ((brace != "{") and \
            (brace != "}") and \
            (brace != "[") and \
            (brace != "]") and \
            (brace != "(") and \
            (brace != ")")):
            if ((beforeBrace == "{") or \
                (beforeBrace == "}") or \
                (beforeBrace == "[") or \
                (beforeBrace == "]") or \
                (beforeBrace == "(") or \
                (beforeBrace == ")")):
                cursor = beforeCursor
                brace = cursor.selectedText();
            else:
                return

        #format = QTextCharFormat()
        #format.setForeground(Qt.red)
        #format.setFontWeight(QFont.Bold)

        if ((brace == "{") or (brace == "}")):
            openBrace = "{"
            closeBrace = "}"
        elif ((brace == "[") or (brace == "]")):
            openBrace = "["
            closeBrace = "]"
        elif ((brace == "(") or (brace == ")")):
            openBrace = "("
            closeBrace = ")"
            
        if (brace == openBrace):
            cursor1 = doc.find(closeBrace, cursor)
            cursor2 = doc.find(openBrace, cursor)
            if (cursor2.isNull()):
                selection.cursor = cursor
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
                selection.cursor = cursor1
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
            else:
                while (cursor1.position() > cursor2.position()):
                    cursor1 = doc.find(closeBrace, cursor1)
                    cursor2 = doc.find(openBrace, cursor2)
                    if (cursor2.isNull()):
                        break
                selection.cursor = cursor
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
                selection.cursor = cursor1
                selection.cursor.clearSelection()
                extraSelections.append(selection)
                self.setExtraSelections(extraSelections)
        else:
            if (brace == closeBrace):
                cursor1 = doc.find(openBrace, cursor, QTextDocument.FindBackward)
                cursor2 = doc.find(closeBrace, cursor, QTextDocument.FindBackward)
                if (cursor2.isNull()):
                    selection.cursor = cursor
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                    selection.cursor = cursor1
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                else:
                    while (cursor1.position() < cursor2.position()):
                        cursor1 = doc.find(openBrace, cursor1, QTextDocument.FindBackward)
                        cursor2 = doc.find(closeBrace, cursor2, QTextDocument.FindBackward)
                        if (cursor2.isNull()):
                            break
                    selection.cursor = cursor
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)
                    selection.cursor = cursor1
                    selection.cursor.clearSelection()
                    extraSelections.append(selection)
                    self.setExtraSelections(extraSelections)

    def insertFromMimeData(self, source):
        self.cursor = self.textCursor()
        self.cursor.movePosition(QTextCursor.End, 
        QTextCursor.MoveAnchor, 1)
        self.setTextCursor(self.cursor)
        if source.hasText():
            pasteList = QStringList()
            pasteList = source.text().split("\n")
            if len(pasteList) > 1:
                self.runningCommand.append(source.text())
                self.updateHistory(pasteList)
        newSource = QMimeData()
        newSource.setText(source.text().replace("\n",
        "\n"+self.alternatePrompt))
        QTextEdit.insertFromMimeData(self, newSource)

    def cut(self):
        if not self.isCursorInEditionZone() or \
        (self.isCursorInEditionZone() and \
        not self.isAnchorInEditionZone()):
            return
        else:
            QTextEdit.cut(self)

    def delete(self):
        if not self.isCursorInEditionZone() or \
        (self.isCursorInEditionZone() and \
        not self.isAnchorInEditionZone()):
            return
        else:
            QTextEdit.delete(self)
    
    def currentCommand(self):
        block = self.cursor.block()
        text = block.text()
        return text.right(text.length()-self.currentPromptLength)

    def appendText(self, out_text):
        if not out_text == "":
            self.append(out_text)
        cursor = self.textCursor()
        cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
        self.setTextCursor(cursor)

    def isCursorInEditionZone(self):
        cursor = self.textCursor()
        pos = cursor.position()
        block = self.document().lastBlock()
        last = block.position() + self.currentPromptLength
        return pos >= last
      
    def isAnchorInEditionZone(self):
        cursor = self.textCursor()
        pos = cursor.anchor()
        block = self.document().lastBlock()
        last =  block.position() + self.currentPromptLength
        return pos >= last

    def updateHistory(self, command):
        if isinstance(command, QStringList):
            for line in command:
                self.history.append(line)
        elif not command == "":
            if len(self.history) <= 0 or \
            not command == self.history[-1]:
                self.history.append(command)
        self.historyIndex = len(self.history)
        self.emit(SIGNAL("updateHistory(PyQt_PyObject)"), command)

    def insertPlainText(self, text):
        if self.isCursorInEditionZone():
          QTextEdit.insertPlainText(self, text)

    def execute(self, text):
        MainWindow.Console.statusBar().showMessage("Running...")
        QApplication.processEvents()
        if not text.trimmed() == "":
            try:
                if (text.startsWith('quit(') or text.startsWith('q(')) \
                and text.count(")") == 1:
                    self.commandError(
                    "Error: System exit from manageR not allowed, close dialog manually")
                else:
                    output_text = QString()
                    if platform.system() == "Windows":
                        tfile = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('tempfile', wantFun=True))
                        tfile = tfile()
                        temp = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('file', wantFun=True))
                        temp = temp(tfile, open='w')
                        sink = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('sink', wantFun=True))
                        sink(temp)
                    else:
                        def write(output):
                            if not QString(output).startsWith("Error"):
                                output_text.append(unicode(output, 'utf-8'))
                            if output_text.length() >= 50000 and output_text[-1] == "\n":
                                self.commandOutput(output_text)
                                output_text.clear()
                            QApplication.processEvents()
                        robjects.rinterface.setWriteConsole(write)
                        def read(prompt): # TODO: This is a terrible workaround
                            input = "\n"  # and needs to be futher investigated...
                            return input
                        robjects.rinterface.setReadConsole(read)
                    try:
                        try_ = robjects.r["try"]
                        parse_ = robjects.r["parse"]
                        paste_ = robjects.r["paste"]
                        seq_along_ = robjects.r["seq_along"]
                        withVisible_ = robjects.r["withVisible"]
                        class_ = robjects.r["class"]
                        result =  try_(parse_(text=paste_(unicode(text))), silent=True)
                        exprs = result
                        result = None
                        for i in list(seq_along_(exprs)):
                            ei = exprs[i-1]
                            try:
                                result =  try_(withVisible_(ei), silent=True)
                            except robjects.rinterface.RRuntimeError, rre:
                                self.commandError(str(rre))
                                self.commandComplete()
                                return
                            visible = result.r["visible"][0][0]
                            if visible:
                                if class_(result.r["value"][0])[0] == "help_files_with_topic" or \
                                    class_(result.r["value"][0])[0] == "hsearch":
                                    self.helpTopic(result.r["value"][0], class_(result.r["value"][0])[0])
                                elif not str(result.r["value"][0]) == "NULL":
                                    robjects.r['print'](result.r["value"][0])
                            else:
                                try:
                                    if text.startsWith('library('):
                                        library = result.r["value"][0][0]
                                        if not library in Libraries:
                                            addLibraryCommands(library)
                                except:
                                    pass
                    except robjects.rinterface.RRuntimeError, rre:
                        # this fixes error output to look more like R's output
                        self.commandError("Error: %s" % (str(" ").join(str(rre).split(":")[1:]).strip()))
                        self.commandComplete()
                        return
                    if platform.system() == "Windows":
                        sink()
                        close = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('close', wantFun=True))
                        close(temp)
                        temp = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('file', wantFun=True))
                        temp = temp(tfile, open='r')
                        s = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('readLines', wantFun=True))
                        s = s(temp)
                        close(temp)
                        unlink = robjects.conversion.ri2py(
                        robjects.rinterface.globalEnv.get('unlink', wantFun=True))
                        unlink(tfile)
                        output_text = QString(str.join(os.linesep, s))
                    if not output_text.isEmpty():
                        self.commandOutput(output_text)
            except Exception, err:
                self.commandError(str(err))
                self.commandComplete()
                return
            self.commandComplete()
        MainWindow.Console.statusBar().clearMessage()

    def helpTopic(self, topic, search):
        if search == "hsearch":
            dialog = searchDialog(self, topic)
        else:
            dialog = helpDialog(self, topic)
        dialog.setWindowModality(Qt.NonModal)
        dialog.setModal(False)
        dialog.show()
        MainWindow.Console.statusBar().showMessage("Help dialog opened", 5000)
        return

    def commandError(self, error):
        self.appendText(unicode(error))
        # Emit a signal here?
                
    def commandOutput(self, output):
        self.appendText(unicode(output))
        # Emit a signal here?
        
    def commandComplete(self):
        self.switchPrompt()
        self.displayPrompt()
        MainWindow.Console.statusBar().showMessage("Complete!", 5000)
        self.emit(SIGNAL("commandComplete()"))


class ConfigForm(QDialog):

    def __init__(self, parent=None):
        super(ConfigForm, self).__init__(parent)

        self.highlightingChanged = False
        fm = QFontMetrics(self.font())
        monofont = QFont(Config["fontfamily"], 10)
        pixmap = QPixmap(16, 16)
        self.colors = {}
        self.boldCheckBoxes = {}
        self.italicCheckBoxes = {}
        self.completionCheckBoxes = {}
        self.editors = {}

        generalWidget = QWidget()
        self.rememberGeometryCheckBox = QCheckBox(
                "&Remember geometry")
        self.rememberGeometryCheckBox.setToolTip("<p>Check this to make "
                "manageR remember the size and position of the console "
                "window and one editR window")
        self.rememberGeometryCheckBox.setChecked(
                Config["remembergeometry"])
        self.backupLineEdit = QLineEdit(Config["backupsuffix"])
        self.backupLineEdit.setToolTip("<p>If nonempty, a backup will be "
                "kept with the given suffix. If empty, no backup will be "
                "made.</p>")
        regex = QRegExp(r"[~.].*")
        self.backupLineEdit.setValidator(QRegExpValidator(regex, self))
        self.backupLineEdit.setFont(monofont)
        backupLabel = QLabel("&Backup suffix:")
        backupLabel.setBuddy(self.backupLineEdit)
        regex = QRegExp(r"*")
        self.inputLineEdit = QLineEdit(Config["beforeinput"])
        self.inputLineEdit.setValidator(QRegExpValidator(regex, self))
        self.inputLineEdit.setInputMask("x" * 40)
        self.inputLineEdit.setFont(monofont)
        self.inputLineEdit.setToolTip("<p>Specify the prompt (e.g. '>') "
                "that will be displayed each time the console is ready "
                "for input.</p>")
        inputPromptLabel = QLabel("&Input prompt:")
        inputPromptLabel.setBuddy(self.inputLineEdit)
        self.outputLineEdit = QLineEdit(Config["afteroutput"])
        self.outputLineEdit.setValidator(QRegExpValidator(regex, self))
        self.outputLineEdit.setInputMask("x" * 40)
        self.outputLineEdit.setFont(monofont)
        self.outputLineEdit.setToolTip("<p>Specify the prompt (e.g. '+') "
                "that will be displayed each time further input to the "
                "console is required.</p>")
        outputPromptLabel = QLabel("&Continuation prompt:")
        outputPromptLabel.setBuddy(self.outputLineEdit)
        self.cwdLineEdit = QLineEdit(Config["setwd"])
        cwdLabel = QLabel("&Default working directory:")
        cwdLabel.setBuddy(self.cwdLineEdit)
        self.cwdLineEdit.setToolTip("<p>Specify the default working "
                "directory for the manageR console. Setting this to "
                "blank, or '.', will use the current Python working directory."
                "Changes made here only take effect when manageR is next run.</p>")
        self.tabWidthSpinBox = QSpinBox()
        self.tabWidthSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.tabWidthSpinBox.setRange(2, 20)
        self.tabWidthSpinBox.setSuffix(" spaces")
        self.tabWidthSpinBox.setValue(Config["tabwidth"])
        self.tabWidthSpinBox.setToolTip("<p>Specify the number of "
                "spaces that a single tab should span.</p>")
        tabWidthLabel = QLabel("&Tab width:")
        tabWidthLabel.setBuddy(self.tabWidthSpinBox)
        self.fontComboBox = QFontComboBox()
        self.fontComboBox.setCurrentFont(monofont)
        self.fontComboBox.setToolTip("<p>Specify the font family for "
                "the manageR console and all EditR windows.</p>")
        fontLabel = QLabel("&Font:")
        fontLabel.setBuddy(self.fontComboBox)
        self.fontSpinBox = QSpinBox()
        self.fontSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.fontSpinBox.setRange(6, 20)
        self.fontSpinBox.setSuffix(" pt")
        self.fontSpinBox.setValue(Config["fontsize"])
        self.fontSpinBox.setToolTip("<p>Specify the font size for  "
                "the manageR console, and all EditR windows.</p>")
        self.timeoutSpinBox = QSpinBox()
        self.timeoutSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.timeoutSpinBox.setRange(0, 20000)
        self.timeoutSpinBox.setSingleStep(100)
        self.timeoutSpinBox.setSuffix(" ms")
        self.timeoutSpinBox.setValue(Config["delay"])
        self.timeoutSpinBox.setToolTip("<p>Specify the time (in milliseconds) "
                "to wait before displaying the autocomplete popup when a set of "
                "possible matches are found.</p>")
        timeoutLabel = QLabel("Popup time delay:")
        timeoutLabel.setBuddy(self.timeoutSpinBox)
        self.mincharsSpinBox = QSpinBox()
        self.mincharsSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.mincharsSpinBox.setRange(1, 4)
        self.mincharsSpinBox.setSuffix(" characters")
        self.mincharsSpinBox.setValue(Config["minimumchars"])
        self.mincharsSpinBox.setToolTip("<p>Specify the minimum number of characters "
                "that must be typed before displaying the autocomplete popup when a "
                "set of possible matches are found.</p>")
        mincharsLabel = QLabel("Minimum word size:")
        mincharsLabel.setBuddy(self.mincharsSpinBox)        
        self.autocompleteCheckBox = QCheckBox("Enable autocomplete/tooltips")
        self.autocompleteCheckBox.setToolTip("<p>Check this to enable "
                "autocompletion of R commands. For the current manageR session," 
                "only newly imported library commands will be added to the "
                "autocomplete list.")
        self.autocompleteCheckBox.setChecked(Config["enableautocomplete"])
        
        maxWidth = fm.width(mincharsLabel.text())
        for widget in (self.backupLineEdit, self.inputLineEdit, self.outputLineEdit,
                self.tabWidthSpinBox, self.mincharsSpinBox, self.timeoutSpinBox,
                self.fontSpinBox):
            maxWidth = max(maxWidth, fm.width(widget.text()))
        for widget in (self.backupLineEdit, self.inputLineEdit, self.outputLineEdit,
                self.tabWidthSpinBox, self.mincharsSpinBox, self.timeoutSpinBox,
                self.fontSpinBox):
            widget.setFixedWidth(maxWidth)

        vbox = QVBoxLayout()
        grid0 = QGridLayout()
        grid0.addWidget(self.rememberGeometryCheckBox,0,0,1,3)
        grid0.addWidget(fontLabel,1,0,1,1)
        grid0.addWidget(self.fontComboBox,1,1,1,1)
        grid0.addWidget(self.fontSpinBox,1,2,1,1)
        grid0.addWidget(tabWidthLabel,2,0,1,1)
        grid0.addWidget(self.tabWidthSpinBox,2,2,1,1,Qt.AlignRight)
        grid0.addWidget(backupLabel,3,0,1,1)
        grid0.addWidget(self.backupLineEdit,3,2,1,1,Qt.AlignRight)
        vbox.addLayout(grid0)
        
        gbox1 = QGroupBox("Console")
        grid1 = QGridLayout()
        grid1.addWidget(inputPromptLabel,0,0,1,1)
        grid1.addWidget(self.inputLineEdit,0,1,1,1,Qt.AlignRight)
        grid1.addWidget(outputPromptLabel,1,0,1,1)
        grid1.addWidget(self.outputLineEdit,1,1,1,1,Qt.AlignRight)
        grid1.addWidget(cwdLabel,2,0,1,1)
        grid1.addWidget(self.cwdLineEdit,2,1,1,1)
        gbox1.setLayout(grid1)
        vbox.addWidget(gbox1)
        
        gbox2 = QGroupBox("Autocompletion")
        grid2 = QGridLayout()
        grid2.addWidget(timeoutLabel,0,0,1,1)
        grid2.addWidget(self.timeoutSpinBox,0,1,1,1,Qt.AlignRight)
        grid2.addWidget(mincharsLabel,1,0,1,1)
        grid2.addWidget(self.mincharsSpinBox,1,1,1,1,Qt.AlignRight)
        grid2.addWidget(self.autocompleteCheckBox,2,0,1,2)
        gbox2.setLayout(grid2)
        vbox.addWidget(gbox2)
        generalWidget.setLayout(vbox)

        highlightingWidget = QWidget()
        self.highlightingCheckBox = QCheckBox("Enable syntax highlighting")
        self.highlightingCheckBox.setToolTip("<p>Check this to enable "
                "syntax highlighting in the console and EditR windows."
                "Changes made here only take effect when manageR is next run.</p>")
        self.highlightingCheckBox.setChecked(Config["enablehighlighting"])
        minButtonWidth = 0
        minWidth = 0
        label = QLabel("Background:")
        label.setMinimumWidth(minWidth)
        minWidth = 0
        color = Config["backgroundcolor"]
        pixmap.fill(QColor(color))
        colorButton = QPushButton("&0 Color...")
        minButtonWidth = max(minButtonWidth,
        10 + pixmap.width() + fm.width(colorButton.text()))
        colorButton.setIcon(QIcon(pixmap))
        self.colors["background"] = [Config["backgroundcolor"], None]
        self.colors["background"][1] = colorButton
        self.connect(colorButton, SIGNAL("clicked()"),
        lambda name="background": self.setColor("background"))

        gbox = QGridLayout()
        gbox.addWidget(self.highlightingCheckBox, 0,0,1,3)
        gbox.addWidget(label,2,0,1,1)
        gbox.addWidget(colorButton,2,3,1,1)
        count = 1
        labels = []
        buttons = []
        for name, labelText in (("normal", "Normal:"),
                ("keyword", "Keywords:"), ("builtin", "Builtins:"),
                ("constant", "Constants:"), ("delimiter", "Delimiters:"),
                ("comment", "Comments:"), ("string", "Strings:"),
                ("number", "Numbers:"), ("error", "Errors:"),
                ("assignment", "Assignment operator:")):
            label = QLabel(labelText)
            labels.append(label)
            boldCheckBox = QCheckBox("Bold")
            boldCheckBox.setChecked(Config["%sfontbold" % name])
            self.boldCheckBoxes[name] = boldCheckBox
            italicCheckBox = QCheckBox("Italic")
            italicCheckBox.setChecked(Config["%sfontitalic" % name])
            self.italicCheckBoxes[name] = italicCheckBox
            self.colors[name] = [Config["%sfontcolor" % name], None]
            pixmap.fill(QColor(self.colors[name][0]))
            if count <= 9:
                colorButton = QPushButton("&%d Color..." % count)
            elif name == "assignment":
                colorButton = QPushButton("&Q Color...")
            else:
                colorButton = QPushButton("Color...")
            count += 1
            minButtonWidth = max(minButtonWidth,
                    10 + pixmap.width() + fm.width(colorButton.text()))
            buttons.append(colorButton)
            colorButton.setIcon(QIcon(pixmap))
            self.colors[name][1] = colorButton
            gbox.addWidget(label,count+2,0,1,1)
            gbox.addWidget(boldCheckBox,count+2,1,1,1)
            gbox.addWidget(italicCheckBox,count+2,2,1,1)
            gbox.addWidget(colorButton,count+2,3,1,1)
            self.connect(colorButton, SIGNAL("clicked()"),
                        lambda name=name: self.setColor(name))

        highlightingWidget.setLayout(gbox)

        tabWidget = QTabWidget()
        tabWidget.addTab(generalWidget, "&General")
        tabWidget.addTab(highlightingWidget, "&Highlighting")

        for name, label, msg in (
                ("newfile", "On &new file",
                 "<font color=green><i>The text here is automatically "
                 "inserted into new R scripts.<br>It may be convenient to add "
                 "your standard libraries and copyright<br/>"
                 "notice here."),
                ("consolestartup", "&At startup",
                 "<font color=green><i><p>manageR executes the lines above "
                 "whenever the R interpreter is started.<br/>"
                 "Use them to add custom functions and/or load "
                 "libraries or additional tools.<br/>"
                 "Changes made here only take "
                 "effect when manageR is next run.</p></font>")):
            editor = REditor(self, int(Config["tabwidth"]))
            editor.setPlainText(Config[name])
            editor.setTabChangesFocus(True)
            RHighlighter(editor.document())
            vbox = QVBoxLayout()
            vbox.addWidget(editor, 1)
            vbox.addWidget(QLabel(msg))
            widget = QWidget()
            widget.setLayout(vbox)
            tabWidget.addTab(widget, label)
            self.editors[name] = editor

        buttonBox = QDialogButtonBox(QDialogButtonBox.Ok|
                                           QDialogButtonBox.Cancel)
        layout = QVBoxLayout()
        layout.addWidget(tabWidget)
        layout.addWidget(buttonBox)
        self.setLayout(layout)

        self.connect(buttonBox, SIGNAL("accepted()"), self.accept)
        self.connect(buttonBox, SIGNAL("rejected()"), self.reject)

        self.setWindowTitle("manageR - Configure")


    def updateUi(self):
        pass # TODO validation, e.g., valid consolestartup, etc.

    def setColor(self, which):
        color = QColorDialog.getColor(
                        QColor(self.colors[which][0]), self)
        if color is not None:
            self.colors[which][0] = color.name()
            pixmap = QPixmap(16, 16)
            pixmap.fill(QColor(color.name()))
            self.colors[which][1].setIcon(QIcon(pixmap))

    def accept(self):
        Config["remembergeometry"] = (self.rememberGeometryCheckBox.isChecked())
        Config["backupsuffix"] = self.backupLineEdit.text()
        inputPrompt = self.inputLineEdit.text()
        if Config["beforeinput"] != inputPrompt:
            self.highlightingChanged = True
            Config["beforeinput"] = inputPrompt
        afterOutput = self.outputLineEdit.text()
        if Config["afteroutput"] != afterOutput:
            self.highlightingChanged = True
            Config["afteroutput"] = afterOutput
        Config["setwd"] = self.cwdLineEdit.text()
        for name in ("consolestartup", "newfile"):
            Config[name] = unicode(self.editors[name].toPlainText())
        Config["tabwidth"] = self.tabWidthSpinBox.value()
        Config["delay"] = self.timeoutSpinBox.value()
        Config["minimumchars"] = self.mincharsSpinBox.value()
        Config["enableautocomplete"] = (self.autocompleteCheckBox.isChecked())
        Config["enablehighlighting"] = (self.highlightingCheckBox.isChecked())
        
        #Config["tooltipsize"] = self.toolTipSizeSpinBox.value()
        family = self.fontComboBox.currentFont().family()
        if Config["fontfamily"] != family:
            self.highlightingChanged = True
            Config["fontfamily"] = family
        size = self.fontSpinBox.value()
        if Config["fontsize"] != size:
            self.highlightingChanged = True
            Config["fontsize"] = size
        for name in ("normal", "keyword", "builtin", "constant",
                "delimiter", "comment", "string", "number", "error",
                "assignment"):
            bold = self.boldCheckBoxes[name].isChecked()
            if Config["%sfontbold" % name] != bold:
                self.highlightingChanged = True
                Config["%sfontbold" % name] = bold
            italic = self.italicCheckBoxes[name].isChecked()
            if Config["%sfontitalic" % name] != italic:
                self.highlightingChanged = True
                Config["%sfontitalic" % name] = italic
            color = self.colors[name][0]
            if Config["%sfontcolor" % name] != color:
                self.highlightingChanged = True
                Config["%sfontcolor" % name] = color
        color = self.colors["background"][0]
        if Config["backgroundcolor"] != color:
            self.highlightingChanged = True
            Config["backgroundcolor"] = color
        QDialog.accept(self)

class helpDialog(QDialog):

    def __init__(self, parent, help_topic):
        QDialog.__init__ (self, parent)
        #initialise the display text edit
        display = QTextEdit(self)
        display.setReadOnly(True)
        #set the font style of the help display
        font = QFont(Config["fontfamily"], Config["fontsize"])
        font.setFixedPitch(True)
        display.setFont(font)
        display.document().setDefaultFont(font)
        #initialise grid layout for dialog
        grid = QGridLayout(self)
        grid.addWidget(display)
        self.setWindowTitle("manageR - Help")
        try:
            help_file = QFile(unicode(help_topic[0]))
        except:
            raise Exception, "Error: %s" % (unicode(help_topic))
        help_file.open(QFile.ReadOnly)
        stream = QTextStream(help_file)
        help_string = QString(stream.readAll())
        #workaround to remove the underline formatting that r uses
        help_string.remove("_")
        display.setPlainText(help_string)
        help_file.close()
        self.resize(650, 400)

class searchDialog(QDialog):

  def __init__(self, parent, help_topic):
      QDialog.__init__ (self, parent)
      #initialise the display text edit
      display = QTextEdit(self)
      display.setReadOnly(True)
      #set the font style of the help display
      font = QFont(Config["fontfamily"], Config["fontsize"])
      font.setFixedPitch(True)
      display.setFont(font)
      display.document().setDefaultFont(font)
      #initialise grid layout for dialog
      grid = QGridLayout(self)
      grid.addWidget(display)
      self.setWindowTitle("manageR - Search Help")
      #get help output from r 
      #note: help_topic should only contain the specific
      #      help topic (i.e. no brackets etc.)
      matches = help_topic.subset("matches")[0]
      #print [matches]
      fields = help_topic.subset("fields")[0]
      pattern = help_topic.subset("pattern")[0]
      fields_string = QString()
      for i in fields:
          fields_string.append(i + " or ")
      fields_string.chop(3)
      display_string = QString("Help files with " + fields_string)
      display_string.append("matching '" + pattern[0] + "' using ")
      display_string.append("regular expression matching:\n\n")
      nrows = robjects.r.nrow(matches)[0]
      ncols = robjects.r.ncol(matches)[0]
      for i in range(1, nrows + 1):
            row = QString()
            pack = matches.subset(i, 3)[0]
            row.append(pack)
            row.append("::")
            pack = matches.subset(i, 1)[0]
            row.append(pack)
            row.append("\t\t")
            pack = matches.subset(i, 2)[0]
            row.append(pack)
            row.append("\n")
            display_string.append(row)
      display.setPlainText(display_string)
      #help_file.close()
      self.resize(650, 400)

class RWDWidget(QWidget):

    def __init__(self, parent, base):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30, 30)
        self.parent = parent
        self.base = base

        self.current = QLineEdit(self)
        font = QFont(Config["fontfamily"], Config["fontsize"])
        self.current.setToolTip("Current working directory")
        self.current.setWhatsThis("Current working directory")
        font.setFixedPitch(True)
        self.current.setFont(font)
        self.current.setText(base)

        self.setwd = QToolButton(self)
        self.setwd.setToolTip("Set working directory")
        self.setwd.setWhatsThis("Set working directory")
        self.setwd.setIcon(QIcon(":mActionWorkingSet.png"))
        self.setwd.setText("setwd")
        self.setwd.setAutoRaise(True)
        
        horiz = QHBoxLayout(self)
        horiz.addWidget(self.current)
        horiz.addWidget(self.setwd)
        self.connect(self.setwd, SIGNAL("clicked()"), self.browseToFolder)
        
    def displayWorkingDir(self,directory):
        if isinstance(directory, tuple):
            directory = directory[-1]
        self.current.setText(directory)
    
    def browseToFolder(self):
        directory = QFileDialog.getExistingDirectory(
        self, "Choose working folder",self.current.text(),
        (QFileDialog.ShowDirsOnly|QFileDialog.DontResolveSymlinks))
        if not directory.isEmpty():
            self.displayWorkingDir(directory)
            self.setWorkingDir(directory)

    def setWorkingDir(self,directory):
        commands = QString('setwd("%s")' % (directory))
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            MainWindow.Console.editor.moveToEnd()
            MainWindow.Console.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            MainWindow.Console.editor.cursor.removeSelectedText()
            MainWindow.Console.editor.cursor.insertText(
            MainWindow.Console.editor.currentPrompt)
            MainWindow.Console.editor.insertFromMimeData(mime)
            MainWindow.Console.editor.entered()
            
class RCommandList(QListWidget):
    def __init__(self, parent):
        QListWidget.__init__(self, parent)
 
    def mousePressEvent(self, event):
        item = self.itemAt(event.globalPos())
        if not item and event.button() == Qt.LeftButton:
            self.clearSelection()
        QListWidget.mousePressEvent(self, event)
        
    def selectionChanged(self, sela, selb):
        self.emit(SIGNAL("selectionChanged()"))
            
class RHistoryWidget(QWidget):

    def __init__(self, parent, console):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30,30)
        self.parent = parent
        self.console = console
        self.commandList = RCommandList(self)
        self.commandList.setAlternatingRowColors(True)
        self.commandList.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.commandList.setSortingEnabled(False)
        self.commandList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        font = QFont(Config["fontfamily"], Config["fontsize"])
        self.commandList.setFont(font)
        self.commandList.setToolTip("Double-click to run single command")
        self.commandList.setWhatsThis("Double-click to run single command")
        self.updateCommands(MainWindow.Console.editor.history)
        
        self.copyButton = QToolButton(self)
        self.copyAction = QAction("&Copy command(s)", self)
        self.copyAction.setStatusTip("Copy the selected command(s) to the clipboard")
        self.copyAction.setToolTip("Copy the selected command(s) to the clipboard")
        self.copyAction.setIcon(QIcon(":mActionEditCopy.png"))
        self.copyAction.setEnabled(False)
        self.copyButton.setDefaultAction(self.copyAction)
        self.copyButton.setAutoRaise(True)
        
        self.selectButton = QToolButton(self)
        self.selectAction = QAction("Select &all", self)
        self.selectAction.setStatusTip("Select all commands")
        self.selectAction.setToolTip("Select all commands")
        self.selectAction.setIcon(QIcon(":mActionEditSelectAll.png"))
        self.selectButton.setDefaultAction(self.selectAction)
        self.selectButton.setAutoRaise(True)
        
        self.insertButton = QToolButton(self)
        self.insertAction = QAction("&Paste to console", self)
        self.insertAction.setStatusTip("Paste the selected command(s) into the console")
        self.insertAction.setToolTip("Paste the selected command(s) into the console")
        self.insertAction.setIcon(QIcon(":mActionEditPaste.png"))
        self.insertAction.setEnabled(False)
        self.insertButton.setDefaultAction(self.insertAction)
        self.insertButton.setAutoRaise(True)
        
        self.runButton = QToolButton(self)
        self.runAction = QAction("&Run command(s)", self)
        self.runAction.setStatusTip("Run the selected command(s) in the console")
        self.runAction.setToolTip("Run the selected command(s) in the console")
        self.runAction.setIcon(QIcon(":mActionRun.png"))
        self.runAction.setEnabled(False)
        self.runButton.setDefaultAction(self.runAction)
        self.runButton.setAutoRaise(True)
        
        self.clearButton = QToolButton(self)
        self.clearAction = QAction("C&lear command list", self)
        self.clearAction.setStatusTip("Clear command list")
        self.clearAction.setToolTip("Clear command list")
        self.clearAction.setIcon(QIcon(":mActionFileClose.png"))
        self.clearAction.setEnabled(True)
        self.clearButton.setDefaultAction(self.clearAction)
        self.clearButton.setAutoRaise(True)
        
        grid = QGridLayout(self)
        horiz = QHBoxLayout()
        horiz.addWidget(self.runButton)
        horiz.addWidget(self.insertButton)
        horiz.addWidget(self.copyButton)
        horiz.addWidget(self.clearButton)
        horiz.addWidget(self.selectButton)
        horiz.addStretch()
        grid.addLayout(horiz, 0, 0, 1, 1)
        grid.addWidget(self.commandList, 1, 0, 1, 1)
        
        self.connect(self.copyAction, SIGNAL("triggered()"), self.copy)
        self.connect(self.insertAction, SIGNAL("triggered()"), self.insert)
        self.connect(self.runAction, SIGNAL("triggered()"), self.run)
        self.connect(self.clearAction, SIGNAL("triggered()"), self.clear)
        self.connect(self.selectAction, SIGNAL("triggered()"), self.selectAll)
        self.connect(self.commandList, SIGNAL("itemDoubleClicked(QListWidgetItem*)"),
        self.doubleClicked)
        self.connect(self.commandList, SIGNAL("selectionChanged()"), self.selectionChanged)
       
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.runAction)
        menu.addSeparator()
        menu.addAction(self.insertAction)
        menu.addAction(self.copyAction)
        menu.addAction(self.clearAction)
        menu.addAction(self.selectAction)
        menu.exec_(event.globalPos())

    def selectionChanged(self):
        if len(self.commandList.selectedItems()) >= 1:
            self.runAction.setEnabled(True)
            self.copyAction.setEnabled(True)
            #self.clearAction.setEnabled(True)
            if len(self.commandList.selectedItems()) == 1:
                self.insertAction.setEnabled(True)
        else:
            self.insertAction.setEnabled(False)
            self.runAction.setEnabled(False)
            self.copyAction.setEnabled(False)
            #self.clearAction.setEnabled(False)

    def copy(self):
        commands = QString()
        selected = self.commandList.selectedItems()
        count = 1
        for item in selected:
            if count == len(selected):
                commands.append(item.text())
            else:
                commands.append(item.text()+"\n")
            count += 1
        clipboard = QApplication.clipboard()
        clipboard.setText(commands, QClipboard.Clipboard)

    def insert(self):
        commands = self.commandList.selectedItems()
        if len(commands) == 1:
            command = commands[0]
        self.insertCommand(command)
        
    def run(self):
        commands = QString()
        selected = self.commandList.selectedItems()
        count = 1
        for item in selected:
            if count == len(selected):
                commands.append(item.text())
            else:
                commands.append(item.text()+"\n")
            count += 1
        self.runCommands(commands)
        
    def selectAll(self):
        self.commandList.selectAll()    
        
    def clear(self):
        self.commandList.clear()
        
    def updateCommands(self, commands):
        if commands:
            if not isinstance(commands, QStringList):
                commands = QStringList(commands)
            self.commandList.addItems(commands)
        
    def insertCommand(self, item):
        MainWindow.Console.editor.cursor.insertText(item.text())
        
    def runCommands(self, commands):
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            MainWindow.Console.editor.moveToEnd()
            MainWindow.Console.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            MainWindow.Console.editor.cursor.removeSelectedText()
            MainWindow.Console.editor.cursor.insertText(
            MainWindow.Console.editor.currentPrompt)
            MainWindow.Console.editor.insertFromMimeData(mime)
            MainWindow.Console.editor.entered()  
           
    def doubleClicked(self, item):
        self.runCommands(item.text())
            
class RVariableWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30,30)
        self.parent = parent
        
        self.variableTable = QTableWidget(0, 2, self)
        labels = QStringList()
        labels.append("Name")
        labels.append("Type")
        self.variableTable.setHorizontalHeaderLabels(labels)
        self.variableTable.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.variableTable.setShowGrid(True)
        self.variableTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.variableTable.setSelectionMode(QAbstractItemView.SingleSelection)

        self.rm = QToolButton(self)
        self.rmAction = QAction("&Remove", self)
        self.rmAction.setToolTip("Remove selected variable")
        self.rmAction.setWhatsThis("Removed selected variable")
        self.rmAction.setIcon(QIcon(":mActionFileRemove.png"))
        self.rm.setDefaultAction(self.rmAction)
        self.rmAction.setEnabled(False)
        self.rm.setAutoRaise(True)
        
        self.export = QToolButton(self)
        self.exportAction = QAction("Export to &file", self)
        self.exportAction.setToolTip("Export data to file")
        self.exportAction.setWhatsThis("Export data to file")
        self.exportAction.setIcon(QIcon(":mActionActionFile.png"))
        self.export.setDefaultAction(self.exportAction)
        self.exportAction.setEnabled(False)
        self.export.setAutoRaise(True)
        
        self.canvas = QToolButton(self)
        self.canvasAction = QAction("Export to &canvas", self)
        self.canvasAction.setToolTip("Export layer to canvas")
        self.canvasAction.setWhatsThis("Export layer to canvas")
        self.canvasAction.setIcon(QIcon(":mActionActionExport.png"))
        self.canvas.setDefaultAction(self.canvasAction)
        self.canvasAction.setEnabled(False)
        self.canvas.setAutoRaise(True)

        #self.layer = QToolButton(self)
        #self.layer.setText("layer")
        #self.layer.setToolTip("Import layer from canvas")
        #self.layer.setWhatsThis("Import layer from canvas")
        #self.layer.setIcon(QIcon(":mActionActionImport.png"))
        #self.layer.setEnabled(True)
        #self.layer.setAutoRaise(True)
        
        self.save = QToolButton(self)
        self.saveAction = QAction("&Save variable", self)
        self.saveAction.setToolTip("Save R variable to file")
        self.saveAction.setWhatsThis("Save R variable to file")
        self.saveAction.setIcon(QIcon(":mActionFileSave.png"))
        self.save.setDefaultAction(self.saveAction)
        self.saveAction.setEnabled(False)
        self.save.setAutoRaise(True)
        
        self.load = QToolButton(self)
        self.loadAction = QAction("&Load variable", self)
        self.loadAction.setToolTip("Load R variable(s) from file")
        self.loadAction.setWhatsThis("Load R variable(s) from file")
        self.loadAction.setIcon(QIcon(":mActionFileOpen.png"))
        self.load.setDefaultAction(self.loadAction)
        self.loadAction.setEnabled(True)
        self.load.setAutoRaise(True)
        
        grid = QGridLayout(self)
        horiz = QHBoxLayout()
        horiz.addWidget(self.rm)
        horiz.addWidget(self.export)
        #horiz.addWidget(self.layer)
        horiz.addWidget(self.canvas)
        horiz.addWidget(self.save)
        horiz.addWidget(self.load)
        horiz.addStretch()
        grid.addLayout(horiz, 0, 0, 1, 1)
        grid.addWidget(self.variableTable, 1, 0, 1, 1)
        
        self.variables = dict()
        self.connect(self.rmAction, SIGNAL("triggered()"), self.removeVariable)
        self.connect(self.exportAction, SIGNAL("triggered()"), self.exportVariable)
        self.connect(self.saveAction, SIGNAL("triggered()"), self.saveVariable)
        self.connect(self.canvasAction, SIGNAL("triggered()"), self.exportToCanvas)
        self.connect(self.loadAction, SIGNAL("triggered()"), self.loadRVariable)
        #self.connect(self.layer, SIGNAL("clicked()"), self.importFromCanvas)
        self.connect(self.variableTable, \
        SIGNAL("itemSelectionChanged()"), self.selectionChanged)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.rmAction)
        menu.addSeparator()
        menu.addAction(self.exportAction)
        menu.addAction(self.canvasAction)
        menu.addAction(self.saveAction)
        menu.addAction(self.loadAction)
        menu.exec_(event.globalPos())

    def updateVariables(self, variables):
        self.variables = {}
        while self.variableTable.rowCount() > 0:
            self.variableTable.removeRow(0)
        if isinstance(variables, tuple):
            variables = variables[0]
        for variable in variables.items():
            self.addVariable(variable)

    def addVariable(self, variable):
        self.variables[variable[0]] = variable[1]
        nameItem = QTableWidgetItem(QString(variable[0]))
        nameItem.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        typeItem = QTableWidgetItem(QString(variable[1]))
        typeItem.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        typeItem.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        row = self.variableTable.rowCount()
        self.variableTable.insertRow(row)
        self.variableTable.setItem(row, 0, nameItem)
        self.variableTable.setItem(row, 1, typeItem)
        self.variableTable.resizeColumnsToContents
      
    def selectionChanged(self):
        row = self.variableTable.currentRow()
        if row < 0 or row >= self.variableTable.rowCount() or \
        self.variableTable.rowCount() < 1:
            self.saveAction.setEnabled(False)
            self.rmAction.setEnabled(False)
            self.canvasAction.setEnabled(False)
            self.exportAction.setEnabled(False)
        else:
            itemName, itemType = self.getVariableInfo(row)
            self.saveAction.setEnabled(True)
            self.rmAction.setEnabled(True)
            self.exportAction.setEnabled(True)
            if itemType in VECTORTYPES:
                #self.canvas.setEnabled(True)
                self.canvasAction.setEnabled(True)
            else:
                #self.canvas.setEnabled(False)
                self.canvasAction.setEnabled(False)

    def removeVariable(self):
        row = self.variableTable.currentRow()
        if row < 0:
            return False
        itemName, itemType = self.getVariableInfo(row)
        self.sendCommands(QString('rm(%s)' % (itemName)))
        
    def exportVariable(self):
        row = self.variableTable.currentRow()
        if row < 0:
            return False
        itemName, itemType = self.getVariableInfo(row)
        if itemType in VECTORTYPES or \
        itemType in RASTERTYPES:
            self.parent.exportRObjects(True, itemName, itemType, False)
        else:
            fd = QFileDialog(self.parent, "Save data to file", "", \
            "Comma separated (*.csv);;Text file (*.txt);;All files (*.*)")
            fd.setAcceptMode(QFileDialog.AcceptSave)
            if not fd.exec_() == QDialog.Accepted:
              return False
            files = fd.selectedFiles()
            selectedFile = files.first()
            if selectedFile.length() == 0:
                return False
            suffix = QString(fd.selectedNameFilter())
            index1 = suffix.lastIndexOf("(")+2
            index2 = suffix.lastIndexOf(")")
            suffix = suffix.mid(index1, index2-index1)
            if not selectedFile.endsWith(suffix):
                selectedFile.append(suffix)
            command = QString('write.table(%s, file = "%s",' % (itemName,selectedFile))
            command.append(QString('append = FALSE, quote = TRUE, sep = ",", eol = "\\n", na = "NA"'))
            command.append(QString(', dec = ".", row.names = FALSE, col.names = TRUE, qmethod = "escape")'))
            self.sendCommands(command)
    
    def saveVariable(self):
        row = self.variableTable.currentRow()
        if row < 0:
            return False
        itemName, itemType = self.getVariableInfo(row)
        fd = QFileDialog(self.parent, "Save data to file", "", \
        "R data file (*.Rda)")
        fd.setAcceptMode(QFileDialog.AcceptSave)
        if not fd.exec_() == QDialog.Accepted:
            return False
        files = fd.selectedFiles()
        selectedFile = files.first()
        if selectedFile.length() == 0:
            return False
        suffix = QString(fd.selectedNameFilter())
        index1 = suffix.lastIndexOf("(")+2
        index2 = suffix.lastIndexOf(")")
        suffix = suffix.mid(index1, index2-index1)
        if not selectedFile.endsWith(suffix):
            selectedFile.append(suffix)
        commands = QString('save(%s, file="%s")' % (itemName,selectedFile))
        self.sendCommands(commands)
      
    def exportToCanvas(self):
        row = self.variableTable.currentRow()
        if row < 0:
            return False
        itemName, itemType = self.getVariableInfo(row)
        if itemType in VECTORTYPES:
            self.parent.exportRObjects(False, itemName, itemType, False)
        else:
            return False

    def importFromCanvas(self):
        mlayer = self.parent.iface.mapCanvas().currentLayer()
        self.parent.importRObjects(mlayer = mlayer)
        return True
        
    def loadRVariable(self):
        fd = QFileDialog(self.parent, "Load R variable(s) from file", "",
        "R data (*.Rda);;All files (*.*)")
        fd.setAcceptMode(QFileDialog.AcceptOpen)
        if fd.exec_() == QDialog.Rejected:
            return False
        files = fd.selectedFiles()
        selectedFile = files.first()
        if selectedFile.length() == 0:
            return False
        self.sendCommands(QString('load("%s")' % (selectedFile)))
      
    def getVariableInfo(self, row):
        item_name = self.variableTable.item(row, 0)
        item_name = item_name.data(Qt.DisplayRole).toString()
        item_type = self.variableTable.item(row, 1)
        item_type = item_type.data(Qt.DisplayRole).toString()
        return (item_name, item_type)
      
    def sendCommands(self, commands):
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            MainWindow.Console.editor.moveToEnd()
            MainWindow.Console.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            MainWindow.Console.editor.cursor.removeSelectedText()
            MainWindow.Console.editor.cursor.insertText(
            MainWindow.Console.editor.currentPrompt)
            MainWindow.Console.editor.insertFromMimeData(mime)
            MainWindow.Console.editor.entered()
            
class RGraphicsWidget(QWidget):

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30, 30)
        self.parent = parent
        
        self.graphicsTable = QTableWidget(0, 2, self)
        labels = QStringList()
        labels.append("Item")
        labels.append("Device")
        self.graphicsTable.setHorizontalHeaderLabels(labels)
        self.graphicsTable.horizontalHeader().setResizeMode(1, QHeaderView.Stretch)
        self.graphicsTable.setShowGrid(True)
        self.graphicsTable.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.graphicsTable.setSelectionMode(QAbstractItemView.SingleSelection)
        
        self.rmButton = QToolButton(self)
        self.rmAction = QAction("&Close device", self)
        self.rmAction.setToolTip("Close selected graphic")
        self.rmAction.setWhatsThis("Close selected graphic")
        self.rmAction.setIcon(QIcon(":mActionFileRemove.png"))
        self.rmButton.setDefaultAction(self.rmAction)
        self.rmAction.setEnabled(False)
        self.rmButton.setAutoRaise(True)
        
        self.exportButton = QToolButton(self)
        self.exportAction = QAction("Export as &bitmap", self)
        self.exportAction.setToolTip("Export graphic as bitmap")
        self.exportAction.setWhatsThis("Export graphic as bitmap")
        self.exportAction.setIcon(QIcon(":mActionGraphicExport.png"))
        self.exportAction.setEnabled(False)
        self.exportButton.setDefaultAction(self.exportAction)
        self.exportButton.setAutoRaise(True)
        
        self.saveButton = QToolButton(self)
        self.saveAction = QAction("Export to &vector", self)
        self.saveAction.setToolTip("Export graphic to vector file")
        self.saveAction.setWhatsThis("Export graphic to vector file")
        self.saveAction.setIcon(QIcon(":mActionGraphicSave.png"))
        self.saveAction.setEnabled(False)
        self.saveButton.setDefaultAction(self.saveAction)
        self.saveButton.setAutoRaise(True)

        self.newButton = QToolButton(self)
        self.newAction = QAction("&New device", self)
        self.newAction.setToolTip("Open new graphics device")
        self.newAction.setWhatsThis("Open new graphics device")
        self.newAction.setIcon(QIcon(":mActionGraphicNew.png"))
        self.newAction.setEnabled(True)
        self.newButton.setDefaultAction(self.newAction)
        self.newButton.setAutoRaise(True)

        self.refreshButton = QToolButton(self)
        self.refreshAction = QAction("&Refresh list", self)
        self.refreshAction.setToolTip("Refresh list of graphic devices")
        self.refreshAction.setWhatsThis("Refresh list of graphic devices")
        self.refreshAction.setIcon(QIcon(":mActionGraphicRefresh.png"))
        self.refreshAction.setEnabled(True)
        self.refreshButton.setDefaultAction(self.refreshAction)
        self.refreshButton.setAutoRaise(True)
      
        grid = QGridLayout(self)
        horiz = QHBoxLayout()
        horiz.addWidget(self.refreshButton)
        horiz.addWidget(self.rmButton)
        horiz.addWidget(self.exportButton)
        horiz.addWidget(self.saveButton)
        horiz.addWidget(self.newButton)
        horiz.addStretch()
        grid.addLayout(horiz, 0, 0, 1, 1)
        grid.addWidget(self.graphicsTable, 1, 0, 1, 1)
        
        self.graphics = dict()
        self.connect(self.rmAction, SIGNAL("triggered()"), self.removeGraphic)
        self.connect(self.exportAction, SIGNAL("triggered()"), self.exportGraphic)
        self.connect(self.saveAction, SIGNAL("triggered()"), self.saveGraphic)
        self.connect(self.newAction, SIGNAL("triggered()"), self.newGraphic)
        self.connect(self.refreshAction, SIGNAL("triggered()"), self.refreshGraphics)
        self.connect(self.graphicsTable, \
        SIGNAL("itemSelectionChanged()"), self.selectionChanged)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.refreshAction)
        menu.addSeparator()
        menu.addAction(self.rmAction)
        menu.addAction(self.exportAction)
        menu.addAction(self.saveAction)
        menu.addAction(self.newAction)
        menu.exec_(event.globalPos())

    def updateGraphics(self, graphics):
        self.graphics = {}
        while self.graphicsTable.rowCount() > 0:
            self.graphicsTable.removeRow(0)
        if isinstance(graphics, tuple):
            graphics = graphics[1]
        for graphic in graphics.items():
            self.addGraphic(graphic)

    def refreshGraphics(self):
        self.parent.updateWidgets()

    def addGraphic(self, graphic):
        self.graphics[graphic[0]] = graphic[1]
        itemID = QTableWidgetItem(QString(str(graphic[0])))
        itemID.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        itemDevice = QTableWidgetItem(QString(graphic[1]))
        itemDevice.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
        itemDevice.setFlags(Qt.ItemIsSelectable|Qt.ItemIsEnabled)
        row = self.graphicsTable.rowCount()
        self.graphicsTable.insertRow(row)
        self.graphicsTable.setItem(row, 0, itemID)
        self.graphicsTable.setItem(row, 1, itemDevice)
        self.graphicsTable.resizeColumnsToContents
      
    def selectionChanged(self):
        row = self.graphicsTable.currentRow()
        if row < 0 or row >= self.graphicsTable.rowCount() or \
        self.graphicsTable.rowCount() < 1:
            self.saveAction.setEnabled(False)
            self.rmAction.setEnabled(False)
            self.exportAction.setEnabled(False)
        else:
            itemName, itemType = self.getGraphicInfo(row)
            self.saveAction.setEnabled(True)
            self.rmAction.setEnabled(True)
            self.exportAction.setEnabled(True)

    def removeGraphic(self):
        row = self.graphicsTable.currentRow()
        if row < 0:
            return False
        itemID, itemDevice = self.getGraphicInfo(row)
        self.graphicsTable.removeRow(row)
        self.sendCommands(QString('dev.off(%s)' % (itemID)))

    def newGraphic(self):
      self.sendCommands(QString('dev.new()'))
        
    def exportGraphic(self):
        row = self.graphicsTable.currentRow()
        if row < 0:
            return False
        itemID, itemDevice = self.getGraphicInfo(row)
        #self.connect(fd, SIGNAL("filterSelected(QString)"), self.setFilter)
        fd = QFileDialog(self.parent, "Save graphic to file", "", \
        "PNG (*.png);;JPEG (*.jpeg);;TIFF (*.TIFF);;BMP (*.bmp)")
        fd.setAcceptMode(QFileDialog.AcceptSave)
        if not fd.exec_() == QDialog.Accepted:
            return False
        files = fd.selectedFiles()
        selectedFile = files.first()
        if selectedFile.length() == 0:
            return False
        suffix = QString(fd.selectedNameFilter())
        index1 = suffix.lastIndexOf("(")+2
        index2 = suffix.lastIndexOf(")")
        suffix = suffix.mid(index1, index2-index1)
        if not selectedFile.endsWith(suffix):
            selectedFile.append(suffix)
        command = QString('dev.set(' + itemID + ')')
        self.sendCommands(command)
        command = QString('dev.copy(%s, filename = "%s", ' % (suffix.remove("."), selectedFile))
        command.append('width = dev.size("px")[1], height = dev.size("px")[2], ')
        command.append('units = "px", bg = "transparent")')
        self.sendCommands(command)
        command = QString('dev.off()')
        self.sendCommands(command)
      
    def saveGraphic(self):
        row = self.graphicsTable.currentRow()
        if row < 0:
            return False
        itemID, itemDevice = self.getGraphicInfo(row)
        fd = QFileDialog(self.parent, "Save R  graphic to file", "", \
        "PDF (*.pdf);;EPS (*.eps);;SVG (*.svg)")
        fd.setAcceptMode(QFileDialog.AcceptSave)
        if not fd.exec_() == QDialog.Accepted:
            return False
        files = fd.selectedFiles()
        selectedFile = files.first()
        if selectedFile.length() == 0:
            return False
        suffix = QString(fd.selectedNameFilter())
        index1 = suffix.lastIndexOf("(")+2
        index2 = suffix.lastIndexOf(")")
        suffix = suffix.mid(index1, index2-index1)
        if not selectedFile.endsWith(suffix):
            selectedFile.append(suffix)
        suffix = suffix.remove(".")
        if suffix == "eps": suffix = "postscript"
        command = QString('dev.set(%s)' % (itemID))
        self.sendCommands(command)
        command = QString('dev.copy(%s, file = "%s")'% (suffix, selectedFile))
        self.sendCommands(command)
        command = QString('dev.off()')
        self.sendCommands(command)
        
    def getGraphicInfo(self, row):
        itemID = self.graphicsTable.item(row, 0)
        itemID = itemID.data(Qt.DisplayRole).toString()
        itemDevice = self.graphicsTable.item(row, 1)
        itemDevice = itemDevice.data(Qt.DisplayRole).toString()
        return (itemID, itemDevice)
      
    def sendCommands(self, commands):
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            MainWindow.Console.editor.moveToEnd()
            MainWindow.Console.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            MainWindow.Console.editor.cursor.removeSelectedText()
            MainWindow.Console.editor.cursor.insertText(
            MainWindow.Console.editor.currentPrompt)
            MainWindow.Console.editor.insertFromMimeData(mime)
            MainWindow.Console.editor.entered()

class MainWindow(QMainWindow):

    NextId = 1
    Instances = set()
    Console = None

    def __init__(self, iface, version, filename=QString(),
                isConsole=True, parent=None):
        super(MainWindow, self).__init__(parent)
        self.Toolbars = {}
        MainWindow.Instances.add(self)
        self.setWindowTitle("manageR[*]")
        self.setWindowIcon(QIcon(":mActionIcon"))
        self.version = version
        self.iface = iface
        if isConsole:
            pixmap = QPixmap(":splash.png")
            splash = QSplashScreen(pixmap)
            splash.show()
            splash.showMessage("Starting manageR!", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            QApplication.processEvents()
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.editor = RConsole(self)
            MainWindow.Console = self
            self.editor.append(welcomeString(self.version))
            self.editor.setFocus(Qt.ActiveWindowFocusReason)
            self.connect(self.editor, SIGNAL("commandComplete()"),self.updateWidgets)
        else:
            self.setAttribute(Qt.WA_DeleteOnClose)
            self.editor = REditor(self, int(Config["tabwidth"]))
        self.setCentralWidget(self.editor)
        if Config["enableautocomplete"]:
            self.completer = RCompleter(self.editor,
            delay=Config["delay"])
        if Config["enablehighlighting"]:                
            self.highlighter = RHighlighter(self.editor, isConsole)
            palette = QPalette(QColor(Config["backgroundcolor"]))
            palette.setColor(QPalette.Active, QPalette.Base, QColor(Config["backgroundcolor"]))
            self.editor.setPalette(palette)
            #self.editor.setTextColor(QColor(Config["normalfontcolor"]))
        self.finder = RFinder(self, self.editor)
        self.finderDockWidget = QDockWidget("Find and Replace Toolbar", self)          
        self.finderDockWidget.setObjectName("findReplace")
        self.finderDockWidget.setAllowedAreas(Qt.BottomDockWidgetArea)
        self.finderDockWidget.setWidget(self.finder)
        self.setCorner(Qt.BottomRightCorner, Qt.BottomDockWidgetArea)
        self.addDockWidget(Qt.BottomDockWidgetArea, self.finderDockWidget)

        fileNewAction = self.createAction("&New File", self.fileNew,
                QKeySequence.New, "mActionFileNew", "Create a R script")
        fileOpenAction = self.createAction("&Open...", self.fileOpen,
                QKeySequence.Open, "mActionFileOpen",
                "Open an existing R script")
        if not isConsole:
            fileSaveAction = self.createAction("&Save", self.fileSave,
                    QKeySequence.Save, "mActionFileSave", "Save R script")
            fileSaveAsAction = self.createAction("Save &As...",
                    self.fileSaveAs, icon="mActionFileSaveAs",
                    tip="Save R script using a new filename")
            fileCloseAction = self.createAction("&Close", self.close,
                    QKeySequence.Close, "mActionFileClose",
                    "Close this editR window")
        fileSaveAllAction = self.createAction("Save A&ll",
                self.fileSaveAll, icon="mActionFileSaveAll",
                tip="Save all R scripts")
        fileConfigureAction = self.createAction("Config&ure...",
                self.fileConfigure, icon="mActionFileConfigure",
                tip="Configure manageR")
        fileQuitAction = self.createAction("&Quit", self.fileQuit,
                "Ctrl+Q", "mActionFileQuit", "Close manageR")
        if not isConsole:
            editUndoAction = self.createAction("&Undo", self.editor.undo,
                    QKeySequence.Undo, "mActionEditUndo",
                    "Undo last editing action")
            editRedoAction = self.createAction("&Redo", self.editor.redo,
                    QKeySequence.Redo, "mActionEditRedo",
                    "Redo last editing action")
        editCopyAction = self.createAction("&Copy", self.editor.copy,
                QKeySequence.Copy, "mActionEditCopy",
                "Copy text to clipboard")
        editCutAction = self.createAction("Cu&t", self.editor.cut,
                QKeySequence.Cut, "mActionEditCut",
                "Cut text to clipboard")
        editPasteAction = self.createAction("&Paste",
                self.editor.paste, QKeySequence.Paste, "mActionEditPaste",
                "Paste from clipboard")
        editSelectAllAction = self.createAction("Select &All",
                self.editor.selectAll, QKeySequence.SelectAll,
                "mActionEditSelectAll", "Select all text")
        if Config["enableautocomplete"]:
            editCompleteAction = self.createAction("Com&plete",
                self.forceSuggest, "Ctrl+Space", "mActionEditComplete",
                "Initiate autocomplete suggestions")
        editFindNextAction = self.createAction("&Find",
                self.toggleFind, QKeySequence.Find,
                "mActionEditFindNext",
                "Find the next occurrence of the given text")
        if not isConsole:
            editReplaceNextAction = self.createAction("&Replace",
                    self.toggleFind, QKeySequence.Replace,
                    "mActionEditReplaceNext",
                    "Replace the next occurrence of the given text")
            editGotoLineAction =  self.createAction("&Go to line",
                    self.editor.gotoLine, "Ctrl+G", "mActionEditGotoLine",
                    "Move the cursor to the given line")
            editIndentRegionAction = self.createAction("&Indent Region",
                    self.editor.indentRegion, "Tab", "mActionEditIndent",
                    "Indent the selected text or the current line")
            editUnindentRegionAction = self.createAction(
                    "Unin&dent Region", self.editor.unindentRegion,
                    "Shift+Tab", "mActionEditUnindent",
                    "Unindent the selected text or the current line")
            editCommentRegionAction = self.createAction("C&omment Region",
                    self.editor.commentRegion, "Ctrl+D", "mActionEditComment",
                    "Comment out the selected text or the current line")
            editUncommentRegionAction = self.createAction(
                    "Uncomment Re&gion", self.editor.uncommentRegion,
                    "Ctrl+Shift+D", "mActionEditUncomment",
                    "Uncomment the selected text or the current line")
            actionRunAction = self.createAction("E&xecute",
                    self.editor.execute, "Ctrl+Return", "mActionRun",
                    "Execute the (selected) text in the manageR console")
        else:
            actionShowPrevAction = self.createAction(
                    "Show Previous Command", self.editor.showNext,
                    "Up", "mActionPrevious",
                    ("Show previous command"))
            actionShowNextAction = self.createAction(
                    "Show Next Command", self.editor.showPrevious,
                    "Down", "mActionNext",
                    ("Show next command"))
            actionImportAttibutesAction = self.createAction(
                    "Import layer attributes", self.importLayerAttributes,
                    "Ctrl+T", "mActionActionTable",
                    ("Import layer attributes"))
            actionImportLayerAction = self.createAction(
                    "Import layer from canvas", self.importRObjects,
                    "Ctrl+L", "mActionActionImport",
                    ("Import layer from canvas"))
            actionExportCanvasAction = self.createAction(
                    "Export layer to canvas", self.exportRObjects,
                    "Ctrl+M", "mActionActionExport",
                    ("Export layer to canvas"))
            actionExportFileAction = self.createAction(
                    "Export layer to file", self.exportToFile,
                    "Ctrl+D", "mActionActionFile",
                    ("Export layer to file"))
            workspaceLoadAction = self.createAction(
                    "Load R workspace", self.loadRWorkspace,
                    "Ctrl+Shift+W", "mActionWorkspaceLoad",
                    ("Load R workspace"))
            workspaceSaveAction = self.createAction(
                    "Save R workspace", self.saveRWorkspace,
                    "Ctrl+W", "mActionWorkspaceSave",
                    ("Save R workspace"))
                    
        helpHelpAction = self.createAction("&Help", self.helpHelp,
                QKeySequence.HelpContents, icon="mActionHelpHelp",
                tip="Commands help")
        helpAboutAction = self.createAction("&About", self.helpAbout,
                icon="mActionIcon", tip="About manageR")

        fileMenu = self.menuBar().addMenu("&File")
        self.addActions(fileMenu, (fileNewAction,))
        #if not isConsole:
            #self.addActions(fileMenu, (fileNewConsoleAction,))
        self.addActions(fileMenu, (fileOpenAction,))
        if not isConsole:
            self.addActions(fileMenu, (fileSaveAction, fileSaveAsAction))
        self.addActions(fileMenu, (fileSaveAllAction, None,
                fileConfigureAction, None,))
        if not isConsole:
            self.addActions(fileMenu, (fileCloseAction,))
        self.addActions(fileMenu, (fileQuitAction,))

        editMenu = self.menuBar().addMenu("&Edit")
        if not isConsole:
            self.addActions(editMenu, (editUndoAction, editRedoAction, None,))
        self.addActions(editMenu, (editCopyAction, editCutAction, editPasteAction,
                                   editSelectAllAction, None, editFindNextAction,))
        if not isConsole:
            self.addActions(editMenu, (editReplaceNextAction, editGotoLineAction, 
                None, editIndentRegionAction,
                editUnindentRegionAction, editCommentRegionAction,
                editUncommentRegionAction))
        if Config["enableautocomplete"]:
            self.addActions(editMenu, (None, editCompleteAction,))
        actionMenu = self.menuBar().addMenu("&Action")
        if not isConsole:
            self.addActions(actionMenu, (actionRunAction,))
        else:
            self.addActions(actionMenu, (actionShowPrevAction, actionShowNextAction,
            actionImportLayerAction, actionImportAttibutesAction,
            actionExportCanvasAction, actionExportFileAction,))
            workspaceMenu = self.menuBar().addMenu("Wo&rkspace")
            self.addActions(workspaceMenu, (workspaceLoadAction, 
            workspaceSaveAction))
            try:
                pluginsMenu = self.menuBar().addMenu("A&nalysis")
                pluginCreator = PluginManager(self)
                pluginCreator.createActions(pluginsMenu)
            except Exception, e:
                message = QMessageBox(self)
                message.setWindowTitle("manageR load error")
                message.setText("Error generating plugin interfaces.\n"
                "Please ensure that your tools.xml file is correctly formatted.")
                message.setInformativeText("Note: Analysis plugins will be disabled for "
                "the current manageR session." )
                message.setDetailedText(str(e))
                message.exec_()
                pluginsMenu.deleteLater()
        self.viewMenu = self.menuBar().addMenu("&View")
        self.windowMenu = self.menuBar().addMenu("&Window")
        self.connect(self.windowMenu, SIGNAL("aboutToShow()"),
                     self.updateWindowMenu)
        helpMenu = self.menuBar().addMenu("&Help")
        self.addActions(helpMenu, (helpHelpAction, helpAboutAction,))

        self.fileToolbar = self.addToolBar("File Toolbar")
        self.fileToolbar.setObjectName("FileToolbar")
        self.Toolbars[self.fileToolbar] = None
        self.addActions(self.fileToolbar, (fileNewAction, fileOpenAction))
        if not isConsole:
            self.addActions(self.fileToolbar, (fileSaveAction,))
        self.editToolbar = self.addToolBar("Edit Toolbar")
        self.editToolbar.setObjectName("EditToolbar")
        self.Toolbars[self.editToolbar] = None
        if not isConsole:
            self.addActions(self.editToolbar, (editUndoAction, editRedoAction,
                                               None,))
        self.addActions(self.editToolbar, (editCopyAction, editCutAction, editPasteAction,
                                           None, editFindNextAction,))
        if not isConsole:
            self.addActions(self.editToolbar, (editReplaceNextAction, None,
                    editIndentRegionAction, editUnindentRegionAction,
                    editCommentRegionAction, editUncommentRegionAction))
        self.actionToolbar = self.addToolBar("Action Toolbar")
        self.actionToolbar.setObjectName("ActionToolbar")
        self.Toolbars[self.actionToolbar] = None
        if not isConsole:
            self.addActions(self.actionToolbar, (actionRunAction,))
        else:
            self.addActions(self.actionToolbar, (None, actionShowPrevAction, 
                actionShowNextAction, None, actionImportLayerAction, 
                actionImportAttibutesAction, actionExportCanvasAction,
                actionExportFileAction,))
        if isConsole:
            workspaceToolbar = self.addToolBar("Workspace Toolbar")
            workspaceToolbar.setObjectName("WorkspaceToolbar")
            self.Toolbars[workspaceToolbar] = None
            self.addActions(workspaceToolbar, (workspaceLoadAction, 
            workspaceSaveAction,))
            action = self.viewMenu.addAction("&%s" % workspaceToolbar.windowTitle())
            self.connect(action, SIGNAL("toggled(bool)"),
                         self.toggleToolbars)
            action.setCheckable(True)
            self.Toolbars[workspaceToolbar] = action
        for toolbar in (self.fileToolbar, self.editToolbar,
                        self.actionToolbar):
            action = self.viewMenu.addAction("&%s" % toolbar.windowTitle())
            self.connect(action, SIGNAL("toggled(bool)"),
                         self.toggleToolbars)
            action.setCheckable(True)
            self.Toolbars[toolbar] = action
        action = self.finderDockWidget.toggleViewAction()
        self.connect(action, SIGNAL("toggled(bool)"), self.toggleToolbars)
        action.setCheckable(True)
        self.viewMenu.addAction(action)
        self.Toolbars[self.finderDockWidget] = action
        if isConsole:
            self.finderDockWidget.setWindowTitle("Find Toolbar")
            self.finder.hideReplace()
        self.connect(self, SIGNAL("destroyed(QObject*)"),
                     MainWindow.updateInstances)

        status = self.statusBar()
        status.setSizeGripEnabled(False)
        status.showMessage("Ready", 5000)
        if not isConsole:
            self.columnCountLabel = QLabel("(empty)")
            status.addPermanentWidget(self.columnCountLabel)
            self.lineCountLabel = QLabel("(empty)")
            status.addPermanentWidget(self.lineCountLabel)
            self.connect(self.editor,
                         SIGNAL("cursorPositionChanged()"),
                         self.updateIndicators)
            self.connect(self.editor.document(),
                         SIGNAL("blockCountChanged(int)"),
                         self.updateIndicators)
        if Config["remembergeometry"]:
            if isConsole:
                self.resize(Config["consolewidth"], Config["consoleheight"])
                self.move(Config["consolex"], Config["consoley"])
            else:
                self.resize(Config["windowwidth"],
                            Config["windowheight"])
                if int(isConsole) + len(MainWindow.Instances) <= 2:
                    self.move(Config["windowx"], Config["windowy"])

        self.restoreState(Config["toolbars"])
        self.filename = QString("")
        if isConsole:
            self.setWindowTitle("manageR")
        else:
            self.filename = filename
            if self.filename.isEmpty():
                while QFileInfo(QString("untitled%d.R" %
                                            MainWindow.NextId)).exists():
                    MainWindow.NextId += 1
                self.filename = QString("untitled%d.R" %
                                               MainWindow.NextId)
                self.editor.setText(Config["newfile"])
                self.editor.moveCursor(QTextCursor.End)
                self.editor.document().setModified(False)
                self.setWindowModified(False)
                self.setWindowTitle("editR - %s[*]" % self.filename)
            else:
                self.loadFile()
            self.connect(self.editor, SIGNAL("textChanged()"),
                         self.updateDirty)

        if isConsole:
            # If requested, set/change working directory
            if not QString(Config["setwd"]).isEmpty() or \
            not QString(Config["setwd"]) == ".":
                splash.showMessage("Setting default working directory", \
                (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
                QApplication.processEvents()
                self.editor.execute(QString('setwd("%s")' % (Config["setwd"])))
                cursor = self.editor.textCursor()
                cursor.movePosition(QTextCursor.StartOfLine,
                QTextCursor.KeepAnchor)
                cursor.removeSelectedText()
            # Process required R frontend tasks (load workspace and history)
            splash.showMessage("Checking for previously saved workspace", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            QApplication.processEvents()
            workspace = QFileInfo()
            workspace.setFile(QDir(robjects.r['getwd']()[0]), ".RData")
            if workspace.exists():
                if self.loadRWorkspace(workspace.absoluteFilePath()):
                    self.editor.append("[Previously saved workspace restored]\n\n")
                else:
                    self.editor.append("Error: Unable to load previously saved workspace:"
                                     "\nCreating new workspace...\n\n")
            splash.showMessage("Checking for history file", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            if self.editor.loadRHistory():
                QApplication.processEvents()
            self.editor.displayPrompt()
            # If requested, execute startup commands
            if not QString(Config["consolestartup"]).isEmpty():
                splash.showMessage("Executing startup commands", \
                (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
                QApplication.processEvents()
                mime = QMimeData()
                mime.setText(Config["consolestartup"])
                self.editor.insertFromMimeData(mime)
                self.editor.entered()
                #self.editor.execute(QString(Config["consolestartup"]))
            # If requested, load all default library functions into CAT
            if Config["enableautocomplete"]:
                splash.showMessage("Loading default library commands", \
                    (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
                QApplication.processEvents()
                for library in robjects.r('.packages()'):
                    addLibraryCommands(library)
            self.createConsoleWidgets()
            splash.showMessage("manageR ready!", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            splash.finish(self)
        QTimer.singleShot(0, self.updateToolbars)
        self.startTimer(50)
        
    def createConsoleWidgets(self):
        graphicWidget = RGraphicsWidget(self)
        graphicWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"),
        graphicWidget.updateGraphics)
        graphicDockWidget = QDockWidget("Graphic Device Manager", self)          
        graphicDockWidget.setObjectName("graphicDockWidget")
        graphicDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        graphicDockWidget.setWidget(graphicWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, graphicDockWidget)
        
        variableWidget = RVariableWidget(self)
        variableWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"),
        variableWidget.updateVariables)
        variableDockWidget = QDockWidget("Workspace Manager", self)          
        variableDockWidget.setObjectName("variableDockWidget")
        variableDockWidget.setAllowedAreas(Qt.RightDockWidgetArea|Qt.LeftDockWidgetArea)
        variableDockWidget.setWidget(variableWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, variableDockWidget)
        
        historyWidget = RHistoryWidget(self, self.editor)
        historyWidget.connect(self.editor, SIGNAL("updateHistory(PyQt_PyObject)"),
        historyWidget.updateCommands)
        historyDockWidget = QDockWidget("Command History Manager", self)          
        historyDockWidget.setObjectName("historyDockWidget")
        historyDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        historyDockWidget.setWidget(historyWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, historyDockWidget)
        
        cwdWidget = RWDWidget(self,robjects.r('getwd()')[0])
        cwdWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"), cwdWidget.displayWorkingDir)
        cwdDockWidget = QDockWidget("Working Directory Manager", self)
        cwdDockWidget.setObjectName("cwdDockWidget")
        cwdDockWidget.setAllowedAreas(Qt.TopDockWidgetArea|Qt.BottomDockWidgetArea)
        cwdDockWidget.setWidget(cwdWidget)
        self.addDockWidget(Qt.TopDockWidgetArea, cwdDockWidget)
        
        self.tabifyDockWidget(variableDockWidget, graphicDockWidget)
        self.tabifyDockWidget(graphicDockWidget, historyDockWidget)

        for widget in [cwdDockWidget, variableDockWidget, 
                       graphicDockWidget, historyDockWidget,]:
            action = widget.toggleViewAction()
            self.connect(action, SIGNAL("toggled(bool)"), self.toggleToolbars)
            action.setCheckable(True)
            self.viewMenu.addAction(action)
            self.Toolbars[widget] = action
        self.updateWidgets()
            
    def updateWidgets(self):
        self.emit(SIGNAL("updateDisplays(PyQt_PyObject)"),currentRObjects())

    def timerEvent(self, e):
        try:
            robjects.rinterface.process_revents()
        except:
            pass
        
    def forceSuggest(self):
        self.completer.suggest(1)

    def toggleFind(self):
        title = self.sender().text()
        toolbar = self.Toolbars[self.finderDockWidget]
        text = self.editor.textCursor().selectedText()
        if not text.isEmpty():
            self.finder.edit.setText(text)
        if not toolbar.isChecked():
            toolbar.setChecked(True)
            self.finder.setFocus()
        elif not self.finder.hasFocus():
            self.finder.setFocus()
        if title == "&Replace":
            self.finder.showReplace()
        else:
            self.finder.hideReplace()

    def loadRWorkspace(self, workspace=None):
        if workspace is None:
            fd = QFileDialog(self, "Open R workspace", 
            robjects.r['getwd']()[0],
            "R workspace (*.RData);;All files (*)")
            fd.setAcceptMode(QFileDialog.AcceptOpen)
            fd.setFilter(QDir.Hidden|QDir.Dirs|QDir.Files)
            if not fd.exec_() == QDialog.Accepted:
                return False
            files = fd.selectedFiles()
            workspace = files.first()
            if workspace.length() == 0:
                return False
        try:
            if not workspace.isEmpty():
                robjects.r['load'](unicode(workspace))
                self.updateWidgets()
        except Exception, e: 
            return False
        return True
        
    def saveRWorkspace(self, workspace=None):
        if workspace is None:
            fd = QFileDialog(self, "Save R workspace", 
            robjects.r['getwd']()[0],
            "R workspace (*.RData);;All files (*)")
            fd.setAcceptMode(QFileDialog.AcceptSave)
            fd.setFilter(QDir.Hidden|QDir.Dirs|QDir.Files)
            if not fd.exec_() == QDialog.Accepted:
                return False
            files = fd.selectedFiles()
            workspace = files.first()
            if workspace.length() == 0:
                return False
        try:
            if not workspace.isEmpty():
                robjects.r['save.image'](unicode(workspace))
        except Exception, e: 
            return False
        return True
        
    def importLayerAttributes(self):
        self.importRObjects(dataOnly=True)
        
    def importRObjects(self, mlayer=None, dataOnly=False):
        if mlayer is None:
            mlayer = self.iface.mapCanvas().currentLayer()
        self.statusBar().showMessage(
        "Importing data from canvas...")
        MainWindow.Console.editor.moveToEnd()
        MainWindow.Console.editor.cursor.movePosition(
        QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        MainWindow.Console.editor.cursor.removeSelectedText()
        MainWindow.Console.editor.cursor.insertText(
        "%smanageR import function" % (MainWindow.Console.editor.currentPrompt))
        QApplication.processEvents()
        try:
            if mlayer is None:
                MainWindow.Console.editor.commandError(
                "Error: No layer selected in layer list")
                MainWindow.Console.editor.commandComplete()
                return
            rbuf = QString()
            def f(x):
                rbuf.append(x)
            robjects.rinterface.setWriteConsole(f)
            if not dataOnly and not isLibraryLoaded("sp"):
                raise Exception(RLibraryError("sp"))
            if mlayer.type() == QgsMapLayer.VectorLayer:
                layerCreator = QVectorLayerConverter(mlayer, dataOnly)
            if mlayer.type() == QgsMapLayer.RasterLayer:
                if dataOnly:
                    MainWindow.Console.editor.commandError(
                    "Error: Cannot load raster layer attributes")
                    MainWindow.Console.editor.commandComplete()
                    return
                if not isLibraryLoaded("rgdal"):
                    raise Exception(RLibraryError("sp"))
                layerCreator = QRasterLayerConverter(mlayer)
            MainWindow.Console.editor.commandOutput(rbuf)
            rLayer, layerName, message = layerCreator.start()
            robjects.globalEnv[str(layerName)] = rLayer
            if not str(layerName) in CAT:
                CAT.append(str(layerName))
            #self.emit(SIGNAL("newObjectCreated(PyQt_PyObject)"), \
            #self.updateRObjects())
            MainWindow.Console.editor.commandOutput(message)
        except Exception, e:
            MainWindow.Console.editor.commandError(e)
        MainWindow.Console.editor.commandComplete()
        
    def exportToFile(self):
        self.exportRObjects(True)
      
    def exportRObjects(self, toFile=False, exportLayer=None, exportType=None, ask=True):
        if toFile:
            self.statusBar().showMessage("Exporting data to file...")
        else:
            self.statusBar().showMessage("Exporting data to canvas...")
        MainWindow.Console.editor.moveToEnd()
        MainWindow.Console.editor.cursor.movePosition(
        QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        MainWindow.Console.editor.cursor.removeSelectedText()
        MainWindow.Console.editor.switchPrompt()
        MainWindow.Console.editor.cursor.insertText(
        "%smanageR export function" % (MainWindow.Console.editor.currentPrompt))
        QApplication.processEvents()
        try:
            if ask:
                result = self.exportRObjectsDialog(toFile)
                if not result is None and not result is False:
                    result, exportLayer, exportType = result
            else:
                result = True
            # If there is no input layer, don't do anything
            if result is None: # this needs to be updated to reflect where we get the R objects from...
                MainWindow.Console.editor.commandError(
                "Error: No R spatial objects available")
                MainWindow.Console.editor.commandComplete()
                return
            if not result:
                MainWindow.Console.editor.commandComplete()
                return
            if not toFile and not isLibraryLoaded("sp"):
                raise Exception(RLibraryError("sp"))
            if toFile and not isLibraryLoaded("rgdal"):
                raise Exception(RLibraryError("rgdal"))
            if not exportType in VECTORTYPES and not exportType in RASTERTYPES:
                MainWindow.Console.editor.commandError(
                "Error: Unrecognised sp object, unable to save to file.")
                MainWindow.Console.editor.commandComplete()
                return
            if not toFile and exportType in RASTERTYPES:
                MainWindow.Console.editor.commandError(
                "Error: Unable to export raster layers to map canvas at this time.")
                MainWindow.Console.editor.commandComplete()
                return
            if not toFile:
                if exportType in VECTORTYPES:
                    layerCreator = RVectorLayerConverter(robjects.r[unicode(exportLayer)], exportLayer)
            else:
                if exportType in VECTORTYPES:
                    drivers = "ESRI Shapefile (*.shp);;MapInfo File (*.mif);;GML (*.gml);;KML (*.kml)"
                else:
                    drivers = "GeoTIFF (*.tif);;Erdas Imagine Images (*.img);;Arc/Info ASCII Grid " \
                    + "(*.asc);;ENVI Header Labelled (*.hdr);;JPEG-2000 part 1 (*.jp2);;Portable " \
                    + "Network Graphics (*.png);;USGS Optional ASCII DEM (*.dem)"
                fileDialog = QFileDialog()
                fileDialog.setConfirmOverwrite(True)
                driver = QString()
                layerName = fileDialog.getSaveFileName(self, "Save OGR",".", drivers, driver)
                if not layerName.isEmpty():
                    fileCheck = QFile(layerName)
                    if fileCheck.exists():
                        if not QgsVectorFileWriter.deleteShapeFile(layerName):
                            MainWindow.Console.editor.commandError(
                            "Error: Unable to overwrite existing file")
                            MainWindow.Console.editor.commandComplete()
                            return
                if exportType in VECTORTYPES:
                    layerCreator = RVectorLayerWriter(unicode(exportLayer), layerName, driver)
                else:
                    layerCreator = RRasterLayerWriter(unicode(exportLayer), layerName, driver)
            layer = layerCreator.start()
            if toFile:
                add = False
                message = "Created file:\n%s" % (layer.source())
                add = QMessageBox.question(self, "manageR", "Would you like to add the new layer to the map canvas?",
                QMessageBox.Yes, QMessageBox.No, QMessageBox.NoButton)
            else:
                add = True
                message = layer.name()+" exported to canvas"
            if add == QMessageBox.Yes or not toFile:
                QgsMapLayerRegistry.instance().addMapLayer(layer)
        except Exception, e:
            MainWindow.Console.editor.commandError(e)
        MainWindow.Console.editor.commandComplete()
  
    def exportRObjectsDialog(self, toFile):
        exportLayer = None
        exportType = None
        dialog = QDialog(self)
        layers = QComboBox(dialog)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok|QDialogButtonBox.Cancel, 
        Qt.Horizontal, dialog)
        dialog.connect(buttons, SIGNAL("rejected()"), dialog.reject)
        dialog.connect(buttons, SIGNAL("accepted()"), dialog.accept)
        r_layers = currentRObjects()[0]
        if not r_layers:
            return None
        found = False
        for layer in r_layers.keys():
            if r_layers[layer] in VECTORTYPES or \
            r_layers[layer] in RASTERTYPES:
                found = True
                layers.addItem(unicode(layer))
        if not found:
            return None
        vbox = QVBoxLayout()
        vbox.addWidget(layers)
        vbox.addWidget(buttons)
        dialog.setLayout(vbox)
        dialog.setWindowTitle('Export R Layer')
        if not dialog.exec_() == QDialog.Accepted:
            return False
        exportLayer = layers.currentText()
        exportType = r_layers[unicode(exportLayer)]
        return True, exportLayer, exportType

    @staticmethod
    def updateInstances(qobj):
        MainWindow.Instances = set([window for window
                in MainWindow.Instances if isAlive(window)])

    def createAction(self, text, slot=None, shortcut=None, icon=None,
                     tip=None, checkable=False, signal="triggered()",
                     param=None):
        action = QAction(text, self)
        if icon is not None:
            action.setIcon(QIcon(":%s.png" % icon))
        if shortcut is not None:
            action.setShortcut(shortcut)
        if tip is not None:
            action.setToolTip(tip)
            action.setStatusTip(tip)
        if slot is not None:
            if param is not None:
                self.connect(action, SIGNAL(signal), slot, param)
            else:
                self.connect(action, SIGNAL(signal), slot)
        if checkable:
            action.setCheckable(True)
        return action


    def addActions(self, target, actions):
        for action in actions:
            if action is None:
                target.addSeparator()
            else:
                target.addAction(action)

    def updateDirty(self):
        self.setWindowModified(self.editor.document().isModified())

    def updateIndicators(self):
        lines = self.editor.document().blockCount()
        cursor = self.editor.textCursor()
        self.columnCountLabel.setText("Column %d" % (
                cursor.columnNumber() + 1))
        if lines == 0:
            text = "(empty)"
        else:
            text = "Line %d of %d " % (cursor.blockNumber() + 1, lines)
        self.lineCountLabel.setText(text)

    def updateToolbars(self):
        for toolbar, action in self.Toolbars.items():
            action.setChecked(toolbar.isVisible())

    def toggleToolbars(self, on):
        title = self.sender().text()
        for toolbar, action in self.Toolbars.items():
            if action.text() == title:
                toolbar.setVisible(on)
                action.setChecked(on)

    def closeEvent(self, event):
        if self == MainWindow.Console:
            ask_save = QMessageBox.question(self, "manageR - Quit", "Save workspace image?", 
            QMessageBox.Yes, QMessageBox.No, QMessageBox.Cancel)
            if ask_save == QMessageBox.Cancel:
                event.ignore()
                return
            elif ask_save == QMessageBox.Yes:
                self.saveRWorkspace(".RData")
                self.editor.saveRHistory()
                robjects.r('rm(list=ls(all=T))')
                robjects.r('gc()')
                try:
                    robjects.r('graphics.off()')
                except:
                    try:
                      for i in list(robjects.r('dev.list()')):
                        robjects.r('dev.next()')
                        robjects.r('dev.off()')
                    except:
                      pass
            if Config["remembergeometry"]:
                Config["consolewidth"] = self.width()
                Config["consoleheight"] = self.height()
                Config["consolex"] = self.x()
                Config["consoley"] = self.y()
            for window in MainWindow.Instances:
                if isAlive(window):
                    window.close()
        else:
            if self.editor.document().isModified():
                reply = QMessageBox.question(self,
                        "editR - Unsaved Changes",
                        "Save unsaved changes in %s" % self.filename,
                        QMessageBox.Save|QMessageBox.Discard|
                        QMessageBox.Cancel)
                if reply == QMessageBox.Save:
                    self.fileSave()
                elif reply == QMessageBox.Cancel:
                    event.ignore()
                    return
                # else accept and discard
            if Config["remembergeometry"]:
                Config["windowwidth"] = self.width()
                Config["windowheight"] = self.height()
                Config["windowx"] = self.x()
                Config["windowy"] = self.y()
            if self.finder is not None:
                Config["findcasesensitive"] = (self.finder
                        .case_sensitive.isChecked())
                Config["findwholewords"] = (self.finder
                        .whole_words.isChecked())
        Config["toolbars"] = self.saveState()
        saveConfig()
        event.accept()      

    def fileConfigure(self):
        form = ConfigForm(self)
        if form.exec_():
            # Should only do this if the highlighting was actually
            # changed since it is computationally expensive.
            if form.highlightingChanged:
                font = QFont(Config["fontfamily"],
                                   Config["fontsize"])
                textcharformat = QTextCharFormat()
                textcharformat.setFont(font)
                RHighlighter.initializeFormats()
                for window in MainWindow.Instances:
                    if isAlive(window):
                        window.statusBar().showMessage("Rehighlighting...")
                        window.editor.setFont(font)
                        window.editor.textcharformat = (textcharformat)
                        if window.highlighter:
                            window.highlighter.rehighlight()
                        if window == MainWindow.Console:
                            window.editor.setPrompt(Config["beforeinput"]+" ",
                            Config["afteroutput"]+" ", True)
                        palette = QPalette(QColor(Config["backgroundcolor"]))
                        palette.setColor(QPalette.Active, 
                        QPalette.Base, QColor(Config["backgroundcolor"]))
                        window.editor.setPalette(palette)
                        window.statusBar().clearMessage()
            saveConfig()


    def fileQuit(self):
        for window in MainWindow.Instances:
            if isAlive(window) and window == MainWindow.Console:
                window.close()
                del window

    def fileNew(self):
        window = MainWindow(self.iface, self.version, isConsole=False)
        window.show()

    def fileOpen(self):
        if not self.filename.isEmpty():
            path = QFileInfo(self.filename).path()
        else:
            path = "."
        filename = QFileDialog.getOpenFileName(self,
                        "manageR - Open File", path,
                        "R scripts (*.R)\nAll files (*)")
        if not filename.isEmpty():
            # To prevent opening the same file twice
            for window in MainWindow.Instances:
                if isAlive(window) and window != MainWindow.Console:
                    if window.filename == filename:
                        window.activateWindow()
                        window.raise_()
                        return
            if (MainWindow.Console != self and
                not self.editor.document().isModified() and
                self.filename.startsWith("untitled")):
                self.filename = filename
                self.loadFile()
            else:
                MainWindow(self.iface, self.version, filename, isConsole=False).show()


    def loadFile(self):
        QApplication.setOverrideCursor(QCursor(Qt.WaitCursor))
        fh = None
        try:
            try:
                fh = QFile(self.filename)
                if not fh.open(QIODevice.ReadOnly):
                    raise IOError, unicode(fh.errorString())
                stream = QTextStream(fh)
                stream.setCodec("UTF-8")
                text = stream.readAll()
                self.editor.setPlainText(text)
                self.editor.document().setModified(False)
            except (IOError, OSError), e:
                QMessageBox.warning(self, "manageR - Load Error",
                        "Failed to load %s: %s" % (self.filename, e))
        finally:
            if fh is not None:
                fh.close()
            QApplication.restoreOverrideCursor()
        self.editor.document().setModified(False)
        self.setWindowModified(False)
        self.setWindowTitle("editR - %s[*]" %
                            QFileInfo(self.filename).fileName())


    def fileSave(self):
        if self.filename.startsWith("untitled"):
            return self.fileSaveAs()
        if (not Config["backupsuffix"].isEmpty() and
            QFile.exists(self.filename)):
            backup = self.filename + Config["backupsuffix"]
            ok = True
            if QFile.exists(backup):
                ok = QFile.remove(backup)
                if not ok:
                    QMessageBox.information(self,
                            "editR - Save Warning",
                            "Failed to remove the old backup %s")
            if ok:
                # Must use copy rather than rename to preserve file
                # permissions; could use rename on Windows though
                if not QFile.copy(self.filename, backup):
                    QMessageBox.information(self,
                            "editR - Save Warning",
                            "Failed to save a backup %s")
        fh = None
        try:
            try:
                fh = QFile(self.filename)
                if not fh.open(QIODevice.WriteOnly):
                    raise IOError, unicode(fh.errorString())
                stream = QTextStream(fh)
                stream.setCodec("UTF-8")
                stream << self.editor.toPlainText()
                self.editor.document().setModified(False)
                self.setWindowModified(False)
                self.setWindowTitle("editR - %s[*]" %
                        QFileInfo(self.filename).fileName())
                self.statusBar().showMessage("Saved %s" % self.filename,
                        5000)
            except (IOError, OSError), e:
                QMessageBox.warning(self, "editR - Save Error",
                        "Failed to save %s: %s" % (self.filename, e))
        finally:
            if fh is not None:
                fh.close()
        return True


    def fileSaveAs(self):
        filename = QFileDialog.getSaveFileName(self,
                            "editR - Save File As",
                            self.filename, "R scripts (*.R)")
        if not filename.isEmpty():
            self.filename = filename
            return self.fileSave()
        return False


    def fileSaveAll(self):
        count = 0
        for window in MainWindow.Instances:
            if (isAlive(window) and window != MainWindow.Console and
                window.editor.document().isModified()):
                if window.fileSave():
                    count += 1
        self.statusBar().showMessage("Saved %d of %d files" % (
                count, len(MainWindow.Instances) -
                       int(MainWindow.Console is not None)), 5000)

    def updateWindowMenu(self):
        self.windowMenu.clear()
        console = MainWindow.Console
        if console is not None and isAlive(console):
            action = self.windowMenu.addAction("&Console", self.raiseWindow)
            action.setData(QVariant(long(id(console))))
            action.setIcon(QIcon(":mActionConsole.png"))
        i = 1
        menu = self.windowMenu
        for window in MainWindow.Instances:
            if window != console and isAlive(window):
                text = (window.windowTitle().replace("manageR - ", "")
                                            .replace("[*]", ""))
                if i == 10:
                    self.windowMenu.addSeparator()
                    menu = menu.addMenu("&More")
                accel = ""
                if i < 10:
                    accel = "&%d " % i
                elif i < 36:
                    accel = "&%c " % chr(i + ord("@") - 9)
                text = "%s%s" % (accel, text)
                i += 1
                action = menu.addAction(text, self.raiseWindow)
                action.setData(QVariant(long(id(window))))
                action.setIcon(QIcon(":mActionWindow.png"))


    def raiseWindow(self):
        action = self.sender()
        if not isinstance(action, QAction):
            return
        windowId = action.data().toLongLong()[0]
        for window in MainWindow.Instances:
            if isAlive(window) and id(window) == windowId:
                window.activateWindow()
                window.raise_()
                break

    def helpHelp(self):
        HelpForm(self.version, self).show()

    def helpAbout(self):
        iconLabel = QLabel()
        icon = QPixmap(":mActionLogo.png")
        iconLabel.setPixmap(icon)
        nameLabel = QLabel("<font size=8 color=#0066CC>&nbsp;"
                                 "<b>manageR</b></font>")
        versionLabel = QLabel("<font color=#0066CC>"
                "%s on %s<br>"
                "manageR %s</font>" % (
                robjects.r.version[12][0], sys.platform,
                self.version))
        aboutLabel = QTextBrowser()
        aboutLabel.setOpenExternalLinks(True)
        aboutLabel.setHtml("""
<h3>Interface to the R statistical programming environment</h3>
Copyright &copy; 2009 Carson J. Q. Farmer
<br/>Carson.Farmer@gmail.com
<br/><a href='http://www.ftools.ca/manageR'>http://www.ftools.ca/manageR</a>
<br/>manageR adds comprehensive statistical capabilities to Quantum 
GIS by loosely coupling QGIS with the R statistical programming environment.
""")
        licenseLabel = QTextBrowser()
        licenseLabel.setOpenExternalLinks(True)
        licenseLabel.setHtml((__license__.replace("\n\n", "<p>")
                                         .replace("(c)", "&copy;")))

        tabWidget = QTabWidget()
        tabWidget.addTab(aboutLabel, "&About")
        tabWidget.addTab(licenseLabel, "&License")
        okButton = QPushButton("OK")

        layout = QVBoxLayout()
        hbox = QHBoxLayout()
        hbox.addWidget(iconLabel)
        hbox.addWidget(nameLabel)
        hbox.addStretch()
        hbox.addWidget(versionLabel)
        layout.addLayout(hbox)
        layout.addWidget(tabWidget)
        hbox = QHBoxLayout()
        hbox.addStretch()
        hbox.addWidget(okButton)
        hbox.addStretch()
        layout.addLayout(hbox)

        dialog = QDialog(self)
        dialog.setLayout(layout)
        dialog.setMinimumSize(
            min(self.width(),
                int(QApplication.desktop().availableGeometry()
                    .width() / 2)),
                int(QApplication.desktop().availableGeometry()
                    .height() / 2))
        self.connect(okButton, SIGNAL("clicked()"), dialog.accept)
        dialog.setWindowTitle("manageR - About")
        dialog.exec_()


def isAlive(qobj):
    import sip
    try:
        sip.unwrapinstance(qobj)
    except RuntimeError:
        return False
    return True


#def main():
    #if not hasattr(sys, "ps1"):
        #sys.ps1 = ">>> "
    #if not hasattr(sys, "ps2"):
        #sys.ps2 = "... "
    #app = QApplication(sys.argv)
    #if not sys.platform.startswith(("linux", "win")):
        #app.setCursorFlashTime(0)
    #app.setOrganizationName("manageR")
    #app.setOrganizationDomain("ftools.ca")
    #app.setApplicationName("manageR")
    #app.setWindowIcon(QIcon(":mActionIcon.png"))
    #loadConfig()

    #if len(sys.argv) > 1:
        #args = sys.argv[1:]
        #if args[0] in ("-h", "--help"):
            #args.pop(0)
            #print """usage: manageR.py [-n|filenames]
#-n or --new means start with new file
#filenames   means start with the given files (which must have .R suffixes);
#otherwise starts with console.
#manageR requires Python 2.5 and PyQt 4.2 (or later versions)
#For more information run the program and click
#Help->About and/or Help->Help"""
            #return
        #if args and args[0] in ("-n", "--new"):
            #args.pop(0)
            #MainWindow().show()
        #dir = QDir()
        #for fname in args:
            #if fname.endswith(".R"):
                #MainWindow(dir.cleanPath(
                        #dir.absoluteFilePath((fname)))).show()
    #if not MainWindow.Instances:
        #MainWindow(isConsole=True).show()
    #app.exec_()
    #saveConfig()

#main()

## TODO:
## Add tooltips to all ConfigForm editing widgets & improve validation
## Add tooltips to all main window actions that don't have any.

