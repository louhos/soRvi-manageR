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

from PyQt4.QtCore import *
from qgis.core import *
import rpy2.robjects as robjects

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
        self.slot_ = robjects.r['@']
        self.get_row_ = robjects.r(''' function(d, i) d[i] ''')
        self.get_full_row_ = robjects.r(''' function(d, i) data.frame(d[i,]) ''')
        self.get_point_row_ = robjects.r(''' function(d, i) d[i,] ''')
        self.class_ = robjects.r['class']
        self.names_ = robjects.r['names']
        self.dim_ = robjects.r['dim']
        self.as_character_ = robjects.r['as.character']

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
        typeof_ = robjects.r['typeof']
        sapply_ = robjects.r['sapply']
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
                    out[provider.fieldNameIndex(str(names[count]))] = QVariant(self.as_character_(field)[0])
                else:
                    out[provider.fieldNameIndex(str(names[count]))] = QVariant(field[0])
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

