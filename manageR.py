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

import os, re, sys, platform, base64
from xml.dom import minidom
import resources
# from multiprocessing import Process, Queue

from PyQt4.QtCore import (PYQT_VERSION_STR, QByteArray, QDir, QEvent,
        QFile, QFileInfo, QIODevice, QPoint, QProcess, QRegExp, QObject,
        QSettings, QString, QT_VERSION_STR, QTextStream, QThread, QRect,
        QTimer, QUrl, QVariant, Qt, SLOT, SIGNAL, QStringList, QMimeData, 
        QEventLoop)
from PyQt4.QtNetwork import QHttp
from PyQt4.QtGui import (QAction, QApplication, QButtonGroup, QCheckBox,
        QColor, QColorDialog, QComboBox, QCursor, QDesktopServices,
        QDialog, QDialogButtonBox, QFileDialog, QFont, QFontComboBox,
        QFontMetrics, QGridLayout, QHBoxLayout, QIcon, QInputDialog,
        QKeySequence, QLabel, QLineEdit, QListWidget, QMainWindow,
        QMessageBox, QPixmap, QPushButton, QRadioButton, QGroupBox,
        QRegExpValidator, QShortcut, QSpinBox, QSplitter, QDirModel,
        QSyntaxHighlighter, QTabWidget, QTextBrowser, QTextCharFormat,
        QTextCursor, QTextDocument, QTextEdit, QPlainTextEdit, QToolTip,
        QVBoxLayout, QPainter, QDoubleSpinBox, QMouseEvent,
        QWidget, QDockWidget, QToolButton, QSpacerItem, QSizePolicy,
        QPalette, QSplashScreen, QTreeWidget, QTreeWidgetItem, QFrame,
        QListView, QTableWidget, QTableWidgetItem, QHeaderView, QMenu, 
        QAbstractItemView, QTextBlockUserData, QTextFormat, QClipboard,)

try:
    from qgis.core import *
except ImportError:
    pass

try:
    import rpy2
    import rpy2.robjects as robjects
    import rpy2.rlike.container as rlc
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
            "plot", "hist", "lines", "points", "require", "load"]

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

def welcomeString(version, isStandalone):
    string = QString("Welcome to manageR %s\n" % version)
    if not isStandalone:
        string.append("QGIS interface to the R statistical analysis program\n")
    string.append("Copyright (C) 2009-2010  Carson J. Q. Farmer\n")
    string.append("Licensed under the terms of GNU GPL 2\n")
    string.append("manageR is free software; ")
    string.append("you can redistribute it and/or modify it under the terms")
    string.append("of the GNU General Public License as published by the Free")
    string.append("Software Foundation; either version 2 of the License, or")
    string.append("(at your option) any later version.")
    string.append("Currently running %s\n" % robjects.r.version[12][0])
    return string

CURRENTDIR = unicode(os.path.abspath( os.path.dirname(__file__)))

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
    Config["useraster"] = settings.value("manageR/useraster",
            QVariant(False)).toBool()
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
            ("assignment", "#50621A", False, False),
            ("syntax", "#FF0000", False, True)):
        Config["%sfontcolor" % name] = settings.value(
                "manageR/%sfontcolor" % name, QVariant(color)).toString()
        if name == "syntax":
            Config["%sfontunderline" % name] = settings.value(
                    "manageR/%sfontunderline" % name, QVariant(bold)).toBool()
        else:
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
    Config["bracketautocomplete"] = settings.value("manageR/bracketautocomplete",
            QVariant(True)).toBool()

def saveConfig():
    settings = QSettings()
    for key, value in Config.items():
        settings.setValue("manageR/%s" % (key), QVariant(value))

def addLibraryCommands(library):
    if Config["enableautocomplete"]:
        if not library in Libraries:
            Libraries.append(library)
            info = robjects.r('lsf.str("package:%s")' % (library))
            info = QString(unicode(info)).replace(", \n    ", ", ")
            items = info.split('\n')
            for item in items:
                CAT.append(item)

def isLibraryLoaded(package="sp"):
    return robjects.r("require(%s)" % (package))[0]

def listDataSets(package): 
    import re
    isLibraryLoaded(package)
    rdata = robjects.r["data"]
    data = rdata(package=package).rx2('results')
    # Get all data sets from R, this might be listing in subset (data set) format
    data_sets = [data.rx(row_i, True)[2] for row_i in range(1, data.nrow + 1)]
    # Get only unique values
    data_sets_unique = set()
    for i, data_set in enumerate(data_sets):
        match = re.split('[()]', data_set)
        if len(match) > 1:
            data_sets_unique.add(match[1])
        else:
            data_sets_unique.add(data_set)
    return list(data_sets_unique)

# This is used whenever we check for sp objects in manageR
def currentRObjects():
    try:
        ls_ = robjects.conversion.ri2py(
        robjects.rinterface.globalEnv.get('ls',wantFun=True))
        class_ = robjects.conversion.ri2py(
        robjects.rinterface.globalEnv.get('class',wantFun=True))
        dev_list_ = robjects.conversion.ri2py(
        robjects.rinterface.globalEnv.get('dev.list',wantFun=True))
        getwd_ = robjects.conversion.ri2py(
        robjects.rinterface.globalEnv.get('getwd',wantFun=True))
    except:
        ls_ = robjects.r.get('ls', mode='function')
        class_ = robjects.r.get('class', mode='function')
        dev_list_ = robjects.r.get('dev.list' , mode='function')
        getwd_ = robjects.r.get('getwd' , mode='function')
    layers = {}
    graphics = {}
    for item in ls_():
        check = class_(robjects.r[item])[0]
        layers[unicode(item)] = check
        if not unicode(item) in CAT:
            CAT.append(unicode(item))
    try:
        # this is throwing exceptions...
        graphics = dict(zip(list(dev_list_()),
        list(dev_list_().names)))
    except:
        graphics = {}
    cwd = getwd_()[0]
    return (layers, graphics, cwd)

original = sys.stdout

class OutputCatcher(QObject):

    def __init__(self, parent=None):
        QObject.__init__(self, parent)
        self.data = ''

    def write(self, stuff):
        self.data += stuff
        #if len(self.data) > 80*100:
            #self.get_and_clean_data()

    def get_and_clean_data(self, emit=True):
        tmp = self.data
        self.clear()
        #original.write(tmp)
        if emit:
            self.emit(SIGNAL("output(QString)"),
            QString(tmp.decode('utf8')))
        QApplication.processEvents()
        return tmp

    def flush(self):
        pass

    def clear(self):
        self.data = ''

sys.stdout = OutputCatcher()

