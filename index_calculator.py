# -*- coding: utf-8 -*-
"""
/***************************************************************************
 IndexCalculator
                                 A QGIS plugin
 This plugin calculates different indexes from Sentinel 2 snapshots.
 Generated by Plugin Builder: http://g-sherman.github.io/Qgis-Plugin-Builder/
                              -------------------
        begin                : 2021-03-07
        git sha              : $Format:%H$
        copyright            : (C) 2021 by Veronika Hajdúchová
        email                : hajduchova18@uniba.sk
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""
from qgis.PyQt.QtCore import *
from qgis.PyQt.QtGui import QIcon
from qgis.PyQt.QtWidgets import QAction, QFileDialog, QProgressBar
from qgis.core import *
from qgis.gui import QgsDoubleSpinBox
from qgis.core import QgsProject, Qgis, QgsRasterLayer
import processing,tempfile
from qgis.utils import iface
import os
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator
from qgis.core import QgsRasterLayer
from qgis.core import QgsProject
from qgis.analysis import QgsRasterCalculatorEntry, QgsRasterCalculator

from qgis.analysis import QgsRasterCalculator, QgsRasterCalculatorEntry


# Initialize Qt resources from file resources.py
from .resources import *
# Import the code for the dialog
from .index_calculator_dialog import IndexCalculatorDialog
import os.path
import time


class IndexCalculator:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'IndexCalculator_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)
            QCoreApplication.installTranslator(self.translator)

        self.dlg = IndexCalculatorDialog()

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&Index Calculator')

        # Check if plugin was started the first time in current QGIS session
        # Must be set in initGui() to survive plugin reloads
  ##      #self.first_start = None
        self.toolbar = self.iface.addToolBar(u'indices')
        self.toolbar.setObjectName(u'indices')




    # noinspection PyMethodMayBeStatic
    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('IndexCalculator', message)


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        self.dlg = IndexCalculatorDialog()


        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            # Adds plugin icon to Plugins toolbar
            self.iface.addToolBarIcon(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/index_calculator/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'Index Calculator'),
            callback=self.run,
            parent=self.iface.mainWindow())

        # will be set False in run()
        self.first_start = True
        
    def update_rasters_boxes(self):

        self.clear_boxes(
                self.dlg.cmb_blue,
                self.dlg.cmb_green,
                self.dlg.cmb_red,
                self.dlg.cmb_vnir,
                self.dlg.cmb_nir,
                self.dlg.cmb_b9,
                self.dlg.cmb_b11,
                self.dlg.cmb_b12
            )

        layers = list()
        layers.append("Not Set")
        layers = layers + [lay.name() for lay in self.iface.mapCanvas().layers()]

        self.add_layers_to_raster_boxes(
            layers,
            self.dlg.cmb_blue,
            self.dlg.cmb_green,
            self.dlg.cmb_red,
            self.dlg.cmb_vnir,
            self.dlg.cmb_nir,
            self.dlg.cmb_b9,
            self.dlg.cmb_b11,
            self.dlg.cmb_b12
        )

    def add_layers_to_raster_boxes(self, layers, *boxes):
        for box in boxes:
            box.addItems(layers)

    def clear_boxes(self, *boxes):
        for box in boxes:
            box.clear()

    # method for selecting the resulting raster file
    def saveRaster(self):
        filename = QFileDialog.getExistingDirectory(
            self.dlg, "Select folder"
        )
        self.dlg.le_output.setText(filename)


    def blue(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_blue.addItems(raster_layers)

    def green(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_green.addItems(raster_layers)

    def red(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_red.addItems(raster_layers)

    def vnir(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_vnir.addItems(raster_layers)

    def nir(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_nir.addItems(raster_layers)

    def b9(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_b9.addItems(raster_layers)
  
    def b11(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_b11.addItems(raster_layers)

    def b12(self):
        layers = [layer for layer in QgsProject.instance().mapLayers().values()]
        raster_layers = []
        for layer in layers:
            if layer.type() == QgsMapLayer.RasterLayer:
                raster_layers.append(layer.name())
        self.dlg.cmb_b12.addItems(raster_layers)


    def getBlue(self):
        layer = None
        layername = self.dlg.cmb_blue.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getGreen(self):
        layer = None
        layername = self.dlg.cmb_green.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getRed(self):
        layer = None
        layername = self.dlg.cmb_red.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getVNir(self):
        layer = None
        layername = self.dlg.cmb_vnir.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer
    
    def getNir(self):
        layer = None
        layername = self.dlg.cmb_nir.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getB9(self):
        layer = None
        layername = self.dlg.cmb_b9.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getB11(self):
        layer = None
        layername = self.dlg.cmb_b11.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer

    def getB12(self):
        layer = None
        layername = self.dlg.cmb_b12.currentText()
        for lyr in QgsProject.instance().mapLayers().values():
            if lyr.name() == layername:
                layer = lyr
                break
        return layer


    def final(self):
        if self.dlg.cb_ARVI.isChecked():
            self.calc_arvi()
        if self.dlg.cb_BRI.isChecked():
            self.calc_bri()
        if self.dlg.cb_CVI.isChecked():
            self.calc_cvi()
        if self.dlg.cb_DVI.isChecked():
            self.calc_dvi()
        if self.dlg.cb_GEMI.isChecked():
            self.calc_gemi()
        if self.dlg.cb_GVMI.isChecked():
            self.calc_gvmi()
        if self.dlg.cb_NDSI.isChecked():
            self.calc_ndsi()
        if self.dlg.cb_NDVI.isChecked():
            self.calc_ndvi()
        if self.dlg.cb_RVI.isChecked():
            self.calc_rvi()
        if self.dlg.cb_SAVI.isChecked():
            self.calc_savi()
############################################################################

    def calc_arvi(self):
        lyr1 = self.getRed()
        lyr2 = self.getBlue()
        lyr3 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"arvi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #blueband
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'blue'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        #nir
        ras3 = QgsRasterCalculatorEntry()
        ras3.ref = 'nir'
        ras3.raster = lyr3
        ras3.bandNumber = 1
        entries.append( ras3 )
        calc = QgsRasterCalculator( '("nir" - (2 * "red") + "blue") / ("nir" + (2 * "red") + "blue")', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("ARVI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_bri(self):
        lyr1 = self.getVNir()
        lyr2 = self.getGreen()
        lyr3 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"bri.tif")

        entries = []
        #vnir band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'vnir'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #green band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'green'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        #nir
        ras3 = QgsRasterCalculatorEntry()
        ras3.ref = 'nir'
        ras3.raster = lyr3
        ras3.bandNumber = 1
        entries.append( ras3 )
        calc = QgsRasterCalculator( '(1.0 / "vnir" - 1.0 / "green") / "nir"', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("BRI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_cvi(self):
        lyr1 = self.getRed()
        lyr2 = self.getNir()
        lyr3 = self.getGreen()
        output = os.path.join(self.dlg.le_output.text(),"cvi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #nir band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'nir'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        #green band
        ras3 = QgsRasterCalculatorEntry()
        ras3.ref = 'green'
        ras3.raster = lyr3
        ras3.bandNumber = 1
        entries.append( ras3 )

        calc = QgsRasterCalculator( '"nir" * ("red" / ("green" * "green"))', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("CVI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_dvi(self):
        lyr1 = self.getVNir()
        lyr2 = self.getB9()
        output = os.path.join(self.dlg.le_output.text(),"dvi.tif")

        entries = []
        #vnir band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'vnir'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #b9 band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'b9'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '"b9" / "vnir"', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("DVI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_gvmi(self):
        lyr1 = self.getNir()
        lyr2 = self.getB12()
        output = os.path.join(self.dlg.le_output.text(),"gvmi.tif")

        entries = []
        #nir band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'nir'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #b12 band#
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'b12'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '(("nir" + 0.1) - ("b12" + 0.02)) / (("nir" + 0.1) + ("b12" + 0.02))', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("GVMI Output Created Successfully", level=Qgis.Success, duration=3)  

    def calc_gemi(self):
        lyr1 = self.getRed()
        lyr2 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"gemi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #nir band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'nir'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '((2.0 * ("nir" ^ 2.0) - "red" ^ 2.0) + 1.5 * "nir" + 0.5 * "red") / ("nir" + "red" + 0.5) * (1.0 - 0.25 * (2.0 * ("nir" ^ 2.0) - "red" ^ 2.0) + 1.5 * "nir" + 0.5 * "red") / ("nir" + "red" + 0.5) - (("red" - 0.125) / (1.0 - "red"))', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("GEMI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_ndsi(self):
        lyr1 = self.getB11()
        lyr2 = self.getB12()
        output = os.path.join(self.dlg.le_output.text(),"ndsi.tif")

        entries = []
        #b11 band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'b11'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #b12 band#
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'b12'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '("b11" -  "b12") / ("b11" + "b12")', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation() 
        self.iface.messageBar().pushMessage("NDSI Output Created Successfully", level=Qgis.Success, duration=3)
        
    def calc_ndvi(self):
        lyr1 = self.getRed()
        lyr2 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"ndvi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #nir band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'nir'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '("nir" -  "red") / ("nir" + "red")', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("NDVI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_rvi(self):
        lyr1 = self.getRed()
        lyr2 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"rvi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #nir band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'nir'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '"nir" / "red"', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("RVI Output Created Successfully", level=Qgis.Success, duration=3)

    def calc_savi(self):
        lyr1 = self.getRed()
        lyr2 = self.getNir()
        output = os.path.join(self.dlg.le_output.text(),"savi.tif")

        entries = []
        #red band
        ras1 = QgsRasterCalculatorEntry()
        ras1.ref = 'red'
        ras1.raster = lyr1
        ras1.bandNumber = 1
        entries.append(ras1)
        #nir band
        ras2 = QgsRasterCalculatorEntry()
        ras2.ref = 'nir'
        ras2.raster = lyr2
        ras2.bandNumber = 1
        entries.append( ras2 )
        calc = QgsRasterCalculator( '(("nir" - "red") / ("nir" + "red" + 0.5)) * (1 + 0.5)', \
        output, 'GTiff', lyr1.extent(), lyr1.width(), lyr1.height(), entries )
        calc.processCalculation()
        self.iface.messageBar().pushMessage("SAVI Output Created Successfully", level=Qgis.Success, duration=3)

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&Index Calculator'),
                action)
            self.iface.removeToolBarIcon(action)
        del self.toolbar

    def run(self):
        """Run method that performs all the real work"""

        # Create the dialog with elements (after translation) and keep reference
        self.update_rasters_boxes()
        
        self.dlg.le_output.clear()

        self.dlg.tb_output.clicked.connect(self.saveRaster)
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            self.final()   
                        
           
            #self.iface.messageBar().pushMessage("Output Created Successfully", level=Qgis.Success, duration=3)            
            self.dlg.tb_output.clicked.disconnect(self.saveRaster)