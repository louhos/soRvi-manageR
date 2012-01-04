#!/usr/bin/env python

import os
import shutil
import sys

# List file that will be copied to QGIS plugins dir
FILES = ['__init__.py', 'LICENSE', 'manageR.py', 
         'plugin.py', 'resources.py', 'tools.xml']
PLUGIN_DIR = 'soRvi-manageR'
    
QGIS_HOME = os.path.expanduser('~/.qgis/python/plugins')

PLUGIN_DIR = os.path.join(QGIS_HOME, PLUGIN_DIR)

if not os.path.exists(QGIS_HOME):
    print('QGIS home folder not found at %s' % QGIS_HOME)
    sys.exit(0)
if not os.path.exists(PLUGIN_DIR):
    print('Plugin dir not found at: %s' % PLUGIN_DIR)
    sys.exit(0)

source_dir = os.path.abspath(os.path.dirname(__file__))
print('**Copying files**')
print('Source: %s' % source_dir)
print('Destination: %s' % os.path.join(QGIS_HOME, PLUGIN_DIR))
for _file in FILES:
    source = os.path.join(source_dir, _file)
    target = os.path.join(PLUGIN_DIR, _file)
    if os.path.exists(source):
        try:
            shutil.copy2(source, target)
            print('Copied file %s' % _file)
        except IOError, e:
            print('Error while copying %s' % _file)
            sys.exit(0)
    else:
        print('File %s not found!' % _file)
print('Finished copying')
sys.exit(1)