class HelpDialog(QDialog):

    def __init__(self, version, parent=None):
        super(HelpDialog, self).__init__(parent)
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
dialog with a text editing region to input user-defined R commands, and an OK and CLOSE button. When 
OK is clicked, the R commands in the text editing region will be run, and when CLOSE is clicked, 
the dialog will be closed. In the example above, query is set to <tt>|1|</tt>, which means take the 
output from the first parameter, and place here. In other words, in this case the entire query is 
equal to whatever is input into the text editing region (default here is <tt>ls()</tt>). Other GUI 
parameters that may be entered include:
<ul>
<li>comboBox: Drop-down list box</li>
<li>doubleSpinBox: Widget for entering numerical values</li>
<li>textEdit: Text editing region</li>
<li>spComboBox: Combobox widget for displaying a dropdown list of variables (e.g. numeric, 
data.frame, Spatial*DataFrame)</li>
<li>spListWidget: Widget for displaying lists of variables (e.g. numeric, data.frame, Spatial*DataFrame)</li>
<li>helpString: Non-graphical parameter that is linked to the help button on the dialog
(can use 'topic:help_topic' or custom html based help text)</li></ul>
Default values for all of the above GUI parameters can be specified in the XML file, using semi-colons 
to separate multiple options. For the spComboBox, the default string should specify the type(s) of 
variables to display (e.g. numeric;data,frame;SpatialPointsDataFrame).
<b>manageR</b> comes with several default R GUI functions which can be used as examples for creating
custom R functions.
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
""" % (version, Config["delay"], CURRENTDIR, #str(os.path.abspath( os.path.dirname(__file__))),
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

class LibrarySplitter(QSplitter):

    def __init__(self, parent):
        super(LibrarySplitter, self).__init__(parent)
        robjects.r("""make.packages.html()""")
        host = "localhost"
        port = robjects.r('tools:::httpdPort')[0]
        home = "/doc/html/packages.html"
        self.home = home
        paths = QStringList(os.path.join(CURRENTDIR, "icons"))
        self.setOrientation(Qt.Vertical)
        self.setFrameStyle(QFrame.StyledPanel|QFrame.Sunken)
        monofont = QFont(Config["fontfamily"], Config["fontsize"])
        self.table = QTableWidget(0, 4, self)
        self.table.setFont(monofont)
        labels = QStringList()
        labels.append("Loaded")
        labels.append("Package")
        labels.append("Title")
        labels.append("Path")
        self.table.setHorizontalHeaderLabels(labels)
        self.table.setShowGrid(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setAlternatingRowColors(True)
        self.viewer = HtmlViewer(self, host, port, home, paths)
        self.update_packages()
        self.connect(self.table, SIGNAL("itemChanged(QTableWidgetItem*)"), self.load_package)
        self.connect(self.table, SIGNAL("itemDoubleClicked(QTableWidgetItem*)"), self.show_package)
        sys.stdout.get_and_clean_data()

    def show_package(self, item):
        row = item.row()
        tmp = self.table.item(row, 1)
        package = tmp.text()
        home = QUrl(self.home)
        curr = QUrl("../../library/%s/html/00Index.html" % package)
        self.viewer.setSource(home.resolved(curr))

    def load_package(self, item):
        mime = QMimeData()
        row = item.row()
        tmp = self.table.item(row, 1)
        package = tmp.text()
        if item.checkState() == Qt.Checked:
            mime.setText("library(%s)" % package)
        else:
            mime.setText("detach('package:%s')" % package)
        MainWindow.Console.editor.moveToEnd()
        MainWindow.Console.editor.cursor.movePosition(
        QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
        MainWindow.Console.editor.cursor.removeSelectedText()
        MainWindow.Console.editor.cursor.insertText(
        MainWindow.Console.editor.currentPrompt)
        MainWindow.Console.editor.insertFromMimeData(mime)
        MainWindow.Console.editor.entered()

    def update_packages(self):
        library_ = robjects.r.get('library', mode='function')
        packages_ = robjects.r.get('.packages', mode='function')
        loaded = list(packages_())
        packages = list(library_()[1])
        length = len(packages)
        self.table.clearContents()
        sys.stdout.get_and_clean_data(False)
        #self.table.setRowCount(length/3)
        package_list = []
        for i in range(length/3):
            package = unicode(packages[i])
            if not package in package_list:
                package_list.append(package)
                self.table.setRowCount(len(package_list))
                item = QTableWidgetItem("Loaded")
                item.setFlags(
                Qt.ItemIsUserCheckable|Qt.ItemIsEnabled|Qt.ItemIsSelectable)
                if package in loaded:
                    item.setCheckState(Qt.Checked)
                else:
                    item.setCheckState(Qt.Unchecked)
                self.table.setItem(i, 0, item)
                item = QTableWidgetItem(unicode(packages[i]))
                item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable)
                self.table.setItem(i, 1, item)
                item = QTableWidgetItem(unicode(packages[i+(2*(length/3))]))
                item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable)
                self.table.setItem(i, 2, item)
                item = QTableWidgetItem(unicode(packages[i+(length/3)]))
                item.setFlags(Qt.ItemIsEnabled|Qt.ItemIsSelectable)
                self.table.setItem(i, 3, item)
        self.table.resizeColumnsToContents()

class LibraryBrowser(QDialog):

    def __init__(self, parent=None):
        super(LibraryBrowser, self).__init__(parent)
        #self.setAttribute(Qt.WA_GroupLeader)
        #self.setAttribute(Qt.WA_DeleteOnClose)
        layout = QVBoxLayout()
        layout.setMargin(0)
        splitter = LibrarySplitter(self)
        layout.addWidget(splitter)
        self.setLayout(layout)
        QShortcut(QKeySequence("Escape"), self, self.close)
        self.setWindowTitle("manageR - Library browser")
        self.resize(500, 500)

class HtmlViewer(QWidget):

    class PBrowser(QTextBrowser):

        def __init__(self, parent, host, port, home, paths):
            QTextBrowser.__init__(self, parent)
            self.http = QHttp()
            self.http.setHost(host, port)
            home = QUrl(home)
            self.base = home
            self.html = QString()
            self.setOpenLinks(True)
            self.setSearchPaths(paths)
            self.connect(self.http, SIGNAL(
            "done(bool)"), self.getData)
            self.anchor = QString()
            self.setSource(home)

        def setSource(self, url):
            url = self.source().resolved(url)
            QTextBrowser.setSource(self, url)

        def loadResource(self, type, name):
            ret = QVariant()
            name.setFragment(QString())
            if type == QTextDocument.HtmlResource:
                loop = QEventLoop()
                loop.connect(self.http, SIGNAL(
                "done(bool)"), SLOT("quit()"))
                self.http.get(name.toString())
                loop.exec_(
                QEventLoop.AllEvents | \
                QEventLoop.WaitForMoreEvents)
                data = QVariant(QString(self.html))
            else:
                fileName = QFileInfo(
                name.toLocalFile()).fileName()
                data = QTextBrowser.loadResource(
                self, type, QUrl(fileName))
            return data

        def getData(self, error):
            if error:
                self.html = self.http.errorString()
            else:
                self.html = self.http.readAll()

    def __init__(self, parent, host, port, home, paths):
        super(HtmlViewer, self).__init__(parent)
        robjects.r("""make.packages.html()""")
        self.viewer = self.PBrowser(self, host, port, home, paths)
        self.parent = parent

        homeButton = QToolButton(self)
        homeAction = QAction("&Home", self)
        homeAction.setToolTip("Return to start page")
        homeAction.setWhatsThis("Return to start page")
        homeAction.setIcon(QIcon(":mActionHome.png"))
        homeButton.setDefaultAction(homeAction)
        homeAction.setEnabled(True)
        homeButton.setAutoRaise(True)

        backwardButton = QToolButton(self)
        backwardAction = QAction("&Back", self)
        backwardAction.setToolTip("Move to previous page")
        backwardAction.setWhatsThis("Move to previous page")
        backwardAction.setIcon(QIcon(":mActionBack.png"))
        backwardButton.setDefaultAction(backwardAction)
        backwardAction.setEnabled(False)
        backwardButton.setAutoRaise(True)

        forwardButton = QToolButton(self)
        forwardAction = QAction("&Forward", self)
        forwardAction.setToolTip("Move to next page")
        forwardAction.setWhatsThis("Move to next page")
        forwardAction.setIcon(QIcon(":mActionForward.png"))
        forwardButton.setDefaultAction(forwardAction)
        forwardAction.setEnabled(False)
        forwardButton.setAutoRaise(True)

        vert = QVBoxLayout(self)
        horiz = QHBoxLayout()
        horiz.addStretch()
        horiz.addWidget(backwardButton)
        horiz.addWidget(homeButton)
        horiz.addWidget(forwardButton)
        horiz.addStretch()
        vert.addLayout(horiz)
        vert.addWidget(self.viewer)
        self.connect(self.viewer, SIGNAL("forwardAvailable(bool)"), forwardAction.setEnabled)
        self.connect(self.viewer, SIGNAL("backwardAvailable(bool)"), backwardAction.setEnabled)
        self.connect(homeAction, SIGNAL("triggered()"), self.home)
        self.connect(backwardAction, SIGNAL("triggered()"), self.backward)
        self.connect(forwardAction, SIGNAL("triggered()"), self.forward)

    def home(self):
        self.viewer.home()

    def backward(self):
        self.viewer.backward()

    def forward(self):
        self.viewer.forward()
        
    def setSource(self, url):
        self.viewer.setSource(url)

class RHighlighter(QSyntaxHighlighter):

    Rules = []
    Formats = {}

    def __init__(self, parent=None, isConsole=False):
        super(RHighlighter, self).__init__(parent)
        self.parent = parent
        if isinstance(self.parent, QPlainTextEdit):
            self.setDocument(self.parent.document())
        self.initializeFormats()
        self.isConsole = isConsole
        RHighlighter.Rules.append((QRegExp(
                r"[a-zA-Z_]+[a-zA-Z_\.0-9]*(?=[\s]*[(])"), "keyword"))
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % keyword for keyword in KEYWORDS])),
                "keyword"))
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % builtin for builtin in BUILTINS])),
                "builtin"))
        #RHighlighter.Rules.append((QRegExp(
                #r"[a-zA-Z_\.][0-9a-zA-Z_\.]*[\s]*=(?=([^=]|$))"), "inbrackets"))
        RHighlighter.Rules.append((QRegExp(
                "|".join([r"\b%s\b" % constant
                for constant in CONSTANTS])), "constant"))
        RHighlighter.Rules.append((QRegExp(
                r"\b[+-]?[0-9]+[lL]?\b"
                r"|\b[+-]?0[xX][0-9A-Fa-f]+[lL]?\b"
                r"|\b[+-]?[0-9]+(?:\.[0-9]+)?(?:[eE][+-]?[0-9]+)?\b"),
                "number"))
        RHighlighter.Rules.append((QRegExp(r"[\)\(]+|[\{\}]+|[][]+"),
                "delimiter"))
        RHighlighter.Rules.append((QRegExp(
                r"[<]{1,2}\-"
                r"|\-[>]{1,2}"
                r"|=(?!=)"
                r"|\$"
                r"|\@"), "assignment"))
        RHighlighter.Rules.append((QRegExp(
                r"([\+\-\*/\^\:\$~!&\|=>@^])([<]{1,2}\-|\-[>]{1,2})"
                r"|([<]{1,2}\-|\-[>]{1,2})([\+\-\*/\^\:\$~!&\|=<@])"
                r"|([<]{3}|[>]{3})"
                r"|([\+\-\*/\^\:\$~&\|@^])="
                r"|=([\+\-\*/\^\:\$~!<>&\|@^])"
                #r"|(\+|\-|\*|/|<=|>=|={1,2}|\!=|\|{1,2}|&{1,2}|:{1,3}|\^|@|\$|~){2,}"
                ),
                "syntax"))
        self.stringRe = QRegExp("(\'[^\']*\'|\"[^\"]*\")")
        self.stringRe.setMinimal(True)
        RHighlighter.Rules.append((self.stringRe, "string"))
        RHighlighter.Rules.append((QRegExp(r"#.*"), "comment"))
        self.multilineSingleStringRe = QRegExp(r"""'(?!")""")
        self.multilineDoubleStringRe = QRegExp(r'''"(?!')''')
        self.bracketBothExpression = QRegExp(r"[\(\)]")
        self.bracketStartExpression = QRegExp(r"\(")
        self.bracketEndExpression = QRegExp(r"\)")

    @staticmethod
    def initializeFormats():
        baseFormat = QTextCharFormat()
        baseFormat.setFontFamily(Config["fontfamily"])
        baseFormat.setFontPointSize(Config["fontsize"])
        for name in ("normal", "keyword", "builtin", "constant",
                "delimiter", "comment", "string", "number", "error",
                "assignment", "syntax"):
            format = QTextCharFormat(baseFormat)
            format.setForeground(
                            QColor(Config["%sfontcolor" % name]))
            if name == "syntax":
                format.setFontUnderline(Config["%sfontunderline" % name])
            else:
                if Config["%sfontbold" % name]:
                    format.setFontWeight(QFont.Bold)
            format.setFontItalic(Config["%sfontitalic" % name])
            RHighlighter.Formats[name] = format

        format = QTextCharFormat(baseFormat)
        if Config["assignmentfontbold"]:
            format.setFontWeight(QFont.Bold)
        format.setForeground(
                QColor(Config["assignmentfontcolor"]))
        format.setFontItalic(Config["%sfontitalic" % name])
        RHighlighter.Formats["inbrackets"] = format

    def highlightBlock(self, text):
        NORMAL, MULTILINESINGLE, MULTILINEDOUBLE, ERROR = range(4)
        INBRACKETS, INBRACKETSSINGLE, INBRACKETSDOUBLE = range(4,7)

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
        
        startIndex = 0
        startCount = 0
        endCount = 0
        endIndex = 0
        if not self.previousBlockState() >= 4:
            startIndex = self.bracketStartExpression.indexIn(text)
        while startIndex >= 0:
            startCount += 1
            endIndex = self.bracketBothExpression.indexIn(text, startIndex+1)
            bracket = self.bracketBothExpression.cap()
            if endIndex == -1 or bracket == "(":
                self.setCurrentBlockState(self.currentBlockState() + 4)
                length = text.length() - startIndex
            elif bracket == ")":
                endCount += 1
                tmpEndIndex = endIndex
                while tmpEndIndex >= 0:
                    tmpLength = self.bracketBothExpression.matchedLength()
                    tmpEndIndex = self.bracketBothExpression.indexIn(text, tmpEndIndex + tmpLength)
                    bracket = self.bracketBothExpression.cap()
                    if tmpEndIndex >= 0:
                        if bracket == ")":
                            endIndex = tmpEndIndex
                            endCount += 1
                        else:
                            startCount += 1
                if startCount > endCount:
                    self.setCurrentBlockState(self.currentBlockState() + 4)
                length = endIndex - startIndex + self.bracketBothExpression.matchedLength() + 1 

            bracketText = text.mid(startIndex, length+1)
            regex = QRegExp(r"[a-zA-Z_\.][0-9a-zA-Z_\.]*[\s]*=(?=([^=]|$))")
            format = "inbrackets"
            i = regex.indexIn(bracketText)
            while i >= 0:
                bracketLength = regex.matchedLength()
                self.setFormat(startIndex + i, bracketLength, RHighlighter.Formats[format])
                length = length + bracketLength
                i = regex.indexIn(bracketText, i + bracketLength)
            startIndex = self.bracketStartExpression.indexIn(text, startIndex + length)
                
        if text.indexOf(self.stringRe) != -1:
            return
        for i, state in ((text.indexOf(self.multilineSingleStringRe),
                          MULTILINESINGLE),
                         (text.indexOf(self.multilineDoubleStringRe),
                          MULTILINEDOUBLE)):
            if (self.previousBlockState() == state or \
            self.previousBlockState() == state + 4) and \
            not text.startsWith(Config["beforeinput"]) and \
            not text.contains("#"):
                if i == -1:
                    i = text.length()
                    self.setCurrentBlockState(state)
                if text.startsWith(Config["afteroutput"]) and self.isConsole:
                    self.setFormat(self.parent.currentPromptLength, i + 1,
                    RHighlighter.Formats["string"])
                else:
                    self.setFormat(0, i + 1, RHighlighter.Formats["string"])
            elif i > -1 and not text.contains("#"):
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
        if text.contains(QRegExp(r"\b.{%d,}" % (minchars))):
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

class Editor(QPlainTextEdit):
    def __init__(self, parent, tabwidth=4):
        super(Editor, self).__init__(parent)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.indent = 0
        self.tabwidth = tabwidth
        self.parent = parent
        self.oldfrmt = QTextCharFormat()
        self.oldpos = None
        self.setFrameShape(QTextEdit.NoFrame)
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
            elif event.key() in (Qt.Key_ParenLeft,
                                 Qt.Key_BracketLeft,
                                 Qt.Key_BraceLeft):
                if Config["bracketautocomplete"]:
                    if event.key() == Qt.Key_ParenLeft:
                        insert = QString(Qt.Key_ParenRight)
                    elif event.key() == Qt.Key_BracketLeft:
                        insert = QString(Qt.Key_BracketRight)
                    else:
                        insert = QString(Qt.Key_BraceRight)
                    userCursor = self.textCursor()
                    cursor = QTextCursor(userCursor)
                    userCursor.insertText("%s%s" % (QString(event.key()), insert))
                    cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
                    self.setTextCursor(cursor)
                    return True
                # Fall through to let the base class handle the movement
        return QPlainTextEdit.event(self, event)

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
        format.setForeground(QColor(Config["delimiterfontcolor"]))
        format.setBackground(QColor(Qt.yellow))#.lighter(160)) #QColor(Config["bracketcolor"])?
        firstselection = QTextEdit.ExtraSelection()
        firstselection.format = format
        secondselection = QTextEdit.ExtraSelection()
        secondselection.format = format
        doc = self.document()
        cursor = self.textCursor()
        beforeCursor = QTextCursor(cursor)

        ## if we find bracket errors
        #syntaxformat = QTextCharFormat()
        #syntaxformat.setForeground(QColor(Config["syntaxfontcolor"]))
        #syntaxformat.setFontUnderline(Config["syntaxfontunderline"])
        #synstaxselection = QTextEdit.ExtraSelection()
        #synstaxselection.format = syntaxformat

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
                firstselection.cursor.clearSelection()
                firstselection.cursor = cursor
                if (not cursor1.isNull()):
                    extraSelections.append(firstselection)
                #self.setExtraSelections(extraSelections)
                secondselection.cursor.clearSelection()
                secondselection.cursor = cursor1
                extraSelections.append(secondselection)
                self.setExtraSelections(extraSelections)
            else:
                while (cursor1.position() > cursor2.position()):
                    cursor1 = doc.find(closeBrace, cursor1)
                    cursor2 = doc.find(openBrace, cursor2)
                    if (cursor2.isNull()):
                        break
                firstselection.cursor.clearSelection()
                firstselection.cursor = cursor
                if (not cursor1.isNull()):
                    extraSelections.append(firstselection)
                #self.setExtraSelections(extraSelections)
                secondselection.cursor.clearSelection()
                secondselection.cursor = cursor1
                extraSelections.append(secondselection)
                self.setExtraSelections(extraSelections)

        else:
            if (brace == closeBrace):
                cursor1 = doc.find(openBrace, cursor, QTextDocument.FindBackward)
                cursor2 = doc.find(closeBrace, cursor, QTextDocument.FindBackward)
                if (cursor2.isNull()):
                    firstselection.cursor.clearSelection()
                    firstselection.cursor = cursor
                    if (not cursor1.isNull()):
                        #cursor.mergeCharFormat(syntaxformat)
                    #else:
                        extraSelections.append(firstselection)
                   # self.setExtraSelections(extraSelections)
                    secondselection.cursor.clearSelection()
                    secondselection.cursor = cursor1
                    extraSelections.append(secondselection)
                    self.setExtraSelections(extraSelections)
                else:
                    while (cursor1.position() < cursor2.position()):
                        cursor1 = doc.find(openBrace, cursor1, QTextDocument.FindBackward)
                        cursor2 = doc.find(closeBrace, cursor2, QTextDocument.FindBackward)
                        if (cursor2.isNull()):
                            break
                    firstselection.cursor.clearSelection()
                    firstselection.cursor = cursor
                    if (not cursor1.isNull()):
                        #cursor.mergeCharFormat(syntaxformat)
                    #else:
                        extraSelections.append(firstselection)
                    #self.setExtraSelections(extraSelections)
                    secondselection.cursor.clearSelection()
                    secondselection.cursor = cursor1
                    extraSelections.append(secondselection)
                    self.setExtraSelections(extraSelections)

    def execute(self):
        cursor = self.textCursor()
        if cursor.hasSelection():
            commands = cursor.selectedText().replace(u"\u2029", "\n")
        else:
            commands = self.toPlainText()
        self.run(commands)

    def run(self, commands):
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

    def source(self):
        self.parent.fileSave()
        commands = QString('source("%s")' % self.parent.filename)
        self.run(commands)

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

    def updateNumbers(self, numbers, event):
        metrics = self.fontMetrics()
        line = self.document().findBlock(
        self.textCursor().position()).blockNumber() + 1

        block = self.firstVisibleBlock()
        count = block.blockNumber()
        painter = QPainter(numbers)
        painter.fillRect(event.rect(), self.palette().base())

        # Iterate over all visible text blocks in the document.
        while block.isValid():
            count += 1
            top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
            # Check if the position of the block is out side of the visible
            # area.
            if not block.isVisible() or top >= event.rect().bottom():
                break
            # Draw the line number right justified at the position of the line.
            rect = QRect(0, top, numbers.width(), metrics.height())
            painter.drawText(rect, Qt.AlignRight, unicode(count))
            block = block.next()
        painter.end()

