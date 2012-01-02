#!/usr/bin/env python
# -*- coding: utf-8 -*-

'''
This file is part of soRvi-manageR

Copyright (C) 2011-12 Joona Lehtomäki

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

This module is extension to manageR-plugin for QGIS By Carson J. Q. Farmer
'''

from PyQt4.QtGui import (QMessageBox)

try:
    import rpy2.robjects as robjects
#  import rpy2.rinterface as rinterface
except ImportError:
    QMessageBox.warning(None , "manageR", "Unable to load manageR: Unable to load required package rpy2."
                        + "\nPlease ensure that both R, and the corresponding version of Rpy2 are correctly installed.")

from manageR import isLibraryLoaded

def listDataSets(package): 
    isLibraryLoaded(package)
    rdata = robjects.r["data"]
    data = rdata(package=package).rx2('results')
    return [data.rx(row_i, True)[2] for row_i in range(1, data.nrow + 1)]

if __name__ == '__main__':
    print(listDataSets('sorvi'))