class REditor(QFrame):

    class NumberBar(QWidget):

        def __init__(self, edit):
            QWidget.__init__(self, edit)

            self.edit = edit
            self.adjustWidth(1)

        def paintEvent(self, event):
            self.edit.updateNumbers(self, event)
            QWidget.paintEvent(self, event)

        def adjustWidth(self, count):
            width = self.fontMetrics().width(unicode(count))
            if self.width() != width:
                self.setFixedWidth(width)

        def updateContents(self, rect, scroll):
            if scroll:
                self.scroll(0, scroll)
            else:
                # It would be nice to do
                # self.update(0, rect.y(), self.width(), rect.height())
                # But we can't because it will not remove the bold on the
                # current line if word wrap is enabled and a new block is
                # selected.
                self.update()

    def __init__(self, parent, tabwidth=4):
        super(REditor, self).__init__(parent)

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        
        monofont = QFont(Config["fontfamily"], Config["fontsize"])
        self.edit = Editor(parent, tabwidth)
        self.edit.setFont(monofont)
        self.number_bar = self.NumberBar(self.edit)
        self.number_bar.setFont(monofont)

        hbox = QHBoxLayout(self)
        hbox.setSpacing(2)
        hbox.setMargin(0)
        hbox.addWidget(self.number_bar)
        hbox.addWidget(self.edit)

        self.edit.blockCountChanged.connect(self.number_bar.adjustWidth)
        self.edit.updateRequest.connect(self.number_bar.updateContents)

    def getText(self):
        return unicode(self.edit.toPlainText())

    def setText(self, text):
        self.edit.setPlainText(text)

    def isModified(self):
        return self.edit.document().isModified()

    def setModified(self, modified):
        self.edit.document().setModified(modified)
        
    def setTabChangesFocus(self, bool):
        self.edit.setTabChangesFocus(bool)
        
    def document(self):
        return self.edit.document()
        
    def toPlainText(self):
        return self.edit.toPlainText()
        
    def appendPlainText(self, text):
        self.edit.appendPlainText(text)
        
    def moveCursor(self, operation, mode = QTextCursor.MoveAnchor):
        self.edit.moveCursor(operation, mode)

class RConsole(QTextEdit):

    class textDialog(QDialog):
    # options(htmlhelp=FALSE) this should probably be added somewhere to make sure the help is always the R help...
        def __init__(self, parent, text):
            QDialog.__init__ (self, parent)
            #initialise the display text edit
            display = QTextBrowser(self)
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
            display.setPlainText(text)
            self.resize(750, 400)

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
        self.setFrameShape(QTextEdit.NoFrame)
        # initialise required variables
        self.history = QStringList()
        self.historyIndex = 0
        self.runningCommand = QString()
        # prepare prompt
        self.reset()
        #self.queue = Queue()
        self.running = False
        self.setPrompt(Config["beforeinput"]+" ", Config["afteroutput"]+" ")
        self.cursor = self.textCursor()
        self.connect(self, SIGNAL("cursorPositionChanged()"),
        self.highlight)
        self.connect(sys.stdout, SIGNAL("output(QString)"),
        self.commandOutput)
        self.timerId = -1

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
        if e.key() == Qt.Key_A and (e.modifiers() == Qt.ControlModifier or \
            e.modifiers() == Qt.MetaModifier):
            self.selectAll()
        else:
            self.cursor = self.textCursor()
            # if the cursor isn't in the edition zone, don't do anything except Ctrl+C
            if not self.isCursorInEditionZone():
                if e.modifiers() == Qt.ControlModifier or \
                    e.modifiers() == Qt.MetaModifier:
                    if e.key() == Qt.Key_C:
                        if self.running:
                            self.terminateCommand()
                        else:
                            QTextEdit.keyPressEvent(self, e)
                else:
                    # all other keystrokes get sent to the input line
                    self.cursor.movePosition(QTextCursor.End, QTextCursor.MoveAnchor)
            else:
                # if Ctrl + C is pressed, then undo the current command
                if e.key() == Qt.Key_C and (e.modifiers() == Qt.ControlModifier or \
                    e.modifiers() == Qt.MetaModifier):
                        if self.running:
                            self.terminateCommand()
                        elif not self.cursor.hasSelection():
                            self.runningCommand.clear()
                            #block = self.cursor.block()
                            #block.setUserState(0)
                            self.switchPrompt(True)
                            self.displayPrompt()
                            MainWindow.Console.statusBar().clearMessage()
                elif e.key() == Qt.Key_Tab:
                    indent = " " * int(Config["tabwidth"])
                    self.cursor.insertText(indent)
                  # if Return is pressed, then perform the commands
                elif e.key() in (Qt.Key_ParenLeft,
                                 Qt.Key_BracketLeft,
                                 Qt.Key_BraceLeft):
                    if Config["bracketautocomplete"]:
                        if e.key() == Qt.Key_ParenLeft:
                            insert = QString(Qt.Key_ParenRight)
                        elif e.key() == Qt.Key_BracketLeft:
                            insert = QString(Qt.Key_BracketRight)
                        else:
                            insert = QString(Qt.Key_BraceRight)
                        #userCursor = self.textCursor()
                        #cursor = QTextCursor(userCursor)
                        self.cursor.insertText("%s%s" % (QString(e.key()), insert))
                        self.cursor.movePosition(QTextCursor.PreviousCharacter, QTextCursor.MoveAnchor)
                        #self.setTextCursor(cursor)
                        #return True
                    else:
                        QTextEdit.keyPressEvent(self, e)
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
                block = self.cursor.block()
                block.setUserState(0)
                self.switchPrompt(True)
                self.displayPrompt()
        if not self.checkBrackets(self.runningCommand):
            self.switchPrompt(False)
            self.cursor.movePosition(QTextCursor.End,
            QTextCursor.MoveAnchor)
            self.cursor.insertText("\n" + self.currentPrompt)
            self.runningCommand.append("\n")
        else:
            self.setExtraSelections([])
            block = self.cursor.block()
            block.setUserState(0)
            if not self.runningCommand.isEmpty():
                command=self.runningCommand
            self.execute(command)
            self.runningCommand.clear()
            self.cursor.movePosition(QTextCursor.End,
            QTextCursor.MoveAnchor)
            #self.switchPrompt(True)
            #self.cursor.movePosition(QTextCursor.End,
            #QTextCursor.MoveAnchor)
        #self.setTextCursor(self.cursor)
        #self.moveToEnd()

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
        s = unicode(command)
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
        #self.emit(SIGNAL("textChanged()"))

    def highlight(self):
        extraSelections = []
        self.setExtraSelections(extraSelections)
        format = QTextCharFormat()
        format.setForeground(QColor(Config["delimiterfontcolor"]))
        format.setBackground(QColor(Qt.yellow))#.lighter(160)) #QColor(Config["bracketcolor"])?
        firstselection = QTextEdit.ExtraSelection()
        firstselection.format = format
        secondselection = QTextEdit.ExtraSelection()
        secondselection.format = format
        doc = self.document()
        cursor = self.textCursor()
        beforeCursor = QTextCursor(cursor)

        ## if we find bracket errors
        #syntaxformat = QTextCharFormat()
        #syntaxformat.setForeground(QColor(Config["syntaxfontcolor"]))
        #syntaxformat.setFontUnderline(Config["syntaxfontunderline"])
        #synstaxselection = QTextEdit.ExtraSelection()
        #synstaxselection.format = syntaxformat
        
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
                firstselection.cursor.clearSelection()
                firstselection.cursor = cursor
                if (not cursor1.isNull()):
                    extraSelections.append(firstselection)
                #self.setExtraSelections(extraSelections)
                secondselection.cursor.clearSelection()
                secondselection.cursor = cursor1
                extraSelections.append(secondselection)
                self.setExtraSelections(extraSelections)
            else:
                while (cursor1.position() > cursor2.position()):
                    cursor1 = doc.find(closeBrace, cursor1)
                    cursor2 = doc.find(openBrace, cursor2)
                    if (cursor2.isNull()):
                        break
                firstselection.cursor.clearSelection()
                firstselection.cursor = cursor
                if (not cursor1.isNull()):
                    extraSelections.append(firstselection)
                #self.setExtraSelections(extraSelections)
                secondselection.cursor.clearSelection()
                secondselection.cursor = cursor1
                extraSelections.append(secondselection)
                self.setExtraSelections(extraSelections)

        else:
            if (brace == closeBrace):
                cursor1 = doc.find(openBrace, cursor, QTextDocument.FindBackward)
                cursor2 = doc.find(closeBrace, cursor, QTextDocument.FindBackward)
                if (cursor2.isNull()):
                    firstselection.cursor.clearSelection()
                    firstselection.cursor = cursor
                    if (not cursor1.isNull()):
                        #cursor.mergeCharFormat(syntaxformat)
                    #else:
                        extraSelections.append(firstselection)
                   # self.setExtraSelections(extraSelections)
                    secondselection.cursor.clearSelection()
                    secondselection.cursor = cursor1
                    extraSelections.append(secondselection)
                    self.setExtraSelections(extraSelections)
                else:
                    while (cursor1.position() < cursor2.position()):
                        cursor1 = doc.find(openBrace, cursor1, QTextDocument.FindBackward)
                        cursor2 = doc.find(closeBrace, cursor2, QTextDocument.FindBackward)
                        if (cursor2.isNull()):
                            break
                    firstselection.cursor.clearSelection()
                    firstselection.cursor = cursor
                    if (not cursor1.isNull()):
                        #cursor.mergeCharFormat(syntaxformat)
                    #else:
                        extraSelections.append(firstselection)
                    #self.setExtraSelections(extraSelections)
                    secondselection.cursor.clearSelection()
                    secondselection.cursor = cursor1
                    extraSelections.append(secondselection)
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

    def updateStatusBar(self, text, time):
        if time > 0:
            MainWindow.Console.statusBar().showMessage(text, time)
        else:
            MainWindow.Console.statusBar().showMessage(text)
        QApplication.processEvents()

    def helpTopic(self, text):
        dialog = self.textDialog(self, text)
        dialog.setWindowModality(Qt.NonModal)
        dialog.setModal(False)
        dialog.show()
        self.updateStatusBar("Help dialog opened", 5000)
        QApplication.processEvents()

    def commandError(self, error):
        self.appendText(unicode(error))
        QApplication.processEvents()

    def commandOutput(self, output):
        self.appendText(unicode(output))
        QApplication.processEvents()

    def commandComplete(self):
        self.updateStatusBar("Complete!", 5000)
        QApplication.processEvents()
        self.running = False
        self.emit(SIGNAL("commandComplete()"))
        #output = sys.stdout.get_and_clean_data()
        #if output:
            #self.appendText(QString(output.decode('utf8')))
        self.switchPrompt()
        self.displayPrompt()
        self.emit(SIGNAL("cursorPositionChanged()"))
        if self.timerId > -1:
            self.killTimer(self.timerId)
        self.timerId = -1
        QApplication.processEvents()

    def terminateCommand(self):
        #if self.p.is_alive():
            #self.p.terminate()
        #self.commandComplete()
        pass

    def execute(self, cmd):
        self.updateStatusBar("Running...", 0)
        QApplication.processEvents()
        self.running = True
        #self.timerId = self.startTimer(30)
        #self.p = Process(target = run, args = (self.queue,robjects.r,cmd,))
        #self.p.start()
        self.run(None, robjects.r, cmd)
        self.commandComplete()

    #def timerEvent(self, e):
        #if not self.queue.empty():
            #self.commandOutput(self.queue.get())
        #elif not self.p.is_alive():
            #self.commandComplete()

    def run(self, q, r, cmd):
        # note that q.put has been replaced with print() for now...
        text = QString(cmd)
        if not text.trimmed() == "":
            try:
                regexp = QRegExp(r"(\bquit\(.*\)|\bq\(.*\))")
                if text.contains(regexp):
                    print "Error: System exit from manageR not allowed, close dialog manually or use Ctrl+Q"
                    sys.stdout.get_and_clean_data()
                    return
                else:
                    pos = 0 # this is used later when checking if new libraries have been loaded
                    output_text = QString()
                    def read(prompt): # TODO: This is a terrible workaround
                        input = "\n"  # and needs to be futher investigated...
                        return input
                    try:
                        robjects.rinterface.set_readconsole(read)
                    except:
                        robjects.rinterface.setReadConsole(read)
                    try:
                        if platform.system() == "Windows":
                            tfile = r.get("tempfile", mode='function')
                            temp = r.get("file", mode='function')
                            sink = r.get("sink", mode='function')
                            tfile = tfile()
                            temp = temp(tfile, open='w')
                            sink(temp)
                        try_ = r.get("try", mode='function')
                        parse_ = r.get("parse", mode='function')
                        paste_ = r.get("paste", mode='function')
                        seq_along_ = r.get("seq_along", mode='function')
                        withVisible_ = r.get("withVisible", mode='function')
                        class_ = r.get("class", mode='function')
                        result =  try_(parse_(text=paste_(unicode(text))), silent=True)
                        exprs = result
                        result = None
                        for i in list(seq_along_(exprs)):
                            ei = exprs[i-1]
                            try:
                                result = try_(withVisible_(ei), silent=True)
                            except robjects.rinterface.RRuntimeError, err:
                                # dont need to print error...
                                sys.stdout.get_and_clean_data()
                                return
                            visible = result[1][0]
                            if visible:
                                tmpclass = class_(result[0])[0]
                                if not tmpclass in ("NULL"):#, "help_files_with_topic", "hsearch"):
                                    print result[0]
                                    #sys.stdout.get_and_clean_data()
                                if tmpclass in ("help_files_with_topic", "hsearch"):
                                    help_string = QString(sys.stdout.get_and_clean_data(False))
                                    # woraround to remove non-ascii text and formatting
                                    help_string.remove("_").replace(u'\xe2\x80\x98', "'").replace(u'\xe2\x80\x99',"'")
                                    self.textDialog(self,help_string).show()
                                    #sys.stdout.get_and_clean_data()
                            else:
                                try:
                                    regexp = QRegExp(r"library\(([\w\d]*)\)")
                                    while not (regexp.indexIn(text, pos) == -1):
                                        library = regexp.cap(1)
                                        pos += regexp.matchedLength()
                                        if not library in Libraries:
                                            addLibraryCommands(library)
                                except Exception, err:
                                    print err
                                    sys.stdout.get_and_clean_data()
                                    return
                        if platform.system() == "Windows":
                            sink()
                            close = r.get("close", mode='function')
                            close(temp)
                            temp = r.get("file", mode='function')
                            temp = temp(tfile, open='r')
                            rlines = r.get("readLines", mode='function')
                            rlines = rlines(temp)
                            close(temp)
                            unlink = r.get("unlink", mode='function')
                            unlink(tfile)
                            rlines = str.join(os.linesep, rlines)
                            if not rlines == "":
                                print rlines
                    except robjects.rinterface.RRuntimeError, err:
                        # dont need to print error...
                        sys.stdout.get_and_clean_data()
                        return
            except Exception, err:
                print err
                sys.stdout.get_and_clean_data()
                return
        sys.stdout.get_and_clean_data()
        return

class ConfigForm(QDialog):

    def __init__(self, parent=None, isStandalone=True):
        super(ConfigForm, self).__init__(parent)
        self.isStandalone = isStandalone
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
        if not isStandalone:
            self.useRasterPackage = QCheckBox(
                    "Use 'raster' package")
            self.useRasterPackage.setToolTip("<p>Check this to make "
                    "manageR use the 'raster' package for loading raster "
                    "layers from QGIS")
            self.useRasterPackage.setChecked(
                    Config["useraster"])
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
        self.cwdLineEdit.setFont(monofont)
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
        self.tabWidthSpinBox.setFont(monofont)
        self.tabWidthSpinBox.setValue(Config["tabwidth"])
        self.tabWidthSpinBox.setToolTip("<p>Specify the number of "
                "spaces that a single tab should span.</p>")
        tabWidthLabel = QLabel("&Tab width:")
        tabWidthLabel.setBuddy(self.tabWidthSpinBox)
        self.fontComboBox = QFontComboBox()
        self.fontComboBox.setCurrentFont(monofont)
        self.fontComboBox.setFont(monofont)
        self.fontComboBox.setToolTip("<p>Specify the font family for "
                "the manageR console and all EditR windows.</p>")
        fontLabel = QLabel("&Font:")
        fontLabel.setBuddy(self.fontComboBox)
        self.fontSpinBox = QSpinBox()
        self.fontSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.fontSpinBox.setRange(6, 20)
        self.fontSpinBox.setSuffix(" pt")
        self.fontSpinBox.setFont(monofont)
        self.fontSpinBox.setValue(Config["fontsize"])
        self.fontSpinBox.setToolTip("<p>Specify the font size for  "
                "the manageR console, and all EditR windows.</p>")
        self.timeoutSpinBox = QSpinBox()
        self.timeoutSpinBox.setAlignment(Qt.AlignVCenter|Qt.AlignRight)
        self.timeoutSpinBox.setRange(0, 20000)
        self.timeoutSpinBox.setFont(monofont)
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
        self.mincharsSpinBox.setRange(1, 100)
        self.mincharsSpinBox.setFont(monofont)
        self.mincharsSpinBox.setSuffix(" chars")
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
        
        self.autocompleteBrackets = QCheckBox("Enable auto-insert of brackets/parentheses")
        self.autocompleteBrackets.setToolTip("<p>Check this to enable "
                "auto-insert of brackets and parentheses when typing R functions and commands.")
        self.autocompleteBrackets.setChecked(Config["bracketautocomplete"])
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
        if not self.isStandalone:
            grid0.addWidget(self.useRasterPackage,4,0,1,3)
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
        grid2.addWidget(self.autocompleteBrackets,3,0,1,2)
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
                ("assignment", "Assignment operator:"), ("syntax", "Syntax errors:")):
            label = QLabel(labelText)
            labels.append(label)
            if name == "syntax":
                boldCheckBox = QCheckBox("Underline")
                boldCheckBox.setChecked(Config["%sfontunderline" % name])
            else:
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
                colorButton = QPushButton("&A Color...")
            elif name == "syntax":
                colorButton = QPushButton("&S Color...")
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
            editor.setText(Config[name])
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
        if not self.isStandalone:
            Config["useraster"] = (self.useRasterPackage.isChecked())
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
        Config["bracketautocomplete"] = (self.autocompleteBrackets.isChecked())
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
                "assignment", "syntax"):
            if name == "syntax":
                underline = self.boldCheckBoxes[name].isChecked()
                if Config["syntaxfontunderline"] != underline:
                    self.highlightingChanged = True
                    Config["syntaxfontunderline"] = underline
            else:
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

class RHistoryWidget(QWidget):

    class ListWidget(QListWidget):
        def __init__(self, parent):
            QListWidget.__init__(self, parent)

        def mousePressEvent(self, event):
            item = self.itemAt(event.globalPos())
            if not item and event.button() == Qt.LeftButton:
                self.clearSelection()
            QListWidget.mousePressEvent(self, event)

        def selectionChanged(self, sela, selb):
            self.emit(SIGNAL("selectionChanged()"))
            QListWidget.selectionChanged(self, sela, selb)
        
    def __init__(self, parent, console):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30,30)
        self.parent = parent
        self.console = console
        self.commandList = self.ListWidget(self)
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
        self.clearAction = QAction("Clear &selected commands", self)
        self.clearAction.setStatusTip("Clear the selected commands")
        self.clearAction.setToolTip("Clear the selected commands")
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
        for i in self.commandList.selectedItems():
            row = self.commandList.row(i)
            item = self.commandList.takeItem(row)
            del item

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
    
    class TreeWidget(QTreeWidget):
        def __init__(self, parent):
            QTreeWidget.__init__(self, parent)

        def mousePressEvent(self, event):
            item = self.itemAt(event.globalPos())
            if not item and event.button() == Qt.LeftButton:
                self.clearSelection()
            QTreeWidget.mousePressEvent(self, event)

        def selectionChanged(self, sela, selb):
            self.emit(SIGNAL("itemSelectionChanged()"))
            QTreeWidget.selectionChanged(self, sela, selb)

    def __init__(self, parent, isStandalone):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30,30)
        self.parent = parent
        self.isStandalone = isStandalone
        self.variableTable = self.TreeWidget(self)
        self.variableTable.setColumnCount(3)
        self.variableTable.setAlternatingRowColors(True)
        labels = QStringList()
        labels.append("Name")
        labels.append("Type")
        labels.append("Size")
        self.variableTable.setHeaderLabels(labels)
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
        
        if not self.isStandalone:
            self.canvas = QToolButton(self)
            self.canvasAction = QAction("Export to &canvas", self)
            self.canvasAction.setToolTip("Export layer to canvas")
            self.canvasAction.setWhatsThis("Export layer to canvas")
            self.canvasAction.setIcon(QIcon(":mActionActionExport.png"))
            self.canvas.setDefaultAction(self.canvasAction)
            self.canvasAction.setEnabled(False)
            self.canvas.setAutoRaise(True)

        self.refresh = QToolButton(self)
        self.refreshAction = QAction("Re&fresh variables", self)
        self.refreshAction.setToolTip("Refresh environment browser")
        self.refreshAction.setWhatsThis("Refresh environment browser")
        self.refreshAction.setIcon(QIcon(":mActionGraphicRefresh.png"))
        self.refresh.setDefaultAction(self.refreshAction)
        self.refreshAction.setEnabled(True)
        self.refresh.setAutoRaise(True)
        
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
        
        self.method = QToolButton(self)
        self.methodAction = QAction("&Print available methods", self)
        self.methodAction.setToolTip("Print available methods for object class")
        self.methodAction.setWhatsThis("Print available methods for object class")
        self.methodAction.setIcon(QIcon(":mActionQuestion.png"))
        self.method.setDefaultAction(self.methodAction)
        self.methodAction.setEnabled(False)
        self.method.setAutoRaise(True)
        
        grid = QGridLayout(self)
        horiz = QHBoxLayout()
        horiz.addWidget(self.refresh)
        horiz.addWidget(self.rm)
        horiz.addWidget(self.export)
        if not self.isStandalone:
            horiz.addWidget(self.canvas)
        horiz.addWidget(self.save)
        horiz.addWidget(self.load)
        horiz.addWidget(self.method)
        horiz.addStretch()
        grid.addLayout(horiz, 0, 0, 1, 1)
        grid.addWidget(self.variableTable, 1, 0, 1, 1)
        
        self.variables = dict()
        self.connect(self.rmAction, SIGNAL("triggered()"), self.removeVariable)
        self.connect(self.exportAction, SIGNAL("triggered()"), self.exportVariable)
        self.connect(self.saveAction, SIGNAL("triggered()"), self.saveVariable)
        if not self.isStandalone:
            self.connect(self.canvasAction, SIGNAL("triggered()"), self.exportToCanvas)
        self.connect(self.loadAction, SIGNAL("triggered()"), self.loadRVariable)
        self.connect(self.methodAction, SIGNAL("triggered()"), self.printRMethods)
        self.connect(self.refreshAction, SIGNAL("triggered()"), self.updateVariables)
        self.connect(self.variableTable, SIGNAL("itemSelectionChanged()"), self.selectionChanged)
        self.updateVariables()

    def mousePressEvent(self, event):
        print "to here"
        item = self.variableTable.itemAt(event.globalPos())
        if not item and event.button() == Qt.LeftButton:
            self.variableTable.clearSelection()
        QListWidget.mousePressEvent(self, event)

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.refreshAction)
        menu.addSeparator()
        menu.addAction(self.exportAction)
        if not self.isStandalone:
            menu.addAction(self.canvasAction)
        menu.addAction(self.saveAction)
        menu.addAction(self.loadAction)
        menu.addAction(self.methodAction)
        menu.addAction(self.rmAction)
        menu.exec_(event.globalPos())

    def selectionChanged(self):
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            self.saveAction.setEnabled(False)
            self.rmAction.setEnabled(False)
            if not self.isStandalone:
                self.canvasAction.setEnabled(False)
            self.exportAction.setEnabled(False)
            self.methodAction.setEnabled(False)
        else:
            itemName, itemType = self.getVariableInfo(items[0])
            self.saveAction.setEnabled(True)
            self.rmAction.setEnabled(True)
            self.exportAction.setEnabled(True)
            self.methodAction.setEnabled(True)
            if not self.isStandalone:
                if itemType in VECTORTYPES:
                    self.canvasAction.setEnabled(True)
                else:
                    self.canvasAction.setEnabled(False)

    def printRMethods(self):
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            return False
        itemName, itemType = self.getVariableInfo(items[0])
        self.sendCommands(QString('methods(class=%s)' % (itemType)))

    def removeVariable(self):
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            return False
        itemName, itemType = self.getVariableInfo(items[0])
        self.sendCommands(QString('rm(%s)' % (itemName)))
        self.updateVariables()
        
    def exportVariable(self):
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            return False
        parents = []
        parent = items[0].parent()
        while parent:
            parents.append(parent.text(0))
            item = parent
            parent = item.parent()
        itemName, itemType = self.getVariableInfo(item)
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
            command = QString('write.table(%s, file = "%s",' % (itemName, selectedFile))
            command.append(QString('append = FALSE, quote = TRUE, sep = ",", eol = "\\n", na = "NA"'))
            command.append(QString(', dec = ".", row.names = FALSE, col.names = TRUE, qmethod = "escape")'))
            self.sendCommands(command)
    
    def saveVariable(self):
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            return False
        parents = []
        parent = items[0].parent()
        while parent:
            parents.append(parent.text(0))
            item = parent
            parent = item.parent()
        itemName, itemType = self.getVariableInfo(item)
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
        items = self.variableTable.selectedItems()
        if len(items) < 1:
            return False
        parents = []
        parent = items[0].parent()
        while parent:
            parents.append(parent.text(0))
            item = parent
            parent = item.parent()
        itemName, itemType = self.getVariableInfo(item)
        if itemType in VECTORTYPES:
            self.parent.exportRObjects(False, itemName, itemType, False)
        else:
            return False

    def importFromCanvas(self):
        mlayer = self.parent.iface.mapCanvas().currentLayer()
        self.parent.importRObjects(mlayer = mlayer)
        self.updateVariables()
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
        self.updateVariables()

    def getVariableInfo(self, item):
        item_name = item.text(0)
        item_type = item.text(1)
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

    def updateVariables(self):
        self.variableTable.clear()
        data = self.browseEnv()
        try:
            numofroots = list(data[0])[0]
        except:
            return False
        rootitems = list(data[1])
        names = list(data[2])
        types = list(data[3])
        dims = list(data[4])
        container = list(data[5])
        parentid = list(data[6])
        itemspercontainer = list(data[7])
        ids = list(data[8])
        def which(L, value):
            i = -1
            tmp = []
            try:
                while 1:
                    i = L.index(value, i+1)
                    tmp.append(i)
            except ValueError:
                pass
            return tmp

        for i in range(int(numofroots)):
            iid = rootitems[i]-1
            a = QTreeWidgetItem(self.variableTable)
            a.setText(0, QString(names[int(iid)]))
            a.setText(1, QString(types[int(iid)]))
            a.setText(2, QString(dims[int(iid)]))
            if container[i]:
                items = which(parentid, i+1)
                for id in items:
                    b = QTreeWidgetItem(a)
                    b.setText(0, QString(names[id]))
                    b.setText(1, QString(types[id]))
                    b.setText(2, QString(dims[id]))

    def browseEnv(self):
        parseEnv = robjects.r("""
        function ()
        {
            excludepatt = "^last\\\.warning"
            objlist <- ls(envir=.GlobalEnv)
            if (length(iX <- grep(excludepatt, objlist)))
                objlist <- objlist[-iX]
            n <- length(objlist)
            if (n == 0L) # do nothing!
                return(invisible())

            str1 <- function(obj) {
                md <- mode(obj)
                lg <- length(obj)
                objdim <- dim(obj)
                if (length(objdim) == 0L)
                    dim.field <- paste("length:", lg)
                else {
                    dim.field <- "dim:"
                    for (i in seq_along(objdim)) dim.field <- paste(dim.field,
                        objdim[i])
                    if (is.matrix(obj))
                        md <- "matrix"
                }
                obj.class <- oldClass(obj)
                if (!is.null(obj.class)) {
                    md <- obj.class[1L]
                    if (inherits(obj, "factor"))
                        dim.field <- paste("levels:", length(levels(obj)))
                }
                list(type = md, dim.field = dim.field)
            }
            N <- 0L
            M <- n
            IDS <- rep.int(NA, n)
            NAMES <- rep.int(NA, n)
            TYPES <- rep.int(NA, n)
            DIMS <- rep.int(NA, n)
            IsRoot <- rep.int(TRUE, n)
            Container <- rep.int(FALSE, n)
            ItemsPerContainer <- rep.int(0, n)
            ParentID <- rep.int(-1, n)
            for (objNam in objlist) {
                Spatial = FALSE
                N <- N + 1L
                obj <- get(objNam, envir = .GlobalEnv)
                if (!is.null(class(obj)) && inherits(obj, "Spatial")) {
                    tmpClass <- oldClass(obj)[1L]
                    obj <- obj@data
                    Spatial = TRUE
                }
                sOb <- str1(obj)
                IDS[N] <- N
                NAMES[N] <- objNam
                if (Spatial)
                    TYPES[N] <- tmpClass
                else
                    TYPES[N] <- sOb$type
                DIMS[N] <- sOb$dim.field
                if (is.recursive(obj) && !is.function(obj) && !is.environment(obj) &&
                    (lg <- length(obj))) {
                    Container[N] <- TRUE
                    ItemsPerContainer[N] <- lg
                    nm <- names(obj)
                    if (is.null(nm))
                        nm <- paste("[[", format(1L:lg), "]]", sep = "")
                    for (i in 1L:lg) {
                        M <- M + 1
                        ParentID[M] <- N
                        if (nm[i] == "")
                        nm[i] <- paste("[[", i, "]]", sep = "")
                        s.l <- str1(obj[[i]])
                        IDS <- c(IDS, M)
                        NAMES <- c(NAMES, nm[i])
                        TYPES <- c(TYPES, s.l$type)
                        DIMS <- c(DIMS, s.l$dim.field)
                    }
                }
                else if (!is.null(class(obj))) {
                    if (inherits(obj, "table")) {
                        obj.nms <- attr(obj, "dimnames")
                        lg <- length(obj.nms)
                        if (length(names(obj.nms)) > 0)
                        nm <- names(obj.nms)
                        else nm <- rep.int("", lg)
                        Container[N] <- TRUE
                        ItemsPerContainer[N] <- lg
                        for (i in 1L:lg) {
                        M <- M + 1L
                        ParentID[M] <- N
                        if (nm[i] == "")
                            nm[i] = paste("[[", i, "]]", sep = "")
                        md.l <- mode(obj.nms[[i]])
                        objdim.l <- dim(obj.nms[[i]])
                        if (length(objdim.l) == 0L)
                            dim.field.l <- paste("length:", length(obj.nms[[i]]))
                        else {
                            dim.field.l <- "dim:"
                            for (j in seq_along(objdim.l)) dim.field.l <- paste(dim.field.l,
                            objdim.l[i])
                        }
                        IDS <- c(IDS, M)
                        NAMES <- c(NAMES, nm[i])
                        TYPES <- c(TYPES, md.l)
                        DIMS <- c(DIMS, dim.field.l)
                        }
                    }
                    else if (inherits(obj, "mts")) {
                        nm <- dimnames(obj)[[2L]]
                        lg <- length(nm)
                        Container[N] <- TRUE
                        ItemsPerContainer[N] <- lg
                        for (i in 1L:lg) {
                        M <- M + 1L
                        ParentID[M] <- N
                        md.l <- mode(obj[[i]])
                        dim.field.l <- paste("length:", dim(obj)[1L])
                        md.l <- "ts"
                        IDS <- c(IDS, M)
                        NAMES <- c(NAMES, nm[i])
                        TYPES <- c(TYPES, md.l)
                        DIMS <- c(DIMS, dim.field.l)
                        }
                    }
                }
            }
            Container <- c(Container, rep.int(FALSE, M - N))
            IsRoot <- c(IsRoot, rep.int(FALSE, M - N))
            ItemsPerContainer <- c(ItemsPerContainer, rep.int(0, M -N))
            RootItems <- which(IsRoot)
            NumOfRoots <- length(RootItems)
            return (list(NumOfRoots, RootItems, NAMES,
                        TYPES, DIMS, Container, ParentID,
                        ItemsPerContainer, IDS))
        }""")
        try:
            return parseEnv()
        except Exception, err:
            print err
            return robjects.r("""list(1, 1, c("Error!"),
                        c("Missing package:"), c("'%s'"), c(F), 1,
                        1, 1)""" % str(err).split('"')[1])


class RGraphicsWidget(QWidget):
    
    class TableWidget(QTableWidget):
        def __init__(self, rows, cols, parent):
            QTableWidget.__init__(self, rows, cols, parent)

        def mousePressEvent(self, event):
            item = self.itemAt(event.globalPos())
            if not item and event.button() == Qt.LeftButton:
                self.clearSelection()
            QTableWidget.mousePressEvent(self, event)

        def selectionChanged(self, sela, selb):
            self.emit(SIGNAL("itemSelectionChanged()"))
            QTableWidget.selectionChanged(self, sela, selb)

    def __init__(self, parent):
        QWidget.__init__(self, parent)
        # initialise standard settings
        self.setMinimumSize(30, 30)
        self.parent = parent
        
        self.graphicsTable = self.TableWidget(0, 2, self)
        self.graphicsTable.setAlternatingRowColors(True)
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

        self.activeButton = QToolButton(self)
        self.activeAction = QAction("Set a&ctive", self)
        self.activeAction.setToolTip("Set active device")
        self.activeAction.setWhatsThis("Set active device")
        self.activeAction.setIcon(QIcon(":mActionGraphicActive.png"))
        self.activeAction.setEnabled(False)
        self.activeButton.setDefaultAction(self.activeAction)
        self.activeButton.setAutoRaise(True)

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
        horiz.addWidget(self.activeButton)
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
        self.connect(self.activeAction, SIGNAL("triggered()"), self.activeGraphic)
        self.connect(self.graphicsTable, SIGNAL("itemSelectionChanged()"), self.selectionChanged)
        
    def contextMenuEvent(self, event):
        menu = QMenu(self)
        menu.addAction(self.refreshAction)
        menu.addSeparator()
        menu.addAction(self.rmAction)
        menu.addAction(self.exportAction)
        menu.addAction(self.activeAction)
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
        itemID = QTableWidgetItem(QString(unicode(graphic[0])))
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
            self.activeAction.setEnabled(False)
        else:
            itemName, itemType = self.getGraphicInfo(row)
            self.saveAction.setEnabled(True)
            self.rmAction.setEnabled(True)
            self.exportAction.setEnabled(True)
            self.activeAction.setEnabled(True)

    def activeGraphic(self):
        row = self.graphicsTable.currentRow()
        if row < 0:
            return False
        itemID, itemDevice = self.getGraphicInfo(row)
        self.sendCommands(QString('dev.set(%s)' % (itemID)))

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
        command = QString('dev.set(%s)' % itemID)
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
    Widgets = set()
    Console = None

    def __init__(self, iface, version, filename=QString(),
                isConsole=True, isStandalone=True, parent=None):
        super(MainWindow, self).__init__(parent)
        self.Toolbars = {}
        MainWindow.Instances.add(self)
        self.setWindowTitle("manageR[*]")
        self.setWindowIcon(QIcon(":mActionIcon"))
        self.version = version
        self.iface = iface
        self.isStandalone = isStandalone
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
            self.editor.append(welcomeString(self.version, isStandalone))
            self.editor.setFocus(Qt.ActiveWindowFocusReason)
            self.setCentralWidget(self.editor)
            self.connect(self.editor, SIGNAL("commandComplete()"),self.updateWidgets)
        else:
            self.setAttribute(Qt.WA_DeleteOnClose)
            editor = REditor(self, int(Config["tabwidth"]))
            self.setCentralWidget(editor)
            self.editor = editor.edit
        if Config["enableautocomplete"]:
            self.completer = RCompleter(self.editor,
            delay=Config["delay"])
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
            actionSourceAction = self.createAction("Run S&cript",
                    self.editor.source,"", "mActionSource",
                    "Run the current EditR script")
        else:
            actionShowPrevAction = self.createAction(
                    "Show Previous Command", self.editor.showNext,
                    "Up", "mActionPrevious",
                    ("Show previous command"))
            actionShowNextAction = self.createAction(
                    "Show Next Command", self.editor.showPrevious,
                    "Down", "mActionNext",
                    ("Show next command"))
            if not isStandalone:
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
        libraryBrowserAction = self.createAction("&Library browser", self.libraryBrowser,
                "Ctrl+H", icon="mActionHelpHelp",
                tip="Library browser")
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
            self.addActions(actionMenu, (actionRunAction, actionSourceAction))
        else:
            self.addActions(actionMenu, (actionShowPrevAction, actionShowNextAction))
            if not isStandalone:
                self.addActions(actionMenu, (None, actionImportLayerAction, actionImportAttibutesAction,
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
                message.setDetailedText(unicode(e))
                message.exec_()
                pluginsMenu.deleteLater()
        self.viewMenu = self.menuBar().addMenu("&View")
        self.windowMenu = self.menuBar().addMenu("&Window")
        self.connect(self.windowMenu, SIGNAL("aboutToShow()"),
                     self.updateWindowMenu)
        helpMenu = self.menuBar().addMenu("&Help")
        self.addActions(helpMenu, (libraryBrowserAction, helpHelpAction, helpAboutAction,))

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
            self.addActions(self.actionToolbar, (actionRunAction, actionSourceAction))
        else:
            self.addActions(self.actionToolbar, (None, actionShowPrevAction, actionShowNextAction))
            if not isStandalone:
                self.addActions(self.actionToolbar, (None, actionImportLayerAction,
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
            self.columnCountLabel = QLabel("Column 1")
            status.addPermanentWidget(self.columnCountLabel)
            self.lineCountLabel = QLabel("Line 1 of 1")
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
                self.editor.appendPlainText(Config["newfile"])
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
                robjects.r['setwd'](unicode(Config["setwd"]))
                #cursor = self.editor.textCursor()
                #cursor.movePosition(QTextCursor.StartOfLine,
                #QTextCursor.KeepAnchor)
                #cursor.removeSelectedText()
            # Process required R frontend tasks (load workspace and history)
            splash.showMessage("Checking for previously saved workspace", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            QApplication.processEvents()
            workspace = QFileInfo()
            workspace.setFile(QDir(robjects.r['getwd']()[0]), ".RData")
            load_text = QString("")
            load_check = False
            if workspace.exists():
                load_check = self.loadRWorkspace(workspace.absoluteFilePath(), False)
                if load_check:
                    load_text = QString("[Previously saved workspace ")
                else:
                    self.editor.append("Error: Unable to load previously saved workspace:"
                                     "\nCreating new workspace...")
            splash.showMessage("Checking for history file", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            if self.editor.loadRHistory():
                if load_check:
                    load_text.append("and R history file ")
                else:
                    load_text = QString("[R history file ")
                QApplication.processEvents()
            if not load_text.isEmpty():
                load_text.append("restored]\n")
                self.editor.appendText(load_text)
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
            self.createConsoleWidgets(isStandalone)
            self.restoreState(Config["toolbars"])
            splash.showMessage("Attempting to start/build R html help", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            QApplication.processEvents()
            robjects.r['help.start'](update = True,
            browser=robjects.r('function(url) return(url)'))
            sys.stdout.clear()
            splash.showMessage("manageR ready!", \
            (Qt.AlignBottom|Qt.AlignHCenter), Qt.white)
            splash.finish(self)

        # we do this last to avoid highlighting things before we start
        if Config["enablehighlighting"]:
            self.highlighter = RHighlighter(self.editor, isConsole)
            palette = QPalette(QColor(Config["backgroundcolor"]))
            palette.setColor(QPalette.Active, QPalette.Base, QColor(Config["backgroundcolor"]))
            self.editor.setPalette(palette)
            #self.editor.setTextColor(QColor(Config["normalfontcolor"]))
        QTimer.singleShot(0, self.updateToolbars)
        self.startTimer(30)
        
    def createConsoleWidgets(self, isStandalone):
        graphicWidget = RGraphicsWidget(self)
        graphicWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"),
        graphicWidget.updateGraphics)
        graphicDockWidget = QDockWidget("Graphic Device Manager", self)          
        graphicDockWidget.setObjectName("graphicDockWidget")
        graphicDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        graphicDockWidget.setWidget(graphicWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, graphicDockWidget)
        MainWindow.Widgets.add(graphicWidget)

        variableWidget = RVariableWidget(self, isStandalone)
        #variableWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"),
        #variableWidget.updateVariables)
        variableDockWidget = QDockWidget("Workspace Manager", self)          
        variableDockWidget.setObjectName("variableDockWidget")
        variableDockWidget.setAllowedAreas(Qt.RightDockWidgetArea|Qt.LeftDockWidgetArea)
        variableDockWidget.setWidget(variableWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, variableDockWidget)
        MainWindow.Widgets.add(variableWidget)
        
        historyWidget = RHistoryWidget(self, self.editor)
        historyWidget.connect(self.editor, SIGNAL("updateHistory(PyQt_PyObject)"),
        historyWidget.updateCommands)
        historyDockWidget = QDockWidget("Command History Manager", self)          
        historyDockWidget.setObjectName("historyDockWidget")
        historyDockWidget.setAllowedAreas(Qt.LeftDockWidgetArea|Qt.RightDockWidgetArea)
        historyDockWidget.setWidget(historyWidget)
        self.addDockWidget(Qt.RightDockWidgetArea, historyDockWidget)
        MainWindow.Widgets.add(historyWidget)
        
        cwdWidget = RWDWidget(self,robjects.r('getwd()')[0])
        cwdWidget.connect(self, SIGNAL("updateDisplays(PyQt_PyObject)"), cwdWidget.displayWorkingDir)
        cwdDockWidget = QDockWidget("Working Directory Manager", self)
        cwdDockWidget.setObjectName("cwdDockWidget")
        cwdDockWidget.setAllowedAreas(Qt.TopDockWidgetArea|Qt.BottomDockWidgetArea)
        cwdDockWidget.setWidget(cwdWidget)
        self.addDockWidget(Qt.TopDockWidgetArea, cwdDockWidget)
        MainWindow.Widgets.add(cwdWidget)
        
        self.tabifyDockWidget(graphicDockWidget, historyDockWidget)
        self.tabifyDockWidget(historyDockWidget, variableDockWidget)

        if Config["enablehighlighting"]:
            palette = QPalette(QColor(Config["backgroundcolor"]))
            palette.setColor(QPalette.Active, QPalette.Base, QColor(Config["backgroundcolor"]))
            graphicWidget.setPalette(palette)
            variableWidget.setPalette(palette)
            historyWidget.setPalette(palette)
            cwdWidget.setPalette(palette)
            
        for widget in [cwdDockWidget, variableDockWidget, 
                       graphicDockWidget, historyDockWidget,]:
            action = widget.toggleViewAction()
            self.connect(action, SIGNAL("toggled(bool)"), self.toggleToolbars)
            action.setCheckable(True)
            self.viewMenu.addAction(action)
            self.Toolbars[widget] = action
        self.updateWidgets()
            
    def updateWidgets(self):
        self.emit(SIGNAL("updateDisplays(PyQt_PyObject)"), currentRObjects())

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

    def sendCommands(self, commands):
        commands = QString(commands)
        if not commands.isEmpty():
            mime = QMimeData()
            mime.setText(commands)
            self.editor.moveToEnd()
            self.editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            self.editor.cursor.removeSelectedText()
            self.editor.cursor.insertText(
            self.editor.currentPrompt)
            self.editor.insertFromMimeData(mime)
            self.editor.entered()

    def loadRWorkspace(self, workspace=None, paste=True):
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
                if paste:
                    self.sendCommands("load('%s')" % workspace)
                else:
                    robjects.r['load'](unicode(workspace))
                self.updateWidgets()
        except Exception, e: 
            return False
        return True
        
    def saveRWorkspace(self, workspace=None, paste=True):
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
            if not QString(workspace).isEmpty():
                if paste:
                    self.sendCommands("save.image('%s')" % unicode(workspace))
                else:
                    robjects.r['save.image'](unicode(workspace))
        except Exception, e: 
            return False
        return True
        
    def importLayerAttributes(self):
        self.importRObjects(dataOnly=True)
        
    def importRObjects(self, mlayer=None, dataOnly=False):
        try:
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
            #try:
            if mlayer is None:
                MainWindow.Console.editor.commandError(
                "Error: No layer selected in layer list\n")
                MainWindow.Console.editor.commandComplete()
                return
            rbuf = QString()
            def f(x):
                rbuf.append(x)
            #robjects.rinterface.set_writeconsole(f)
            if not dataOnly and not isLibraryLoaded("sp"):
                raise Exception(RLibraryError("sp"))
            if mlayer.type() == QgsMapLayer.VectorLayer:
                layerCreator = QVectorLayerConverter(mlayer, dataOnly)
            if mlayer.type() == QgsMapLayer.RasterLayer:
                if dataOnly:
                    MainWindow.Console.editor.commandError(
                    "Error: Cannot load raster layer attributes\n")
                    MainWindow.Console.editor.commandComplete()
                    return
                package = "rgdal"
                if Config['useraster']:
                    if not isLibraryLoaded("raster"):
                        raise Exception(RLibraryError("raster"))
                    package = "raster"
                else:
                    if not isLibraryLoaded("rgdal"):
                        raise Exception(RLibraryError("rgdal"))
                    package = "rgdal"
                layerCreator = QRasterLayerConverter(mlayer, package)
            rbuf = sys.stdout.get_and_clean_data(False)
            if rbuf:
                MainWindow.Console.editor.commandOutput(rbuf)
            rLayer, layerName, message = layerCreator.start()
            robjects.r.assign(unicode(layerName), rLayer)
            if not unicode(layerName) in CAT:
                CAT.append(unicode(layerName))
            #self.emit(SIGNAL("newObjectCreated(PyQt_PyObject)"), \
            #self.updateRObjects())
            MainWindow.Console.editor.commandOutput(message)
            #except Exception, e:
            #    MainWindow.Console.editor.commandError(e)
            MainWindow.Console.editor.commandComplete()
        except Exception, err:
            sys.stdout.get_and_clean_data()
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
            ask_save = QMessageBox.question(self, "manageR - Quit", "Save workspace image and history?", 
            QMessageBox.Yes, QMessageBox.No, QMessageBox.Cancel)
            if ask_save == QMessageBox.Cancel:
                event.ignore()
                return
            elif ask_save == QMessageBox.Yes:
                if not self.saveRWorkspace(".RData"):
                    QMessageBox.warning(self, "manageR - Quit", "Unable to save workspace image: Error writing to disk!")
                if not self.editor.saveRHistory():
                    QMessageBox.warning(self, "manageR - Quit", "Unable to save history: Error writing to disk!")
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
        form = ConfigForm(self, self.isStandalone)
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
                for widget in MainWindow.Widgets:
                        palette = QPalette(QColor(Config["backgroundcolor"]))
                        palette.setColor(QPalette.Active,
                        QPalette.Base, QColor(Config["backgroundcolor"]))
                        widget.setPalette(palette)
            saveConfig()


    def fileQuit(self):
        for window in MainWindow.Instances:
            if isAlive(window) and window == MainWindow.Console:
                window.close()
                del window

    def fileNew(self):
        window = MainWindow(self.iface, self.version, isConsole=False, isStandalone=True)
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
                MainWindow(self.iface, self.version, filename, isConsole=False, isStandalone=True).show()


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
        HelpDialog(self.version, self).show()

    def libraryBrowser(self):
        LibraryBrowser(self).show()

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
Copyright &copy; 2009-2010 Carson J. Q. Farmer
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

class QVectorLayerConverter(QObject):

  def __init__(self, mlayer, data_only):
    QObject.__init__(self)
    self.mlayer = mlayer
    self.data_only = data_only
    self.running = False

    # variables are retrived by 'getting' them from the global environment,
    # specifying that we want functions only, which avoids funtions being
    # masked by variable names
    try:
      env = rinterface.globalEnv
      self.as_character_ = robjects.conversion.ri2py(env.get('as.character',wantFun=True))
      self.data_frame_ = robjects.conversion.ri2py(env.get('data.frame',wantFun=True))
      self.matrix_ = robjects.conversion.ri2py(env.get('matrix',wantFun=True))
      self.unlist_ = robjects.conversion.ri2py(env.get('unlist',wantFun=True))
    except:
      self.as_character_ = robjects.r.get('as.character', mode='function')
      self.data_frame_ = robjects.r.get('data.frame', mode='function')
      self.matrix_ = robjects.r.get('matrix', mode='function')
      self.unlist_ = robjects.r.get('unlist', mode='function')
    if not self.data_only:
      # variables from package sp (only needed if featching geometries as well)
      try:
        self.CRS_ = robjects.conversion.ri2py(env.get('CRS',wantFun=True))
        self.Polygon_ = robjects.conversion.ri2py(env.get('Polygon',wantFun=True))
        self.Polygons_ = robjects.conversion.ri2py(env.get('Polygons',wantFun=True))
        self.SpatialPolygons_ = robjects.conversion.ri2py(env.get('SpatialPolygons',wantFun=True))
        self.Line_ = robjects.conversion.ri2py(env.get('Line',wantFun=True))
        self.Lines_ = robjects.conversion.ri2py(env.get('Lines',wantFun=True))
        self.SpatialLines_ = robjects.conversion.ri2py(env.get('SpatialLines',wantFun=True))
        self.SpatialPoints_ = robjects.conversion.ri2py(env.get('SpatialPoints',wantFun=True))
        self.SpatialPointsDataFrame_ = robjects.conversion.ri2py(env.get('SpatialPointsDataFrame',wantFun=True))
        self.SpatialLinesDataFrame_ = robjects.conversion.ri2py(env.get('SpatialLinesDataFrame',wantFun=True))
        self.SpatialPolygonsDataFrame_ = robjects.conversion.ri2py(env.get('SpatialPolygonsDataFrame',wantFun=True))
      except:
        self.CRS_ = robjects.r.get('CRS', mode='function')
        self.Polygon_ = robjects.r.get('Polygon', mode='function')
        self.Polygons_ = robjects.r.get('Polygons', mode='function')
        self.SpatialPolygons_ = robjects.r.get('SpatialPolygons', mode='function')
        self.Line_ = robjects.r.get('Line', mode='function')
        self.Lines_ = robjects.r.get('Lines', mode='function')
        self.SpatialLines_ = robjects.r.get('SpatialLines', mode='function')
        self.SpatialPoints_ = robjects.r.get('SpatialPoints', mode='function')
        self.SpatialPointsDataFrame_ = robjects.r.get('SpatialPointsDataFrame', mode='function')
        self.SpatialLinesDataFrame_ = robjects.r.get('SpatialLinesDataFrame', mode='function')
        self.SpatialPolygonsDataFrame_ = robjects.r.get('SpatialPolygonsDataFrame', mode='function')

  def start( self ):
    self.running = True
    provider = self.mlayer.dataProvider()
    extra = QString()
    if not self.data_only:
      sRs = provider.crs()
      if not sRs.isValid():
        projString = 'NA'
        extra.append( "Unable to determine projection information\nPlease specify using:\n" )
        extra.append( "e.g. layer@proj4string <- CRS('+proj=longlat +datum=NAD83')" )
      else:
        if not sRs.geographicFlag():
          projString = unicode( sRs.toProj4() )
        else:
          # TODO: Find better way to handle geographic coordinate systems
          # As far as I can tell, R does not like geographic coodinate systems input
          # into it's proj4string argument...
          projString = 'NA'
          extra.append( "Unable to determine projection information\nPlease specify using:\n" )
          extra.append( "layer@proj4string <- CRS('+proj=longlat +datum=NAD83') for example." )

    attrIndex = provider.attributeIndexes()
    provider.select(attrIndex)
    fields = provider.fields()
    if len(fields.keys()) <= 0:
      raise Exception("Error: Attribute table must have at least one field")
    df = {}
    types = {}
    order = []
    for (id, field) in fields.iteritems():
      # initial read in has correct ordering...
      name = unicode(field.name())
      df[ name ] = []
      types[ name ] = int( field.type() )
      order.append(name)
    fid = {"fid": []}
    Coords = []
    if self.mlayer.selectedFeatureCount() > 0:
      features = self.mlayer.selectedFeatures()
      for feat in features:
        for (key, value) in df.iteritems():
          df[key].append(self.convertAttribute(feat.attributeMap()[provider.fieldNameIndex(key)]))
        fid["fid"].append(feat.id())
        if not self.data_only:
          if not self.getNextGeometry( Coords, feat):
            raise Exception("Error: Unable to convert layer geometry")
    else:
      feat = QgsFeature()
      while provider.nextFeature(feat):
        for key in df.keys():
          attrib = self.convertAttribute(feat.attributeMap()[provider.fieldNameIndex(key)])
          df[key].append(attrib)
        fid["fid"].append(feat.id())
        if not self.data_only:
          if not self.getNextGeometry( Coords, feat):
            raise Exception("Error: Unable to convert layer geometry")
    tmp = []
    for key in order:
      if types[key] == 10:
        tmp.append((str(key), self.as_character_(robjects.StrVector(df[key]))))
      else:
        tmp.append((str(key), robjects.FloatVector(df[key])))
    try:
        data_frame = rlc.OrdDict(tmp)
    except:
        data_frame = rlike.container.OrdDict(tmp)
    #fid[ "fid" ] = robjects.IntVector( fid["fid"] )
    #data_frame = robjects.r(''' function( d ) data.frame( d ) ''')
    #data = data_frame( df )
    data_frame = robjects.DataFrame(data_frame)
    #data = data_frame( df )
    #data['row.names'] = fid[ "fid" ]
    if not self.data_only:
      message = QString( "QGIS Vector Layer\n" )
      spds = self.createSpatialDataset(feat.geometry().type(), Coords, data_frame, projString)
    else:
      message = QString("QGIS Attribute Table\n")
      spds = data_frame
    length = len(fid["fid"])
    width = len(order)
    name = unicode(self.mlayer.name())
    source = unicode(self.mlayer.publicSource())
    name = unicode(QFileInfo(name).baseName())
    make_names_ = robjects.r.get('make.names', mode='function')
    newname = make_names_(name)[0]
    message.append(QString("Name: " + unicode(newname) + "\nSource: " + unicode(source)))
    message.append( QString("\nwith " + unicode(length) + " rows and " + unicode(width) + " columns"))
    if not newname == name:
      message.append(QString("\n**Note: layer name syntax changed"))
    message.append("\n" + extra)
    return (spds, name, message)

  # Function to retrieve QgsGeometry (polygon) coordinates
  # and convert to a format that can be used by R
  # Return: Item of class Polygons (R class)
  def getPolygonCoords(self, geom, fid):
    if geom.isMultipart():
      keeps = []
      polygon = geom.asMultiPolygon() #multi_geom is a multipolygon
      for lines in polygon:
        for line in lines:
          keeps.append(self.Polygon_(self.matrix_(self.unlist_([self.convertToXY(point) for point in line]),\
          nrow=len([self.convertToXY(point) for point in line]), byrow=True)))
      return self.Polygons_(keeps, fid)
    else:
      lines = geom.asPolygon() #multi_geom is a polygon
      Polygon = [self.Polygon_(self.matrix_(self.unlist_([self.convertToXY(point) for point in line]),\
      nrow=len([self.convertToXY(point) for point in line]), byrow=True)) for line in lines]
      return self.Polygons_(Polygon, fid)

  # Function to retrieve QgsGeometry (line) coordinates
  # and convert to a format that can be used by R
  # Return: Item of class Lines (R class)
  def getLineCoords(self, geom, fid):
    if geom.isMultipart():
      keeps = []
      lines = geom.asMultiPolyline() #multi_geom is a multipolyline
      for line in lines:
        for line in lines:
          keeps.append(self.Line_(self.matrix_(self.unlist_([self.convertToXY(point) for point in line]), \
          nrow=len([self.convertToXY(point) for point in line]), byrow=True)))
      return self.Lines_(keeps, unicode(fid))
    else:
      line = geom.asPolyline() #multi_geom is a line
      Line = self.Line_(self.matrix_(self.unlist_([self.convertToXY(point) for point in line]), \
      nrow = len([self.convertToXY(point) for point in line]), byrow=True))
      return self.Lines_(Line, unicode(fid))

  # Function to retrieve QgsGeometry (point) coordinates
  # and convert to a format that can be used by R
  # Return: Item of class Matrix (R class)
  def getPointCoords(self, geom, fid):
    if geom.isMultipart():
      points = geom.asMultiPoint() #multi_geom is a multipoint
      return [self.convertToXY(point) for point in points]
    else:
      point = geom.asPoint() #multi_geom is a point
      return self.convertToXY(point)

  # Helper function to get coordinates of input geometry
  # Does not require knowledge of input geometry type
  # Return: Appends R type geometry to input list
  def getNextGeometry(self, Coords, feat):
    geom = feat.geometry()
    if geom.type() == 0:
      Coords.append(self.getPointCoords(geom, feat.id()))
      return True
    elif geom.type() == 1:
      Coords.append(self.getLineCoords( geom, feat.id()))
      return True
    elif geom.type() == 2:
      Coords.append(self.getPolygonCoords( geom, feat.id()))
      return True
    else:
      return False

  # Helper function to create Spatial*DataFrame from
  # input spatial and attribute information
  # Return: Object of class Spatial*DataFrame (R class)
  def createSpatialDataset(self, vectType, Coords, data, projString):
    if vectType == 0:
      # For points, coordinates must be input as a matrix, hense the extra bits below...
      # Not sure if this will work for multipoint features?
      spatialData = self.SpatialPoints_(self.matrix_(self.unlist_(Coords), \
      nrow = len(Coords), byrow = True), proj4string = self.CRS_(projString))
      return self.SpatialPointsDataFrame_(spatialData, data)#, match_ID = True )
        #kwargs = {'match.ID':"FALSE"}
        #return SpatialPointsDataFrame( spatialData, data, **kwargs )
    elif vectType == 1:
      spatialData = self.SpatialLines_(Coords, proj4string = self.CRS_(projString))
      kwargs = {'match.ID':"FALSE"}
      return self.SpatialLinesDataFrame_(spatialData, data, **kwargs)
    elif vectType == 2:
      spatialData = self.SpatialPolygons_(Coords, proj4string = self.CRS_(projString))
      kwargs = {'match.ID':"FALSE"}
      return self.SpatialPolygonsDataFrame_(spatialData, data, **kwargs)
    else:
      return ""

  # Function to convert QgsPoint to x, y coordinate
  # Return: list
  def convertToXY(self, inPoint):
    return [inPoint.x(), inPoint.y()]

  # Function to convert attribute to string or double
  # for input into R object
  # Return: Double or String
  def convertAttribute(self, attribute):
    Qtype = attribute.type()
    if Qtype == 10:
      return attribute.toString()
    else:
      return attribute.toDouble()[0]


class QRasterLayerConverter(QObject):

    def __init__(self, mlayer, package):
        QObject.__init__(self)
        self.running = False
        self.mlayer = mlayer
        self.package = package

    def start(self):
        dsn = unicode(self.mlayer.source())
        layer = unicode(self.mlayer.name())
        dsn.replace("\\", "/")
        if self.package == "raster":
            rcode = "raster('%s')" % dsn
        else:
            rcode = "readGDAL(fname = '%s')" % dsn
        rlayer = robjects.r(rcode)
        try:
          summary_ = robjects.conversion.ri2py(
          rinterface.globalEnv.get('summary',wantFun=True))
          slot_ = robjects.conversion.ri2py(
          rinterface.globalEnv.get('@',wantFun=True))
        except:
          summary_ = robjects.r.get('summary', mode='function')
          slot_ = robjects.r.get('@', mode='function')
        message = QString("QGIS Raster Layer\n")
        message.append("Name: " + unicode(self.mlayer.name())
        + "\nSource: " + unicode(self.mlayer.source()) + "\n")
        if self.package == 'raster':
            message.append("Used package 'raster'")
        else:
            message.append(unicode(summary_(slot_(rlayer, 'grid'))))
            message.append("Used package 'rgdal'")
        return (rlayer, layer, message)

class RVectorLayerWriter(QObject):

    def __init__(self, layerName, outName, driver):
        QObject.__init__(self)
        self.driver = driver
        self.outName = outName
        self.layerName = layerName

    def start(self):
        error = False
        filePath = QFileInfo(self.outName).absoluteFilePath()
        filePath.replace("\\", "/")
        file_name = QFileInfo(self.outName).baseName()
        driver_list = self.driver.split("(")
        self.driver = driver_list[0]
        self.driver.chop(1)
        extension = driver_list[1].right(5)
        extension.chop(1)
        if not filePath.endsWith(extension, Qt.CaseInsensitive):
          filePath = filePath.append(extension)
        if not file_name.isEmpty():
          r_code = "writeOGR(obj=%s, dsn='%s', layer='%s', driver='%s')" % (unicode(self.layerName),
          unicode(filePath), unicode(file_name), unicode(self.driver))
        robjects.r(r_code)
        vlayer = QgsVectorLayer(unicode(filePath), unicode(file_name), "ogr")
        return vlayer

class RRasterLayerWriter(QObject):

    def __init__(self, layerName, outName, driver):
        QObject.__init__(self)
        self.driver = driver
        self.layerName = layerName
        self.outName = outName

    def start(self):
        filePath = QFileInfo(self.outName).absoluteFilePath()
        filePath.replace("\\", "/")
        file_name = QFileInfo(self.outName).baseName()
        driver_list = self.driver.split("(")
        self.driver = driver_list[0]
        self.driver.chop(1)
        extension = driver_list[1].right(5)
        extension.chop(1)
        if self.driver == "GeoTIFF": self.driver = "GTiff"
        elif self.driver == "Erdas Imagine Images": self.driver = "HFA"
        elif self.driver == "Arc/Info ASCII Grid": self.driver = "AAIGrid"
        elif self.driver == "ENVI Header Labelled": self.driver = "ENVI"
        elif self.driver == "JPEG-2000 part 1": self.driver = "JPEG2000"
        elif self.driver == "Portable Network Graphics": self.driver = "PNG"
        elif self.driver == "USGS Optional ASCII DEM": self.driver = "USGSDEM"
        if not filePath.endsWith(extension, Qt.CaseInsensitive) and self.driver != "ENVI":
            filePath = filePath.append(extension)
        if not filePath.isEmpty():
            if self.driver == "AAIGrid" or self.driver == "JPEG2000" or \
            self.driver == "PNG" or self.driver == "USGSDEM":
                r_code = "saveDataset(dataset=copyDataset(create2GDAL(dataset=%s, type='Float32'), driver='%s'), filename='%s')" % (unicode(self.layerName),
                unicode(self.driver), unicode(filePath))
                robjects.r(r_code)
            else:
                r_code = "writeGDAL(dataset=%s, fname='%s', drivername='%s', type='Float32')" % (unicode(self.layerName),
                unicode(filePath), unicode(self.driver))
        robjects.r(r_code)
        rlayer = QgsRasterLayer(unicode(filePath), unicode(file_name))
        return rlayer

class RVectorLayerConverter(QObject):
    '''
    RVectorLayerConvert:
    This aclass is used to convert an R
    vector layer to a QgsVector layer for export
    to the QGIS map canvas.
    '''
    def __init__(self, r_layer, layer_name):
        QObject.__init__(self)
        self.r_layer = r_layer
        self.layer_name = layer_name
        # define R functions as python variables
        self.slot_ = robjects.r.get('@', mode='function')
        self.get_row_ = robjects.r(''' function(d, i) d[i] ''')
        self.get_full_row_ = robjects.r(''' function(d, i) data.frame(d[i,]) ''')
        self.get_point_row_ = robjects.r(''' function(d, i) d[i,] ''')
        self.class_ = robjects.r.get('class', mode='function')
        self.names_ = robjects.r.get('names', mode='function')
        self.dim_ = robjects.r.get('dim', mode='function')
        self.as_character_ = robjects.r.get('as.character', mode='function')

    #def run(self):
    def start(self):
        '''
        Main working function
        Emits threadSuccess when completed successfully
        Emits threadError when errors occur
        '''
        self.running = True
        error = False
        vtype = self.checkIfRObject(self.r_layer)
        vlayer = QgsVectorLayer(vtype, unicode(self.layer_name), "memory")
        crs = QgsCoordinateReferenceSystem()
        crs_string =  self.slot_(self.slot_(self.r_layer, "proj4string"), "projargs")[0]
        # Figure out a better way to handle this problem:
        # QGIS does not seem to like the proj4 string that R outputs when it
        # contains +towgs84 as the final parameter
        crs_string = crs_string.lstrip().partition(" +towgs84")[0]
        if crs.createFromProj4(crs_string):
            vlayer.setCrs(crs)
        provider = vlayer.dataProvider()
        fields = self.getAttributesList()
        self.addAttributeSorted(fields, provider)
        rowCount = self.getRowCount()
        feat = QgsFeature()
        for row in range(1, rowCount + 1):
            if vtype == "Point": coords = self.getPointCoords(row)
            elif vtype == "Polygon": coords = self.getPolygonCoords(row)
            else: coords = self.getLineCoords(row)
            attrs = self.getRowAttributes(provider, row)
            feat.setGeometry(coords)
            feat.setAttributeMap(attrs)
            provider.addFeatures([feat])
        vlayer.updateExtents()
        return vlayer

    def addAttributeSorted(self, attributeList, provider):
        '''
        Add attribute to memory provider in correct order
        To preserve correct order they must be added one-by-one
        '''
        for (i, j) in attributeList.iteritems():
            try:
                provider.addAttributes({i : j})
            except:
                if j == "int": j = QVariant.Int
                elif j == "double": j = QVariant.Double
                else: j = QVariant.String
                provider.addAttributes([QgsField(i, j)])

    def getAttributesList(self):
        '''
        Get list of attributes for R layer
        Return: Attribute list in format to be used by memory provider
        '''
        typeof_ = robjects.r.get('typeof', mode='function')
        sapply_ = robjects.r.get('sapply', mode='function')
        try:
            in_types = sapply_(self.slot_(self.r_layer, "data"), typeof_)
        except:
            raise Exception("Error: R vector layer contains unsupported field type(s)")
        in_names = self.names_(self.r_layer)
        out_fields = dict()
        for i in range(0, len(in_types)):
            if in_types[i] == "double": out_fields[in_names[i]] = "double"
            elif in_types[i] == "integer": out_fields[in_names[i]] = "int"
            else: out_fields[in_names[i]] =  "string"
        return out_fields

    def checkIfRObject(self, layer):
        '''
        Check if the input layer is an sp vector layer
        Return: True if it is, as well as the vector type
        '''
        check = self.class_(layer)[0]
        if check == "SpatialPointsDataFrame": return "Point"
        elif check == "SpatialPolygonsDataFrame": return "Polygon"
        elif check == "SpatialLinesDataFrame": return "LineString"
        else:
            raise Exception("Error: R vector layer is not of type Spatial*DataFrame")

    def getRowCount(self):
        '''
        Get the number of features in the R spatial layer
        Return: Feature count
        '''
        return int(self.dim_(self.slot_(self.r_layer, "data"))[0])

    def getRowAttributes(self, provider, row):
        '''
        Get attributes associated with a single R feature
        Return: python dictionary containing key/value pairs,
        where key = field index and value = attribute
        '''
        temp = self.get_full_row_(self.slot_(self.r_layer, "data"), row)
        names = self.names_(self.r_layer)
        out = {}
        if not provider.fieldCount() > 1:
            out = {0 : QVariant(temp[0])}
        else:
        #    return dict(zip([provider.fieldNameIndex(str(name)) for name in names],
        #    [QVariant(item[0]) for item in temp]))
            count = 0
            for field in temp:
                if self.class_(field)[0] == "factor":
                    out[provider.fieldNameIndex(unicode(names[count]))] = QVariant(self.as_character_(field)[0])
                else:
                    out[provider.fieldNameIndex(unicode(names[count]))] = QVariant(field[0])
                count += 1
        return out

    def getPointCoords(self, row):
        '''
        Get point coordinates of an R point feature
        Return: QgsGeometry from a point
        '''
        coords = self.get_point_row_(self.slot_(self.r_layer, 'coords'), row)
        return QgsGeometry.fromPoint(QgsPoint(coords[0], coords[1]))

    def getPolygonCoords(self, row):
        '''
        Get polygon coordinates of an R polygon feature
        Return: QgsGeometry from a polygon and multipolygon
        '''
        Polygons = self.get_row_(self.slot_(self.r_layer, "polygons"), row)
        polygons_list = []
        for Polygon in Polygons:
            polygon_list = []
            polygons = self.slot_(Polygon, "Polygons")
            for polygon in polygons:
                line_list = []
                points_list = self.slot_(polygon, "coords")
                y_value = len(points_list)  / 2
                for j in range(0, y_value):
                    line_list.append(self.convertToQgsPoints(
                    (points_list[j], points_list[j + y_value])))
                polygon_list.append(line_list)
            polygons_list.append(polygon_list)
        return QgsGeometry.fromMultiPolygon(polygons_list)

    def getLineCoords(self, row):
        '''
        Get line coordinates of an R line feature
        Return: QgsGeometry from a line or multiline
        '''
        Lines = self.get_row_(self.slot_(self.r_layer, 'lines'), row)
        lines_list = []
        for Line in Lines:
            lines = self.slot_(Line, "Lines")
            for line in lines:
                line_list = []
                points_list = self.slot_(line, "coords")
                y_value = len(points_list)  / 2
                for j in range(0, y_value):
                    line_list.append(self.convertToQgsPoints((points_list[j], points_list[j + y_value])))
            lines_list.append(line_list)
        return QgsGeometry.fromMultiPolyline(lines_list)

    def convertToQgsPoints(self, in_list):
        '''
        Function to convert x, y coordinates list to QgsPoint
        Return: QgsPoint
        '''
        return QgsPoint(in_list[0], in_list[1])

"""Usage:
from PyQt4 import QtCore, QtGui
from GenericVerticalUI import GenericVerticalUI
class GenericNewDialog(QDialog):
    def __init__(self):
        QDialog.__init__(self)
        # Set up the user interface from Designer.
        self.ui = GenericVerticalUI ()
        interface=[["label combobox","comboBox","a;b;c;d","false"   ] , ["label spinbox","doubleSpinBox","10","false"   ] ]
        self.ui.setupUi(self,interface)
"""

class SpComboBox(QComboBox):
    def __init__(self, parent=None, types=QStringList()):
        super(SpComboBox, self).__init__(parent)
        self.types = types

    def spTypes(self):
        return self.types

class SpListWidget(QListWidget):
    def __init__(self, parent=None,
        types=QStringList(), delimiter=','):
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
            widget = QComboBox(ParentClass)
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
            QAbstractItemView.ExtendedSelection)
        elif widgetType=="doubleSpinBox":
            widget = QDoubleSpinBox(ParentClass)
            widget.setValue(float(default))
            widget.setFixedHeight(26)
            widget.setMaximum(999999.9999)
            widget.setDecimals(4)
        elif widgetType=="textEdit":
            widget = QTextEdit(ParentClass)
            widget.setPlainText(default)
            widget.setMinimumHeight(116)
        elif widgetType=="helpString":
            self.helpString = default
            skip = True
        elif widgetType == "dataComboBox":
            # Check that the R package can be and is loaded
            isLibraryLoaded(default)
            # Create the widget
            widget = QComboBox(ParentClass)
            widget.addItems(listDataSets(package=default))
            widget.setFixedHeight(26)
        else:
            #if unknown assumes lineEdit
            widget = QLineEdit(ParentClass)
            widget.setText(default)
            widget.setFixedHeight(26)
        if not skip:
            hbox = QHBoxLayout()
            name="widget"+unicode(self.widgetCounter)
            widget.setObjectName(name)
            widget.setMinimumWidth(250)
            self.widgets.append(widget)
            name="label"+unicode(self.widgetCounter)
            self.widgetCounter += 1
            label = QLabel(ParentClass)
            label.setObjectName(name)
            label.setFixedWidth(width*8)
            label.setText(parameters[0])
            hbox.addWidget(label)
            hbox.addWidget(widget)
            self.vbox.addLayout(hbox)

    def isSpatial(self):
        return self.hasSpComboBox

    def updateRObjects(self):
        splayers = currentRObjects()[0]
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
                            names =  robjects.r('names(%s)' % (layer))
                            if not unicode(names) == 'NULL':
                                for item in list(names):
                                    if splayers[layer] == "data.frame":
                                        value = layer+"$"+item
                                    else:
                                        value = layer+"@data$"+item
                                    if unicode(robjects.r('class(%s)' % (value))[0]) == sptype.strip() \
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
        self.vbox = QVBoxLayout(self.ParentClass)
        for item in itemlist:
            if len(item[0]) > width:
                width = len(item[0])
        # Draw a label/widget pair for every item in the list
        for item in itemlist:
            self.addGuiItem(self.ParentClass, item, width)
        self.showCommands = QCheckBox("Append commands to console",self.ParentClass)
        self.buttonBox = QDialogButtonBox(self.ParentClass)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(
        QDialogButtonBox.Help|QDialogButtonBox.Close|QDialogButtonBox.Ok)
        self.buttonBox.setObjectName("buttonBox")
        self.vbox.addWidget(self.showCommands)
        self.vbox.addWidget(self.buttonBox)
        # accept gets connected in the plugin manager
        QObject.connect(self.buttonBox, SIGNAL("rejected()"), self.ParentClass.reject)
        QObject.connect(self.buttonBox, SIGNAL("helpRequested()"), self.help)
        #QMetaObject.connectSlotsByName(self.ParentClass)

    def help(self):
        if QString(self.helpString).startsWith("topic:"):
            topic = QString(self.helpString).remove("topic:")
            self.ParentClass.parent().editor.moveToEnd()
            self.ParentClass.parent().editor.cursor.movePosition(
            QTextCursor.StartOfBlock, QTextCursor.KeepAnchor)
            self.ParentClass.parent().editor.cursor.removeSelectedText()
            self.ParentClass.parent().editor.cursor.insertText(
            "%shelp(%s)" % (
            self.ParentClass.parent().editor.currentPrompt,
            unicode(topic)))
            self.ParentClass.parent().editor.execute(
            QString("help('%s')" % (unicode(topic))))
        else:
            HelpForm(self.ParentClass, self.helpString).show()

class HelpForm(QDialog):

    def __init__(self, parent=None, text=""):
        #super(HelpForm, self).__init__(parent)
        self.setAttribute(Qt.WA_GroupLeader)
        self.setAttribute(Qt.WA_DeleteOnClose)
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setHtml(text)
        layout = QVBoxLayout()
        layout.setMargin(0)
        layout.addWidget(browser)
        self.setLayout(layout)
        self.resize(400, 200)
        QShortcut(QKeySequence("Escape"), self, self.close)
        self.setWindowTitle("R plugin - Help")

class PluginManager:
    def __init__(self, parent):#, iface):
        ## Save reference to the QGIS interface
        #self.iface = iface
        #self.tools = os.path.join(str(os.path.abspath(os.path.dirname(__file__))),"tools.xml")
        self.tools = os.path.join(CURRENTDIR,"tools.xml")
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
                text=unicode(item.toPlainText())
            elif type(item)==type(QLineEdit()):
                text=unicode(item.text())
            elif type(item)==type(QDoubleSpinBox()):
                text=unicode(item.value())
            elif type(item)==type(QComboBox()):
                text=unicode(item.currentText())
            elif isinstance(item, SpListWidget):
                items=item.selectedItems()
                text=QString()
                for j in items:
                    text.append(j.text()+item.spDelimiter())
                text.remove(-1,1)
            else:
                try:
                    text=unicode(item.currentText())
                except:
                    text="Error loading widget."
            command = command.replace("|"+unicode(i+1)+"|",text)
        self.runCommand(command)
        self.dlg.close()

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
        # show the dialog
        self.dlg.show()

class PluginsDialog(QDialog):
    def __init__(self, parent, interface):
        QDialog.__init__(self, parent)
        self.ui = GenericVerticalUI()
        self.ui.setupUi(self, interface)

def isAlive(qobj):
    import sip
    try:
        sip.unwrapinstance(qobj)
    except RuntimeError:
        return False
    return True

if __name__ == '__main__':
    app = QApplication(sys.argv)
    try:
        import rpy2
        import rpy2.robjects as robjects
    #  import rpy2.rinterface as rinterface
    except ImportError:
        QMessageBox.warning(None , "manageR", "Unable to load manageR: Unable to load required package rpy2."
        + "\nPlease ensure that both R, and the corresponding version of Rpy2 are correctly installed.")

    if not sys.platform.startswith(("linux", "win")):
        app.setCursorFlashTime(0)
    app.setOrganizationName("manageR")
    app.setOrganizationDomain("ftools.ca")
    app.setApplicationName("manageR")
    app.setWindowIcon(QIcon(":mActionIcon.png"))
    loadConfig()

    if len(sys.argv) > 1:
        args = sys.argv[1:]
        if len(args)>0:
            sys.stdout = original
            print """usage: manageR.py
                manageR requires Python 2.5 and PyQt 4.2 (or later versions)
                For more information run the program and click
                Help->About and/or Help->Help"""
            sys.exit(0)

    if not MainWindow.Instances:
        MainWindow(None, "1.0").show()
    app.exec_()
    saveConfig()

