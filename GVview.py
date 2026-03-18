#!/usr/bin/env python

import os, sys
os.environ['PYART_QUIET'] = '1'  # Suppress PyART citation

# ==================== SUPPRESS macOS Qt WARNINGS ====================
if sys.platform == "darwin":  # macOS only
    os.environ['QT_MAC_WANTS_LAYER'] = '1'
    os.environ['QT_LOGGING_RULES'] = 'qt.qpa.*=false'

import pyart
import numpy as np
import math
import copy
import matplotlib
matplotlib.use('Qt5Agg')
matplotlib.rcParams['backend'] = 'Qt5Agg'
matplotlib.rcParams['agg.path.chunksize'] = 0
import matplotlib.pyplot as plt
import matplotlib.colors as colors
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.colors import Normalize

# ==================== SUPPRESS NSOpenPanel WARNING DURING PyQt5 IMPORT ====================
if sys.platform == "darwin":
    import io
    old_stderr = sys.stderr
    sys.stderr = io.StringIO()  # Temporarily capture stderr

# Import PyQt5 (warning happens here)
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QComboBox, QPushButton, QLabel, QSizePolicy,
                            QFileDialog, QCheckBox, QSpinBox, QDoubleSpinBox,
                            QDialog, QTabWidget, QFormLayout, QDialogButtonBox, 
                            QTableWidget, QHeaderView, QTableWidgetItem, QToolBar, 
                            QAction, QMessageBox, QListWidget, QAbstractItemView,
                            QTextEdit, QLineEdit, QFrame)
from PyQt5.QtCore import Qt, QTimer, QThread, pyqtSignal, QSettings
from PyQt5.QtGui import QFont

# Restore stderr after PyQt5 is imported
if sys.platform == "darwin":
    sys.stderr = old_stderr

# Continue with other imports
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.shapereader as shpreader
from cartopy.mpl.gridliner import LONGITUDE_FORMATTER, LATITUDE_FORMATTER
from PIL import Image
import datetime
from cftime import date2num, num2date
import gzip, gc
import tempfile
import shutil
import requests
import platform
import mmap
import warnings
warnings.filterwarnings('ignore')

plt.rcParams['figure.max_open_warning'] = 0
plt.rcParams['axes.formatter.useoffset'] = False

def create_gv_colormaps():
    """
    Create all GPM-GV legacy colormaps from IDL RSL color tables.
    Returns a dictionary of colormap objects.
    """
    from matplotlib.colors import ListedColormap
    
    colormaps = {}
    
    # ==================== GV_DZ: Reflectivity ====================
    # Range: -20 to 60 dBZ, Bin: 5 dBZ, 17 colors
    r = [0, 102, 153,   0,   0,   0,   0,   0,   0, 255, 255, 255, 241, 196, 151, 239, 135]
    g = [0, 102, 153, 218, 109,   0, 241, 190, 139, 253, 195, 138,   0,   0,   0,   0,  35]
    b = [0, 102, 153, 223, 227, 232,   1,   0,   0,   0,   0,   0,   0,   0,   0, 255, 255]
    colors_dz = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_dz = ListedColormap(colors_dz, name='GV_DZ')
    cmap_dz.set_bad(color='black')
    colormaps['GV_DZ'] = cmap_dz
    
    # ==================== GV_VR: Velocity ====================
    # Range: -32.5 to +32.5 m/s, Bin: 5 m/s, 15 colors
    r = [0,   0,   0,   0,   0,   0,   0, 255, 246, 255, 255, 241, 196, 151, 239]
    g = [0,   0, 109, 218, 139, 190, 241, 255, 246, 195, 138,   0,   0,   0,   0]
    b = [0, 232, 223, 227,   0,   0,   1, 255,   0,   0,   0,   0,   0,   0, 255]
    colors_vr = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_vr = ListedColormap(colors_vr, name='GV_VR')
    cmap_vr.set_bad(color='black')
    colormaps['GV_VR'] = cmap_vr
    
    # ==================== GV_SW: Spectrum Width ====================
    # Range: 0 to 21+ m/s, Bin: 2 m/s, 14 colors
    r = [0,   0,   0,   0,   0,   0,   0, 255, 255, 255, 241, 196, 151, 239]
    g = [0, 218, 109,   0, 241, 190, 139, 253, 195, 138,   0,   0,   0,   0]
    b = [0, 223, 227, 232,   1,   0,   0,   0,   0,   0,   0,   0,   0, 255]
    colors_sw = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_sw = ListedColormap(colors_sw, name='GV_SW')
    cmap_sw.set_bad(color='black')
    colormaps['GV_SW'] = cmap_sw
    
    # ==================== GV_DR: Differential Reflectivity (ZDR) ====================
    # Range: -3 to +3 dB, Bin: 0.5 dB, 16 colors
    r = [0, 153,   0,   0,   0,   0,   0,   0, 255, 255, 255, 241, 196, 151, 239, 135]
    g = [0, 153, 218, 109,   0, 241, 190, 139, 253, 195, 138,   0,   0,   0,   0,  35]
    b = [0, 153, 223, 227, 232,   1,   0,   0,   0,   0,   0,   0,   0,   0, 255, 255]
    colors_dr = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_dr = ListedColormap(colors_dr, name='GV_DR')
    cmap_dr.set_bad(color='black')
    colormaps['GV_DR'] = cmap_dr
    
    # ==================== GV_KD: Specific Differential Phase (KDP) ====================
    # Range: -2 to +3 deg/km, Bin: 0.5 deg/km, 14 colors
    r = [0,   0,   0,   0,   0,   0, 255, 255, 255, 241, 196, 151, 239, 135]
    g = [0, 218,   0, 241, 190, 139, 253, 195, 138,   0,   0,   0,   0,  35]
    b = [0, 223, 232,   1,   0,   0,   0,   0,   0,   0,   0,   0, 255, 255]
    colors_kd = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_kd = ListedColormap(colors_kd, name='GV_KD')
    cmap_kd.set_bad(color='black')
    colormaps['GV_KD'] = cmap_kd
    
    # ==================== GV_RH: Correlation Coefficient (RhoHV) ====================
    # Range: 0.0 to 0.98+, variable bins, 13 colors
    r = [0,   0,   0,   0,   0,   0,   0, 246, 255, 255, 241, 196, 151]
    g = [0,   0, 109, 218, 139, 190, 241, 246, 195, 138,   0,   0,   0]
    b = [0, 232, 223, 227,   0,   0,   1,   0,   0,   0,   0,   0,   0]
    colors_rh = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_rh = ListedColormap(colors_rh, name='GV_RH')
    cmap_rh.set_bad(color='black')
    colormaps['GV_RH'] = cmap_rh
    
    # ==================== GV_PH: Differential Phase (PhiDP) ====================
    # Range: 0 to 360 degrees, 13 colors
    r = [0,   0,   0,   0,   0,   0,   0, 246, 255, 255, 241, 196, 151]
    g = [0,   0, 109, 218, 139, 190, 241, 246, 195, 138,   0,   0,   0]
    b = [0, 232, 223, 227,   0,   0,   1,   0,   0,   0,   0,   0,   0]
    colors_ph = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_ph = ListedColormap(colors_ph, name='GV_PH')
    cmap_ph.set_bad(color='black')
    colormaps['GV_PH'] = cmap_ph
    
    # ==================== GV_HC: Hydrometeor Classification ====================
    # 8 classes
    r = [0,  72,   0,   0, 153,   0, 239, 135]
    g = [0,  72, 109, 218, 153, 241,   0,  35]
    b = [0,  72, 227, 223, 153,   0, 255, 255]
    colors_hc = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_hc = ListedColormap(colors_hc, name='GV_HC')
    cmap_hc.set_bad(color='black')
    colormaps['GV_HC'] = cmap_hc
    
    # ==================== GV_RR: Rain Rate ====================
    # Range: 0 to 80+ mm/hr, Bin: 5 mm/hr, 18 colors
    r = [0, 102,   0,   0,   0,   0,   0,   0,   0, 255, 255, 255, 241, 196, 151, 239, 135, 255]
    g = [0, 153, 153, 218, 109,   0, 241, 190, 139, 253, 195, 138,   0,   0,   0,   0,  35, 255]
    b = [0, 153, 153, 223, 227, 232,   1,   0,   0,   0,   0,   0,   0,   0,   0, 255, 255, 255]
    colors_rr = [[r[i]/255., g[i]/255., b[i]/255.] for i in range(len(r))]
    cmap_rr = ListedColormap(colors_rr, name='GV_RR')
    cmap_rr.set_bad(color='black')
    colormaps['GV_RR'] = cmap_rr
    
    return colormaps

# Create and store all GV colormaps globally
_GV_COLORMAPS = create_gv_colormaps()

# Register all colormaps with matplotlib
for name, cmap in _GV_COLORMAPS.items():
    try:
        matplotlib.cm.register_cmap(name=name, cmap=cmap)
    except:
        pass

#print(f"✓ Registered {len(_GV_COLORMAPS)} GPM-GV legacy colormaps: {', '.join(_GV_COLORMAPS.keys())}")

def check_cm(cmap_name):
    """Handles old and new versions of colormaps, including custom GV colormaps
    
    ALWAYS returns a STRING name, never a colormap object
    """
    
    # Handle custom GPM-GV colormaps - return NAME string, not object
    if cmap_name in _GV_COLORMAPS:
        return cmap_name  # Return the name string
    
    # Handle standard colormaps - return name string
    candidates = [cmap_name, f'pyart_{cmap_name}']
    for name in candidates:
        try:
            plt.cm.get_cmap(name)  # Test if it exists
            return name  # Return the working name
        except:
            continue
    
    # Fallback to a basic colormap
    print(f"WARNING: Colormap '{cmap_name}' not found, using 'viridis'")
    return 'viridis'
    
# Define HID colormaps at module level for use in field configs
_HID_COLORS_SUMMER = ['White', 'LightBlue', 'MediumBlue', 'DarkOrange', 'LightPink',
                      'Cyan', 'DarkGray', 'Lime', 'Yellow', 'Red', 'Fuchsia']

_HID_COLORS_WINTER = ['White', 'Orange', 'Purple', 'Fuchsia', 'Pink', 'Cyan',
                      'LightBlue', 'Blue']

_EC_HID_COLORS = ['White', 'LightPink', 'Darkorange', 'LightBlue', 'Lime', 'MediumBlue', 
                  'DarkGray', 'Cyan', 'Red', 'Yellow']

# Create colormaps
_CMAPHID_SUMMER = colors.ListedColormap(_HID_COLORS_SUMMER)
_CMAPHID_WINTER = colors.ListedColormap(_HID_COLORS_WINTER)
_CMAPHID_EC = colors.ListedColormap(_EC_HID_COLORS)
_CMAP_METH = colors.ListedColormap(_HID_COLORS_SUMMER[0:6])

_FIELD_CONFIGS = {
        'CZ': {'units': 'Zh [dBZ]', 'vmin': 0, 'vmax': 70, 'Nbins': 14, 
               'title': 'Corrected Reflectivity [dBZ]', 'cmap': check_cm('NWSRef')},
        'DZ': {'units': 'Zh [dBZ]', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
               'title': 'RAW Reflectivity [dBZ]', 'cmap': check_cm('NWSRef')},
        'ZZ': {'units': 'Zh [dBZ]', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
               'title': 'RAW Reflectivity [dBZ]', 'cmap': check_cm('NWSRef')},       
        'DR': {'units': 'Zdr [dB]', 'vmin': -1, 'vmax': 3, 'Nbins': 16,
               'title': 'Differential Reflectivity [dB]', 'cmap': check_cm('HomeyerRainbow')},
        'VR': {'units': 'Velocity [m/s]', 'vmin': -20, 'vmax': 20, 'Nbins': 12,
               'title': 'Radial Velocity [m/s]', 'cmap': check_cm('NWSVel')},
        'SW': {'units': 'Spectrum Width', 'vmin': 0, 'vmax': 21, 'Nbins': 12,
               'title': 'Spectrum Width', 'cmap': check_cm('NWS_SPW')},
        'corrected_velocity': {'units': 'Velocity [m/s]', 'vmin': -20, 'vmax': 20, 'Nbins': 12,
                              'title': 'Dealiased Radial Velocity [m/s]', 'cmap': check_cm('NWSVel')},
        'KD': {'units': 'Kdp [deg/km]', 'vmin': -2, 'vmax': 3, 'Nbins': 10,
               'title': 'Specific Differential Phase [deg/km]', 'cmap': check_cm('HomeyerRainbow')},
        'KDPB': {'units': 'Kdp [deg/km]', 'vmin': -2, 'vmax': 5, 'Nbins': 8,
                 'title': 'Specific Differential Phase [deg/km] (Bringi)', 'cmap': check_cm('HomeyerRainbow')},
        'PH': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 360, 'Nbins': 36,
               'title': 'Differential Phase [deg]', 'cmap': check_cm('Carbone42')},
        'PHM': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 360, 'Nbins': 36,
                'title': 'Differential Phase [deg] Marks', 'cmap': check_cm('Carbone42')},
        'PHIDPB': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 360, 'Nbins': 36,
                   'title': 'Differential Phase [deg] Bringi', 'cmap': check_cm('Carbone42')},
        'RH': {'units': 'Correlation', 'vmin': 0.7, 'vmax': 1.0, 'Nbins': 12,
               'title': 'Correlation Coefficient', 'cmap': check_cm('LangRainbow12')},
        'SD': {'units': 'Std(PhiDP)', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
               'title': 'Standard Deviation of PhiDP', 'cmap': check_cm('NWSRef')},
        'SQ': {'units': 'SQI', 'vmin': 0, 'vmax': 1, 'Nbins': 10,
               'title': 'Signal Quality Index', 'cmap': check_cm('LangRainbow12')},
        'FH': {'units': 'HID', 'vmin': 0, 'vmax': 11, 'Nbins': 0,
               'title': 'Summer Hydrometeor Identification', 'cmap': 'CMAPHID_SUMMER'},
        'FS': {'units': 'HID', 'vmin': 0, 'vmax': 11, 'Nbins': 0,
               'title': 'Summer Hydrometeor Identification', 'cmap': 'CMAPHID_SUMMER'},
        'FW': {'units': 'HID', 'vmin': 0, 'vmax': 8, 'Nbins': 0,
               'title': 'Winter Hydrometeor Identification', 'cmap': 'CMAPHID_WINTER'},
        'NT': {'units': 'HID', 'vmin': 0, 'vmax': 8, 'Nbins': 0,
               'title': 'No TEMP Winter Hydrometeor Identification', 'cmap': 'CMAPHID_WINTER'},
        'EC': {'units': 'HID', 'vmin': 0, 'vmax': 9, 'Nbins': 0,
               'title': 'Radar Echo Classification', 'cmap': 'CMAPHID_EC'},
        'MRC': {'units': 'HIDRO Method', 'vmin': 0, 'vmax': 5, 'Nbins': 0,
               'title': 'HIDRO Method', 'cmap': _CMAP_METH},
        'MW': {'units': 'Water Mass [g/m^3]', 'vmin': 0, 'vmax': 3, 'Nbins': 25,
               'title': 'Water Mass [g/m^3]', 'cmap': 'turbo'},
        'MI': {'units': 'Ice Mass [g/m^3]', 'vmin': 0, 'vmax': 3, 'Nbins': 25,
               'title': 'Ice Mass [g/m^3]', 'cmap': 'turbo'},
        'RC': {'units': 'HIDRO Rain Rate [mm/hr]', 'vmin': 1e-2, 'vmax': 3e2, 'Nbins': 0,
               'title': 'HIDRO Rain Rate [mm/hr]', 'cmap': check_cm('RefDiff')},
        'RP': {'units': 'PolZR Rain Rate [mm/hr]', 'vmin': 1e-2, 'vmax': 3e2, 'Nbins': 0,
               'title': 'PolZR Rain Rate [mm/hr]', 'cmap': check_cm('RefDiff')},
        'RA': {'units': 'Attenuation Rain Rate [mm/hr]', 'vmin': 1e-2, 'vmax': 3e2, 'Nbins': 0,
               'title': 'Attenuation Rain Rate [mm/hr]', 'cmap': check_cm('RefDiff')},
        'DM': {'units': 'DM [mm]', 'vmin': 0.5, 'vmax': 5, 'Nbins': 8,
               'title': 'DM [mm]', 'cmap': check_cm('BlueBrown10')},
        'NW': {'units': 'Log[Nw, m^-3 mm^-1]', 'vmin': 0.5, 'vmax': 7, 'Nbins': 12,
               'title': 'Log[Nw, m^-3 mm^-1]', 'cmap': check_cm('BlueBrown10')},
               
        # ODIM H5 field names
        'DBZH': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                 'title': 'Horizontal Reflectivity', 'cmap': check_cm('NWSRef')},
        'TH': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
               'title': 'Total Reflectivity', 'cmap': check_cm('NWSRef')},
        'RHOHV': {'units': 'Correlation', 'vmin': 0.7, 'vmax': 1.0, 'Nbins': 12,
                  'title': 'Correlation Coefficient', 'cmap': check_cm('LangRainbow12')},
        'UPHIDP': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 180, 'Nbins': 18,
                   'title': 'Unfolded Differential Phase', 'cmap': check_cm('Carbone42')},
        'WRADH': {'units': 'Spectrum Width [m/s]', 'vmin': 0, 'vmax': 10, 'Nbins': 10,
                  'title': 'Spectrum Width', 'cmap': check_cm('NWS_SPW')},
        'PHIDP': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 180, 'Nbins': 18,
                  'title': 'Differential Phase', 'cmap': check_cm('Carbone42')},
        'ZDR': {'units': 'Zdr [dB]', 'vmin': -2, 'vmax': 5, 'Nbins': 14,
                'title': 'Differential Reflectivity', 'cmap': check_cm('HomeyerRainbow')},
        'KDP': {'units': 'Kdp [deg/km]', 'vmin': -1, 'vmax': 4, 'Nbins': 10,
                'title': 'Specific Differential Phase', 'cmap': check_cm('HomeyerRainbow')},
        'SQIH': {'units': 'SQI', 'vmin': 0, 'vmax': 1, 'Nbins': 10,
                 'title': 'Signal Quality Index', 'cmap': check_cm('LangRainbow12')},
        'VRADH': {'units': 'Velocity [m/s]', 'vmin': -30, 'vmax': 30, 'Nbins': 12,
                  'title': 'Radial Velocity', 'cmap': check_cm('NWSVel')},
                  
        # D3R field names
        'Reflectivity': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                        'title': 'Reflectivity', 'cmap': check_cm('NWSRef')},
        'ReflectivityV': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                         'title': 'Vertical Reflectivity', 'cmap': check_cm('NWSRef')},
        'ReflectivityHV': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                          'title': 'Cross-Polar Reflectivity', 'cmap': check_cm('NWSRef')},
        'Velocity': {'units': 'm/s', 'vmin': -30, 'vmax': 30, 'Nbins': 12,
                    'title': 'Radial Velocity', 'cmap': check_cm('NWSVel')},
        'SpectralWidth': {'units': 'm/s', 'vmin': 0, 'vmax': 10, 'Nbins': 10,
                         'title': 'Spectral Width', 'cmap': check_cm('NWS_SPW')},
        'DifferentialReflectivity': {'units': 'dB', 'vmin': -2, 'vmax': 5, 'Nbins': 14,
                                    'title': 'Differential Reflectivity', 'cmap': check_cm('HomeyerRainbow')},
        'DifferentialPhase': {'units': 'deg', 'vmin': 0, 'vmax': 180, 'Nbins': 18,
                             'title': 'Differential Phase', 'cmap': check_cm('Carbone42')},
        'CopolarCorrelation': {'units': '', 'vmin': 0.7, 'vmax': 1.0, 'Nbins': 12,
                              'title': 'Copolar Correlation Coefficient', 'cmap': check_cm('LangRainbow12')},
        'NormalizedCoherentPower': {'units': '', 'vmin': 0, 'vmax': 1, 'Nbins': 10,
                                   'title': 'Normalized Coherent Power', 'cmap': 'viridis'},
        'SignalPower_H': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                         'title': 'Signal Power (H)', 'cmap': 'plasma'},
        'SignalPower_V': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                         'title': 'Signal Power (V)', 'cmap': 'plasma'},
        'SignalPower_HV': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                          'title': 'Signal Power (HV)', 'cmap': 'plasma'},
        'RawPower_H': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                      'title': 'Raw Power (H)', 'cmap': 'inferno'},
        'RawPower_V': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                      'title': 'Raw Power (V)', 'cmap': 'inferno'},
        'RawPower_HV': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                       'title': 'Raw Power (HV)', 'cmap': 'inferno'},
        'Signal+Clutter_toNoise_H': {'units': 'dB', 'vmin': 0, 'vmax': 40, 'Nbins': 10,
                                    'title': 'Signal+Clutter to Noise (H)', 'cmap': 'viridis'},
        'ClutterPowerH': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                         'title': 'Clutter Power (H)', 'cmap': 'magma'},
        'ClutterPowerV': {'units': 'dBm', 'vmin': -120, 'vmax': -60, 'Nbins': 12,
                         'title': 'Clutter Power (V)', 'cmap': 'magma'},
        'MaskSecondTrip': {'units': '', 'vmin': 0, 'vmax': 1, 'Nbins': 2,
                          'title': 'Second Trip Mask', 'cmap': 'gray'},
                          
        # ==================== NEXRAD 88D RAW FIELDS (NEW) ====================
        'REF': {'units': 'Zh [dBZ]', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                'title': 'Reflectivity [dBZ]', 'cmap': check_cm('NWSRef')},
        'VEL': {'units': 'Velocity [m/s]', 'vmin': -30, 'vmax': 30, 'Nbins': 12,
                'title': 'Radial Velocity [m/s]', 'cmap': check_cm('NWSVel')},
        'ZDR': {'units': 'Zdr [dB]', 'vmin': -2, 'vmax': 5, 'Nbins': 14,
                'title': 'Differential Reflectivity [dB]', 'cmap': check_cm('HomeyerRainbow')},
        'PHI': {'units': 'PhiDP [deg]', 'vmin': 0, 'vmax': 180, 'Nbins': 18,
                'title': 'Differential Phase [deg]', 'cmap': check_cm('Carbone42')},
        'RHO': {'units': 'Correlation', 'vmin': 0.5, 'vmax': 1.0, 'Nbins': 10,
                'title': 'Correlation Coefficient', 'cmap': check_cm('LangRainbow12')},
        'CFP': {'units': 'dB', 'vmin': 0, 'vmax': 1, 'Nbins': 10,
                'title': 'Clutter Filter Power', 'cmap': 'viridis'},

        # Add common PyART field names as fallbacks
        'reflectivity': {'units': 'dBZ', 'vmin': 0, 'vmax': 70, 'Nbins': 14,
                        'title': 'Reflectivity', 'cmap': check_cm('NWSRef')},
        'velocity': {'units': 'm/s', 'vmin': -30, 'vmax': 30, 'Nbins': 12,
                    'title': 'Velocity', 'cmap': check_cm('NWSVel')},
        'spectrum_width': {'units': 'm/s', 'vmin': 0, 'vmax': 10, 'Nbins': 10,
                          'title': 'Spectrum Width', 'cmap': check_cm('NWS_SPW')},
        'differential_reflectivity': {'units': 'dB', 'vmin': -2, 'vmax': 5, 'Nbins': 14,
                                    'title': 'Differential Reflectivity', 'cmap': check_cm('HomeyerRainbow')},
        'cross_correlation_ratio': {'units': '', 'vmin': 0.5, 'vmax': 1.0, 'Nbins': 10,
                                   'title': 'Cross Correlation Ratio', 'cmap': check_cm('LangRainbow12')},
        'differential_phase': {'units': 'deg', 'vmin': 0, 'vmax': 180, 'Nbins': 18,
                              'title': 'Differential Phase', 'cmap': check_cm('Carbone42')},
        'specific_differential_phase': {'units': 'deg/km', 'vmin': -1, 'vmax': 4, 'Nbins': 10,
                                       'title': 'Specific Differential Phase', 'cmap': check_cm('HomeyerRainbow')}
    }

class PlottingCache:
    """Cache manager for expensive plotting operations"""
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if not self._initialized:
            self._map_features_cache = None
            self._logos_cache = {}
            self._field_cache = {}
            self._coordinate_cache = {}
            self._initialized = True
    
    def get_map_features(self):
        """Get all map features (counties, states, reefs, minor islands)"""
        if self._map_features_cache is None:
            self._map_features_cache = self._load_counties_states()
        return self._map_features_cache
    
    def _load_counties_states(self):
        """Load counties, states, reefs, and minor islands"""
        try:
            base_dir = os.path.dirname(__file__)
            shapefile_dir = os.path.join(base_dir, "shape_files/")
            
            # ==================== Load US Counties ====================
            COUNTIES = None
            county_shapefile = os.path.join(shapefile_dir, "countyl010g.shp")
            if os.path.exists(county_shapefile):
                try:
                    reader = shpreader.Reader(county_shapefile)
                    counties = list(reader.geometries())
                    COUNTIES = cfeature.ShapelyFeature(counties, ccrs.PlateCarree())
                except Exception as e:
                    print(f"⚠️ Could not load counties: {e}")
    
            # ==================== Load States ====================
            STATES = cfeature.NaturalEarthFeature(
                                        category='cultural',
                                        name='admin_1_states_provinces_lines',
                                        scale='10m',
                                        facecolor='none')
            
            # ==================== Load Reefs ====================
            REEFS = None
            reef_shapefile = os.path.join(shapefile_dir, "ne_10m_reefs.shp")
            if os.path.exists(reef_shapefile):
                try:
                    reef_reader = shpreader.Reader(reef_shapefile)
                    reefs = list(reef_reader.geometries())
                    REEFS = cfeature.ShapelyFeature(reefs, ccrs.PlateCarree())
                except Exception as e:
                    print(f"⚠️ Could not load reefs: {e}")
            
            # ==================== Load Minor Islands ====================
            MINOR_ISLANDS = None
            islands_shapefile = os.path.join(shapefile_dir, "ne_10m_minor_islands.shp")
            if os.path.exists(islands_shapefile):
                try:
                    islands_reader = shpreader.Reader(islands_shapefile)
                    islands = list(islands_reader.geometries())
                    MINOR_ISLANDS = cfeature.ShapelyFeature(islands, ccrs.PlateCarree())
                except Exception as e:
                    print(f"⚠️ Could not load minor islands: {e}")
            
            return COUNTIES, STATES, REEFS, MINOR_ISLANDS
            
        except Exception as e:
            print(f"Error loading shapefiles: {e}")
            STATES = cfeature.NaturalEarthFeature(
                                        category='cultural',
                                        name='admin_1_states_provinces_lines',
                                        scale='50m',
                                        facecolor='none')
            return None, STATES, None, None
        
    def get_logo(self, logo_name):
        if logo_name not in self._logos_cache:
            try:
                logo_dir = os.path.dirname(__file__)
                logo_path = os.path.join(logo_dir, f'{logo_name}.png')
                self._logos_cache[logo_name] = Image.open(logo_path)
            except:
                # Create a dummy image if logo not found
                self._logos_cache[logo_name] = Image.new('RGBA', (100, 50), (255, 255, 255, 0))
        return self._logos_cache[logo_name]
    
    def get_processed_field(self, radar, field_name):
        cache_key = f"{field_name}_{id(radar)}"
        if cache_key not in self._field_cache:
            self._field_cache[cache_key] = self._process_field(radar, field_name)
        return self._field_cache[cache_key]
    
    def _process_field(self, radar, field_name):
        if field_name == 'RC':
            rc = radar.fields['RC']['data'].copy()
            rc[rc < 0.01] = np.nan
            return {"data": rc, "units": "mm/h",
                   "long_name": "HIDRO Rainfall Rate", "_FillValue": -32767.0,
                   "standard_name": "HIDRO Rainfall Rate"}
        elif field_name == 'RP':
            rp = radar.fields['RP']['data'].copy()
            rp[rp < 0.01] = np.nan
            return {"data": rp, "units": "mm/h",
                   "long_name": "Polzr_Rain_Rate", "_FillValue": -32767.0,
                   "standard_name": "Polzr_Rain_Rate"}
        elif field_name == 'RA':
            ra = radar.fields['RA']['data'].copy()
            ra[ra < 0.01] = np.nan
            return {"data": ra, "units": "mm/h",
                   "long_name": "A_Rain_Rate", "_FillValue": -32767.0,
                   "standard_name": "A_Rain_Rate"}
        return None
    
    def get_coordinate_transform(self, radar_lat, radar_lon, max_range):
        cache_key = f"{radar_lat}_{radar_lon}_{max_range}"
        if cache_key not in self._coordinate_cache:
            self._coordinate_cache[cache_key] = self._calculate_coordinates(radar_lat, radar_lon, max_range)
        return self._coordinate_cache[cache_key]
    
    def _calculate_coordinates(self, radar_lat, radar_lon, max_range):
        dtor = math.pi/180.0
        maxrange_meters = max_range * 1000.
        meters_to_lat = 1. / 111177.
        meters_to_lon = 1. / (111177. * math.cos(radar_lat * dtor))

        min_lat = radar_lat - maxrange_meters * meters_to_lat
        max_lat = radar_lat + maxrange_meters * meters_to_lat
        min_lon = radar_lon - maxrange_meters * meters_to_lon
        max_lon = radar_lon + maxrange_meters * meters_to_lon
        
        lon_grid = np.arange(round(min_lon, 2) - 1.00, round(max_lon, 2) + 1.00, 1.0)
        lat_grid = np.arange(round(min_lat, 2) - 1.00, round(max_lat, 2) + 1.00, 1.0)
        
        return {
            'min_lat': min_lat, 'max_lat': max_lat,
            'min_lon': min_lon, 'max_lon': max_lon,
            'lon_grid': lon_grid, 'lat_grid': lat_grid,
            'meters_to_lat': meters_to_lat, 'meters_to_lon': meters_to_lon
        }
        

    def add_radials_vectorized(self, display, radar_lat, radar_lon, max_range, coord_data):
        """Add radials using vectorized operations"""
        azimuths = np.arange(0, 360, 30)
        dtor = math.pi / 180.0
        maxrange_meters = max_range * 1000.
    
        for azi in azimuths:
            azimuth = 90. - azi
            dazimuth = azimuth * dtor
            lon_maxrange = radar_lon + math.cos(dazimuth) * coord_data['meters_to_lon'] * maxrange_meters
            lat_maxrange = radar_lat + math.sin(dazimuth) * coord_data['meters_to_lat'] * maxrange_meters
            display.plot_line_geo([radar_lon, lon_maxrange], [radar_lat, lat_maxrange],
                                  line_style='--', lw=0.5, color='white')
                                  
    def add_radials_fast(self, ax, max_range):
        """Add radials for FAST plots (x-y coordinates)"""
        azimuths = np.arange(0, 360, 30)
        dtor = math.pi / 180.0
        
        for azi in azimuths:
            azimuth = 90. - azi
            dazimuth = azimuth * dtor
            x_end = max_range * math.cos(dazimuth)
            y_end = max_range * math.sin(dazimuth)
            
            # Draw line from center (0,0) to the end point
            ax.plot([0, x_end], [0, y_end], '--', color='white', linewidth=0.5)

# Initialize cache
_cache = PlottingCache()

class LayoutManager:
    """Automated layout manager that adapts to platform, DPI, content, and user preferences"""
    
    # Class-level storage for learned preferences per platform/DPI combination
    _learned_preferences = {}
    
    def __init__(self, canvas_width_px, canvas_height_px, canvas_dpi, device_ratio, 
             num_fields=1, platform_name=None, user_prefs=None, scan_type="PPI"):
        self.canvas_width_px = canvas_width_px
        self.canvas_height_px = canvas_height_px
        self.canvas_dpi = canvas_dpi
        self.device_ratio = device_ratio
        self.num_fields = num_fields
        self.platform = platform_name or platform.system()
        self.user_prefs = user_prefs or {}
        self.scan_type = scan_type
        
        # ==================== CALCULATE GRID LAYOUT FIRST ====================
        # Must be done BEFORE generating config key
        self.n_rows, self.n_cols = self._calculate_grid_layout()
        
        # ==================== THEN generate config key ====================
        # Now we have n_rows and n_cols available
        self.config_key = self._generate_config_key()
        
        # ==================== Load learned preferences ====================
        self.learned_params = self._load_learned_preferences()
        
        # ==================== Calculate effective DPI ====================
        self.effective_dpi = self._calculate_effective_dpi()
        
        # ==================== Calculate figure size ====================
        self.fig_width, self.fig_height = self.get_figure_size()
        
        # ==================== Calculate title Y position ====================
        self.title_y_pos = self.get_title_position()
            
    def _generate_config_key(self):
        """Generate unique key for this display configuration"""
        
        # Round DPI to nearest 25 for grouping similar displays
        dpi_bucket = int(round(self.canvas_dpi / 25.0) * 25)
        
        # Get grid layout
        grid_layout = f"{self.n_rows}x{self.n_cols}"
        
        # Include scan type and grid layout in the config key
        return f"{self.platform}_{dpi_bucket}_{self.device_ratio:.1f}_{self.scan_type}_{grid_layout}"
    
    def _load_learned_preferences(self):
        """Load learned preferences for this display configuration including grid layout"""
        
        # Try to load from QSettings
        settings = QSettings("GPM-GV", "RadarViewer")
        
        # ==================== COMMON DEFAULTS (apply to all grids) ====================
        common_defaults = {
                'padding_factor': self._get_default_padding_factor(),
                'dpi_scale_factor': 0.7 if self.platform == "Darwin" else 1.0,
                'font_scale': 1.0,
        }
        
        # ==================== RHI-SPECIFIC DEFAULTS ====================
        if self.scan_type == "RHI":
                if self.num_fields == 1:
                        grid_defaults = {
                                'figure_width': 12.0,
                                'figure_height': 3.5,
                                'title_y_position': 0.98,
                                'margin_scale': 1.0,
                                'h_spacing_scale': 1.0, 
                                'v_spacing_scale': 1.0,
                                'top_margin': 0.92,
                                'bottom_margin': 0.15,
                        }
                elif self.n_rows == 1 and self.n_cols == 2:  # 2 RHI plots
                        grid_defaults = {
                                'figure_width': 23.5,
                                'figure_height': 5.0,
                                'title_y_position': 0.96,
                                'margin_scale': 0.7,
                                'h_spacing_scale': 0.10,
                                'v_spacing_scale': 1.0,
                                'top_margin': 0.820,
                                'bottom_margin': 0.15,
                        }
                elif self.n_rows == 2 and self.n_cols == 2:  # 3-4 RHI plots
                        grid_defaults = {
                                'figure_width': 24.0,
                                'figure_height': 9.5,
                                'title_y_position': 0.99,
                                'margin_scale': 1.0,
                                'h_spacing_scale': 0.10, 
                                'v_spacing_scale': 5.9, 
                                'top_margin': 0.92,
                                'bottom_margin': 0.7,
                        }
                elif self.n_rows == 3 and self.n_cols == 2:  # 5-6 RHI plots
                        grid_defaults = {
                                'figure_width': 24.0,
                                'figure_height': 5.5,
                                'title_y_position': 0.99,
                                'margin_scale': 0.85,
                                'h_spacing_scale': 1.0,  
                                'v_spacing_scale': 4.0,  
                                'top_margin': 0.94,
                                'bottom_margin': 0.20,
                        }
                else:  # Generic RHI
                        grid_defaults = {
                                'figure_width': 24.0,
                                'figure_height': 3.5 * self.n_rows,
                                'title_y_position': 0.94,
                                'margin_scale': 0.85,
                                'h_spacing_scale': 1.0,  
                                'v_spacing_scale': 1.0, 
                                'top_margin': 0.90,
                                'bottom_margin': 0.10,
                        }
        
        # ==================== PPI GRID-SPECIFIC DEFAULTS ====================
        elif self.num_fields == 1:
                grid_defaults = {
                        'figure_width': 15.0,
                        'figure_height': 9.5,
                        'title_y_position': 1.0,
                        'margin_scale': 2.0,
                        'h_spacing_scale': 1.20,    
                        'v_spacing_scale': 1.20,    
                        'top_margin': 0.95, 
                        'bottom_margin': 0.08, 
                }
        elif self.n_rows == 1 and self.n_cols == 2:  # 1x2
                grid_defaults = {
                        'figure_width': 20.0,
                        'figure_height': 9.0,
                        'title_y_position': 0.99,
                        'margin_scale': 1.1,
                        'h_spacing_scale': 1.4,     
                        'v_spacing_scale': 1.4,     
                        'top_margin': 0.98,
                        'bottom_margin': 0.08,
                }
        elif self.n_rows == 1 and self.n_cols == 3:  # 1x3
                grid_defaults = {
                        'figure_width': 22.5,
                        'figure_height': 7.5,
                        'title_y_position': 0.94,
                        'margin_scale': 0.8,
                        'h_spacing_scale': 1.3,     
                        'v_spacing_scale': 1.3,    
                        'top_margin': 0.94, 
                        'bottom_margin': 0.08, 
                }
        elif self.n_rows == 2 and self.n_cols == 2:  # 2x2
                grid_defaults = {
                        'figure_width': 12.0,
                        'figure_height': 9.5,
                        'title_y_position': 0.99,
                        'margin_scale': .91,
                        'h_spacing_scale': 0.10,     
                        'v_spacing_scale': 2.60,    
                        'top_margin': 0.91,
                        'bottom_margin': 0.10,
                }
        elif self.n_rows == 2 and self.n_cols == 3:  # 2x3
                grid_defaults = {
                        'figure_width': 17.5,
                        'figure_height': 9.5,
                        'title_y_position': 0.98,
                        'margin_scale': 0.9,
                        'h_spacing_scale': 0.10,     
                        'v_spacing_scale': 2.50,     
                        'top_margin': 0.91,
                        'bottom_margin': 0.10,
                }
        elif self.n_rows == 3 and self.n_cols == 3:  # 3x3
                grid_defaults = {
                        'figure_width': 13.0,
                        'figure_height': 4.0,
                        'title_y_position': 0.99,
                        'margin_scale': 0.8,
                        'h_spacing_scale': 2.5,    
                        'v_spacing_scale': 2.2,   
                        'top_margin': 0.93,
                        'bottom_margin': 0.15,
                }
        else:  # Generic for other grid sizes
                grid_defaults = {
                        'figure_width': 12.0 + (self.n_cols * 2),
                        'figure_height': 8.0 + (self.n_rows * 2),
                        'title_y_position': 0.96,
                        'margin_scale': 0.9,
                        'h_spacing_scale': 1.0,    
                        'v_spacing_scale': 1.0,     
                        'top_margin': 0.94,
                        'bottom_margin': 0.10,
                }
        
        # ==================== MERGE ALL DEFAULTS ====================
        defaults = {**common_defaults, **grid_defaults}
        
        # ==================== LOAD SAVED PREFERENCES ====================
        settings.beginGroup(f"layout/{self.config_key}")
        learned = {}
        for key, default_val in defaults.items():
                learned[key] = settings.value(key, default_val, type=float)
        settings.endGroup()
        
        # ==================== APPLY USER PREFERENCE OVERRIDES ====================
        if 'h_spacing_scale' in self.user_prefs:
                learned['h_spacing_scale'] = self.user_prefs['h_spacing_scale']
        
        if 'v_spacing_scale' in self.user_prefs:
                learned['v_spacing_scale'] = self.user_prefs['v_spacing_scale']
        
        if 'font_scale' in self.user_prefs:
                learned['font_scale'] *= self.user_prefs['font_scale']
        
        if 'figure_width' in self.user_prefs:
                learned['figure_width'] = self.user_prefs['figure_width']
        
        if 'figure_height' in self.user_prefs:
                learned['figure_height'] = self.user_prefs['figure_height']
        
        if 'title_y_position' in self.user_prefs:
                learned['title_y_position'] = self.user_prefs['title_y_position']
        
        if 'top_margin' in self.user_prefs:
                learned['top_margin'] = self.user_prefs['top_margin']    
                
        if 'bottom_margin' in self.user_prefs:
                learned['bottom_margin'] = self.user_prefs['bottom_margin']                    
        
        return learned
    
    def _get_default_padding_factor(self):
        """Get default padding factor based on platform"""
        defaults = {
            "Darwin": 0.86,
            "Linux": 0.95,
            "Windows": 0.93
        }
        return defaults.get(self.platform, 0.93)
    
    def save_preference(self, param_name, value):
        """Save a learned preference for this display configuration"""
        settings = QSettings("GPM-GV", "RadarViewer")
        settings.beginGroup(f"layout/{self.config_key}")
        settings.setValue(param_name, value)
        settings.endGroup()
        
        # Update in-memory copy
        self.learned_params[param_name] = value
    
    def _calculate_effective_dpi(self):
        """Calculate platform-adjusted effective DPI"""
        base_dpi = self.canvas_dpi
        
        if self.platform == "Darwin":
            # macOS Retina: adjust using device ratio and learned factor
            dpi = int(base_dpi * self.device_ratio * self.learned_params['dpi_scale_factor'])
        else:
            # Other platforms: use canvas DPI directly
            dpi = base_dpi
        
        # Apply reasonable bounds
        return max(72, min(dpi, 200))
    
    def _calculate_grid_layout(self):
        """Determine optimal grid layout (rows x cols) for number of fields"""
        
        # ==================== RHI LAYOUT (WIDER, SHORTER) ====================
        if self.scan_type == "RHI":
                # RHI plots are wider and shorter - use 2 columns when possible
                if self.num_fields == 1:
                        return 1, 1
                else:
                        # Use 2 columns for multiple RHI plots
                        nrows = (self.num_fields + 1) // 2
                        ncols = 2
                        return nrows, ncols
        
        # ==================== PPI LAYOUT (STANDARD GRID) ====================
        else:  # PPI or default
                if self.num_fields == 1:
                        return 1, 1
                elif self.num_fields == 2:
                        return 1, 2
                elif self.num_fields == 3:
                        return 1, 3
                elif self.num_fields == 4:
                        return 2, 2
                elif self.num_fields <= 6:
                        return 2, 3
                elif self.num_fields <= 9:
                        return 3, 3
                else:
                        return int(np.ceil(self.num_fields / 3)), 3
    
    def get_figure_size(self):
        """Calculate optimal figure size in inches with learned scaling"""
        
        # Get width and height from learned preferences
        fig_width = self.learned_params.get('figure_width', 12.0)
        fig_height = self.learned_params.get('figure_height', 8.0)
        
        # Apply learned padding factor as a multiplier
        padding_factor = self.learned_params['padding_factor']
        fig_width *= padding_factor
        fig_height *= padding_factor
        
        # Ensure minimums based on number of fields
        min_width = max(6.0, self.n_cols * 3.5)
        min_height = max(4.0, self.n_rows * 3.0)
        
        fig_width = max(fig_width, min_width)
        fig_height = max(fig_height, min_height)
                
        return fig_width, fig_height
    
    def get_subplot_positions(self):
        """Calculate subplot positions [left, bottom, width, height] for all fields"""
        positions = []
        
        # Apply learned scaling factors
        margin_scale = self.learned_params['margin_scale']
        h_spacing_scale = self.learned_params.get('h_spacing_scale', 1.0)
        v_spacing_scale = self.learned_params.get('v_spacing_scale', 1.0)
        
        # Base margins (scaled by learned preferences)
        left_margin = 0.06 * margin_scale
        right_margin = 0.02 * margin_scale
        
        # Use learned margins
        bottom_margin = self.learned_params.get('bottom_margin', 0.08)
        top_margin = self.learned_params.get('top_margin', 0.96 if self.num_fields > 1 else 0.98)
        
        # Spacing between subplots
        h_spacing = 0.015 * h_spacing_scale if self.n_cols > 1 else 0  # Horizontal
        v_spacing = 0.02 * v_spacing_scale if self.n_rows > 1 else 0   # Vertical
        
        # Account for colorbar width
        colorbar_width = 0.025
        
        # Calculate available space
        available_width = 1.0 - left_margin - right_margin
        available_height = top_margin - bottom_margin
        
        # Calculate subplot dimensions
        plot_width = (available_width - (self.n_cols - 1) * h_spacing - self.n_cols * colorbar_width) / self.n_cols
        plot_height = (available_height - (self.n_rows - 1) * v_spacing) / self.n_rows
        
        # Generate positions for each subplot
        for i in range(self.num_fields):
                row = i // self.n_cols
                col = i % self.n_cols
                
                left = left_margin + col * (plot_width + colorbar_width + h_spacing)
                bottom = top_margin - (row + 1) * plot_height - row * v_spacing
                
                positions.append([left, bottom, plot_width, plot_height])
        
        return positions
        
    def get_title_position(self):
        """Calculate optimal suptitle y-position from learned preferences"""
        
        if self.num_fields == 1:
                return None  # No suptitle for single field
        
        # Get title Y position from learned preferences
        title_y = self.learned_params.get('title_y_position', 0.98)
        
        # Clamp to reasonable bounds
        title_y = max(0.90, min(title_y, 1.0))
                
        return title_y
    
    def get_font_sizes(self):
        """Calculate DPI-scaled font sizes"""
        base_dpi = 100
        scale_factor = (self.effective_dpi / base_dpi) * self.learned_params['font_scale']
        
        # Clamp scale factor
        scale_factor = max(0.8, min(scale_factor, 1.5))
        
        base_sizes = {
            'title_fontsize': 12,
            'subtitle_fontsize': 10,
            'axis_fontsize': 9,
            'colorbar_fontsize': 8,
            'tick_labelsize': 7,
            'suptitle_fontsize': 14
        }
        
        scaled_sizes = {}
        for key, base_size in base_sizes.items():
            scaled_size = base_size * scale_factor
            min_size = base_size * 0.8
            max_size = base_size * 1.6
            scaled_sizes[key] = int(max(min_size, min(scaled_size, max_size)))
        
        return scaled_sizes
    
    def auto_calibrate(self, canvas_widget):
        """Auto-calibrate layout based on actual canvas rendering"""
        # Detect if plots are being cut off or have too much space
        try:
            # Get the actual rendered size
            actual_width = canvas_widget.width()
            actual_height = canvas_widget.height()
            
            # Calculate how well we're using the space
            utilization_width = self.canvas_width_px / max(actual_width, 1)
            utilization_height = self.canvas_height_px / max(actual_height, 1)
            
            # If we're not filling the space well, adjust padding factor
            target_utilization = 0.95  # Aim for 95% space utilization
            
            if utilization_width < 0.85 or utilization_height < 0.85:
                # Too much wasted space - increase padding factor
                adjustment = 1.05
                new_padding = self.learned_params['padding_factor'] * adjustment
                self.save_preference('padding_factor', min(new_padding, 0.99))
                
            elif utilization_width > 1.05 or utilization_height > 1.05:
                # Plots being cut off - decrease padding factor
                adjustment = 0.95
                new_padding = self.learned_params['padding_factor'] * adjustment
                self.save_preference('padding_factor', max(new_padding, 0.80))
                
        except Exception as e:
            print(f"Auto-calibration failed: {e}")

class RadarSettings:
    """Class to manage and store radar display settings"""
    
    def __init__(self):
        # Field-specific settings
        self.field_settings = {}
        
        # Default field settings
        self.default_settings = {
            'vmin': None,  # Use default
            'vmax': None,  # Use default
            'cmap': None,  # Use default
            'colorbar_ticks': None  # Use default
        }
        
        # Available colormaps
        self.available_cmaps = [
            # ==================== STANDARD MATPLOTLIB ====================
            'viridis', 'plasma', 'inferno', 'magma', 'cividis',
            'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds',
            'YlOrBr', 'YlOrRd', 'OrRd', 'PuRd', 'RdPu', 'BuPu',
            'GnBu', 'PuBu', 'YlGnBu', 'PuBuGn', 'BuGn', 'YlGn',
            'jet', 'rainbow', 'turbo', 'gist_rainbow', 'coolwarm', 'seismic',
            
            # ==================== PYART REFLECTIVITY ====================
            'NWSRef', 'pyart_NWSRef',
            'RefDiff', 'pyart_RefDiff',
            'ChaseSpectral', 'pyart_ChaseSpectral',
            'SpectralExtended', 'pyart_SpectralExtended',
            
            # ==================== PYART VELOCITY ====================
            'NWSVel', 'pyart_NWSVel',
            'BuDRd', 'pyart_BuDRd',
            'BuDRd18', 'pyart_BuDRd18',
            'BuOr', 'pyart_BuOr',
            'BuOr8', 'pyart_BuOr8',
            'BuOrR14', 'pyart_BuOrR14',
            'BuOr12', 'pyart_BuOr12',
            'RdYlBu11b', 'pyart_RdYlBu11b',
            
            # ==================== PYART DIFFERENTIAL REFLECTIVITY (ZDR) ====================
            'Theodore16', 'pyart_Theodore16',
            'LangRainbow12', 'pyart_LangRainbow12',
            'HomeyerRainbow', 'pyart_HomeyerRainbow',
            'balance', 'pyart_balance',
            
            # ==================== PYART PHIDP / KDP ====================
            'Carbone42', 'pyart_Carbone42',
            'Carbone17', 'pyart_Carbone17',
            'Carbone11', 'pyart_Carbone11',
            
            # ==================== PYART SPECTRUM WIDTH ====================
            'NWS_SPW', 'pyart_NWS_SPW',
            
            # ==================== PYART OTHER ====================
            'BlueBrown10', 'pyart_BlueBrown10',
            'BlueBrown11', 'pyart_BlueBrown11',
            'BrBu10', 'pyart_BrBu10',
            'BrBu12', 'pyart_BrBu12',
            'Wild25', 'pyart_Wild25',
            'Cat12', 'pyart_Cat12',
            'StepSeq25', 'pyart_StepSeq25',
            'SCook18', 'pyart_SCook18',
            'EWilson17', 'pyart_EWilson17',
            'GrMg16', 'pyart_GrMg16',
            'PuOr12', 'pyart_PuOr12',
            'rate_Z', 'pyart_rate_Z',
            'acid', 'pyart_acid',
            'yuv', 'pyart_yuv',
            
            # ==================== GPM-GV LEGACY (IDL) ====================
            'GV_DZ', 'GV_VR', 'GV_SW', 'GV_DR', 'GV_KD', 
            'GV_RH', 'GV_PH', 'GV_HC', 'GV_RR',
        ]     
           
        # Load settings from QSettings
        self.qsettings = QSettings("GPM-GV", "RadarViewer")
        self.load_settings()
        
    def get_categorized_cmaps(self):
        """Return colormaps organized by category for easier selection"""
        return {
            'PyART Reflectivity': [
                'NWSRef', 'pyart_NWSRef', 'RefDiff', 'pyart_RefDiff',
                'ChaseSpectral', 'pyart_ChaseSpectral', 
                'SpectralExtended', 'pyart_SpectralExtended'
            ],
            'PyART Velocity': [
                'NWSVel', 'pyart_NWSVel', 'BuDRd', 'pyart_BuDRd',
                'BuDRd18', 'pyart_BuDRd18', 'BuOr', 'pyart_BuOr',
                'BuOr8', 'pyart_BuOr8', 'BuOrR14', 'pyart_BuOrR14',
                'RdYlBu11b', 'pyart_RdYlBu11b'
            ],
            'PyART Dual-Pol (ZDR)': [
                'Theodore16', 'pyart_Theodore16',
                'LangRainbow12', 'pyart_LangRainbow12',
                'HomeyerRainbow', 'pyart_HomeyerRainbow',
                'balance', 'pyart_balance'
            ],
            'PyART PhiDP/KDP': [
                'Carbone42', 'pyart_Carbone42',
                'Carbone17', 'pyart_Carbone17',
                'Carbone11', 'pyart_Carbone11'
            ],
            'PyART Other': [
                'NWS_SPW', 'pyart_NWS_SPW',
                'BlueBrown10', 'pyart_BlueBrown10',
                'BlueBrown11', 'pyart_BlueBrown11',
                'Wild25', 'pyart_Wild25'
            ],
            'Matplotlib Sequential': [
                'viridis', 'plasma', 'inferno', 'magma', 'cividis',
                'Greys', 'Purples', 'Blues', 'Greens', 'Oranges', 'Reds'
            ],
            'Matplotlib Diverging': [
                'coolwarm', 'seismic', 'RdBu', 'RdYlBu', 'RdYlGn'
            ],
            'Matplotlib Rainbow': [
                'jet', 'rainbow', 'turbo', 'gist_rainbow'
            ],
            'GPM-GV Legacy (IDL)': [
                'GV_DZ',  # Reflectivity (-20 to 60 dBZ)
                'GV_VR',  # Velocity (-32.5 to +32.5 m/s)
                'GV_SW',  # Spectrum Width (0 to 21+ m/s)
                'GV_DR',  # Differential Reflectivity (-3 to +3 dB)
                'GV_KD',  # Specific Differential Phase (-2 to +3 deg/km)
                'GV_RH',  # Correlation Coefficient (0 to 0.98+)
                'GV_PH',  # Differential Phase (0 to 360 deg)
                'GV_HC',  # Hydrometeor Classification
                'GV_RR',  # Rain Rate (0 to 80+ mm/hr)
            ]
        }
    
    def load_settings(self):
        """Load settings from QSettings"""
        size = self.qsettings.beginReadArray("field_settings")
        for i in range(size):
            self.qsettings.setArrayIndex(i)
            field = self.qsettings.value("field")
            if field:
                # Load colormap name - KEEP AS STRING, don't convert
                cmap_name = self.qsettings.value("cmap")
                if cmap_name == "@Invalid()":
                    cmap_name = None
                
                # Load colorbar ticks
                ticks_str = self.qsettings.value("colorbar_ticks")
                if ticks_str and ticks_str != "@Invalid()":
                    try:
                        colorbar_ticks = [float(x) for x in ticks_str.split(',')]
                    except:
                        colorbar_ticks = None
                else:
                    colorbar_ticks = None
                
                settings = {
                    'vmin': self.qsettings.value("vmin", type=float),
                    'vmax': self.qsettings.value("vmax", type=float),
                    'cmap': cmap_name,  # Store as STRING
                    'colorbar_ticks': colorbar_ticks
                }
                self.field_settings[field] = settings
        self.qsettings.endArray()
    
    def save_settings(self):
        """Save settings to QSettings"""
        # Without this, deleted fields remain in QSettings
        self.qsettings.remove("field_settings")
        
        self.qsettings.beginWriteArray("field_settings")
        for i, (field, settings) in enumerate(self.field_settings.items()):
            self.qsettings.setArrayIndex(i)
            self.qsettings.setValue("field", field)
            
            # Only save numeric values if they're not None
            if settings['vmin'] is not None:
                self.qsettings.setValue("vmin", float(settings['vmin']))
            if settings['vmax'] is not None:
                self.qsettings.setValue("vmax", float(settings['vmax']))
        
            # Save colormap as string name - be very explicit
            cmap = settings.get('cmap')
            cmap_name = None
            if cmap is not None:
                # Try multiple ways to get the colormap name
                if hasattr(cmap, 'name'):
                    cmap_name = str(cmap.name)
                elif isinstance(cmap, str):
                    cmap_name = cmap
                else:
                    # Last resort - try to convert to string
                    try:
                        cmap_name = str(cmap)
                    except:
                        cmap_name = "viridis"  # fallback default
            
            # Only save if we got a valid string
            if cmap_name:
                self.qsettings.setValue("cmap", cmap_name)
            
            # Save colorbar ticks as comma-separated string
            ticks = settings.get('colorbar_ticks')
            if ticks is not None:
                try:
                    # Convert to list if it's a numpy array
                    if hasattr(ticks, 'tolist'):
                        ticks = ticks.tolist()
                    # Convert to comma-separated string
                    if len(ticks) > 0:
                        ticks_str = ','.join([str(float(t)) for t in ticks])
                        self.qsettings.setValue("colorbar_ticks", ticks_str)
                except Exception as e:
                    print(f"Error saving colorbar ticks: {e}")
        
        self.qsettings.endArray()
        #self.qsettings.clear()
        self.qsettings.sync()  # Force write to disk
        #print(f"Settings saved to: {self.qsettings.fileName()}")
    
    def get_field_setting(self, field, setting_name, default=None):
        """Get a setting for a specific field"""
        if field in self.field_settings and setting_name in self.field_settings[field]:
            value = self.field_settings[field][setting_name]
            if value is not None:
                return value
        return default
    
    def set_field_setting(self, field, setting_name, value):
        """Set a setting for a specific field"""
        #print(f"=== set_field_setting called ===")
        #print(f"  field: {field}")
        #print(f"  setting_name: {setting_name}")
        #print(f"  value: {value} (type: {type(value)})")
        
        if field not in self.field_settings:
            self.field_settings[field] = self.default_settings.copy()
        self.field_settings[field][setting_name] = value
        
        #print(f"  field_settings[{field}] now: {self.field_settings[field]}")
            
    def reset_field_settings(self, field):
        """Reset a field's settings to default"""
        if field in self.field_settings:
            del self.field_settings[field]
            self.save_settings()
            
class AnnotationManager:
    """Manage point and text annotations on radar plots"""
    
    def __init__(self):
        self.annotations = []
        self.qsettings = QSettings("GPM-GV", "RadarViewer")
        self.load_annotations()
    
    def add_annotation(self, lat, lon, label="", symbol='v', size=5, 
                      color='white', enabled=True):
        """Add a new annotation"""
        annotation = {
            'lat': lat,
            'lon': lon,
            'label': label,
            'symbol': symbol,
            'size': size,
            'color': color,
            'enabled': enabled
        }
        self.annotations.append(annotation)
        self.save_annotations()
        return annotation
    
    def remove_annotation(self, index):
        """Remove annotation by index"""
        if 0 <= index < len(self.annotations):
            del self.annotations[index]
            self.save_annotations()
    
    def update_annotation(self, index, **kwargs):
        """Update annotation properties"""
        if 0 <= index < len(self.annotations):
            self.annotations[index].update(kwargs)
            self.save_annotations()
    
    def get_enabled_annotations(self):
        """Get list of enabled annotations"""
        return [ann for ann in self.annotations if ann.get('enabled', True)]
    
    def save_annotations(self):
        """Save annotations to QSettings"""
        self.qsettings.beginWriteArray("annotations")
        for i, ann in enumerate(self.annotations):
            self.qsettings.setArrayIndex(i)
            self.qsettings.setValue("lat", ann['lat'])
            self.qsettings.setValue("lon", ann['lon'])
            self.qsettings.setValue("label", ann.get('label', ''))
            self.qsettings.setValue("symbol", ann.get('symbol', 'v'))
            self.qsettings.setValue("size", ann.get('size', 10))
            self.qsettings.setValue("color", ann.get('color', 'white'))
            self.qsettings.setValue("enabled", ann.get('enabled', True))
        self.qsettings.endArray()
    
    def load_annotations(self):
        """Load annotations from QSettings"""
        size = self.qsettings.beginReadArray("annotations")
        self.annotations = []
        for i in range(size):
            self.qsettings.setArrayIndex(i)
            ann = {
                'lat': self.qsettings.value("lat", type=float),
                'lon': self.qsettings.value("lon", type=float),
                'label': self.qsettings.value("label", type=str),
                'symbol': self.qsettings.value("symbol", "v", type=str),
                'size': self.qsettings.value("size", 10, type=int),
                'color': self.qsettings.value("color", "white", type=str),
                'enabled': self.qsettings.value("enabled", True, type=bool)
            }
            self.annotations.append(ann)
        self.qsettings.endArray()
    
    def clear_all(self):
        """Clear all annotations"""
        self.annotations = []
        self.save_annotations()
        
class AnnotationDialog(QDialog):
    """Dialog for managing annotations"""
    
    def __init__(self, parent, annotation_manager):
        super().__init__(parent)
        self.parent = parent
        self.ann_mgr = annotation_manager
        
        self.setWindowTitle("Manage Annotations")
        self.setGeometry(200, 200, 700, 500)
        
        layout = QVBoxLayout()
        
        # ==================== ANNOTATION TABLE ====================
        self.table = QTableWidget()
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "Enabled", "Latitude", "Longitude", "Label", 
            "Symbol", "Size", "Color", "Actions"
        ])
        
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.Stretch)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        
        self.populate_table()
        layout.addWidget(self.table)
        
        # ==================== ADD NEW ANNOTATION SECTION ====================
        add_group = QWidget()
        add_layout = QVBoxLayout(add_group)

        # Row 1: Coordinates and Label
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)

        row1_layout.addWidget(QLabel("Add New:"))

        self.lat_spin = QDoubleSpinBox()
        self.lat_spin.setRange(-90, 90)
        self.lat_spin.setDecimals(4)
        self.lat_spin.setSuffix("°")
        self.lat_spin.setPrefix("Lat: ")
        self.lat_spin.setMinimumWidth(120)
        row1_layout.addWidget(self.lat_spin)

        self.lon_spin = QDoubleSpinBox()
        self.lon_spin.setRange(-180, 180)
        self.lon_spin.setDecimals(4)
        self.lon_spin.setSuffix("°")
        self.lon_spin.setPrefix("Lon: ")
        self.lon_spin.setMinimumWidth(120)
        row1_layout.addWidget(self.lon_spin)

        row1_layout.addWidget(QLabel("Label:"))
        self.label_edit = QLineEdit()
        self.label_edit.setPlaceholderText("Enter label (optional)")
        self.label_edit.setMinimumWidth(200) 
        row1_layout.addWidget(self.label_edit, stretch=1)

        add_layout.addWidget(row1)

        # Row 2: Appearance and Add Button
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)

        row2_layout.addWidget(QLabel("Symbol:"))
        self.symbol_combo = QComboBox()
        self.symbol_combo.addItems(['v', '^', '<', '>', 'o', 's', '*', '+', 'x', 'D', 'p', 'h'])
        row2_layout.addWidget(self.symbol_combo)

        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 20)
        self.size_spin.setValue(5)
        self.size_spin.setPrefix("Size: ")
        row2_layout.addWidget(self.size_spin)

        row2_layout.addWidget(QLabel("Color:"))
        self.color_combo = QComboBox()
        self.color_combo.addItems(['white', 'black', 'red', 'blue', 'green', 
                                   'yellow', 'cyan', 'magenta', 'orange'])
        row2_layout.addWidget(self.color_combo)

        row2_layout.addStretch()

        add_button = QPushButton("Add Annotation")
        add_button.clicked.connect(self.add_annotation)
        row2_layout.addWidget(add_button)

        add_layout.addWidget(row2)

        layout.addWidget(add_group)
        
        # ==================== PRESET LOCATIONS ====================
        preset_group = QWidget()
        preset_layout = QHBoxLayout(preset_group)
        preset_layout.addWidget(QLabel("Quick Add:"))
        
        # Add button for radar location
        radar_btn = QPushButton("Current Radar Location")
        radar_btn.clicked.connect(self.add_radar_location)
        preset_layout.addWidget(radar_btn)
        
        preset_layout.addStretch()
        layout.addWidget(preset_group)
        
        # ==================== BUTTONS ====================
        button_layout = QHBoxLayout()
        
        clear_button = QPushButton("Clear All")
        clear_button.clicked.connect(self.clear_all)
        button_layout.addWidget(clear_button)
        
        button_layout.addStretch()
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(self.apply_changes)
        button_layout.addWidget(buttons)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def populate_table(self):
        """Populate table with current annotations"""
        self.table.setRowCount(len(self.ann_mgr.annotations))
        
        for row, ann in enumerate(self.ann_mgr.annotations):
            # Enabled checkbox
            enabled_check = QCheckBox()
            enabled_check.setChecked(ann.get('enabled', True))
            enabled_check.stateChanged.connect(
                lambda state, r=row: self.toggle_annotation(r, state)
            )
            self.table.setCellWidget(row, 0, enabled_check)
            
            # Latitude
            self.table.setItem(row, 1, QTableWidgetItem(f"{ann['lat']:.4f}"))
            
            # Longitude
            self.table.setItem(row, 2, QTableWidgetItem(f"{ann['lon']:.4f}"))
            
            # Label
            self.table.setItem(row, 3, QTableWidgetItem(ann.get('label', '')))
            
            # Symbol
            self.table.setItem(row, 4, QTableWidgetItem(ann.get('symbol', 'v')))
            
            # Size
            self.table.setItem(row, 5, QTableWidgetItem(str(ann.get('size', 5))))
            
            # Color
            self.table.setItem(row, 6, QTableWidgetItem(ann.get('color', 'white')))
            
            # Delete button
            delete_btn = QPushButton("Delete")
            delete_btn.clicked.connect(lambda _, r=row: self.delete_annotation(r))
            self.table.setCellWidget(row, 7, delete_btn)
    
    def add_annotation(self):
        """Add new annotation from input fields"""
        lat = self.lat_spin.value()
        lon = self.lon_spin.value()
        label = self.label_edit.text()
        symbol = self.symbol_combo.currentText()
        size = self.size_spin.value()
        color = self.color_combo.currentText()
        
        self.ann_mgr.add_annotation(lat, lon, label, symbol, size, color)
        self.populate_table()
        
        # Clear input fields
        self.label_edit.clear()
    
    def add_radar_location(self):
        """Add annotation for current radar location"""
        if hasattr(self.parent, 'radar') and self.parent.radar:
            radar_lat = self.parent.radar.latitude['data'][0]
            radar_lon = self.parent.radar.longitude['data'][0]
            
            # Try to get site name
            site = ""
            if 'instrument_name' in self.parent.radar.metadata:
                site = self.parent.radar.metadata['instrument_name']
                if isinstance(site, bytes):
                    site = site.decode()
            
            self.lat_spin.setValue(radar_lat)
            self.lon_spin.setValue(radar_lon)
            self.label_edit.setText(site if site else "Radar")
    
    def toggle_annotation(self, row, state):
        """Toggle annotation enabled state"""
        self.ann_mgr.update_annotation(row, enabled=(state == Qt.Checked))
    
    def delete_annotation(self, row):
        """Delete annotation"""
        reply = QMessageBox.question(
            self, 'Delete Annotation',
            'Are you sure you want to delete this annotation?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.ann_mgr.remove_annotation(row)
            self.populate_table()
    
    def clear_all(self):
        """Clear all annotations"""
        reply = QMessageBox.question(
            self, 'Clear All',
            'Are you sure you want to delete all annotations?',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.ann_mgr.clear_all()
            self.populate_table()
    
    def apply_changes(self):
        """Apply changes and update plot"""
        self.parent.update_plot()

class SettingsDialog(QDialog):
    """Dialog for configuring radar display settings"""
    
    def __init__(self, parent, data_obj, settings):
        super().__init__(parent)
        self.data_obj = data_obj
        self.settings = settings
        self.parent = parent
        
        self.setWindowTitle("Colorbar Display Settings")
        self.resize(550, 600)
        
        # Create tabs
        self.tabs = QTabWidget()
        self.field_tab = QWidget()
        self.general_tab = QWidget()
        
        self.tabs.addTab(self.field_tab, "Field Settings")
        
        # Set up the field settings tab
        self.setup_field_tab()
        
        # Add buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel | QDialogButtonBox.Apply)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        
        # Main layout
        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        layout.addWidget(self.button_box)
        
        self.setLayout(layout)
    
    def setup_field_tab(self):
        """Set up the field settings tab with table for all fields"""
        layout = QVBoxLayout()
        
        # Create table for field settings
        self.field_table = QTableWidget()
        self.field_table.setColumnCount(5)
        self.field_table.setHorizontalHeaderLabels(["Field", "Min Value", "Max Value", "Colormap", "Reset"])
        
        # Set minimum width to prevent horizontal scrollbar
        self.field_table.setMinimumWidth(500)
        
        # Adjust column widths - optimized for space
        header = self.field_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)  # Field name
        header.setSectionResizeMode(1, QHeaderView.Fixed)              # Min Value
        header.setSectionResizeMode(2, QHeaderView.Fixed)              # Max Value  
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)            # Colormap - takes remaining space
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)  # Reset button
        
        # Set fixed widths for numeric columns
        self.field_table.setColumnWidth(1, 90)   # Min Value
        self.field_table.setColumnWidth(2, 90)   # Max Value
        
        # Populate the table
        self.populate_field_table()
        
        layout.addWidget(self.field_table)
        self.field_tab.setLayout(layout)
    
    def populate_field_table(self):
        """Populate the field settings table"""
        
        # Detect data type and get fields
        fields = []
        data_type = None
        
        if hasattr(self.data_obj, 'fields'):
            # PyART Radar or Grid object
            fields = list(self.data_obj.fields.keys())
            data_type = 'pyart'
        elif hasattr(self.data_obj, 'data_vars'):
            # ==================== FILTER XARRAY FIELDS ====================
            # xarray Dataset - filter to only plottable fields
            fields = get_plottable_fields(self.data_obj, 'xarray')
            data_type = 'xarray'
            
            print(f"Colorbar settings: showing {len(fields)} plottable fields")
            # ==================== END FILTER ====================
        else:
            QMessageBox.warning(self, "Error", "Could not determine data type")
            return
        
        if not fields:
            QMessageBox.warning(self, "No Fields", "No plottable data fields found")
            return
        
        # Set row count
        self.field_table.setRowCount(len(fields))
        
        # Add each field to the table
        for row, field in enumerate(fields):
            # Field name
            field_item = QTableWidgetItem(field)
            field_item.setFlags(field_item.flags() & ~Qt.ItemIsEditable)  
            self.field_table.setItem(row, 0, field_item)
            
            # ==================== GET DEFAULT VALUES BASED ON DATA TYPE ====================
            if data_type == 'xarray':
                default_info = get_xarray_field_info(self.data_obj, field)
            else:  # pyart (radar or grid)
                default_info = get_field_info(self.data_obj, field)
            
            default_vmin, default_vmax = default_info[1], default_info[2]
            default_cmap = default_info[3]  # This is the colormap object or name
            # ==================== END GET DEFAULTS ====================
            
            # Convert colormap to display name
            if hasattr(default_cmap, 'name'):
                default_cmap_name = default_cmap.name
            elif isinstance(default_cmap, str):
                default_cmap_name = default_cmap
            else:
                default_cmap_name = "viridis"
            
            # Clean up the name for display (remove 'pyart_' prefix)
            display_default_name = default_cmap_name.replace('pyart_', '')
            
            # Min value
            vmin_spinbox = QDoubleSpinBox()
            vmin_spinbox.setRange(-1000, 1000)
            vmin_spinbox.setDecimals(2)
            stored_vmin = self.settings.get_field_setting(field, 'vmin')
            vmin_spinbox.setValue(stored_vmin if stored_vmin is not None else default_vmin)
            vmin_spinbox.valueChanged.connect(lambda v, f=field: self.settings.set_field_setting(f, 'vmin', v))
            self.field_table.setCellWidget(row, 1, vmin_spinbox)
            
            # Max value
            vmax_spinbox = QDoubleSpinBox()
            vmax_spinbox.setRange(-1000, 1000)
            vmax_spinbox.setDecimals(2)
            stored_vmax = self.settings.get_field_setting(field, 'vmax')
            vmax_spinbox.setValue(stored_vmax if stored_vmax is not None else default_vmax)
            vmax_spinbox.valueChanged.connect(lambda v, f=field: self.settings.set_field_setting(f, 'vmax', v))
            self.field_table.setCellWidget(row, 2, vmax_spinbox)
            
            # ==================== COLORMAP SELECTION WITH DEFAULT NAME ====================
            cmap_combo = QComboBox()
            cmap_combo.setMaximumWidth(160)
            cmap_combo.setMaxVisibleItems(15)
            cmap_combo.setSizeAdjustPolicy(QComboBox.AdjustToContents)
            
            # Show default colormap name in the "Default" option
            cmap_combo.addItem(f"Default ({display_default_name})", None)
            cmap_combo.insertSeparator(1)
            
            # Get categories from centralized method
            categories = self.settings.get_categorized_cmaps()
            
            for category, cmaps in categories.items():
                # Add category label (simplified from "PyART Reflectivity" to "Reflectivity")
                display_category = category.replace('PyART ', '').replace('Matplotlib ', '')
                cmap_combo.addItem(f"── {display_category} ──", None)
                idx = cmap_combo.count() - 1
                item = cmap_combo.model().item(idx)
                item.setEnabled(False)
                
                # Add colormaps from this category
                for cmap_name in cmaps:
                    # Special handling for GV colormaps
                    if cmap_name.startswith('GV_'):
                        # GV colormaps are in our custom dictionary
                        if cmap_name in _GV_COLORMAPS:
                            cmap_combo.addItem(cmap_name, cmap_name)
                    else:
                        # Try to get from matplotlib
                        try:
                            plt.cm.get_cmap(cmap_name)
                            # Display clean name (remove pyart_ prefix for display)
                            display_name = cmap_name.replace('pyart_', '')
                            cmap_combo.addItem(display_name, cmap_name)  # Display vs actual value
                        except:
                            pass  # Skip if colormap doesn't exist in this PyART version
            
            # BLOCK signals while setting initial value
            cmap_combo.blockSignals(True)
            
            # Set the stored value (won't trigger signal)
            stored_cmap = self.settings.get_field_setting(field, 'cmap')
            if stored_cmap:
                index = cmap_combo.findData(stored_cmap)
                if index >= 0:
                    cmap_combo.setCurrentIndex(index)
            
            cmap_combo.currentIndexChanged.connect(
                lambda idx, f=field, c=cmap_combo, vmin=vmin_spinbox, vmax=vmax_spinbox: 
                self._save_all_field_settings(f, vmin, vmax, c, idx)
            )
            
            # Unblock signals
            cmap_combo.blockSignals(False)
            
            self.field_table.setCellWidget(row, 3, cmap_combo)  
                   
            # Reset button
            reset_btn = QPushButton("Reset")
            reset_btn.clicked.connect(lambda _, f=field, r=row, dt=data_type: self.reset_field_row(f, r, dt))
            self.field_table.setCellWidget(row, 4, reset_btn)
    
    def reset_field_row(self, field, row, data_type=None):
        """Reset a field's settings to defaults"""
        self.settings.reset_field_settings(field)
        
        # ==================== GET DEFAULTS BASED ON DATA TYPE ====================
        # Get default values based on data type
        if data_type == 'xarray':
            default_info = get_xarray_field_info(self.data_obj, field)
        elif hasattr(self.data_obj, 'data_vars'):
            # Detect if it's xarray
            default_info = get_xarray_field_info(self.data_obj, field)
        else:
            # PyART radar or grid
            default_info = get_field_info(self.data_obj, field)
        # ==================== END GET DEFAULTS ====================
        
        default_vmin, default_vmax = default_info[1], default_info[2]
        
        # Update the widgets
        vmin_spinbox = self.field_table.cellWidget(row, 1)
        vmin_spinbox.setValue(default_vmin)
        
        vmax_spinbox = self.field_table.cellWidget(row, 2)
        vmax_spinbox.setValue(default_vmax)
        
        cmap_combo = self.field_table.cellWidget(row, 3)
        cmap_combo.setCurrentIndex(0)  # Default
        
    def accept(self):
        """OK button - save and close"""
        self.settings.save_settings()  
        super().accept()
    
    def apply_settings(self):
        """Apply the current settings"""
        self.settings.save_settings()  
        self.parent.update_plot()
        
    def _save_all_field_settings(self, field, vmin_spinbox, vmax_spinbox, cmap_combo, cmap_idx):
        """Save all settings for a field (vmin, vmax, cmap)"""
        # Save colormap
        self.settings.set_field_setting(field, 'cmap', cmap_combo.itemData(cmap_idx))
        
        # Save current vmin/vmax (even if user hasn't explicitly changed them)
        self.settings.set_field_setting(field, 'vmin', vmin_spinbox.value())
        self.settings.set_field_setting(field, 'vmax', vmax_spinbox.value())
        
        print(f"Saved all settings for {field}: vmin={vmin_spinbox.value()}, vmax={vmax_spinbox.value()}, cmap={cmap_combo.itemData(cmap_idx)}")

def discrete_cmap(N, base_cmap=None):
    """Create an N-bin discrete colormap from the specified input map"""
    try:
        # If base_cmap is already a colormap object, use it directly
        if hasattr(base_cmap, 'N'):
            base = base_cmap
        else:
            base = plt.cm.get_cmap(base_cmap)
        
        color_list = base(np.linspace(0, 1, N))
        cmap_name = getattr(base, 'name', 'custom') + str(N)
        return colors.ListedColormap(color_list, cmap_name, N)
    except:
        return plt.cm.get_cmap('viridis')

class MidpointNormalize(colors.Normalize):
    def __init__(self, vmin=None, vmax=None, vcenter=None, clip=False):
        self.vcenter = vcenter
        super().__init__(vmin, vmax, clip)

    def __call__(self, value, clip=None):
        x, y = [self.vmin, self.vcenter, self.vmax], [0, 0.5, 1.]
        return np.ma.masked_array(np.interp(value, x, y,
                                           left=-np.inf, right=np.inf))

    def inverse(self, value):
        y, x = [self.vmin, self.vcenter, self.vmax], [0, 0.5, 1]
        return np.interp(value, x, y, left=-np.inf, right=np.inf)

def adjust_fhc_colorbar_for_pyart(cb):
    cb.set_ticks(np.arange(0.5, 11, 1.0))
    cb.ax.set_yticklabels(['No Echo', 'Drizzle', 'Rain', 'Ice Crystals', 
                          'Aggregates', 'Wet Snow', 'Vertical Ice', 
                          'LD Graupel', 'HD Graupel', 'Hail', 'Big Drops'])
    cb.ax.set_ylabel('')
    cb.ax.tick_params(length=0)
    return cb

def adjust_fhw_colorbar_for_pyart(cb):
    cb.set_ticks(np.arange(0.5, 8, 1.0))
    cb.ax.set_yticklabels(['No Echo','Ice Crystals', 'Plates', 'Dendrites', 
                          'Aggregates', 'Wet Snow','Frozen Precip', 'Rain'])
    cb.ax.set_ylabel('')
    cb.ax.tick_params(length=0)
    return cb

def adjust_ec_colorbar_for_pyart(cb):
    cb.set_ticks(np.arange(1.4, 9, 0.9))
    cb.ax.set_yticklabels(["Aggregates", "Ice Crystals", "Light Rain", 
                          "Rimed Particles", "Rain", "Vertically Ice", 
                          "Wet Snow", "Melting Hail", "Dry Hail/High Density Graupel"])
    cb.ax.set_ylabel('')
    cb.ax.tick_params(length=0)
    return cb

def adjust_meth_colorbar_for_pyart(cb, tropical=False):
    if not tropical:
        cb.set_ticks(np.arange(1.25, 5, 0.833))
        cb.ax.set_yticklabels(['R(Kdp, Zdr)', 'R(Kdp)', 'R(Z, Zdr)', 'R(Z)', 'R(Zrain)'])
    else:
        cb.set_ticks(np.arange(1.3, 6, 0.85))
        cb.ax.set_yticklabels(['R(Kdp, Zdr)', 'R(Kdp)', 'R(Z, Zdr)', 'R(Z_all)', 'R(Z_c)', 'R(Z_s)'])
    cb.ax.set_ylabel('')
    cb.ax.tick_params(length=0)
    return cb

def adjust_special_colorbars(field, display, index):
    """Adjust special colorbars efficiently"""
    if not hasattr(display, 'cbs') or len(display.cbs) <= index:
        return
        
    colorbar_adjustments = {
        'FH': adjust_fhc_colorbar_for_pyart,
        'FH2': adjust_fhc_colorbar_for_pyart,
        'MRC': adjust_meth_colorbar_for_pyart,
        'MRC2': adjust_meth_colorbar_for_pyart,
        'FS': adjust_fhc_colorbar_for_pyart,
        'FW': adjust_fhw_colorbar_for_pyart,
        'NT': adjust_fhw_colorbar_for_pyart,
        'EC': adjust_ec_colorbar_for_pyart
    }
    
    if field in colorbar_adjustments:
        display.cbs[index] = colorbar_adjustments[field](display.cbs[index])

def get_field_info(radar, field):
    """Optimized field info retrieval with auto-detection for unknown fields"""
    
    # Try to get from predefined configs first
    if field in _FIELD_CONFIGS:
        config = _FIELD_CONFIGS[field]
        cmap = config['cmap']
        
        # Handle special HID colormaps
        if cmap == 'CMAPHID_SUMMER':
            cmap = _CMAPHID_SUMMER
        elif cmap == 'CMAPHID_WINTER':
            cmap = _CMAPHID_WINTER
        elif cmap == 'CMAPHID_EC':
            cmap = _CMAPHID_EC
        elif cmap == 'CMAP_METH':
            cmap = _CMAP_METH
        # Handle GV colormaps
        elif isinstance(cmap, str) and cmap in _GV_COLORMAPS:
            cmap = _GV_COLORMAPS[cmap]
        elif isinstance(cmap, str):
            cmap = check_cm(cmap)
        
        return (config['units'], config['vmin'], config['vmax'], 
                cmap, config['title'], config['Nbins'])
    
    # ==================== AUTO-DETECT FOR UNKNOWN FIELDS ====================
    
    # Initialize defaults
    units = 'Unknown'
    vmin, vmax = 0, 70  # Fallback defaults
    cmap = 'viridis'
    title = f'{field}'
    Nbins = 0
    
    try:
        # Handle different data structures
        if hasattr(radar, 'fields') and field in radar.fields:
            # PyART Radar object
            field_data = radar.fields[field]
            data = field_data['data']
            units = field_data.get('units', 'Unknown')
            title = field_data.get('long_name', field)
            
        elif hasattr(radar, 'data_vars') and field in radar.data_vars:
            # xarray Dataset
            field_data = radar[field]
            data = field_data.values
            units = field_data.attrs.get('units', 'Unknown')
            title = field_data.attrs.get('long_name', field)
            
        else:
            # Can't find the field, use defaults
            print(f"  WARNING: Could not locate field '{field}' in data structure")
            return units, vmin, vmax, cmap, title, Nbins
        
        # ==================== COMPUTE ROBUST MIN/MAX (FIXED) ====================
        # Handle masked arrays and read-only arrays safely
        try:
            # Convert to numpy array and make it writable
            if np.ma.is_masked(data):
                # For masked arrays, get the unmasked data
                valid_data = np.ma.compressed(data).copy()
            else:
                # For regular arrays, flatten and remove NaNs
                data_flat = np.asarray(data).flatten()
                valid_data = data_flat[~np.isnan(data_flat)].copy()
            
            if valid_data.size > 0:
                # Use 1st and 99th percentile to avoid extreme outliers
                p01 = float(np.percentile(valid_data, 1))
                p99 = float(np.percentile(valid_data, 99))
                
                # Add 10% padding to the range
                data_range = p99 - p01
                vmin = p01 - 0.1 * data_range
                vmax = p99 + 0.1 * data_range
                
                # Round to nice numbers
                vmin = np.floor(vmin * 10) / 10  # Round down to 0.1
                vmax = np.ceil(vmax * 10) / 10   # Round up to 0.1
                                
                # ==================== SMART COLORMAP SELECTION ====================
                # Choose colormap based on data characteristics
                if vmin < 0 and vmax > 0:
                    # Diverging data (e.g., velocity)
                    cmap = check_cm('NWSVel')
                    #print(f"  Selected diverging colormap (data crosses zero)")
                elif 'velocity' in field.lower() or 'vel' in field.lower():
                    cmap = check_cm('NWSVel')
                elif 'refl' in field.lower() or 'dbz' in field.lower() or 'zh' in field.lower():
                    cmap = check_cm('NWSRef')
                elif 'zdr' in field.lower() or 'dr' in field.lower():
                    cmap = check_cm('HomeyerRainbow')
                elif 'kdp' in field.lower() or 'kd' in field.lower():
                    cmap = check_cm('HomeyerRainbow')
                elif 'rhohv' in field.lower() or 'rho' in field.lower() or 'correlation' in field.lower():
                    cmap = check_cm('LangRainbow12')
                    # Correlation usually ranges 0-1, but may have been scaled
                    if vmax <= 1.5:
                        vmin = max(vmin, 0.5)  # Typical correlation lower bound
                        vmax = 1.0
                else:
                    cmap = 'viridis'  # Safe default
                    
            else:
                print(f"  WARNING: No valid data found for field '{field}'")
                
        except Exception as compute_error:
            print(f"  ERROR: Could not compute statistics for '{field}': {compute_error}")
            # Use safe defaults on computation error
            vmin, vmax = 0, 70
            
    except Exception as e:
        print(f"  ERROR: Auto-detection failed for '{field}': {e}")
        # Use safe defaults on error
                
    return units, vmin, vmax, cmap, title, Nbins

def get_radar_info(radar, sweep):
    """Optimized radar info extraction with better site name handling"""
    
    # Extract site name with priority handling
    site = ''
    if 'site_name' in radar.metadata:
        site = radar.metadata['site_name']
    elif 'instrument_name' in radar.metadata:
        site = radar.metadata['instrument_name']
    
    # Handle bytes conversion
    if isinstance(site, bytes):
        site = site.decode().upper()
    else:
        site = str(site).upper()

    # Handle ODIM format
    if radar.metadata.get('original_container') == 'odim_h5':
        try:
            site = radar.metadata['source'].replace(',', ':').split(':')[1].upper()
        except:
            site = radar.metadata.get('site_name', '').upper()

    # Site name mapping for faster lookup
    site_mappings = {
        'NPOL1': 'NPOL', 'NPOL2': 'NPOL', 'LAVA1': 'KWAJ',
        'AN1-P': 'AL1', 'JG1-P': 'JG1', 'MC1-P': 'MC1', 'NT1-P': 'NT1',
        'PE1-P': 'PE1', 'SF1-P': 'SF1', 'ST1-P': 'ST1', 'SV1-P': 'SV1',
        'TM1-P': 'TM1', 'GUNN_PT': 'CPOL', 'REUNION': 'Reunion', 'CP2RADAR': 'CP2'
    }
    
    # Clean up byte strings in site names
    site = site.replace('\x00', '').strip()
    site = site_mappings.get(site, site)
    
    # Handle special system metadata
    if 'system' in radar.metadata:
        system_sites = {'KuD3R': 'KuD3R', 'KaD3R': 'KaD3R'}
        site = system_sites.get(radar.metadata['system'], site)

    # Get radar datetime efficiently
    try:
        radar_DT = pyart.util.datetime_from_radar(radar)
    except:
        radar_DT = datetime.datetime.now()
        
    # Handle special time formats for certain radars
    if radar_DT.year > 2000 and site in ['NPOL', 'KWAJ']:
        try:
            EPOCH_UNITS = "seconds since 1970-01-01T00:00:00Z"
            dtrad = num2date(0, radar.time["units"])
            epnum = date2num(dtrad, EPOCH_UNITS)
            radar_DT = num2date(epnum, EPOCH_UNITS)
        except:
            pass

    elv = radar.fixed_angle['data'][sweep]
    string_csweep = str(sweep).zfill(2)
    
    # Format date/time strings efficiently
    year = f'{radar_DT.year:04d}'
    month = f'{radar_DT.month:02d}'
    day = f'{radar_DT.day:02d}'
    hh = f'{radar_DT.hour:02d}'
    mm = f'{radar_DT.minute:02d}'
    ss = f'{radar_DT.second:02d}'
    
    mydate = f'{month}/{day}/{year}'
    mytime = f'{hh}:{mm}:{ss}'

    return site, mydate, mytime, elv, year, month, day, hh, mm, ss, string_csweep

def get_grid_field_info(grid_data, field):
    """Get field info for gridded data - similar to radar but for grids"""
    # Use the same field configurations but adapt for gridded data
    units, vmin, vmax, cmap, title, Nbins = get_field_info(grid_data, field)
    return units, vmin, vmax, cmap, title, Nbins

def get_xarray_field_info(ds, field):
    """Extract field info from xarray dataset"""
    if field in ds.data_vars:
        var = ds[field]
        
        # Try to get units from attributes
        units = var.attrs.get('units', 'Unknown')
        
        # Try to get reasonable vmin/vmax from data
        data_min = float(var.min().values) if var.size > 0 else -10
        data_max = float(var.max().values) if var.size > 0 else 70
        
        # Add some padding to the range
        data_range = data_max - data_min
        vmin = data_min - 0.1 * data_range
        vmax = data_max + 0.1 * data_range
        
        # Default colormap based on field name
        if any(x in field.lower() for x in ['refl', 'dbz', 'zh', 'CZ']):
            cmap = check_cm('NWSRef')
        elif any(x in field.lower() for x in ['vel', 'vr', 'VR']):
            cmap = check_cm('NWSVel')
        elif any(x in field.lower() for x in ['zdr', 'dr', 'DR']):
            cmap = check_cm('HomeyerRainbow')
        else:
            cmap = 'viridis'
        
        title = var.attrs.get('long_name', field)
        
        return units, vmin, vmax, cmap, title, 0
    
    return 'Unknown', -10, 70, 'viridis', field, 0
    
def get_plottable_fields(data, data_type):
    """Filter data variables to only return plottable fields (exclude metadata)"""
    
    if data_type == 'xarray':
        all_vars = list(data.data_vars.keys())
        
        # Find the main data dimensions (exclude single values)
        dims = data.dims
        main_dims = [d for d, size in dims.items() if size > 1]
        
        # Determine what dimensions we expect for plottable data
        # For TIME-HEIGHT: should have 'time' and 'range'/'height'
        # For RHI: should have 'z' and 'x' (and maybe 'sweep')
        # For PPI: should have 'x' and 'y' (and maybe 'z'/'level')
        
        plottable = []
        
        for var in all_vars:
            var_dims = data[var].dims
            var_shape = data[var].shape
            
            # Skip single-value variables (metadata)
            if len(var_dims) == 1 and var_shape[0] == 1:
                continue
            
            # Skip 1D coordinate arrays
            if len(var_dims) == 1:
                continue
            
            # For 2D or 3D data, check if it has the main dimensions
            if len(var_dims) >= 2:
                # Check if variable has at least 2 of the main dimensions
                matching_dims = [d for d in var_dims if d in main_dims]
                
                # If it has 2 or more main dimensions, it's plottable
                if len(matching_dims) >= 2:
                    plottable.append(var)
        
        return plottable
    
    elif data_type == 'grid':
        # PyART Grid - all fields in .fields are plottable
        return list(data.fields.keys())
    
    elif data_type == 'radar':
        # PyART Radar - all fields in .fields are plottable
        return list(data.fields.keys())
    
    else:
        # Unknown type - return all
        if hasattr(data, 'fields'):
            return list(data.fields.keys())
        elif hasattr(data, 'data_vars'):
            return list(data.data_vars.keys())
        else:
            return []
    
def create_manual_subplots(fig, num_fields, canvas_dpi, layout_manager):
    """Create manually positioned subplots using LayoutManager"""
    axes = []
    
    # Get positions from layout manager
    positions = layout_manager.get_subplot_positions()
    
    # Create axes at calculated positions
    for i in range(num_fields):
        if i < len(positions):
            pos = positions[i]
            ax = fig.add_axes(pos)
            axes.append(ax)
    
    # Get font sizes
    font_sizes = layout_manager.get_font_sizes()
    
    return axes, font_sizes
    
def fix_colorbar_height(ax):
    """Fix PyART colorbar to match axis height"""
    try:
        # Find the colorbar associated with this axis
        # PyART stores it in the axis's collections
        for collection in ax.collections:
            if hasattr(collection, 'colorbar') and collection.colorbar:
                cb = collection.colorbar
                
                # Get the axis position
                ax_pos = ax.get_position()
                
                # Get the colorbar axis position
                cb_pos = cb.ax.get_position()
                
                # Set colorbar height to match axis height
                cb.ax.set_position([cb_pos.x0, ax_pos.y0, cb_pos.width, ax_pos.height])
                
                return True
                
        # Alternative: check for _colorbar attribute
        if hasattr(ax, '_colorbar'):
            cb = ax._colorbar
            ax_pos = ax.get_position()
            cb_pos = cb.ax.get_position()
            cb.ax.set_position([cb_pos.x0, ax_pos.y0, cb_pos.width, ax_pos.height])
            return True
            
    except Exception as e:
        print(f"Could not fix colorbar height: {e}")
        return False

def get_dpi_scaled_sizes(canvas_dpi):
    """Calculate font sizes and spacing based on DPI - IMPROVED"""
    base_dpi = 100
    system = platform.system()
        
    # Platform-specific scaling
    if system == "Darwin":  # macOS
        # On Retina displays, don't over-scale fonts
        # Use a gentler scaling curve
        if canvas_dpi > 144:  # Likely Retina
            effective_dpi = 100 + (canvas_dpi - 144) * 0.3  # Gentle scaling
        else:
            effective_dpi = canvas_dpi
        scale_factor = effective_dpi / base_dpi
    elif system == "Windows":
        # Windows handles DPI scaling at OS level, so be conservative
        scale_factor = min(canvas_dpi / base_dpi, 1.3)  # Cap at 30% increase
    else:  # Linux
        # Linux usually reports accurate DPI
        scale_factor = canvas_dpi / base_dpi
    
    # Clamp scale factor to reasonable range
    scale_factor = max(0.8, min(scale_factor, 1.5))
    
    # Define base sizes (optimized for 100 DPI)
    base_sizes = {
        'title_fontsize': 12,      # Subplot titles
        'subtitle_fontsize': 10,   # Subplot subtitles
        'axis_fontsize': 9,        # Axis labels
        'colorbar_fontsize': 8,    # Colorbar labels
        'tick_labelsize': 7,       # Tick labels
        'suptitle_fontsize': 14    # Main figure title
    }
    
    # Scale all sizes with bounds
    scaled_sizes = {}
    for key, base_size in base_sizes.items():
        scaled_size = base_size * scale_factor
        # Minimum readable, maximum 2x base
        min_size = max(6, base_size * 0.8)
        max_size = base_size * 1.6
        scaled_sizes[key] = int(max(min_size, min(scaled_size, max_size)))
    
    return scaled_sizes, scale_factor
    
def apply_dpi_scaling_to_axes(axes, font_sizes):
    """Apply DPI-scaled font sizes to axes after plotting - IMPROVED"""
    
    for ax in axes:
        try:
            # Scale title with proper weight
            title = ax.get_title()
            if title:
                ax.set_title(title, fontsize=font_sizes['subtitle_fontsize'], 
                           fontweight='bold', pad=8)
            
            # Scale tick labels
            ax.tick_params(axis='both', which='major', 
                          labelsize=font_sizes['tick_labelsize'],
                          pad=4)
            ax.tick_params(axis='both', which='minor', 
                          labelsize=max(5, font_sizes['tick_labelsize'] - 1))
            
            # Scale axis labels with padding
            xlabel = ax.get_xlabel()
            ylabel = ax.get_ylabel()
            if xlabel:
                ax.set_xlabel(xlabel, fontsize=font_sizes['axis_fontsize'], 
                            labelpad=6)
            if ylabel:
                ax.set_ylabel(ylabel, fontsize=font_sizes['axis_fontsize'],
                            labelpad=6)
            
            # Scale colorbar if present - check multiple ways
            # Method 1: Check collections
            for collection in ax.collections:
                if hasattr(collection, 'colorbar') and collection.colorbar:
                    cb = collection.colorbar
                    cb.ax.tick_params(labelsize=font_sizes['colorbar_fontsize'])
                    cb_label = cb.ax.get_ylabel()
                    if cb_label:
                        cb.ax.set_ylabel(cb_label, 
                                       fontsize=font_sizes['colorbar_fontsize'],
                                       labelpad=8)
            
            # Method 2: Check if ax has a colorbar attribute
            if hasattr(ax, '_colorbar'):
                cb = ax._colorbar
                cb.ax.tick_params(labelsize=font_sizes['colorbar_fontsize'])
                cb_label = cb.ax.get_ylabel()
                if cb_label:
                    cb.ax.set_ylabel(cb_label, 
                                   fontsize=font_sizes['colorbar_fontsize'],
                                   labelpad=8)
                
        except Exception as e:
            print(f"Error scaling fonts for axis: {e}")
            continue
            
def remove_HDF_header(file):
    """Remove HDF header from certain .hdf5 files for PyART compatibility"""
    import mmap
    
    dn = os.path.abspath(file)
    os.makedirs(os.path.dirname(dn) + '/temp/', exist_ok=True)
    temp_dir = os.path.dirname(dn) + '/temp/'
    temp_file = shutil.copy(file, temp_dir)

    with open(temp_file, "r+b") as f:
        mmapped_file = mmap.mmap(f.fileno(), 0)
    
        # Find the first two line breaks and remove them
        first_newline = mmapped_file.find(b"\n")
        second_newline = mmapped_file.find(b"\n", first_newline + 1)
    
        if second_newline != -1:
            mmapped_file.move(0, second_newline + 1, len(mmapped_file) - (second_newline + 1))
            mmapped_file.flush()
    
        mmapped_file.close()

    return temp_file

def reorder_sweeps(radar):
    """Reorder sweeps in ascending order and fix negative azimuths"""
    final_radar = pyart.util.subset_radar(radar, list(radar.fields), ele_min=0., ele_max=90.)

    # Azimuths are negative, modify them to fit 0-360
    if final_radar.azimuth['data'][0] < 0:
        final_radar.azimuth['data'] = np.mod(final_radar.azimuth['data'], 360)
        az = final_radar.get_azimuth(0)

    return final_radar

def unzip_file(file):
    """Decompress .gz file"""
    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
        temp_path = temp_file.name
    
    with gzip.open(file, 'rb') as f_in:
        with open(temp_path, 'wb') as f_out:
            shutil.copyfileobj(f_in, f_out)
    
    return temp_path
    
def merge_split_cuts(radar, time_gap=120):
    """Merge split-cut NEXRAD sweeps (separate ref/vel scans at same elevation)"""
    
    sweeps = []
    for i, elev in enumerate(radar.fixed_angle['data']):
        start = radar.sweep_start_ray_index['data'][i]
        end = radar.sweep_end_ray_index['data'][i] + 1
        time = float(np.mean(radar.time['data'][start:end]))

        fields_present = set()
        for field in radar.fields:
            data = radar.fields[field]['data'][start:end]
            if np.ma.is_masked(data) and data.mask.all():
                continue
            fields_present.add(field)

        sweeps.append({
            'index': i,
            'elev': round(float(elev), 3),
            'time': time,
            'has_ref': any(f in fields_present for f in ['REF', 'DZ', 'CZ', 'DBZH', 'reflectivity']),
            'has_vel': any(f in fields_present for f in ['VEL', 'VR', 'VRADH', 'velocity'])
        })

    # Group by elevation angle, then split by time gap
    grouped = []
    for elev in sorted(set(s['elev'] for s in sweeps)):
        subset = [s for s in sweeps if s['elev'] == elev]
        subset.sort(key=lambda x: x['time'])

        group = []
        prev_time = None
        for s in subset:
            if prev_time is None or abs(s['time'] - prev_time) > time_gap:
                if group:
                    grouped.append(group)
                group = [s]
            else:
                group.append(s)
            prev_time = s['time']

        if group:
            grouped.append(group)

    # For each group, pick best REF + VEL sweep
    ref_sweeps = []
    vel_sweeps = []

    for group in grouped:
        best_ref = next((s for s in group if s['has_ref']), None)
        best_vel = next((s for s in group if s['has_vel']), None)

        if best_ref:
            ref_sweeps.append(best_ref['index'])
        if best_vel:
            vel_sweeps.append(best_vel['index'])

    # Extract and merge
    radar_dz = radar.extract_sweeps(sorted(ref_sweeps))
    radar_vr = radar.extract_sweeps(sorted(vel_sweeps))

    radar_new = copy.deepcopy(radar_dz)

    # Try to merge velocity fields (handle different field names)
    vel_field_names = ['VEL', 'VR', 'VRADH', 'velocity', 'SW', 'spectrum_width']
    for field_name in vel_field_names:
        if field_name in radar_vr.fields:
            data = radar_vr.fields[field_name]['data']
            # Find the reflectivity field name
            ref_field = None
            for rf in ['REF', 'DZ', 'CZ', 'DBZH', 'reflectivity']:
                if rf in radar_new.fields:
                    ref_field = rf
                    break
            
            if ref_field and data.shape == radar_new.fields[ref_field]['data'].shape:
                radar_new.add_field(field_name, radar_vr.fields[field_name], replace_existing=True)

    return radar_new
    
def detect_gridded_scan_type(data, data_type):
    """Detect if gridded data is PPI, RHI, or Time-Height based on dimensions/coordinates"""
    
    if data_type == 'xarray':
        # Check dimensions
        dims = list(data.dims.keys())
        
        # ==================== TIME-HEIGHT (MRR, QVP, Profilers) ====================
        # Has 'time' dimension AND a vertical dimension
        has_time = 'time' in dims
        has_vertical = any(vdim in dims for vdim in ['height', 'range', 'altitude', 'z', 'level'])
        
        # If it has time + vertical but NOT horizontal dimensions, it's TIME-HEIGHT
        has_horizontal = any(hdim in dims for hdim in ['x', 'y', 'lon', 'lat', 'longitude', 'latitude'])
        
        if has_time and has_vertical:
            # Check if it's 2D time-height (profiler) or 3D+ (scanning radar)
            if len(dims) == 2:
                # Only time and height - definitely TIME-HEIGHT
                return "TIME-HEIGHT"
            elif not has_horizontal:
                # Has time, vertical, but no horizontal - still TIME-HEIGHT
                return "TIME-HEIGHT"
        
        # ==================== RHI (Range-Height Indicator) ====================
        # Has z (height) and x (range) dimensions but not y or time
        if 'z' in dims and 'x' in dims and 'y' not in dims and 'time' not in dims:
            return "RHI"
        
        # RHI: or height and range with sweep dimension
        if 'height' in dims and 'range' in dims and 'sweep' in dims:
            return "RHI"
        
        # RHI: height and x with sweep
        if ('height' in dims or 'z' in dims) and 'x' in dims and 'sweep' in dims:
            return "RHI"
        
        # ==================== PPI (Plan Position Indicator) ====================
        # Has x and y (horizontal) dimensions
        if 'x' in dims and 'y' in dims:
            return "PPI"
        
        # PPI: or lat/lon
        if ('lat' in dims or 'latitude' in dims) and ('lon' in dims or 'longitude' in dims):
            return "PPI"
        
        # ==================== CHECK GLOBAL ATTRIBUTES AS FALLBACK ====================
        # Only use attributes if dimension-based detection is ambiguous
        if 'source' in data.attrs:
            source = str(data.attrs['source']).lower()
            if 'mrr' in source or 'micro rain radar' in source or 'qvp' in source:
                return "TIME-HEIGHT"
        
        if 'description' in data.attrs:
            desc = str(data.attrs['description']).lower()
            if 'rhi' in desc:
                return "RHI"
            if 'ppi' in desc:
                return "PPI"
            if 'qvp' in desc or 'quasi-vertical' in desc:
                return "TIME-HEIGHT"
    
    elif data_type == 'grid':
        # PyART Grid - check structure
        if hasattr(data, 'nz') and hasattr(data, 'nx') and not hasattr(data, 'ny'):
            return "RHI"
        # Typical PyART grid is PPI
        return "PPI"
    
    # Default to PPI
    return "PPI"

class RadarViewer(QMainWindow):
    """Improved RadarViewer with settings functionality"""
    
    def __init__(self):
        super().__init__()
        
        # Initialize variables
        self.radar = None
        self.current_field = None
        self.current_sweep = 0
        self.scan_type = "PPI"
        self.multifield_mode = False
        self.selected_fields = []
        self._resize_timer = None
        self._loading = False
        
        # Add data type tracking
        self.data_type = None
        self.gridded_data = None
        
        # Initialize settings
        self.qsettings = QSettings("GPM-GV", "RadarViewer")
        self.settings = RadarSettings()
        
        # Initialize annotation manager
        self.annotation_manager = AnnotationManager()
        
        # ==================== ZOOM STATE ====================
        self.zoom_xlim = None      # Zoom x limits (km for fast, lon for cartopy)
        self.zoom_ylim = None      # Zoom y limits (km for fast, lat for cartopy)
        self.zoom_enabled = False  # Is zoom mode active?
        self.zoom_rect_selectors = []  # Store selectors for cleanup
        
        # Set up the window with platform-specific dimensions
        self.setWindowTitle("GPM-GV Radar Viewer")
        if platform.system() == "Linux":
            self.setGeometry(100, 100, 1200, 800)
        else:
            self.setGeometry(100, 100, 1400, 900)
        
        # Create main widget and layout
        self.main_widget = QWidget(self)
        self.setCentralWidget(self.main_widget)
        self.layout = QVBoxLayout(self.main_widget)
        
        # Create toolbar
        self.create_toolbar()
        
        # Create top control panel
        self.create_control_panel()
        
        # Create canvas with proper sizing
        self.figure = plt.figure(figsize=(12, 8), dpi=100)
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        
        # Enable proper backing store
        self.canvas.setUpdatesEnabled(True)
        self.canvas.setMinimumSize(400, 300)
        
        self.canvas.setStyleSheet("background-color: white;")  # Forces white background
        self.figure.patch.set_facecolor('white')
        
        self.canvas.setFocusPolicy(Qt.StrongFocus)
        self.canvas.setFocus()
        
        self.layout.addWidget(self.canvas, stretch=1)
        
        # Initialize status bar
        self.statusBar().showMessage("Ready - Please load a radar file")
        
        # Create resize timer for debouncing
        self._resize_timer = QTimer()
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._handle_resize)
        
        # Connect to window resize signals
        self.canvas.mpl_connect('resize_event', self._on_canvas_resize)
        
        # Load user display preferences
        self.load_display_preferences()
        
    def show_layout_tuning(self):
        """Show dialog to manually tune layout parameters"""

        if not hasattr(self, '_last_layout_mgr') or not self._last_layout_mgr:
                QMessageBox.warning(self, "No Layout", "Please plot data first.")
                return
        
        layout_mgr = self._last_layout_mgr
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Layout Tuning")
        dialog.setGeometry(200, 200, 150, 450)
        layout = QFormLayout()
        
        # ==================== GRID INFORMATION ====================
        grid_label = QLabel(
                f"<b>Grid Configuration: {layout_mgr.n_rows}x{layout_mgr.n_cols}</b>\n"
                #f"Scan Type: {layout_mgr.scan_type}\n"
                #f"Fields: {layout_mgr.num_fields}\n"
                f"Config Key: {layout_mgr.config_key}"
        )
        layout.addRow("Current Grid:", grid_label)
        
        # ==================== SEPARATOR ====================
        separator = QLabel("─" * 50)
        layout.addRow(separator)
        
        # ==================== FIGURE WIDTH CONTROL ====================
        width_spin = QDoubleSpinBox()
        width_spin.setRange(4.0, 30.0)
        width_spin.setSingleStep(0.5)
        width_spin.setDecimals(1)
        width_spin.setValue(layout_mgr.learned_params.get('figure_width', 12.0))
        width_spin.setSuffix(" inches")
        layout.addRow("Figure Width:", width_spin)
        
        # ==================== FIGURE HEIGHT CONTROL ====================
        height_spin = QDoubleSpinBox()
        height_spin.setRange(3.0, 18.0)
        height_spin.setSingleStep(0.5)
        height_spin.setDecimals(1)
        height_spin.setValue(layout_mgr.learned_params.get('figure_height', 8.0))
        height_spin.setSuffix(" inches")
        layout.addRow("Figure Height:", height_spin)
        
        # ==================== TITLE Y POSITION CONTROL ====================
        title_y_spin = QDoubleSpinBox()
        title_y_spin.setRange(0.85, 1.0)
        title_y_spin.setSingleStep(0.01)
        title_y_spin.setDecimals(3)
        title_y_spin.setValue(layout_mgr.learned_params.get('title_y_position', 0.98))
        layout.addRow("Title Y Position:", title_y_spin)
        
        # ==================== TOP MARGIN CONTROL ====================
        top_margin_spin = QDoubleSpinBox()
        top_margin_spin.setRange(0.80, 0.98)
        top_margin_spin.setSingleStep(0.01)
        top_margin_spin.setDecimals(3)
        top_margin_spin.setValue(layout_mgr.learned_params.get('top_margin', 0.96))
        layout.addRow("Top Margin:", top_margin_spin)
        
        # ==================== BOTTOM MARGIN CONTROL ====================
        bottom_margin_spin = QDoubleSpinBox()
        bottom_margin_spin.setRange(0.02, 0.20)
        bottom_margin_spin.setSingleStep(0.01)
        bottom_margin_spin.setDecimals(3)
        bottom_margin_spin.setValue(layout_mgr.learned_params.get('bottom_margin', 0.08))
        layout.addRow("Bottom Margin:", bottom_margin_spin)
        
        # ==================== PADDING FACTOR CONTROL ====================
        padding_spin = QDoubleSpinBox()
        padding_spin.setRange(0.5, 1.0)
        padding_spin.setSingleStep(0.01)
        padding_spin.setDecimals(3)
        padding_spin.setValue(layout_mgr.learned_params['padding_factor'])
        layout.addRow("Padding Factor:", padding_spin)
        
        # ==================== MARGIN SCALE CONTROL ====================
        margin_spin = QDoubleSpinBox()
        margin_spin.setRange(0.5, 2.0)
        margin_spin.setSingleStep(0.1)
        margin_spin.setValue(layout_mgr.learned_params['margin_scale'])
        layout.addRow("Margin Scale:", margin_spin)
        
        # ==================== HORIZONTAL SPACING CONTROL (NEW) ====================
        h_spacing_spin = QDoubleSpinBox()
        h_spacing_spin.setRange(0.1, 6.0)
        h_spacing_spin.setSingleStep(0.1)
        h_spacing_spin.setDecimals(2)
        h_spacing_spin.setValue(layout_mgr.learned_params.get('h_spacing_scale', 1.0))
        layout.addRow("Horizontal Spacing:", h_spacing_spin)
        
        # ==================== VERTICAL SPACING CONTROL (NEW) ====================
        v_spacing_spin = QDoubleSpinBox()
        v_spacing_spin.setRange(0.1, 6.0)
        v_spacing_spin.setSingleStep(0.1)
        v_spacing_spin.setDecimals(2)
        v_spacing_spin.setValue(layout_mgr.learned_params.get('v_spacing_scale', 1.0))
        layout.addRow("Vertical Spacing:", v_spacing_spin)
        
        # ==================== FONT SCALE CONTROL ====================
        font_spin = QDoubleSpinBox()
        font_spin.setRange(0.5, 2.0)
        font_spin.setSingleStep(0.1)
        font_spin.setValue(layout_mgr.learned_params['font_scale'])
        layout.addRow("Font Scale:", font_spin)
        
        # ==================== SEPARATOR ====================
        separator2 = QLabel("─" * 50)
        layout.addRow(separator2)
        
        # ==================== INFORMATION LABEL ====================
        info_label = QLabel(
                f"Effective DPI: {layout_mgr.effective_dpi}\n"
                f"Current Fig Size: {layout_mgr.fig_width:.1f}x{layout_mgr.fig_height:.1f} inches"
        )
        layout.addRow(info_label)
        
        # ==================== AUTO-CALIBRATE BUTTON ====================
        auto_cal_button = QPushButton("Auto-Calibrate")
        auto_cal_button.clicked.connect(
                lambda: self._auto_calibrate_layout(layout_mgr)
        )
        layout.addRow(auto_cal_button)
        
        # ==================== RESET BUTTON ====================
        reset_button = QPushButton("Reset to Grid Defaults")
        reset_button.clicked.connect(
                lambda: self._reset_layout_defaults(layout_mgr)
        )
        layout.addRow(reset_button)
        
        # ==================== DIALOG BUTTONS ====================
        buttons = QDialogButtonBox(
                QDialogButtonBox.Ok | 
                QDialogButtonBox.Cancel | 
                QDialogButtonBox.Apply
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        buttons.button(QDialogButtonBox.Apply).clicked.connect(
                lambda: self._apply_layout_changes(
                        layout_mgr, 
                        width_spin,
                        height_spin,
                        title_y_spin,
                        top_margin_spin,
                        bottom_margin_spin,
                        padding_spin, 
                        margin_spin, 
                        h_spacing_spin,      # NEW
                        v_spacing_spin,      # NEW
                        font_spin
                )
        )
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
                self._apply_layout_changes(
                        layout_mgr, 
                        width_spin,
                        height_spin,
                        title_y_spin,
                        top_margin_spin,
                        bottom_margin_spin,
                        padding_spin, 
                        margin_spin, 
                        h_spacing_spin,      # NEW
                        v_spacing_spin,      # NEW
                        font_spin
                )
    
    def _apply_layout_changes(self, layout_mgr, width_spin, height_spin, title_y_spin,
                        top_margin_spin, bottom_margin_spin, padding_spin, 
                        margin_spin, h_spacing_spin, v_spacing_spin, font_spin):
        """Apply and save layout parameter changes"""
        
        layout_mgr.save_preference('figure_width', width_spin.value())
        layout_mgr.save_preference('figure_height', height_spin.value())
        layout_mgr.save_preference('title_y_position', title_y_spin.value())
        layout_mgr.save_preference('top_margin', top_margin_spin.value())
        layout_mgr.save_preference('bottom_margin', bottom_margin_spin.value())
        layout_mgr.save_preference('padding_factor', padding_spin.value())
        layout_mgr.save_preference('margin_scale', margin_spin.value())
        layout_mgr.save_preference('h_spacing_scale', h_spacing_spin.value())  # NEW
        layout_mgr.save_preference('v_spacing_scale', v_spacing_spin.value())  # NEW
        layout_mgr.save_preference('font_scale', font_spin.value())
        
        self.update_plot()
    
    def _auto_calibrate_layout(self, layout_mgr):
        """Run auto-calibration"""
        layout_mgr.auto_calibrate(self.canvas)
        QMessageBox.information(self, "Auto-Calibration", 
                              "Layout calibrated based on current display.\n"
                              "Click Apply to see changes.")
    
    def _reset_layout_defaults(self, layout_mgr):
        """Reset layout to default values"""
        settings = QSettings("GPM-GV", "RadarViewer")
        settings.beginGroup(f"layout/{layout_mgr.config_key}")
        settings.remove("")  # Remove all keys in this group
        settings.endGroup()
        
        QMessageBox.information(self, "Reset", "Layout reset to defaults.\nReload data to see changes.")
    
    def load_display_preferences(self):
        """Load user's display scaling preferences"""
        self.display_prefs = {
            'font_scale': self.settings.qsettings.value('display/font_scale', 1.0, type=float),
            'spacing_scale': self.settings.qsettings.value('display/spacing_scale', 1.0, type=float),
        }
    
    def show_display_preferences(self):
        """Show dialog to adjust display scaling"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Display Preferences")
        layout = QFormLayout()
        
        font_spin = QDoubleSpinBox()
        font_spin.setRange(0.5, 2.0)
        font_spin.setSingleStep(0.1)
        font_spin.setValue(self.display_prefs['font_scale'])
        layout.addRow("Font Scale:", font_spin)
        
        spacing_spin = QDoubleSpinBox()
        spacing_spin.setRange(0.5, 2.0)
        spacing_spin.setSingleStep(0.1)
        spacing_spin.setValue(self.display_prefs['spacing_scale'])
        layout.addRow("Spacing Scale:", spacing_spin)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec_() == QDialog.Accepted:
            self.display_prefs['font_scale'] = font_spin.value()
            self.display_prefs['spacing_scale'] = spacing_spin.value()
            
            self.settings.qsettings.setValue('display/font_scale', font_spin.value())
            self.settings.qsettings.setValue('display/spacing_scale', spacing_spin.value())
            
            self.update_plot()
            
    def update_ui_for_data_type(self):
        """Update UI controls based on loaded data type and scan type"""
        
        if self.data_type == 'radar':
            # Radar data - enable range control
            self.range_spinner.setEnabled(True)
            self.range_spinner.setToolTip("Maximum display range from radar")
            
            # Height control only for RHI
            if self.scan_type == "RHI":
                self.height_spinner.setEnabled(True)
                self.height_spinner.setToolTip("Maximum height for RHI display")
            else:
                self.height_spinner.setEnabled(False)
                self.height_spinner.setToolTip("Height control only for RHI scans")
        
        elif self.data_type in ['grid', 'xarray']:
            # Check scan type for gridded data
            if self.scan_type == "TIME-HEIGHT":
                # Profiler data - disable range, enable height
                self.range_spinner.setEnabled(False)
                self.range_spinner.setToolTip("Range control disabled for profiler data")
                
                self.height_spinner.setEnabled(False)
                self.height_spinner.setToolTip("Maximum height for time-height display")
            
            elif self.scan_type == "RHI":
                # Gridded RHI - enable both
                self.range_spinner.setEnabled(False)
                self.range_spinner.setToolTip("Maximum range for RHI display")
                
                self.height_spinner.setEnabled(False)
                self.height_spinner.setToolTip("Maximum height for RHI display")
            
            else:  # PPI
                # Gridded PPI - enable range
                self.range_spinner.setEnabled(False)
                self.range_spinner.setToolTip("Maximum display range")
                
                self.height_spinner.setEnabled(False)
                self.height_spinner.setToolTip("Height control only for RHI/profiler data")            
    
    def create_toolbar(self):
        """Create the main toolbar with settings and options"""
        self.toolbar_top = QToolBar("Main Toolbar")
        self.addToolBar(self.toolbar_top)
        
        # Data Info action
        data_info_action = QAction("Data Info", self)
        data_info_action.setToolTip("View data metadata and information")
        data_info_action.triggered.connect(self.show_data_info)
        self.toolbar_top.addAction(data_info_action)
        self.toolbar_top.addSeparator()        
        
        # Layout Tuning action
        layout_action = QAction("Plot Layout", self)
        layout_action.setToolTip("Tune layout and spacing")
        layout_action.triggered.connect(self.show_layout_tuning)
        self.toolbar_top.addAction(layout_action)
        self.toolbar_top.addSeparator()
        
        # Colorbar Settings action
        settings_action = QAction("Update Colorbars", self)
        settings_action.setToolTip("Configure Colorbar")
        settings_action.triggered.connect(self.show_settings)
        self.toolbar_top.addAction(settings_action)
        self.toolbar_top.addSeparator()
        
        # Annotations action
        annotations_action = QAction("Add Annotations", self)
        annotations_action.setToolTip("Manage map annotations")
        annotations_action.triggered.connect(self.show_annotations_dialog)
        self.toolbar_top.addAction(annotations_action)
        self.toolbar_top.addSeparator()
        
        # Zoom Mode toggle
        self.zoom_action = QAction("Zoom Mode", self)
        self.zoom_action.setToolTip("Enable zoom box (PPI only) - Drag box to zoom")
        self.zoom_action.setCheckable(True)
        self.zoom_action.toggled.connect(self.toggle_zoom_mode)
        self.toolbar_top.addAction(self.zoom_action)
        
        # Reset Zoom
        reset_zoom_action = QAction("Reset Zoom", self)
        reset_zoom_action.setToolTip("Reset to full view")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        self.toolbar_top.addAction(reset_zoom_action)
        self.toolbar_top.addSeparator()
        
        # Clear data action
        clear_action = QAction("Clear Viewer", self)
        clear_action.setToolTip("Clear all loaded data and reset viewer")
        clear_action.triggered.connect(self.clear_all_data)
        self.toolbar_top.addAction(clear_action)
        self.toolbar_top.addSeparator()
    
    def show_settings(self):
        """Show the settings dialog"""
        if not self.radar and not self.gridded_data:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return
    
        # Pass the appropriate data object to the dialog
        data_obj = self.radar if self.radar else self.gridded_data
        
        # Create dialog fresh each time (don't reuse)
        dialog = SettingsDialog(self, data_obj, self.settings)
        
        # Use exec_() for modal behavior
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.update_plot()
        
        # Explicitly delete dialog after use
        dialog.deleteLater()
            
    def show_data_info(self):
        """Show metadata information about the loaded data"""
        if self.data_type == 'radar' and not self.radar:
            QMessageBox.warning(self, "No Data", "Please load radar data first.")
            return
        elif self.data_type in ['grid', 'xarray'] and not self.gridded_data:
            QMessageBox.warning(self, "No Data", "Please load gridded data first.")
            return
        elif not self.data_type:
            QMessageBox.warning(self, "No Data", "Please load data first.")
            return
        
        # Create dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Data Information")
        dialog.setGeometry(200, 200, 700, 600)
        
        layout = QVBoxLayout()
        
        # Create tabs for different info categories
        tabs = QTabWidget()
        
        # General Info Tab
        general_tab = QWidget()
        general_layout = QVBoxLayout()
        general_text = QTextEdit()
        general_text.setReadOnly(True)
        general_text.setFont(QFont("Courier", 10))
        
        # Collect general info
        info_text = self._collect_general_info()
        general_text.setPlainText(info_text)
        
        general_layout.addWidget(general_text)
        general_tab.setLayout(general_layout)
        tabs.addTab(general_tab, "General Info")
        
        # Fields Tab
        fields_tab = QWidget()
        fields_layout = QVBoxLayout()
        fields_table = QTableWidget()
        
        # Populate fields table
        self._populate_fields_table(fields_table)
        
        fields_layout.addWidget(fields_table)
        fields_tab.setLayout(fields_layout)
        tabs.addTab(fields_tab, "Fields")
        
        # Metadata Tab
        metadata_tab = QWidget()
        metadata_layout = QVBoxLayout()
        metadata_text = QTextEdit()
        metadata_text.setReadOnly(True)
        metadata_text.setFont(QFont("Courier", 9))
        
        # Collect all metadata
        metadata_info = self._collect_metadata()
        metadata_text.setPlainText(metadata_info)
        
        metadata_layout.addWidget(metadata_text)
        metadata_tab.setLayout(metadata_layout)
        tabs.addTab(metadata_tab, "All Metadata")
        
        layout.addWidget(tabs)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(dialog.close)
        layout.addWidget(close_button)
        
        dialog.setLayout(layout)
        dialog.exec_()

    def _collect_general_info(self):
        """Collect general information about the data"""
        info = []
        info.append("="*60)
        info.append("DATA INFORMATION")
        info.append("="*60)
        info.append("")
        
        if self.data_type == 'radar':
            radar = self.radar
            
            # Basic info
            info.append(f"Data Type: Radar")
            
            # Site information
            if 'instrument_name' in radar.metadata:
                site = radar.metadata['instrument_name']
                if isinstance(site, bytes):
                    site = site.decode()
                info.append(f"Site: {site}")
            
            # Time information
            try:
                radar_time = pyart.util.datetime_from_radar(radar)
                info.append(f"Date/Time: {radar_time.strftime('%Y-%m-%d %H:%M:%S UTC')}")
            except:
                info.append(f"Date/Time: Unable to parse")
            
            # Location
            info.append(f"Latitude: {radar.latitude['data'][0]:.4f}°")
            info.append(f"Longitude: {radar.longitude['data'][0]:.4f}°")
            info.append(f"Altitude: {radar.altitude['data'][0]:.1f} m")
            
            # Scan information
            info.append(f"\nScan Information:")
            info.append(f"  Number of sweeps: {radar.nsweeps}")
            info.append(f"  Scan type: {radar.scan_type if hasattr(radar, 'scan_type') else 'Unknown'}")
            info.append(f"  Number of gates: {radar.ngates}")
            info.append(f"  Number of rays: {radar.nrays}")
            
            # Elevation angles
            info.append(f"\nElevation Angles:")
            for i, elev in enumerate(radar.fixed_angle['data']):
                info.append(f"  Sweep {i}: {elev:.2f}°")
            
            # Available fields
            info.append(f"\nAvailable Fields ({len(radar.fields)}):")
            for field in radar.fields.keys():
                info.append(f"  - {field}")
            
        elif self.data_type == 'grid':
            grid = self.gridded_data
            
            info.append(f"Data Type: PyART Grid")
            
            # Time
            try:
                if hasattr(grid, 'time') and 'data' in grid.time:
                    time_val = grid.time['data'][0]
                    if hasattr(time_val, 'strftime'):
                        info.append(f"Time: {time_val.strftime('%Y-%m-%d %H:%M:%S UTC')}")
                    else:
                        info.append(f"Time: {time_val}")
            except:
                info.append(f"Time: Unknown")
            
            # Origin
            info.append(f"Origin Latitude: {grid.origin_latitude['data'][0]:.4f}°")
            info.append(f"Origin Longitude: {grid.origin_longitude['data'][0]:.4f}°")
            info.append(f"Origin Altitude: {grid.origin_altitude['data'][0]:.1f} m")
            
            # Grid dimensions
            info.append(f"\nGrid Dimensions:")
            info.append(f"  X: {grid.nx} points")
            info.append(f"  Y: {grid.ny} points")
            info.append(f"  Z: {grid.nz} points")
            
            # Grid spacing
            if hasattr(grid, 'x') and hasattr(grid, 'y') and hasattr(grid, 'z'):
                x_spacing = (grid.x['data'][-1] - grid.x['data'][0]) / (grid.nx - 1) / 1000.0
                y_spacing = (grid.y['data'][-1] - grid.y['data'][0]) / (grid.ny - 1) / 1000.0
                info.append(f"\nGrid Spacing:")
                info.append(f"  X: {x_spacing:.2f} km")
                info.append(f"  Y: {y_spacing:.2f} km")
            
            # Available fields
            info.append(f"\nAvailable Fields ({len(grid.fields)}):")
            for field in grid.fields.keys():
                info.append(f"  - {field}")
            
        elif self.data_type == 'xarray':
            ds = self.gridded_data
            
            info.append(f"Data Type: xarray Dataset")
            
            # Dimensions
            info.append(f"\nDimensions:")
            for dim, size in ds.dims.items():
                info.append(f"  {dim}: {size}")
            
            # Coordinates
            info.append(f"\nCoordinates:")
            for coord in ds.coords:
                info.append(f"  {coord}: {ds.coords[coord].shape}")
            
            # Variables
            info.append(f"\nData Variables ({len(ds.data_vars)}):")
            for var in ds.data_vars:
                info.append(f"  - {var}: {ds[var].shape}")
            
            # Attributes
            if ds.attrs:
                info.append(f"\nGlobal Attributes:")
                for key, val in list(ds.attrs.items())[:10]:  # First 10 attrs
                    info.append(f"  {key}: {val}")
        
        info.append("")
        info.append("="*60)
        
        return "\n".join(info)
        
    def show_annotations_dialog(self):
        """Show annotation management dialog"""
        dialog = AnnotationDialog(self, self.annotation_manager)
        if dialog.exec_() == QDialog.Accepted:
            self.update_plot()

    def _populate_fields_table(self, table):
        """Populate the fields table with field information"""
        if self.data_type == 'radar':
            fields = self.radar.fields
        elif self.data_type == 'grid':
            fields = self.gridded_data.fields
        elif self.data_type == 'xarray':
            # For xarray, create a dict-like structure
            fields = {var: self.gridded_data[var] for var in self.gridded_data.data_vars}
        else:
            return
        
        table.setColumnCount(4)
        table.setHorizontalHeaderLabels(["Field Name", "Units", "Long Name", "Data Range"])
        table.setRowCount(len(fields))
        
        for i, (field_name, field_data) in enumerate(fields.items()):
            # Field name
            table.setItem(i, 0, QTableWidgetItem(field_name))
            
            # Units
            if self.data_type == 'xarray':
                units = field_data.attrs.get('units', 'N/A')
            else:
                units = field_data.get('units', 'N/A')
            table.setItem(i, 1, QTableWidgetItem(str(units)))
            
            # Long name
            if self.data_type == 'xarray':
                long_name = field_data.attrs.get('long_name', 'N/A')
            else:
                long_name = field_data.get('long_name', 'N/A')
            table.setItem(i, 2, QTableWidgetItem(str(long_name)))
            
            # Data range
            try:
                if self.data_type == 'xarray':
                    data = field_data.values
                else:
                    data = field_data['data']
                
                valid_data = data[~np.isnan(data)]
                if len(valid_data) > 0:
                    data_range = f"{valid_data.min():.2f} to {valid_data.max():.2f}"
                else:
                    data_range = "All NaN"
            except:
                data_range = "Unable to compute"
            
            table.setItem(i, 3, QTableWidgetItem(data_range))
        
        # Adjust column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)

    def _collect_metadata(self):
        """Collect all metadata as text"""
        info = []
        
        if self.data_type == 'radar':
            radar = self.radar
            
            info.append("RADAR METADATA")
            info.append("="*60)
            info.append("\nRadar Object Metadata:")
            for key, val in radar.metadata.items():
                if isinstance(val, bytes):
                    val = val.decode()
                info.append(f"  {key}: {val}")
            
            info.append("\n\nCoordinate Information:")
            for coord in ['latitude', 'longitude', 'altitude']:
                if hasattr(radar, coord):
                    coord_data = getattr(radar, coord)
                    info.append(f"\n{coord.upper()}:")
                    for key, val in coord_data.items():
                        if key != 'data':
                            info.append(f"  {key}: {val}")
            
        elif self.data_type == 'grid':
            grid = self.gridded_data
            
            info.append("GRID METADATA")
            info.append("="*60)
            info.append("\nGrid Object Metadata:")
            for key, val in grid.metadata.items():
                info.append(f"  {key}: {val}")
            
        elif self.data_type == 'xarray':
            ds = self.gridded_data
            
            info.append("XARRAY DATASET METADATA")
            info.append("="*60)
            info.append("\nGlobal Attributes:")
            for key, val in ds.attrs.items():
                info.append(f"  {key}: {val}")
            
            info.append("\n\nVariable Details:")
            for var in ds.data_vars:
                info.append(f"\n{var}:")
                info.append(f"  Shape: {ds[var].shape}")
                info.append(f"  Dtype: {ds[var].dtype}")
                info.append(f"  Attributes:")
                for attr_key, attr_val in ds[var].attrs.items():
                    info.append(f"    {attr_key}: {attr_val}")
        
        return "\n".join(info)
    
    def on_quick_cmap_changed(self, index):
        """Handle quick colormap selection"""
        if self.current_field and self.radar:
            cmap = self.cmap_combo.itemData(index)
            self.settings.set_field_setting(self.current_field, 'cmap', cmap)
            self.update_plot()
    
    def on_quick_vmin_changed(self, value):
        """Handle quick vmin change"""
        if self.current_field and self.radar:
            self.settings.set_field_setting(self.current_field, 'vmin', value)
    
    def on_quick_vmax_changed(self, value):
        """Handle quick vmax change"""
        if self.current_field and self.radar:
            self.settings.set_field_setting(self.current_field, 'vmax', value)
    
    def reset_quick_settings(self):
        """Reset quick settings for current field"""
        if self.current_field and self.radar:
            self.settings.reset_field_settings(self.current_field)
            
            # Update the UI controls
            default_info = get_field_info(self.radar, self.current_field)
            default_vmin, default_vmax = default_info[1], default_info[2]
            
            self.vmin_spin.setValue(default_vmin)
            self.vmax_spin.setValue(default_vmax)
            self.cmap_combo.setCurrentIndex(0)  # Default
            
            self.update_plot()
    
    def _on_canvas_resize(self, event):
        """Handle canvas resize events"""
        if self.radar and event.width > 100 and event.height > 100:
            self._resize_timer.start(300)  # 300ms debounce
    
    def _handle_resize(self):
        """Update plots after resize with debouncing"""
        if self.radar:
            self.update_plot()
    
    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        if self._resize_timer and self.radar:
            self._resize_timer.start(300)  # 300ms debounce
            
    def create_separator(self, orientation='vertical'):
        """Create a separator line"""
        separator = QFrame()
        if orientation == 'vertical':
            separator.setFrameShape(QFrame.VLine)
        else:
            separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        return separator
            
    def create_control_panel(self):
        """Create the control panel with all UI elements in compact 2-row layout"""
        control_panel = QWidget()
        control_layout = QVBoxLayout(control_panel)  # Changed to vertical for rows
        
        # ===== ROW 1: File Loading and NEXRAD =====
        row1 = QWidget()
        row1_layout = QHBoxLayout(row1)
        
        # File selection (compact)
        self.load_button = QPushButton("Load Radar File")
        self.load_button.clicked.connect(self.load_radar_file)
        row1_layout.addWidget(self.load_button)
        row1_layout.addWidget(self.create_separator('vertical'))
        
        row1_layout.addWidget(QLabel("Realtime NEXRAD:"))
        
        # NEXRAD selection (more compact)
        self.site_combo = QComboBox()
        self.site_combo.setEditable(True)
        self.site_combo.setMaximumWidth(250)  # Limit width
        
        # Comprehensive NEXRAD site list GROUPED by state
        nexrad_sites_by_state = [
            ('━━━ Alabama ━━━', None),
            ('KBMX - Birmingham, AL', 'KBMX'),
            ('KEOX - Ft Rucker, AL', 'KEOX'),
            ('KHTX - Huntsville/Hytop, AL', 'KHTX'),
            ('KMXX - Maxwell AFB, AL', 'KMXX'),
            ('KMOB - Mobile, AL', 'KMOB'),
            
            ('━━━ Alaska ━━━', None),
            ('PAHG - Anchorage/Kenai, AK', 'PAHG'),
            ('PABC - Bethel, AK', 'PABC'),
            ('PACG - Biorka Island/Sitka, AK', 'PACG'),
            ('PAPD - Fairbanks/Pedro Dome, AK', 'PAPD'),
            ('PAKC - King Salmon, AK', 'PAKC'),
            ('PAIH - Middleton Island, AK', 'PAIH'),
            ('PAEC - Nome, AK', 'PAEC'),
            
            ('━━━ Arizona ━━━', None),
            ('KFSX - Flagstaff, AZ', 'KFSX'),
            ('KIWA - Phoenix, AZ', 'KIWA'),
            ('KEMX - Tucson, AZ', 'KEMX'),
            ('KYUX - Yuma, AZ', 'KYUX'),
            
            ('━━━ Arkansas ━━━', None),
            ('KSRX - Fort Smith, AR', 'KSRX'),
            ('KLZK - Little Rock, AR', 'KLZK'),
            
            ('━━━ California ━━━', None),
            ('KBBX - Beale AFB, CA', 'KBBX'),
            ('KEYX - Edwards AFB, CA', 'KEYX'),
            ('KBHX - Eureka, CA', 'KBHX'),
            ('KVTX - Los Angeles, CA', 'KVTX'),
            ('KDAX - Sacramento, CA', 'KDAX'),
            ('KNKX - San Diego, CA', 'KNKX'),
            ('KMUX - San Francisco, CA', 'KMUX'),
            ('KHNX - San Joaquin Valley, CA', 'KHNX'),
            ('KSOX - Santa Ana Mountains, CA', 'KSOX'),
            ('KVBX - Vandenberg AFB, CA', 'KVBX'),
            
            ('━━━ Colorado ━━━', None),
            ('KFTG - Denver, CO', 'KFTG'),
            ('KGJX - Grand Junction, CO', 'KGJX'),
            ('KPUX - Pueblo, CO', 'KPUX'),
            
            ('━━━ Delaware ━━━', None),
            ('KDOX - Dover AFB, DE', 'KDOX'),
            
            ('━━━ Florida ━━━', None),
            ('KJAX - Jacksonville, FL', 'KJAX'),
            ('KBYX - Key West, FL', 'KBYX'),
            ('KMLB - Melbourne, FL', 'KMLB'),
            ('KAMX - Miami, FL', 'KAMX'),
            ('KEVX - Northwest Florida/Eglin AFB, FL', 'KEVX'),
            ('KTLH - Tallahassee, FL', 'KTLH'),
            ('KTBW - Tampa Bay, FL', 'KTBW'),
            
            ('━━━ Georgia ━━━', None),
            ('KFFC - Atlanta, GA', 'KFFC'),
            ('KJGX - Robins AFB, GA', 'KJGX'),
            ('KVAX - Moody AFB, GA', 'KVAX'),
            
            ('━━━ Hawaii ━━━', None),
            ('PHKM - Kamuela/Kohala, HI', 'PHKM'),
            ('PHMO - Molokai, HI', 'PHMO'),
            ('PHKI - South Kauai, HI', 'PHKI'),
            ('PHWA - South Shore, HI', 'PHWA'),
            
            ('━━━ Idaho ━━━', None),
            ('KCBX - Boise, ID', 'KCBX'),
            ('KSFX - Pocatello, ID', 'KSFX'),
            
            ('━━━ Illinois ━━━', None),
            ('KLOT - Chicago, IL', 'KLOT'),
            ('KILX - Lincoln, IL', 'KILX'),
            
            ('━━━ Indiana ━━━', None),
            ('KVWX - Evansville, IN', 'KVWX'),
            ('KIND - Indianapolis, IN', 'KIND'),
            ('KIWX - Northern Indiana/North Webster, IN', 'KIWX'),
            
            ('━━━ Iowa ━━━', None),
            ('KDMX - Des Moines, IA', 'KDMX'),
            ('KDVN - Quad Cities/Davenport, IA', 'KDVN'),
            
            ('━━━ Kansas ━━━', None),
            ('KDDC - Dodge City, KS', 'KDDC'),
            ('KGLD - Goodland, KS', 'KGLD'),
            ('KTWX - Topeka, KS', 'KTWX'),
            ('KICT - Wichita, KS', 'KICT'),
            
            ('━━━ Kentucky ━━━', None),
            ('KHPX - Ft Campbell, KY', 'KHPX'),
            ('KJKL - Jackson, KY', 'KJKL'),
            ('KLVX - Louisville, KY', 'KLVX'),
            ('KPAH - Paducah, KY', 'KPAH'),
            
            ('━━━ Louisiana ━━━', None),
            ('KPOE - Ft Polk, LA', 'KPOE'),
            ('KLCH - Lake Charles, LA', 'KLCH'),
            ('KLIX - New Orleans, LA', 'KLIX'),
            ('KSHV - Shreveport, LA', 'KSHV'),
            
            ('━━━ Maine ━━━', None),
            ('KCBW - Caribou, ME', 'KCBW'),
            ('KGYX - Portland, ME', 'KGYX'),
            
            ('━━━ Massachusetts ━━━', None),
            ('KBOX - Boston, MA', 'KBOX'),
            
            ('━━━ Michigan ━━━', None),
            ('KDTX - Detroit, MI', 'KDTX'),
            ('KAPX - Gaylord, MI', 'KAPX'),
            ('KGRR - Grand Rapids, MI', 'KGRR'),
            ('KMQT - Marquette, MI', 'KMQT'),
            
            ('━━━ Minnesota ━━━', None),
            ('KDLH - Duluth, MN', 'KDLH'),
            ('KMPX - Minneapolis, MN', 'KMPX'),
            
            ('━━━ Mississippi ━━━', None),
            ('KGWX - Columbus AFB, MS', 'KGWX'),
            ('KDGX - Jackson, MS', 'KDGX'),
            
            ('━━━ Missouri ━━━', None),
            ('KEAX - Kansas City, MO', 'KEAX'),
            ('KSGF - Springfield, MO', 'KSGF'),
            ('KLSX - St Louis, MO', 'KLSX'),
            
            ('━━━ Montana ━━━', None),
            ('KBLX - Billings, MT', 'KBLX'),
            ('KGGW - Glasgow, MT', 'KGGW'),
            ('KTFX - Great Falls, MT', 'KTFX'),
            ('KMSX - Missoula, MT', 'KMSX'),
            
            ('━━━ Nebraska ━━━', None),
            ('KUEX - Hastings, NE', 'KUEX'),
            ('KLNX - North Platte, NE', 'KLNX'),
            ('KOAX - Omaha, NE', 'KOAX'),
            
            ('━━━ Nevada ━━━', None),
            ('KLRX - Elko, NV', 'KLRX'),
            ('KESX - Las Vegas, NV', 'KESX'),
            ('KRGX - Reno, NV', 'KRGX'),
            
            ('━━━ New Mexico ━━━', None),
            ('KABX - Albuquerque, NM', 'KABX'),
            ('KFDX - Cannon AFB, NM', 'KFDX'),
            ('KHDX - Holloman AFB, NM', 'KHDX'),
            
            ('━━━ New York ━━━', None),
            ('KENX - Albany, NY', 'KENX'),
            ('KBGM - Binghamton, NY', 'KBGM'),
            ('KBUF - Buffalo, NY', 'KBUF'),
            ('KTYX - Montague/Ft Drum, NY', 'KTYX'),
            ('KOKX - New York City/Upton, NY', 'KOKX'),
            
            ('━━━ North Carolina ━━━', None),
            ('KMHX - Morehead City, NC', 'KMHX'),
            ('KRAX - Raleigh/Durham, NC', 'KRAX'),
            ('KLTX - Wilmington, NC', 'KLTX'),
            
            ('━━━ North Dakota ━━━', None),
            ('KBIS - Bismarck, ND', 'KBIS'),
            ('KMVX - Grand Forks, ND', 'KMVX'),
            ('KMBX - Minot AFB, ND', 'KMBX'),
            
            ('━━━ Ohio ━━━', None),
            ('KILN - Cincinnati/Wilmington, OH', 'KILN'),
            ('KCLE - Cleveland, OH', 'KCLE'),
            
            ('━━━ Oklahoma ━━━', None),
            ('KFDR - Frederick/Altus AFB, OK', 'KFDR'),
            ('KTLX - Oklahoma City, OK', 'KTLX'),
            ('KINX - Tulsa, OK', 'KINX'),
            ('KVNX - Vance AFB, OK', 'KVNX'),
            
            ('━━━ Oregon ━━━', None),
            ('KMAX - Medford, OR', 'KMAX'),
            ('KPDT - Pendleton, OR', 'KPDT'),
            ('KRTX - Portland, OR', 'KRTX'),
            
            ('━━━ Pennsylvania ━━━', None),
            ('KCCX - State College, PA', 'KCCX'),
            ('KDIX - Philadelphia, PA', 'KDIX'),
            ('KPBZ - Pittsburgh, PA', 'KPBZ'),
            
            ('━━━ Puerto Rico ━━━', None),
            ('TJUA - San Juan, PR', 'TJUA'),
            
            ('━━━ South Carolina ━━━', None),
            ('KCAE - Columbia, SC', 'KCAE'),
            ('KCLX - Charleston, SC', 'KCLX'),
            ('KGSP - Greer, SC', 'KGSP'),
            
            ('━━━ South Dakota ━━━', None),
            ('KABR - Aberdeen, SD', 'KABR'),
            ('KUDX - Rapid City, SD', 'KUDX'),
            ('KFSD - Sioux Falls, SD', 'KFSD'),
            
            ('━━━ Tennessee ━━━', None),
            ('KMRX - Knoxville/Morristown, TN', 'KMRX'),
            ('KNQA - Memphis, TN', 'KNQA'),
            ('KOHX - Nashville, TN', 'KOHX'),
            
            ('━━━ Texas ━━━', None),
            ('KAMA - Amarillo, TX', 'KAMA'),
            ('KBRO - Brownsville, TX', 'KBRO'),
            ('KGRK - Central Texas/Ft Hood, TX', 'KGRK'),
            ('KCRP - Corpus Christi, TX', 'KCRP'),
            ('KDFX - Laughlin AFB, TX', 'KDFX'),
            ('KDYX - Dyess AFB, TX', 'KDYX'),
            ('KFWS - Ft Worth, TX', 'KFWS'),
            ('KHGX - Houston, TX', 'KHGX'),
            ('KLBB - Lubbock, TX', 'KLBB'),
            ('KMAF - Midland/Odessa, TX', 'KMAF'),
            ('KSJT - San Angelo, TX', 'KSJT'),
            ('KEWX - San Antonio, TX', 'KEWX'),
            
            ('━━━ Utah ━━━', None),
            ('KICX - Cedar City, UT', 'KICX'),
            ('KMTX - Salt Lake City, UT', 'KMTX'),
            
            ('━━━ Vermont ━━━', None),
            ('KCXX - Burlington, VT', 'KCXX'),
            
            ('━━━ Virginia ━━━', None),
            ('KFCX - Blacksburg, VA', 'KFCX'),
            ('KLWX - Sterling, VA', 'KLWX'),
            ('KAKQ - Wakefield, VA', 'KAKQ'),
            
            ('━━━ Washington ━━━', None),
            ('KLGX - Langley Hill, WA', 'KLGX'),
            ('KATX - Seattle, WA', 'KATX'),
            ('KOTX - Spokane, WA', 'KOTX'),
            
            ('━━━ West Virginia ━━━', None),
            ('KRLX - Charleston, WV', 'KRLX'),
            
            ('━━━ Wisconsin ━━━', None),
            ('KARX - La Crosse, WI', 'KARX'),
            ('KGRB - Green Bay, WI', 'KGRB'),
            ('KMKX - Milwaukee, WI', 'KMKX'),
            
            ('━━━ Wyoming ━━━', None),
            ('KCYS - Cheyenne, WY', 'KCYS'),
            ('KRIW - Riverton, WY', 'KRIW'),
            
            ('━━━ International ━━━', None),
            ('PGUA - Andersen AFB, Guam', 'PGUA'),
            ('RKSG - Camp Humphreys, KO', 'RKSG'),
            ('RODN - Kadena, JP', 'RODN'),
            ('RKJK - Kunsan, KO', 'RKJK'),
        ]
        
        # Add items to combo box with state headers disabled
        for display_name, site_code in nexrad_sites_by_state:
            self.site_combo.addItem(display_name, site_code)
            # Disable state header items so they can't be selected
            if site_code is None:
                index = self.site_combo.count() - 1
                item = self.site_combo.model().item(index)
                item.setEnabled(False)
                font = item.font()
                font.setBold(True)
                item.setFont(font)
        
        # Add placeholder text at the beginning
        self.site_combo.insertItem(0, "Select Radar Site", None)
        self.site_combo.model().item(0).setEnabled(False)  # Make placeholder unselectable
        self.site_combo.setCurrentIndex(0)
        
        row1_layout.addWidget(self.site_combo)
        
        self.nexrad_button = QPushButton("Load")
        self.nexrad_button.clicked.connect(self.load_nexrad_data)
        row1_layout.addWidget(self.nexrad_button)
        
        self.check_site_button = QPushButton("Check")
        self.check_site_button.clicked.connect(self.check_nexrad_site)
        row1_layout.addWidget(self.check_site_button)
        row1_layout.addWidget(self.create_separator('vertical'))

        # Radials toggle
        self.radials_checkbox = QCheckBox("Radials")
        self.radials_checkbox.setChecked(
            self.qsettings.value("display/show_radials", True, type=bool)
        )
        self.radials_checkbox.setToolTip("Show/hide radial lines (30° intervals)")
        self.radials_checkbox.stateChanged.connect(self.update_plot)
        self.radials_checkbox.stateChanged.connect(
            lambda: self.qsettings.setValue("display/show_radials", self.radials_checkbox.isChecked())
        )
        row1_layout.addWidget(self.radials_checkbox)
        
        # Range Rings toggle
        self.range_rings_checkbox = QCheckBox("Range Rings")
        self.range_rings_checkbox.setChecked(
            self.qsettings.value("display/show_range_rings", True, type=bool)
        )
        self.range_rings_checkbox.setToolTip("Show/hide range rings")
        self.range_rings_checkbox.stateChanged.connect(self.update_plot)
        self.range_rings_checkbox.stateChanged.connect(
            lambda: self.qsettings.setValue("display/show_range_rings", self.range_rings_checkbox.isChecked())
        )
        row1_layout.addWidget(self.range_rings_checkbox)
        
        # Range Ring Spacing control
        self.range_ring_spacing_spin = QSpinBox()
        self.range_ring_spacing_spin.setRange(10, 200)
        self.range_ring_spacing_spin.setValue(
            self.qsettings.value("display/range_ring_spacing", 50, type=int)
        )
        self.range_ring_spacing_spin.setSuffix(" km")
        self.range_ring_spacing_spin.setPrefix("@ ")
        self.range_ring_spacing_spin.setMaximumWidth(90)
        self.range_ring_spacing_spin.setToolTip("Range ring spacing interval")
        self.range_ring_spacing_spin.editingFinished.connect(self.update_plot)
        self.range_ring_spacing_spin.editingFinished.connect(
            lambda: self.qsettings.setValue("display/range_ring_spacing", 
                                            self.range_ring_spacing_spin.value())
        )
        row1_layout.addWidget(self.range_ring_spacing_spin)
        
        # Grid toggle
        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.setChecked(
            self.qsettings.value("display/show_grid", True, type=bool)
        )
        self.grid_checkbox.setToolTip("Show/hide coordinate grid lines")
        self.grid_checkbox.stateChanged.connect(self.update_plot)
        self.grid_checkbox.stateChanged.connect(
            lambda: self.qsettings.setValue("display/show_grid", self.grid_checkbox.isChecked())
        )
        row1_layout.addWidget(self.grid_checkbox)
        
        row1_layout.addStretch()
        control_layout.addWidget(row1)
        
        # ===== ROW 2: Display Controls =====
        row2 = QWidget()
        row2_layout = QHBoxLayout(row2)
        
        # Field selection
        row2_layout.addWidget(QLabel("Field:"))
        self.field_combo = QComboBox()
        self.field_combo.setMaximumWidth(120)
        self.field_combo.currentTextChanged.connect(self.on_field_changed)
        row2_layout.addWidget(self.field_combo)
        
        # Sweep selection
        row2_layout.addWidget(QLabel("Sweep:"))
        self.sweep_combo = QComboBox()
        self.sweep_combo.setMaximumWidth(120)
        self.sweep_combo.currentIndexChanged.connect(self.on_sweep_changed)
        row2_layout.addWidget(self.sweep_combo)
        
        # Max range control
        row2_layout.addWidget(QLabel("Range:"))
        self.range_spinner = QSpinBox()
        self.range_spinner.setRange(10, 500)
        self.range_spinner.setValue(150)
        self.range_spinner.setSuffix(" km")
        self.range_spinner.setMaximumWidth(80)
        self.range_spinner.editingFinished.connect(self.update_plot)
        row2_layout.addWidget(self.range_spinner)
        
        # Max height for RHI plots
        row2_layout.addWidget(QLabel("RHI Height:"))
        self.height_spinner = QSpinBox()
        self.height_spinner.setRange(1, 25)
        self.height_spinner.setValue(10)
        self.height_spinner.setSuffix(" km")
        self.height_spinner.setMaximumWidth(80)
        self.height_spinner.editingFinished.connect(self.update_plot)
        row2_layout.addWidget(self.height_spinner)
        
        # Plot type selection (Fast or Map)
        row2_layout.addWidget(QLabel("Plot:"))
        self.plot_type_combo = QComboBox()
        self.plot_type_combo.addItems(["Fast", "Map"])
        self.plot_type_combo.setCurrentText("Fast")
        self.plot_type_combo.setMaximumWidth(80)
        self.plot_type_combo.currentTextChanged.connect(self.on_plot_type_changed)
        row2_layout.addWidget(self.plot_type_combo)
        
        # Multi-field checkbox
        self.multifield_checkbox = QCheckBox("Multi-field")
        self.multifield_checkbox.setChecked(False)
        self.multifield_checkbox.stateChanged.connect(self.toggle_multifield_mode)
        row2_layout.addWidget(self.multifield_checkbox)
        
        # Select fields button
        self.field_selection_button = QPushButton("Select Fields")
        self.field_selection_button.clicked.connect(self.select_multiple_fields)
        self.field_selection_button.setEnabled(False)
        row2_layout.addWidget(self.field_selection_button)
        
        # Update and Save buttons
        plot_button = QPushButton("Update")
        plot_button.clicked.connect(self.update_plot)
        row2_layout.addWidget(plot_button)
        
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_plot)
        row2_layout.addWidget(save_button)
        
        row2_layout.addStretch()
        control_layout.addWidget(row2)
        
        self.layout.addWidget(control_panel)
        
    def toggle_multifield_mode(self, state):
        """Toggle between single field and multi-field modes"""
        self.multifield_mode = bool(state)
        self.field_selection_button.setEnabled(self.multifield_mode)
                
        # If turning off multi-field mode, reset to single field
        if not self.multifield_mode:
            self.selected_fields = []
        
        self.update_plot()
        
    def select_multiple_fields(self):
        """Open a dialog to select multiple fields for display"""
        if not self.radar:
            self.statusBar().showMessage("No radar data loaded")
            return
                
        dialog = QDialog(self)
        dialog.setWindowTitle("Select Fields")
        dialog.setGeometry(200, 200, 300, 400)  # Make dialog bigger
        dialog_layout = QVBoxLayout(dialog)
        
        # Create a list widget with checkboxes
        field_list = QListWidget()
        field_list.setSelectionMode(QAbstractItemView.MultiSelection)
        
        # Add all available fields
        for field in self.radar.fields.keys():
            field_list.addItem(field)
        
        # Pre-select any previously selected fields
        for i in range(field_list.count()):
            field_item = field_list.item(i)
            if field_item.text() in self.selected_fields:
                field_item.setSelected(True)
        
        dialog_layout.addWidget(field_list)
        
        # Add OK/Cancel buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        dialog_layout.addWidget(button_box)
        
        # Show dialog and process result
        if dialog.exec_() == QDialog.Accepted:
            self.selected_fields = [item.text() for item in field_list.selectedItems()]
                        
            # Ensure we have at least one field selected
            if not self.selected_fields:
                self.selected_fields = [self.current_field] if self.current_field else []
                
            self.statusBar().showMessage(f"Selected {len(self.selected_fields)} fields for display")
            self.update_plot()
        else:
            print("Field selection dialog cancelled")
            
    def get_system_dpi(self):
        """Get the system's actual DPI with platform-specific handling"""
        try:
            screen = QApplication.primaryScreen()
            logical_dpi = screen.logicalDotsPerInch()
            physical_dpi = screen.physicalDotsPerInch()
            device_ratio = screen.devicePixelRatio()
            
            system = platform.system()
                        
            # Use device_ratio to get effective DPI on macOS
            if system == "Darwin":  # macOS
                # On Retina displays, logical DPI is low (72) but device_ratio is 2.0
                # Effective DPI = logical_dpi * device_ratio
                dpi = int(logical_dpi * device_ratio)
            else:
                # Use logical DPI as it accounts for system display scaling
                dpi = int(logical_dpi)
            
            # Reasonable bounds to prevent extreme values
            dpi = max(72, min(dpi, 200))
            
            return dpi, device_ratio 
            
        except Exception as e:
            return 100, 1.0   # Safe fallback

    def update_plot(self):
        """Plot radar or gridded data with handling of sizing and cleanup"""
    
        # Check what type of data we have and if it's loaded
        if self.data_type == 'radar':
            if not self.radar:
                print("No radar data loaded")
                return
            data_obj = self.radar
        elif self.data_type in ['grid', 'xarray']:
            if not self.gridded_data:
                print("No gridded data loaded")
                return
            data_obj = self.gridded_data
        else:
            print("No valid data loaded")
            return
    
        # Check conditions for plotting
        has_current_field = bool(self.current_field)
        has_selected_fields = self.multifield_mode and bool(self.selected_fields)
    
        if not has_current_field and not has_selected_fields:
            print("No fields available for plotting")
            return
    
        try:
            # ==================== SIMPLE CLEARING (NO FANCY TRICKS) ====================
            plt.close('all')
            
            if hasattr(self, 'figure') and self.figure is not None:
                self.figure.clear()
                plt.close(self.figure)
                self.figure = None
            
            gc.collect()
            # ==================== END CLEARING ====================
                        
            max_range = self.range_spinner.value()
            mask_outside = True
            plot_fast = (self.plot_type_combo.currentText() == "Fast")
            max_height = self.height_spinner.value()
            
            # Get canvas size
            canvas_width_px = self.canvas.width()
            canvas_height_px = self.canvas.height()
            canvas_dpi, device_ratio = self.get_system_dpi()
                            
            # Handle different data types
            if self.data_type == 'radar':
                self._plot_radar_data(max_range, mask_outside, plot_fast, max_height, 
                                    canvas_width_px, canvas_height_px, canvas_dpi, device_ratio)
            elif self.data_type in ['grid', 'xarray']:
                self._plot_gridded_data(max_range, max_height, 
                                      canvas_width_px, canvas_height_px, canvas_dpi)
            
        except Exception as e:
            self.statusBar().showMessage(f"Error plotting: {str(e)}")
            print(f"Error in update_plot: {str(e)}")
            import traceback
            traceback.print_exc()
        
    def _plot_radar_data(self, max_range, mask_outside, plot_fast, max_height, 
                        canvas_width_px, canvas_height_px, canvas_dpi, device_ratio):
        """Plot radar data with automated layout"""
        
        # Check if in multi-field mode with selected fields
        if self.multifield_mode and self.selected_fields:
            # Force map mode for multi-field to avoid coordinate issues
            if plot_fast and self.scan_type == "PPI":
                plot_fast = False
            
            # CREATE LAYOUT MANAGER - handles all sizing automatically
            layout_mgr = LayoutManager(
                canvas_width_px, canvas_height_px, canvas_dpi, device_ratio,
                num_fields=len(self.selected_fields),
                platform_name=platform.system(),
                user_prefs=self.display_prefs,
                scan_type=self.scan_type
            )
            
            # Save for tuning dialog
            self._last_layout_mgr = layout_mgr
            
            # Get figure size from layout manager
            fig_width, fig_height = layout_mgr.get_figure_size()
                        
            # Create figure
            self.figure = plt.figure(figsize=(fig_width, fig_height), dpi=canvas_dpi)
            self.figure._viewer_prefs = self.display_prefs
            self.figure.patch.set_facecolor('white')
            self.figure.set_tight_layout(False)
            
            # Create subplots using layout manager
            axes, font_sizes = create_manual_subplots(self.figure, len(self.selected_fields), 
                                                     canvas_dpi, layout_mgr)
                        
            # Get info for overall title
            site, mydate, mytime, elv, _, _, _, _, _, _, _ = get_radar_info(self.radar, self.current_sweep)

            # Add title at calculated position
            title_y = layout_mgr.get_title_position()
            if title_y:
                self.figure.suptitle(
                    f'{site} {mydate} {mytime} UTC PPI Elev: {elv:.1f} deg',
                    fontsize=font_sizes['suptitle_fontsize'], 
                    fontweight='bold', 
                    y=title_y 
                )
            
            # Plot each field (this part stays the same)
            for idx, field in enumerate(self.selected_fields):
                if idx >= len(axes):
                    break
                    
                try:
                    ax = axes[idx]
                    
                    # Handle projections for cartopy
                    if self.scan_type == "PPI" and not plot_fast:
                        pos = ax.get_position()
                        ax.remove()
                        
                        radar_lat = self.radar.latitude['data'][0]
                        radar_lon = self.radar.longitude['data'][0]
                        projection = ccrs.LambertConformal(radar_lon, radar_lat)
                        
                        ax = self.figure.add_axes([pos.x0, pos.y0, pos.width, pos.height], 
                                                projection=projection)
                        axes[idx] = ax
                    
                    # Plot the field
                    plotter = RadarPlotter(
                        radar=self.radar,
                        scan_type=self.scan_type,
                        plot_fast=plot_fast,
                        max_range=max_range,
                        max_height=max_height,
                        mask_outside=mask_outside,
                        show_radials=self.radials_checkbox.isChecked(),
                        show_range_rings=self.range_rings_checkbox.isChecked(),
                        range_ring_spacing=self.range_ring_spacing_spin.value(),
                        show_grid=self.grid_checkbox.isChecked()                  
                    )
                    
                    if self.scan_type == "PPI":
                        if plot_fast:
                            plotter.plot_ppi_fast(field, self.current_sweep, ax, self.settings)
                        else:
                            projection = ccrs.LambertConformal(
                                self.radar.longitude['data'][0], 
                                self.radar.latitude['data'][0]
                            )
                            plotter.plot_ppi_cartopy(field, self.current_sweep, ax, projection, 
                            self.settings, self.annotation_manager, self.zoom_xlim, self.zoom_ylim )                    
                    else:
                        plotter.plot_rhi(field, self.current_sweep, ax, self.settings)
                    
                    fix_colorbar_height(ax)
                    
                    if len(self.selected_fields) > 1:
                        ax.set_title(field, fontsize=font_sizes['subtitle_fontsize'], fontweight='bold')
                    
                    if self.scan_type == "PPI":
                        try:
                            ax.set_aspect('equal')
                        except:
                            pass
                            
                except Exception as field_error:
                    print(f"Error plotting field {field}: {str(field_error)}")
                    import traceback
                    traceback.print_exc()
                    continue
            
            # ==================== APPLY ZOOM TO ALL AXES (NEW) ====================
            if self.scan_type == "PPI" and self.zoom_xlim is not None:
                for ax in axes:
                    try:
                        ax.set_xlim(self.zoom_xlim)
                        ax.set_ylim(self.zoom_ylim)
                    except:
                        pass
            
            apply_dpi_scaling_to_axes(axes, font_sizes)
            self.statusBar().showMessage(f"Displaying {len(self.selected_fields)} radar fields")
                      
        else:  # Single field mode
            # CREATE LAYOUT MANAGER for single field
            layout_mgr = LayoutManager(
                    canvas_width_px, canvas_height_px, canvas_dpi, device_ratio,
                    num_fields=1,
                    platform_name=platform.system(),
                    user_prefs=self.display_prefs,
                    scan_type=self.scan_type
             )
        
            # Save for tuning dialog
            self._last_layout_mgr = layout_mgr
        
            # Get figure size from layout manager
            fig_width, fig_height = layout_mgr.get_figure_size()
                    
            self.figure = plt.figure(figsize=(fig_width, fig_height), dpi=canvas_dpi)
            self.figure.patch.set_facecolor('white')
            
            # Get subplot position from layout manager
            positions = layout_mgr.get_subplot_positions()
            pos = positions[0]
            
            # Create axis
            if self.scan_type == "PPI" and not plot_fast:
                radar_lat = self.radar.latitude['data'][0]
                radar_lon = self.radar.longitude['data'][0]
                projection = ccrs.LambertConformal(radar_lon, radar_lat)
                ax = self.figure.add_axes(pos, projection=projection)
            else:
                ax = self.figure.add_axes(pos)
            
            # Plot the field
            plotter = RadarPlotter(
                radar=self.radar,
                scan_type=self.scan_type,
                plot_fast=plot_fast,
                max_range=max_range,
                max_height=max_height,
                mask_outside=mask_outside,
                show_radials=self.radials_checkbox.isChecked(),
                show_range_rings=self.range_rings_checkbox.isChecked(),
                range_ring_spacing=self.range_ring_spacing_spin.value(),
                show_grid=self.grid_checkbox.isChecked()   
            )
            
            if self.scan_type == "PPI":
                if plot_fast:
                    plotter.plot_ppi_fast(self.current_field, self.current_sweep, ax, self.settings)
                else:
                    projection = ccrs.LambertConformal(
                        self.radar.longitude['data'][0], 
                        self.radar.latitude['data'][0]
                    )
                    plotter.plot_ppi_cartopy(self.current_field, self.current_sweep, ax, projection, 
                         self.settings, self.annotation_manager, self.zoom_xlim, self.zoom_ylim)
            else:
                plotter.plot_rhi(self.current_field, self.current_sweep, ax, self.settings)
            
            if self.scan_type == "PPI":
                try:
                    ax.set_aspect('equal')
                except:
                    pass
            
            fix_colorbar_height(ax)
            
            # ==================== APPLY ZOOM (NEW) ====================
            if self.scan_type == "PPI" and self.zoom_xlim is not None:
                try:
                    ax.set_xlim(self.zoom_xlim)
                    ax.set_ylim(self.zoom_ylim)
                except:
                    pass
            
            # Update status
            mode = "Fast" if plot_fast else "Map"
            angle = self.radar.fixed_angle['data'][self.current_sweep]
            if self.scan_type == "PPI":
                self.statusBar().showMessage(
                    f"Displaying {self.current_field} - PPI Elevation: {angle:.1f}° ({mode})"
                )
            else:
                self.statusBar().showMessage(
                    f"Displaying {self.current_field} - RHI Azimuth: {angle:.1f}°"
                )
                
        # ==================== CONNECT NEW FIGURE TO CANVAS ====================
        # Store reference to old figure
        old_figure = self.canvas.figure
        
        # Set the new figure
        self.canvas.figure = self.figure
        
        # Clean up old figure AFTER setting new one
        if old_figure is not None and old_figure != self.figure:
            try:
                old_figure.clear()
                plt.close(old_figure)
                del old_figure  # Explicit deletion
            except:
                pass
        
        # Force garbage collection
        gc.collect()
        
        # Draw new figure - USE NON-BLOCKING DRAW
        self.canvas.draw_idle()  # ← CHANGED: Non-blocking prevents flicker
        
        # Single process events call
        QApplication.processEvents()

    def _plot_gridded_data(self, max_range, max_height, canvas_width_px, canvas_height_px, canvas_dpi):
        """Plot gridded data with automated layout"""
        
        if not self.current_field:
                print("No field selected for gridded data")
                return
        
        # CREATE LAYOUT MANAGER
        _, device_ratio = self.get_system_dpi()
        layout_mgr = LayoutManager(
                canvas_width_px, canvas_height_px, canvas_dpi, device_ratio,
                num_fields=1,
                platform_name=platform.system()  # ✓ FIXED - was 'platform'
        )
        
        # Save for tuning dialog
        self._last_layout_mgr = layout_mgr
        
        # Get figure size
        fig_width, fig_height = layout_mgr.get_figure_size()
                
        self.figure = plt.figure(figsize=(fig_width, fig_height), dpi=canvas_dpi)
        self.figure.patch.set_facecolor('white')
        
        # Determine projection
        use_projection = False
        projection = None
        
        if self.data_type == 'grid':
            try:
                use_projection = True
                origin_lat = self.gridded_data.origin_latitude['data'][0]
                origin_lon = self.gridded_data.origin_longitude['data'][0]
                projection = ccrs.LambertConformal(origin_lon, origin_lat)
            except Exception as e:
                use_projection = False
        
        elif self.data_type == 'xarray':
            try:
                has_latlon = ('lat' in self.gridded_data.coords and 'lon' in self.gridded_data.coords) or \
                            ('latitude' in self.gridded_data.coords and 'longitude' in self.gridded_data.coords)
                if has_latlon:
                    use_projection = True
                    if 'lat' in self.gridded_data.coords:
                        lat_center = float(self.gridded_data.coords['lat'].mean())
                        lon_center = float(self.gridded_data.coords['lon'].mean())
                    else:
                        lat_center = float(self.gridded_data.coords['latitude'].mean())
                        lon_center = float(self.gridded_data.coords['longitude'].mean())
                    projection = ccrs.LambertConformal(lon_center, lat_center)
            except:
                use_projection = False
        
        # Create subplot
        if use_projection and projection:
            ax = self.figure.add_subplot(111, projection=projection)
        else:
            ax = self.figure.add_subplot(111)
        
        # Create plotter and plot
        plotter = GriddedPlotter(
            data=self.gridded_data,
            data_type=self.data_type,
            max_range=max_range,
            max_height=max_height
        )
        
        if self.scan_type == "RHI":
            plotter.plot_grid_rhi(self.current_field, self.current_sweep, ax, self.settings)
        else:
            plotter.plot_grid_ppi(self.current_field, self.current_sweep, ax, self.settings)
        
        if self.scan_type == "PPI":
            try:
                ax.set_aspect('equal')
            except:
                pass
        
        # Update status
        if self.data_type == 'grid' and hasattr(self.gridded_data, 'z'):
            try:
                level_height = self.gridded_data.z['data'][self.current_sweep] / 1000.0
                self.statusBar().showMessage(
                    f"Displaying {self.current_field} - {self.data_type.upper()} Level {self.current_sweep}: {level_height:.1f} km"
                )
            except:
                self.statusBar().showMessage(
                    f"Displaying {self.current_field} - {self.data_type.upper()} Level: {self.current_sweep}"
                )
        else:
            self.statusBar().showMessage(
                f"Displaying {self.current_field} - {self.data_type.upper()} Level: {self.current_sweep}"
            )
        
        # Store reference to old figure
        old_figure = self.canvas.figure
        
        # Set the new figure
        self.canvas.figure = self.figure
        
        # Clean up old figure AFTER setting new one
        if old_figure is not None and old_figure != self.figure:
            try:
                old_figure.clear()
                plt.close(old_figure)
                del old_figure  # Explicit deletion
            except:
                pass
        
        # Force garbage collection
        gc.collect()
        
        # Draw new figure with full render
        self.canvas.draw()
        self.canvas.flush_events()
        
        # Ensure Qt processes the paint event
        self.canvas.update()
        QApplication.processEvents()
            
    def load_radar_file(self):
        """Open a file dialog to select a radar or gridded data file"""
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Radar/Grid File", "", 
            "Data Files (*.nc *.h5 *.mdv *.gz *.hdf5 *.cdf *_V06);;All Files (*)", 
            options=options
        )
    
        if file_path:
            try:
                self._loading = True
                self.statusBar().showMessage(f"Loading file: {file_path}")
            
                # Handle compressed files
                processed_file_path = file_path
                if file_path.endswith('.cf.gz'):
                    self.statusBar().showMessage(f"Decompressing gzipped file...")
                
                    with tempfile.NamedTemporaryFile(suffix='.nc', delete=False) as temp_file:
                        temp_path = temp_file.name
                
                    with gzip.open(file_path, 'rb') as f_in:
                        with open(temp_path, 'wb') as f_out:
                            shutil.copyfileobj(f_in, f_out)
                
                    processed_file_path = temp_path
                    self.statusBar().showMessage(f"Decompressed file, now loading...")
            
                # Determine file type
                file_ext = os.path.splitext(file_path)[1].lower()
                file_name = os.path.basename(file_path)
                
                # Check if D3R file
                is_d3r = 'D3R' in file_name.upper() or 'd3r' in file_name.lower()
                
                # Check if GAMIC file (NEW)
                is_gamic = any(x in file_name.upper() for x in ['GAMIC', 'LONGRANGE', 'HYDRO'])
                
                # Try different loading methods based on file type
                loaded_data = None
                data_type = None
                temp_file_created = False
                
                # Handle compressed .gz files
                if file_ext == '.gz' and not file_path.endswith('.cf.gz'):
                    self.statusBar().showMessage(f"Decompressing .gz file...")
                    processed_file_path = unzip_file(file_path)
                    temp_file_created = True
                    file_ext = '.nc'
                
                # D3R special handling
                if is_d3r and file_ext == '.nc':
                    try:
                        self.statusBar().showMessage(f"Loading as D3R radar data...")
                        loaded_data = pyart.aux_io.read_d3r_gcpex_nc(processed_file_path, 
                                                                      file_field_names=True, 
                                                                      read_altitude_from_nc=True)
                        data_type = 'radar'
                        self.statusBar().showMessage(f"Loaded as D3R Radar object")
                    except Exception as e:
                        print(f"Failed to load as D3R: {e}")
                
                # ==================== GAMIC H5 SPECIAL HANDLING (NEW) ====================
                elif is_gamic and file_ext == '.h5':
                    try:
                        self.statusBar().showMessage(f"Loading as GAMIC HDF5 radar data...")
                        loaded_data = pyart.aux_io.read_gamic(processed_file_path, 
                                                              file_field_names=True)
                        data_type = 'radar'
                        self.statusBar().showMessage(f"Loaded as GAMIC Radar object")
                    except Exception as e:
                        print(f"Failed to load as GAMIC: {e}")
                
                # ODIM H5 special handling (try after GAMIC)
                elif file_ext == '.h5' and not is_gamic:
                    try:
                        self.statusBar().showMessage(f"Loading as ODIM H5 radar data...")
                        loaded_data = pyart.aux_io.read_odim_h5(processed_file_path, file_field_names=True)
                        loaded_data = reorder_sweeps(loaded_data)
                        data_type = 'radar'
                        self.statusBar().showMessage(f"Loaded as ODIM H5 Radar object")
                    except Exception as e:
                        # If ODIM fails, try GAMIC as fallback
                        try:
                            self.statusBar().showMessage(f"Trying GAMIC format...")
                            loaded_data = pyart.aux_io.read_gamic(processed_file_path, 
                                                                  file_field_names=True)
                            data_type = 'radar'
                            self.statusBar().showMessage(f"Loaded as GAMIC Radar object")
                        except Exception as e2:
                            print(f"Failed to load as GAMIC: {e2}")
                
                # HDF5 with header removal
                elif file_ext == '.hdf5':
                    try:
                        self.statusBar().showMessage(f"Loading .hdf5 file (removing header)...")
                        temp_cleaned = remove_HDF_header(processed_file_path)
                        loaded_data = pyart.aux_io.read_odim_h5(temp_cleaned, file_field_names=True)
                        loaded_data = reorder_sweeps(loaded_data)
                        
                        # Clean up temp file and directory
                        os.remove(temp_cleaned)
                        temp_dir = os.path.dirname(temp_cleaned)
                        try:
                            os.rmdir(temp_dir)
                        except:
                            pass
                        
                        data_type = 'radar'
                        self.statusBar().showMessage(f"Loaded as HDF5 Radar object")
                    except Exception as e:
                        print(f"Failed to load as HDF5: {e}")
                
                # Standard PyART loading if not handled above
                if loaded_data is None:
                    try:
                        # Try as radar with file_field_names
                        loaded_data = pyart.io.read(processed_file_path, file_field_names=True)
                        data_type = 'radar'
                        self.statusBar().showMessage(f"Loaded as PyART Radar object")
                    except:
                        try:
                            # Try as grid
                            loaded_data = pyart.io.read_grid(processed_file_path)
                            data_type = 'grid'
                            self.statusBar().showMessage(f"Loaded as PyART Grid object")
                        except:
                            pass
            
                # If PyART fails, try xarray
                if loaded_data is None:
                    try:
                        import xarray as xr
                        loaded_data = xr.open_dataset(processed_file_path)
                        data_type = 'xarray'
                        self.statusBar().showMessage(f"Loaded as xarray Dataset")
                    except Exception as e:
                        self.statusBar().showMessage(f"Failed to load with xarray: {e}")
            
                if data_type in ['grid', 'xarray']:
                    detected_scan_type = detect_gridded_scan_type(loaded_data, data_type)
                    self.scan_type = detected_scan_type
                    
                    if detected_scan_type == "TIME-HEIGHT":
                        # For profilers, "max range" doesn't make sense, but max height does
                        self.range_spinner.setEnabled(False)  # Disable range control
                        self.range_spinner.setToolTip("Range control disabled for profiler data")
            
                if loaded_data is None:
                    self.statusBar().showMessage(f"Could not load file: {file_path}")
                    self._loading = False
                    return
            
                # Store the data based on type
                if data_type == 'radar':
                    self.radar = loaded_data
                    self.gridded_data = None
                    
                    # NEXRAD split-cut merging
                    if self.radar.metadata.get('original_container') == 'NEXRAD Level II':
                        self.statusBar().showMessage(f"Merging NEXRAD split cuts...")
                        try:
                            self.radar = merge_split_cuts(self.radar)
                            self.statusBar().showMessage(f"Split cuts merged successfully")
                        except Exception as e:
                            self.statusBar().showMessage(f"Warning: Could not merge split cuts")
                else:
                    self.radar = None
                    self.gridded_data = loaded_data
            
                self.data_type = data_type
            
                # Clean up temp file if created
                if temp_file_created:
                    try:
                        os.remove(processed_file_path)
                    except:
                        pass
            
                self.statusBar().showMessage(f"File loaded as {data_type}: {file_path}")
                self.update_field_list()
                self.update_sweep_list()
                self.detect_scan_type()
                self.update_ui_for_data_type()
                self._loading = False
                self.update_plot()
            
            except Exception as e:
                self._loading = False
                self.statusBar().showMessage(f"Error loading file: {str(e)}")
                print(f"Error details: {e}")
                import traceback
                traceback.print_exc()
                
    def load_nexrad_data(self):
        """Load the latest NEXRAD data for selected site"""
        # Extract the 4-letter site code from the combo box data
        site_code = self.site_combo.currentData()
        
        # If user typed manually, try to parse it
        if site_code is None:
            site_text = self.site_combo.currentText().upper()
            # Try to extract 4-letter code (K*** or P*** or R*** or T***)
            parts = site_text.split()
            for part in parts:
                if len(part) == 4 and part[0] in ['K', 'P', 'R', 'T']:
                    site_code = part
                    break
            
            if not site_code:
                site_code = site_text[:4] if len(site_text) >= 4 else site_text
        
        site = site_code.upper()
        
        if len(site) != 4:
            QMessageBox.warning(self, "Invalid Site", "Please select or enter a valid NEXRAD site")
            return
        
        # Disable button during download
        self.nexrad_button.setEnabled(False)
        self.nexrad_button.setText("Downloading...")
        
        # Create and start download thread
        self.download_thread = NexradDownloader(site, num_files=1)
        self.download_thread.progress.connect(self.update_download_progress)
        self.download_thread.finished.connect(self.nexrad_download_finished)
        self.download_thread.error.connect(self.nexrad_download_error)
        self.download_thread.start()
    
    def update_download_progress(self, message):
        """Update status bar with download progress"""
        self.statusBar().showMessage(message)
    
    def nexrad_download_finished(self, file_path):
        """Handle successful NEXRAD download"""
        try:
            self._loading = True  # START: Prevent cascading updates
            self.statusBar().showMessage(f"Processing downloaded NEXRAD file...")
        
            # Handle the bz2 extension issue for PyART
            processed_file_path = file_path
        
            if file_path.endswith('.bz2'):
                # PyART expects .bz not .bz2
                new_path = file_path[:-1]  # Remove the '2' from '.bz2'
                os.rename(file_path, new_path)
                processed_file_path = new_path
        
            self.statusBar().showMessage(f"Loading NEXRAD file...")
        
            # Use the enhanced loading logic
            loaded_data = None
            data_type = None
        
            # Try PyART first (NEXRAD should always be radar data)
            try:
                loaded_data = pyart.io.read(processed_file_path)
                data_type = 'radar'
                self.statusBar().showMessage(f"Loaded NEXRAD as PyART Radar object")
            except Exception as radar_error:
                print(f"Failed to load NEXRAD as radar: {radar_error}")
                # For NEXRAD, we don't expect it to be anything other than radar data
                raise radar_error
        
            if loaded_data is None:
                self.statusBar().showMessage(f"Could not load NEXRAD file: {processed_file_path}")
                return
        
            # Store the data based on type
            if data_type == 'radar':
                self.radar = loaded_data
                self.gridded_data = None
                    
                # NEXRAD split-cut merging
                if self.radar.metadata.get('original_container') == 'NEXRAD Level II':
                    self.statusBar().showMessage(f"Merging NEXRAD split cuts...")
                    try:
                        self.radar = merge_split_cuts(self.radar)
                        self.statusBar().showMessage(f"Split cuts merged successfully")
                    except Exception as e:
                        print(f"Could not merge split cuts: {e}")
                        self.statusBar().showMessage(f"Warning: Could not merge split cuts")
            else:
                self.radar = None
                self.gridded_data = loaded_data
            
            self.data_type = data_type
        
            # Clean up temp file
            try:
                os.remove(processed_file_path)
            except:
                print(f"Could not remove temp file: {processed_file_path}")
        
            self.statusBar().showMessage(f"NEXRAD file loaded successfully from {os.path.basename(file_path)}")
            self.update_field_list()
            self.update_sweep_list()
            self.detect_scan_type()
            self.update_ui_for_data_type()
            self._loading = False  # END: Re-enable updates
            
            # Now do ONE final plot update
            self.update_plot()
        
        except Exception as e:
            self._loading = False  # Re-enable on error
            self.statusBar().showMessage(f"Error loading NEXRAD file: {str(e)}")
            print(f"Error details: {str(e)}")
            import traceback
            traceback.print_exc()
        finally:
            self.nexrad_button.setEnabled(True)
            self.nexrad_button.setText("Load Latest NEXRAD")
    
    def nexrad_download_error(self, error_message):
        """Handle NEXRAD download errors"""
        QMessageBox.critical(self, "Download Error", error_message)
        self.statusBar().showMessage("NEXRAD download failed")
        self.nexrad_button.setEnabled(True)
        self.nexrad_button.setText("Load Latest NEXRAD")
        
    def clear_all_data(self):
        """Clear all loaded data and reset the viewer"""
        
        # Ask for confirmation
        reply = QMessageBox.question(
                self, 
                'Clear All Data', 
                'Are you sure you want to clear all loaded data?\n\nThis will close all plots and reset the viewer.',
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.No
        )
        
        if reply == QMessageBox.No:
                return
        
        try:
                # ==================== CLEAR PLOT DATA ====================
                if hasattr(self, 'figure') and self.figure:
                        self.figure.clear()
                        plt.close(self.figure)
                        self.figure = None
                
                # Close all matplotlib figures
                plt.close('all')
                
                # ==================== RECREATE CANVAS TO CLEAR GHOSTS ====================
                if hasattr(self, 'canvas') and self.canvas:
                    # Remove old canvas
                    self.layout.removeWidget(self.canvas)
                    
                    if self.canvas.figure:
                        plt.close(self.canvas.figure)
                    
                    self.canvas.deleteLater()
                    QApplication.processEvents()
                    gc.collect()
                    
                    # Create fresh canvas
                    self.figure = plt.figure(figsize=(12, 8), dpi=100)
                    self.canvas = FigureCanvas(self.figure)
                    self.canvas.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
                    self.canvas.setUpdatesEnabled(True)
                    self.canvas.setMinimumSize(400, 300)
                    self.canvas.setStyleSheet("background-color: white;")
                    self.figure.patch.set_facecolor('white')
                    self.canvas.setFocusPolicy(Qt.StrongFocus)
                    
                    # Add back to layout
                    self.layout.addWidget(self.canvas, stretch=1)
                    
                    # Reconnect resize handler
                    self.canvas.mpl_connect('resize_event', self._on_canvas_resize)
                    
                    QApplication.processEvents()
                # ==================== END CANVAS RECREATION ====================
                
                # ==================== CLEAR RADAR/GRID DATA ====================
                self.radar = None
                self.gridded_data = None
                self.data_type = None
                
                # ==================== RESET FIELD/SWEEP DATA ====================
                self.current_field = None
                self.current_sweep = 0
                self.scan_type = "PPI"
                self.multifield_mode = False
                self.selected_fields = []
                
                # ==================== CLEAR LAYOUT MANAGER ====================
                if hasattr(self, '_last_layout_mgr'):
                        self._last_layout_mgr = None
                
                # ==================== CLEAR CACHES ====================
                if hasattr(self, '_field_list_cache'):
                        self._field_list_cache = {}
                
                # ==================== RESET UI ELEMENTS ====================
                self.field_combo.clear()
                self.sweep_combo.clear()
                self.multifield_checkbox.setChecked(False)
                self.field_selection_button.setEnabled(False)
                
                # Reset spinners to defaults
                self.range_spinner.setValue(150)
                self.height_spinner.setValue(10)
                
                # Reset quick settings
                if hasattr(self, 'vmin_spin'):
                        self.vmin_spin.setValue(0)
                        self.vmax_spin.setValue(70)
                        self.cmap_combo.setCurrentIndex(0)
                
                # ==================== UPDATE STATUS ====================
                self.statusBar().showMessage("All data cleared - Canvas recreated")
                                
        except Exception as e:
                self.statusBar().showMessage(f"Error clearing data: {str(e)}")
                print(f"Error in clear_all_data: {e}")
                import traceback
                traceback.print_exc()
    
    # ==================== ZOOM METHODS ====================

    def toggle_zoom_mode(self, checked):
        """Toggle zoom mode on/off"""
        if self.scan_type != "PPI":
            self.zoom_action.setChecked(False)
            self.statusBar().showMessage("Zoom only available for PPI plots")
            return
        
        if not self.figure or not hasattr(self.figure, 'axes') or len(self.figure.axes) == 0:
            self.zoom_action.setChecked(False)
            self.statusBar().showMessage("No plot available to zoom")
            return
        
        self.zoom_enabled = checked
        
        if checked:
            self.statusBar().showMessage("Zoom mode ON - Click and drag on plot to draw zoom box")
            
            # Disconnect old handlers if they exist
            if hasattr(self, '_zoom_press_cid'):
                try:
                    self.canvas.mpl_disconnect(self._zoom_press_cid)
                    self.canvas.mpl_disconnect(self._zoom_motion_cid)
                    self.canvas.mpl_disconnect(self._zoom_release_cid)
                except:
                    pass
            
            # Connect manual event handlers
            self._zoom_press_cid = self.canvas.mpl_connect('button_press_event', 
                                                            self._on_zoom_press)
            self._zoom_motion_cid = self.canvas.mpl_connect('motion_notify_event', 
                                                             self._on_zoom_motion)
            self._zoom_release_cid = self.canvas.mpl_connect('button_release_event', 
                                                              self._on_zoom_release)
            
            # Initialize zoom drawing state
            self._zoom_start = None
            self._zoom_rect = None
            self._zoom_ax = None
            self._zoom_last_update = None
                            
        else:
            self.statusBar().showMessage("Zoom mode OFF")
            
            # Disconnect handlers
            if hasattr(self, '_zoom_press_cid'):
                try:
                    self.canvas.mpl_disconnect(self._zoom_press_cid)
                    self.canvas.mpl_disconnect(self._zoom_motion_cid)
                    self.canvas.mpl_disconnect(self._zoom_release_cid)
                except:
                    pass
                
                # Clean up attributes
                for attr in ['_zoom_press_cid', '_zoom_motion_cid', '_zoom_release_cid',
                           '_zoom_start', '_zoom_rect', '_zoom_ax', '_zoom_last_update']:
                    if hasattr(self, attr):
                        delattr(self, attr)
            
            # Clean up any drawn rectangle
            if hasattr(self, '_zoom_rect') and self._zoom_rect:
                try:
                    self._zoom_rect.remove()
                except:
                    pass
                self._zoom_rect = None
                self.canvas.draw_idle()
                            
    def _on_zoom_press(self, event):
        """Mouse press - start drawing zoom box"""
        if not self.zoom_enabled:
            return
        
        if event.inaxes is None or event.xdata is None or event.ydata is None:
            return
        
        # Check if we clicked on a plot axis (not colorbar)
        if hasattr(event.inaxes, 'get_label') and 'colorbar' in event.inaxes.get_label():
            return
        
        self._zoom_start = (event.xdata, event.ydata)
        self._zoom_ax = event.inaxes
        self._zoom_last_update = (event.xdata, event.ydata)
        
    def _on_zoom_motion(self, event):
        """Mouse motion - update zoom box (throttled for performance)"""
        if not self.zoom_enabled or self._zoom_start is None:
            return
        
        if event.inaxes != self._zoom_ax or event.xdata is None or event.ydata is None:
            return
        
        # ==================== THROTTLE UPDATES FOR PERFORMANCE ====================
        # Only update if mouse moved significantly (reduces drawing overhead)
        if hasattr(self, '_zoom_last_update') and self._zoom_last_update is not None:
            last_x, last_y = self._zoom_last_update
            dx = abs(event.xdata - last_x)
            dy = abs(event.ydata - last_y)
            
            # Auto-detect coordinate type and set appropriate threshold
            if max(abs(event.xdata), abs(event.ydata)) < 1000:
                threshold = 0.005  # ~500m in degrees
            else:
                threshold = 1000  # 1000 meters for x-y coordinates
            
            # Skip this update if movement is too small
            if dx < threshold and dy < threshold:
                return
            
            self._zoom_last_update = (event.xdata, event.ydata)
        
        # Remove old rectangle if it exists
        if self._zoom_rect:
            try:
                self._zoom_rect.remove()
            except:
                pass
            self._zoom_rect = None
        
        # Draw new rectangle with lightweight styling
        x0, y0 = self._zoom_start
        width = event.xdata - x0
        height = event.ydata - y0
        
        from matplotlib.patches import Rectangle
        self._zoom_rect = Rectangle(
            (x0, y0), width, height,
            fill=False,  # No fill = faster drawing
            edgecolor='yellow',
            alpha=0.9,
            linewidth=2,
            linestyle='-',  # Solid line is faster than dashed
            transform=self._zoom_ax.transData,
            zorder=1000
        )
        self._zoom_ax.add_patch(self._zoom_rect)
        
        # ==================== FORCE IMMEDIATE UPDATE ====================
        self.canvas.draw_idle()
        self.canvas.flush_events()
        QApplication.processEvents()
        
    def _on_zoom_release(self, event):
        """Mouse release - apply zoom"""
        if not self.zoom_enabled or self._zoom_start is None:
            return
        
        if event.inaxes != self._zoom_ax or event.xdata is None or event.ydata is None:
            # Clean up - zoom cancelled
            if self._zoom_rect:
                try:
                    self._zoom_rect.remove()
                except:
                    pass
                self._zoom_rect = None
            
            self.canvas.draw_idle()
            self._zoom_start = None
            return
        
        # Get zoom box coordinates
        x0, y0 = self._zoom_start
        x1, y1 = event.xdata, event.ydata
                
        # ==================== SMART BOX SIZE CHECK ====================
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        
        # Determine coordinate type
        if max(abs(x0), abs(x1), abs(y0), abs(y1)) < 1000:
            min_size = 0.01  # Degrees
            coord_type = "degrees"
        else:
            min_size = 1000  # Meters
            coord_type = "meters"
                
        if dx < min_size or dy < min_size:
            # Box too small - cancel zoom
            if self._zoom_rect:
                try:
                    self._zoom_rect.remove()
                except:
                    pass
                self._zoom_rect = None
            
            self.canvas.draw_idle()
            self._zoom_start = None
            self.statusBar().showMessage(
                f"Zoom box too small (minimum {min_size} {coord_type}), zoom cancelled"
            )
            return
        
        # Set zoom limits
        self.zoom_xlim = sorted([x0, x1])
        self.zoom_ylim = sorted([y0, y1])
                
        # Clean up rectangle
        if self._zoom_rect:
            try:
                self._zoom_rect.remove()
            except:
                pass
            self._zoom_rect = None
        
        self._zoom_start = None
        self._zoom_ax = None
        
        # Disable zoom mode
        self.zoom_enabled = False
        self.zoom_action.setChecked(False)
        
        # Redraw with zoom applied
        self.update_plot()
        
        self.statusBar().showMessage(
            f"Zoomed to X=[{self.zoom_xlim[0]:.2f}, {self.zoom_xlim[1]:.2f}], "
            f"Y=[{self.zoom_ylim[0]:.2f}, {self.zoom_ylim[1]:.2f}]"
        )
        
    def reset_zoom(self):
        """Reset zoom to full view"""
        self.zoom_xlim = None
        self.zoom_ylim = None
        self.zoom_enabled = False
        self.zoom_action.setChecked(False)
    
        # Clean up any drawn zoom rectangle
        if hasattr(self, '_zoom_rect') and self._zoom_rect:
            try:
                self._zoom_rect.remove()
            except:
                pass
            self._zoom_rect = None
    
        # Clean up zoom event handlers if they exist
        if hasattr(self, '_zoom_press_cid'):
            try:
                self.canvas.mpl_disconnect(self._zoom_press_cid)
                self.canvas.mpl_disconnect(self._zoom_motion_cid)
                self.canvas.mpl_disconnect(self._zoom_release_cid)
            except:
                pass
        
            # Remove attributes
            for attr in ['_zoom_press_cid', '_zoom_motion_cid', '_zoom_release_cid',
                         '_zoom_start', '_zoom_ax', '_zoom_last_update']:
                if hasattr(self, attr):
                    delattr(self, attr)
    
        # Redraw plot at full zoom
        if self.radar or self.gridded_data:
            self.update_plot()
    
        self.statusBar().showMessage("Zoom reset to full view")
            
    def update_field_list(self):
        """Update the field dropdown with available fields"""
        self.field_combo.clear()
        
        if self.data_type == 'radar' and self.radar:
            # Radar data
            for field in self.radar.fields.keys():
                self.field_combo.addItem(field)
            
            # Set default field
            default_fields = ['CZ', 'DBZH', 'Reflectivity', 'TH', 'reflectivity', 'DBZ', 'corrected_reflectivity', 'DZ']
            for field in default_fields:
                index = self.field_combo.findText(field)
                if index >= 0:
                    self.field_combo.setCurrentIndex(index)
                    self.current_field = field
                    break
        
        elif self.data_type in ['grid', 'xarray'] and self.gridded_data:
            # ==================== FILTER GRIDDED DATA FIELDS ====================
            # Get only plottable fields (exclude metadata)
            plottable_fields = get_plottable_fields(self.gridded_data, self.data_type)
                        
            for field in plottable_fields:
                self.field_combo.addItem(field)
            # ==================== END FILTER ====================
            
            # Set default field for gridded data
            default_fields = ['reflectivity', 'reflectivity_factor', 'DBZ', 'REFL', 'dbz', 'refl', 
                             'signal_to_noise_ratio']
            for field in default_fields:
                index = self.field_combo.findText(field)
                if index >= 0:
                    self.field_combo.setCurrentIndex(index)
                    self.current_field = field
                    break
        
        # If no default field was found, use the first one
        if not self.current_field and self.field_combo.count() > 0:
            self.current_field = self.field_combo.currentText()

    def update_sweep_list(self):
        """Update the sweep dropdown with available levels/sweeps"""
        self.sweep_combo.clear()
        
        if self.data_type == 'radar' and self.radar:
            # Radar data - use existing logic
            for i in range(len(self.radar.sweep_number['data'])):
                if self.scan_type == "PPI":
                    angle = self.radar.fixed_angle['data'][i]
                    self.sweep_combo.addItem(f"Sweep {i}: {angle:.1f}°")
                else:  # RHI
                    angle = self.radar.fixed_angle['data'][i]
                    self.sweep_combo.addItem(f"Azimuth {i}: {angle:.1f}°")
        
        elif self.data_type == 'grid' and self.gridded_data:
            # PyART Grid - use z levels
            n_levels = self.gridded_data.nz
            for i in range(n_levels):
                height = self.gridded_data.z['data'][i] / 1000.0  # Convert to km
                self.sweep_combo.addItem(f"Level {i}: {height:.1f} km")
        
        elif self.data_type == 'xarray' and self.gridded_data:
            # ==================== XARRAY DATASET ====================
            
            # Check if this is TIME-HEIGHT profiler data
            if self.scan_type == "TIME-HEIGHT":
                # For time-height data, "sweeps" are time indices
                # Just show a single entry since we plot the entire time series
                self.sweep_combo.addItem("Full Time Series")
                self.current_sweep = 0
                return
            
            # Check if this is RHI data with sweep dimension
            if self.scan_type == "RHI" and 'sweep' in self.gridded_data.dims:
                # RHI with multiple sweeps (azimuths)
                n_sweeps = self.gridded_data.sizes['sweep']
                for i in range(n_sweeps):
                    if 'sweep' in self.gridded_data.coords:
                        try:
                            sweep_val = float(self.gridded_data.coords['sweep'][i].values)
                            self.sweep_combo.addItem(f"Azimuth {i}: {sweep_val:.1f}°")
                        except:
                            self.sweep_combo.addItem(f"Azimuth {i}")
                    else:
                        self.sweep_combo.addItem(f"Azimuth {i}")
                
                # ==================== EARLY RETURN - Don't continue to vertical dims ====================
                self.current_sweep = 0
                return
            
            # ==================== NOT RHI - Handle as vertical levels ====================
            # Find vertical dimension
            vertical_dims = ['z', 'level', 'height', 'altitude', 'lev']
            vertical_dim = None
            
            for dim in vertical_dims:
                if dim in self.gridded_data.dims:
                    vertical_dim = dim
                    break
            
            if vertical_dim:
                # Has a vertical dimension
                n_levels = self.gridded_data.sizes[vertical_dim]
                for i in range(n_levels):
                    if vertical_dim in self.gridded_data.coords:
                        try:
                            coord_val = float(self.gridded_data.coords[vertical_dim][i].values)
                            self.sweep_combo.addItem(f"Level {i}: {coord_val:.1f}")
                        except:
                            self.sweep_combo.addItem(f"Level {i}")
                    else:
                        self.sweep_combo.addItem(f"Level {i}")
            else:
                # No clear vertical dimension, try to find any 3D structure
                if self.gridded_data.data_vars:
                    first_var = list(self.gridded_data.data_vars.keys())[0]
                    var_dims = self.gridded_data[first_var].dims
                    
                    if len(var_dims) > 2:
                        # Find the non-spatial dimension
                        non_spatial = [d for d in var_dims if d not in ['x', 'y', 'lon', 'lat', 'longitude', 'latitude']]
                        if non_spatial:
                            dim_size = self.gridded_data.sizes[non_spatial[0]]
                            for i in range(dim_size):
                                self.sweep_combo.addItem(f"Index {i}")
                        else:
                            # Only 2D data
                            self.sweep_combo.addItem("Level 0")
                    else:
                        # 2D data only
                        self.sweep_combo.addItem("Level 0")
                else:
                    # No data variables found
                    self.sweep_combo.addItem("Level 0")
        
        self.current_sweep = 0
    
    def detect_scan_type(self):
        """Try to detect if this is a PPI or RHI scan"""
        if not self.radar:
            return
            
        # Check scan_type attribute if it exists
        if hasattr(self.radar, 'scan_type'):
            if self.radar.scan_type == 'ppi':
                self.scan_type = "PPI"
                #self.scan_combo.setCurrentText("PPI")
            elif self.radar.scan_type == 'rhi':
                self.scan_type = "RHI"
                #self.scan_combo.setCurrentText("RHI")
        
        # If not defined, try to determine from sweep info
        elif hasattr(self.radar, 'sweep_mode'):
            modes = self.radar.sweep_mode['data']
            if modes.size > 0:
                # Check if any sweep mode indicates RHI
                for mode in modes:
                    if isinstance(mode, bytes):
                        mode = mode.decode('utf-8')
                    if 'rhi' in mode.lower():
                        self.scan_type = "RHI"
                        self.scan_combo.setCurrentText("RHI")
                        break
    
    def on_field_changed(self, field_name):
        """Handle field selection change"""
        self.current_field = field_name
        
        # Update quick settings controls if toolbar exists
        if hasattr(self, 'vmin_spin') and field_name:
            if self.data_type == 'radar' and self.radar:
                default_info = get_field_info(self.radar, field_name)
            elif self.data_type == 'grid' and self.gridded_data:
                default_info = get_grid_field_info(self.gridded_data, field_name)
            elif self.data_type == 'xarray' and self.gridded_data:
                default_info = get_xarray_field_info(self.gridded_data, field_name)
            else:
                default_info = ('Unknown', 0, 70, 'viridis', field_name, 0)
            
            default_vmin, default_vmax = default_info[1], default_info[2]
            
            # Get custom settings if available
            custom_vmin = self.settings.get_field_setting(field_name, 'vmin', default_vmin)
            custom_vmax = self.settings.get_field_setting(field_name, 'vmax', default_vmax)
            custom_cmap = self.settings.get_field_setting(field_name, 'cmap')
            
            # Update the controls
            self.vmin_spin.setValue(custom_vmin)
            self.vmax_spin.setValue(custom_vmax)
            
            if custom_cmap:
                index = self.cmap_combo.findData(custom_cmap)
                if index >= 0:
                    self.cmap_combo.setCurrentIndex(index)
                else:
                    self.cmap_combo.setCurrentIndex(0)  # Default
            else:
                self.cmap_combo.setCurrentIndex(0)  # Default
        
        # Only update plot if not currently loading
        if not self._loading:
            self.update_plot()
    
    def on_sweep_changed(self, index):
        """Handle sweep selection change"""
        self.current_sweep = index
        
        # Only update plot if not currently loading
        if not self._loading:
            self.update_plot()
        
    def on_plot_type_changed(self, plot_type):
        """Handle plot type selection change between Fast and Map"""
        self.update_plot()
        
    def save_plot(self):
        """Save the current plot as an image file"""
        
        # Check if any data is loaded
        if not self.radar and not self.gridded_data:
            self.statusBar().showMessage("No data loaded")
            return
        
        # ==================== SMART DEFAULT FILENAME ====================
        # Generate a descriptive default filename
        default_name = "plot.png"
        
        try:
            if self.radar:
                # Radar data - use site and field name
                site = "UNKNOWN"
                if 'instrument_name' in self.radar.metadata:
                    site = str(self.radar.metadata['instrument_name'])
                    if isinstance(site, bytes):
                        site = site.decode()
                
                # Get date/time
                try:
                    radar_time = pyart.util.datetime_from_radar(self.radar)
                    time_str = radar_time.strftime('%Y%m%d_%H%M%S')
                except:
                    time_str = "unknown_time"
                
                # Build filename
                field = self.current_field if self.current_field else "field"
                scan = self.scan_type
                default_name = f"{site}_{field}_{scan}_{time_str}.png"
                
            elif self.gridded_data:
                # Gridded data - use scan type and field
                field = self.current_field if self.current_field else "field"
                scan = self.scan_type
                
                # Try to get time from data
                time_str = "unknown_time"
                if self.data_type == 'xarray':
                    if 'time' in self.gridded_data.coords:
                        try:
                            import pandas as pd
                            first_time = pd.Timestamp(self.gridded_data.coords['time'].values[0])
                            time_str = first_time.strftime('%Y%m%d_%H%M%S')
                        except:
                            pass
                    
                    # Try to get location info
                    location = "unknown"
                    try:
                        if 'latitude' in self.gridded_data.data_vars or 'latitude' in self.gridded_data.coords:
                            lat = float(self.gridded_data['latitude'].values)
                            lon = float(self.gridded_data['longitude'].values)
                            location = f"{lat:.2f}N_{lon:.2f}E"
                    except:
                        pass
                    
                    default_name = f"{scan}_{field}_{location}_{time_str}.png"
                else:
                    default_name = f"{scan}_{field}_{time_str}.png"
            
            # Clean up filename (remove spaces, special chars)
            default_name = default_name.replace(' ', '_').replace('/', '_').replace(':', '_')
            
        except Exception as e:
            print(f"Error generating filename: {e}")
            default_name = "plot.png"
        # ==================== END SMART FILENAME ====================
        
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Plot", default_name,  # ← Use smart default
            "PNG Files (*.png);;PDF Files (*.pdf);;JPEG Files (*.jpg);;All Files (*)", 
            options=options
        )
        
        if file_path:
            try:
                # Auto-detect format from extension
                if not any(file_path.endswith(ext) for ext in ['.png', '.pdf', '.jpg', '.jpeg']):
                    file_path += '.png'
                
                # Save with high quality
                self.figure.savefig(file_path, dpi=300, bbox_inches='tight', 
                                   facecolor='white', edgecolor='none')
                self.statusBar().showMessage(f"Plot saved to {file_path}")
            except Exception as e:
                self.statusBar().showMessage(f"Error saving plot: {str(e)}")
                print(f"Save error details: {e}")
                import traceback
                traceback.print_exc()
            
    def check_nexrad_site(self):
        """Check if a NEXRAD site has current data"""
        # Extract the 4-letter site code from the combo box data
        site_code = self.site_combo.currentData()
        
        # If user typed manually, try to parse it
        if site_code is None:
            site_text = self.site_combo.currentText().upper()
            parts = site_text.split()
            for part in parts:
                if len(part) == 4 and part[0] in ['K', 'P', 'R', 'T']:
                    site_code = part
                    break
            
            if not site_code:
                site_code = site_text[:4] if len(site_text) >= 4 else site_text
        
        site = site_code.upper()
        
        if len(site) != 4:
            QMessageBox.warning(self, "Invalid Site", "Please select or enter a valid NEXRAD site")
            return
        
        try:
            self.statusBar().showMessage(f"Checking site {site}...")
            url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/radar/nexrad_level2/{site}/dir.list"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                lines = response.text.strip().split('\n')
                file_count = 0
                recent_files = []
                
                for line in lines:
                    line = line.strip()
                    if line and len(line.split()) >= 2:
                        file_count += 1
                        filename = line.split()[-1]
                        if filename.endswith('.gz') or filename.endswith('.bz2') or '_V06' in filename:
                            recent_files.append(filename)
                
                if recent_files:
                    msg = f"✅ Site {site} is accessible!\n"
                    msg += f"Found {len(recent_files)} data files\n"
                    msg += f"Most recent: {recent_files[-1] if recent_files else 'None'}"
                    QMessageBox.information(self, "Site Check - Success", msg)
                else:
                    msg = f"⚠️ Site {site} is accessible but no radar data files found\n"
                    msg += f"Directory has {file_count} entries but no .gz/.bz2 files"
                    QMessageBox.warning(self, "Site Check - No Data", msg)
                
                self.statusBar().showMessage(f"Site check complete for {site}")
                
            else:
                QMessageBox.warning(self, "Site Check - Error", 
                                  f"❌ Site {site} returned HTTP status {response.status_code}\n"
                                  f"This site may not exist or be offline.")
                self.statusBar().showMessage(f"Site {site} check failed")
                
        except requests.exceptions.Timeout:
            QMessageBox.critical(self, "Site Check - Timeout", 
                               f"⏱️ Timeout connecting to {site}\nServer may be slow or unreachable")
        except requests.exceptions.ConnectionError:
            QMessageBox.critical(self, "Site Check - Connection Error", 
                               f"🌐 Connection error\nCheck your internet connection")
        except Exception as e:
            QMessageBox.critical(self, "Site Check - Error", f"Error checking site {site}:\n{str(e)}")
            self.statusBar().showMessage("Site check failed")
            
class GriddedPlotter:
    """Class to handle gridded data plotting (PyART Grids and xarray) with RHI support"""
    
    def __init__(self, data, data_type, max_range=150, max_height=10):
        self.data = data
        self.data_type = data_type
        self.max_range = max_range
        self.max_height = max_height
        self._cache = PlottingCache()
    
    def plot_grid_ppi(self, field, level, ax, settings=None):
        """Plot gridded data at a specific level with map background or RHI/Time-Height if applicable"""
        
        # ==================== DETECT SCAN TYPE ====================
        scan_type = detect_gridded_scan_type(self.data, self.data_type)
        
        if scan_type == "RHI":
            # This is RHI data, redirect to RHI plotting
            print(f"Detected RHI gridded data, using RHI plot method")
            self.plot_xarray_rhi(field, level, ax, settings)
            return
        
        # ==================== TIME-HEIGHT ROUTING ====================
        elif scan_type == "TIME-HEIGHT":
            # This is MRR/profiler data, redirect to time-height plotting
            print(f"Detected TIME-HEIGHT profiler data, using time-height plot method")
            self.plot_time_height(field, level, ax, settings)
            return
        # ==================== END ROUTING ====================
        
        # ==================== PPI PLOTTING ====================
        if self.data_type == 'grid':
            # PyART Grid object
            
            units, vmin, vmax, cmap, _, Nbins = get_grid_field_info(self.data, field)
            
            # Apply custom settings if available
            if settings:
                custom_vmin = settings.get_field_setting(field, 'vmin')
                custom_vmax = settings.get_field_setting(field, 'vmax')
                custom_cmap = settings.get_field_setting(field, 'cmap')
                
                if custom_vmin is not None:
                    vmin = custom_vmin
                if custom_vmax is not None:
                    vmax = custom_vmax
                if custom_cmap:
                    if custom_cmap in _GV_COLORMAPS:
                        cmap = _GV_COLORMAPS[custom_cmap]
                    else:
                        try:
                            cmap = custom_cmap
                        except:
                            pass
            
            # Apply discrete colormap if needed
            if Nbins > 0:
                cmap = discrete_cmap(Nbins, base_cmap=cmap)
                        
            # Get time for title
            try:
                if hasattr(self.data, 'time') and isinstance(self.data.time, dict):
                    grid_time = self.data.time['data'][0]
                    if hasattr(grid_time, 'strftime'):
                        time_str = grid_time.strftime('%m/%d/%Y %H:%M:%S UTC')
                    else:
                        time_str = str(grid_time)
                else:
                    time_str = 'Unknown Time'
            except:
                time_str = 'Unknown Time'
            
            title = f'{field} - Level {level} - {time_str}'
            
            # Get origin and calculate extent
            origin_lat = self.data.origin_latitude['data'][0]
            origin_lon = self.data.origin_longitude['data'][0]
            
            x = self.data.x['data'] / 1000.0  # km
            y = self.data.y['data'] / 1000.0  # km
            
            meters_to_lat = 1.0 / 111177.0
            meters_to_lon = 1.0 / (111177.0 * np.cos(np.radians(origin_lat)))
            
            min_lon = origin_lon + (x.min() * 1000.0 * meters_to_lon)
            max_lon = origin_lon + (x.max() * 1000.0 * meters_to_lon)
            min_lat = origin_lat + (y.min() * 1000.0 * meters_to_lat)
            max_lat = origin_lat + (y.max() * 1000.0 * meters_to_lat)
            
            
            # ==================== ADD BASE MAP FEATURES FIRST ====================
            try:
                COUNTIES, STATES, REEFS, MINOR_ISLANDS = self._cache.get_map_features()
                
                ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor="#414141", zorder=0)
                ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='black', 
                              edgecolor='none', zorder=0)
                ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor="#414141", 
                              edgecolor='white', linewidth=0.25, zorder=1)
                
                if MINOR_ISLANDS:
                    ax.add_feature(MINOR_ISLANDS, facecolor='#3d3d3d', edgecolor='white', 
                                  linewidth=0.3, zorder=2)
                
                
            except Exception as e:
                print(f"   ⚠️ Could not add base map features: {e}")
            
            # ==================== PLOT GRID DATA MANUALLY ====================
            # PyART's plot_grid() is unreliable with projections - do it manually
            
            try:
                # Get the data for this level
                data = self.data.fields[field]['data'][level, :, :]
                                
                # Convert grid coordinates to lat/lon
                # x and y are in km, need to convert to degrees
                lon_grid = origin_lon + (x * 1000.0 * meters_to_lon)
                lat_grid = origin_lat + (y * 1000.0 * meters_to_lat)
                
                # Create 2D coordinate arrays
                LON, LAT = np.meshgrid(lon_grid, lat_grid)
                                
                # Plot using pcolormesh with explicit PlateCarree transform
                im = ax.pcolormesh(LON, LAT, data,
                                  transform=ccrs.PlateCarree(),
                                  cmap=cmap, 
                                  vmin=vmin, 
                                  vmax=vmax,
                                  shading='auto',
                                  zorder=10)
                
                # Add colorbar
                cb = plt.colorbar(im, ax=ax, label=units, pad=0.02, shrink=0.9)
                
                # Set extent
                ax.set_extent([min_lon, max_lon, min_lat, max_lat], crs=ccrs.PlateCarree())
                
            except Exception as e:
                print(f"   ❌ Manual plotting failed: {e}")
                import traceback
                traceback.print_exc()
            
            # ==================== ADD BOUNDARIES ON TOP ====================
            try:
                COUNTIES, STATES, REEFS, MINOR_ISLANDS = self._cache.get_map_features()
                
                ax.coastlines(resolution='50m', linewidth=0.5, color='white', zorder=100)
                ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor='white', zorder=100)
                ax.add_feature(STATES, linewidth=0.3, edgecolor='white', zorder=100)
                
                if REEFS:
                    ax.add_feature(REEFS, facecolor='none', edgecolor='cyan', 
                                  linewidth=0.4, zorder=100, alpha=0.8)
                
                if COUNTIES:
                    ax.add_feature(COUNTIES, facecolor='none', edgecolor='white', 
                                  linewidth=0.25, zorder=100)
                
                # Grid lines
                gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', 
                                 alpha=0.5, linestyle='--', zorder=150)
                gl.top_labels = False
                gl.right_labels = False
                gl.xformatter = LONGITUDE_FORMATTER
                gl.yformatter = LATITUDE_FORMATTER
                                
            except Exception as e:
                print(f"   ⚠️ Could not add boundaries: {e}")
            
            # Add title
            ax.set_title(title, fontsize=10, fontweight='bold')
                        
        elif self.data_type == 'xarray':
            # xarray Dataset - PPI
            self.plot_xarray_ppi(field, level, ax, settings)
    
    def plot_xarray_ppi(self, field, level, ax, settings=None):
        """Plot xarray PPI data at a specific level with map background"""
                
        if field not in self.data.data_vars:
            print(f"   ❌ Field '{field}' not found in data vars!")
            ax.text(0.5, 0.5, f'Field {field} not found', 
                   transform=ax.transAxes, ha='center', va='center')
            return
                
        # Get field info
        units, vmin, vmax, cmap, title, _ = get_xarray_field_info(self.data, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                if custom_cmap in _GV_COLORMAPS:
                    cmap = _GV_COLORMAPS[custom_cmap]
                else:
                    try:
                        cmap = custom_cmap
                    except:
                        pass
    
        # Select the data at the specified level
        data_var = self.data[field]
        
        # Try to determine which dimension represents vertical levels
        vertical_dims = ['z', 'level', 'height', 'altitude', 'lev']
        vertical_dim = None
        for dim in vertical_dims:
            if dim in data_var.dims:
                vertical_dim = dim
                break
        
        if vertical_dim and data_var.sizes[vertical_dim] > level:
            plot_data = data_var.isel({vertical_dim: level})
        else:
            if len(data_var.dims) > 2:
                non_spatial_dims = [d for d in data_var.dims if d not in ['x', 'y', 'lon', 'lat']]
                if non_spatial_dims:
                    plot_data = data_var.isel({non_spatial_dims[0]: min(level, data_var.sizes[non_spatial_dims[0]]-1)})
                else:
                    plot_data = data_var
            else:
                plot_data = data_var
        
        # If plot_data still has more than 2 dimensions, squeeze or select first index
        while len(plot_data.shape) > 2:
            # Find the dimension with size 1 and squeeze it, or take first index
            squeezed = False
            for dim in plot_data.dims:
                if plot_data.sizes[dim] == 1:
                    plot_data = plot_data.squeeze(dim)
                    squeezed = True
                    break
            
            if not squeezed:
                # If no dimension has size 1, take first index of first dimension
                first_dim = plot_data.dims[0]
                plot_data = plot_data.isel({first_dim: 0})
                print(f"   Selected first index of: {first_dim}")
        
        # Check if we have lat/lon coordinates
        has_latlon = False
        lon_name = None
        lat_name = None
        
        for ln in ['lon', 'longitude', 'x']:
            if ln in plot_data.coords or ln in self.data.coords:
                lon_name = ln
                break
        
        for lt in ['lat', 'latitude', 'y']:
            if lt in plot_data.coords or lt in self.data.coords:
                lat_name = lt
                break
        
        has_latlon = (lon_name is not None and lat_name is not None)
                
        # Create the plot
        try:
            if has_latlon and hasattr(ax, 'projection'):
                # Geographic coordinates with projection
                if lon_name in plot_data.coords:
                    lons = plot_data.coords[lon_name].values
                    lats = plot_data.coords[lat_name].values
                else:
                    lons = self.data.coords[lon_name].values
                    lats = self.data.coords[lat_name].values
                
                # Check if coordinates are in meters instead of degrees
                if lons.max() > 360 or lons.min() < -180 or abs(lons.max()) > 10000:
                    
                    # Try to find actual lat/lon if they exist as variables
                    if 'latitude' in self.data.data_vars and 'longitude' in self.data.data_vars:
                        actual_lats = self.data['latitude'].values
                        actual_lons = self.data['longitude'].values
                        
                        if actual_lats.size > 1:
                            lats = actual_lats
                            lons = actual_lons
                
                extent = [lons.min(), lons.max(), lats.min(), lats.max()]
                
                # Get data values and mask fill values
                data_vals = plot_data.values
                
                # Mask common fill values
                data_vals = np.ma.masked_where(data_vals < -30000, data_vals)
                data_vals = np.ma.masked_invalid(data_vals)  # Also mask NaN/Inf
                                
                # For 2D lat/lon arrays (like your 801x801), use pcolormesh instead of imshow
                if len(lons.shape) == 2 and len(lats.shape) == 2:
                    im = ax.pcolormesh(lons, lats, data_vals,
                                      transform=ccrs.PlateCarree(),
                                      cmap=cmap, vmin=vmin, vmax=vmax,
                                      shading='nearest', zorder=5)
                else:
                    # 1D coordinates - create meshgrid for pcolormesh                    
                    # Create 2D coordinate arrays from 1D
                    LON, LAT = np.meshgrid(lons, lats)
                    
                    # Use pcolormesh which respects pixel boundaries better
                    im = ax.pcolormesh(LON, LAT, data_vals,
                                      transform=ccrs.PlateCarree(),
                                      cmap=cmap, 
                                      vmin=vmin, 
                                      vmax=vmax,
                                      shading='nearest',
                                      zorder=10)
                                        
                    # Set extent to match data bounds
                    lon_spacing = (lons[-1] - lons[0]) / (len(lons) - 1) if len(lons) > 1 else 0.1
                    lat_spacing = (lats[-1] - lats[0]) / (len(lats) - 1) if len(lats) > 1 else 0.1
                    
                    extent = [
                        lons[0] - lon_spacing/2,
                        lons[-1] + lon_spacing/2,
                        lats[0] - lat_spacing/2,
                        lats[-1] + lat_spacing/2
                    ]
                    
                ax.set_extent(extent, crs=ccrs.PlateCarree())
                
                # Add map features
                try:
                    ax.coastlines(resolution='50m', linewidth=0.5, color='white', zorder=10)
                    ax.add_feature(cfeature.BORDERS, linewidth=0.5, edgecolor='white', zorder=10)
                    ax.add_feature(cfeature.STATES, linewidth=0.3, edgecolor='white', zorder=10)
                    ax.add_feature(cfeature.LAND.with_scale('50m'), facecolor='black', 
                                   edgecolor='none', zorder=0)
                    ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor="#414141", zorder=0)
                    ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor="#414141", 
                                  edgecolor='white', linewidth=0.25, zorder=1)
                    
                    gl = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', 
                                     alpha=0.5, linestyle='--', zorder=15)
                    gl.top_labels = False
                    gl.right_labels = False
                    gl.xformatter = LONGITUDE_FORMATTER
                    gl.yformatter = LATITUDE_FORMATTER
                    
                except Exception as e:
                    print(f"   Could not add map features: {e}")
                
                # Add colorbar
                cb = plt.colorbar(im, ax=ax, label=units, pad=0.02)
                
            else:
                # No geographic coordinates - use xarray's built-in plotting
                if len(plot_data.dims) == 2:
                    im = plot_data.plot.imshow(
                        ax=ax, 
                        cmap=cmap, 
                        vmin=vmin, 
                        vmax=vmax,
                        add_colorbar=True, 
                        cbar_kwargs={'label': units}
                    )
                else:
                    im = plot_data.plot.pcolormesh(
                        ax=ax, 
                        cmap=cmap, 
                        vmin=vmin, 
                        vmax=vmax,
                        add_colorbar=True, 
                        cbar_kwargs={'label': units}
                    )
            
            ax.set_title(f'{title} - Level {level}', fontsize=10, fontweight='bold')
            
        except Exception as e:
            print(f"   ❌ ERROR plotting xarray data: {e}")
            import traceback
            traceback.print_exc()
            ax.text(0.5, 0.5, f'Error plotting {field}\n{str(e)}', 
                   transform=ax.transAxes, ha='center', va='center')    
                   
    def plot_xarray_rhi(self, field, sweep_index, ax, settings=None):
        """Plot xarray RHI data (height vs range)"""
        
        if field not in self.data.data_vars:
            ax.text(0.5, 0.5, f'Field {field} not found', 
                   transform=ax.transAxes, ha='center', va='center')
            return
        
        # Get field info
        units, vmin, vmax, cmap, title, _ = get_xarray_field_info(self.data, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                if custom_cmap in _GV_COLORMAPS:
                    cmap = _GV_COLORMAPS[custom_cmap]
                else:
                    try:
                        cmap = custom_cmap
                    except:
                        pass
        
        # Get the data variable
        data_var = self.data[field]
        
        # Select the sweep
        if 'sweep' in data_var.dims:
            if sweep_index < data_var.sizes['sweep']:
                plot_data = data_var.isel(sweep=sweep_index)
            else:
                plot_data = data_var.isel(sweep=0)
        else:
            plot_data = data_var
        
        # Get coordinates - try different naming conventions
        z_coord = None
        x_coord = None
        
        for z_name in ['z', 'height', 'altitude', 'Z', 'HEIGHT']:
            if z_name in plot_data.coords:
                z_coord = plot_data.coords[z_name]
                break
            elif z_name in self.data.coords:
                z_coord = self.data.coords[z_name]
                break
        
        for x_name in ['x', 'range', 'distance', 'X', 'RANGE']:
            if x_name in plot_data.coords:
                x_coord = plot_data.coords[x_name]
                break
            elif x_name in self.data.coords:
                x_coord = self.data.coords[x_name]
                break
        
        if z_coord is None or x_coord is None:
            ax.text(0.5, 0.5, f'Could not find z/x coordinates for RHI\nDims: {list(plot_data.dims)}\nCoords: {list(plot_data.coords)}', 
                   transform=ax.transAxes, ha='center', va='center', fontsize=8)
            return
        
        # Convert to km if needed
        z_vals = z_coord.values
        x_vals = x_coord.values
        
        # Check if values are in meters (typically > 100) and convert to km
        if z_vals.max() > 100:  # Likely in meters
            z_vals = z_vals / 1000.0
            z_label = 'Height (km)'
        else:
            z_label = 'Height (km)'
        
        if x_vals.max() > 100:  # Likely in meters
            x_vals = x_vals / 1000.0
            x_label = 'Range (km)'
        else:
            x_label = 'Range (km)'
        
        # Create the plot
        try:
            # Get data values
            data_vals = plot_data.values
            
            # Handle different dimension orders
            if data_vals.shape[0] == len(z_vals) and data_vals.shape[1] == len(x_vals):
                # Data is (z, x) - correct orientation
                plot_vals = data_vals
            elif data_vals.shape[0] == len(x_vals) and data_vals.shape[1] == len(z_vals):
                # Data is (x, z) - transpose needed
                plot_vals = data_vals.T
            else:
                # Shape mismatch - try to plot anyway
                print(f"Warning: Data shape {data_vals.shape} doesn't match coords z={len(z_vals)}, x={len(x_vals)}")
                plot_vals = data_vals
            
            # Use pcolormesh for better control
            im = ax.pcolormesh(x_vals, z_vals, plot_vals,
                              cmap=cmap, vmin=vmin, vmax=vmax,
                              shading='auto')
            
            # Set labels
            ax.set_xlabel(x_label, fontsize=10)
            ax.set_ylabel(z_label, fontsize=10)
            
            # Set limits
            ax.set_xlim([0, min(x_vals.max(), self.max_range)])
            ax.set_ylim([0, min(z_vals.max(), self.max_height)])
            
            # Add colorbar
            cb = plt.colorbar(im, ax=ax, label=units, pad=0.02)
            
            # Add title
            sweep_info = f"Sweep {sweep_index}" if 'sweep' in data_var.dims else ""
            
            # Try to get azimuth info if available
            if 'sweep' in self.data.coords and sweep_index < len(self.data.coords['sweep']):
                try:
                    sweep_val = float(self.data.coords['sweep'][sweep_index].values)
                    sweep_info = f"Azimuth: {sweep_val:.1f}°"
                except:
                    pass
            
            ax.set_title(f'{title} {sweep_info}', fontsize=10, fontweight='bold')
            
            # Set background
            ax.set_facecolor('black')
            
            # Add grid
            ax.grid(True, color='white', linestyle=':', linewidth=0.5, alpha=0.5)
            
        except Exception as e:
            print(f"Error plotting xarray RHI: {e}")
            import traceback
            traceback.print_exc()
            ax.text(0.5, 0.5, f'Error plotting {field}\n{str(e)}', 
                   transform=ax.transAxes, ha='center', va='center')
    
    def plot_grid_rhi(self, field, azimuth_index, ax, settings=None):
        """Plot RHI-like cross-section for gridded data"""
        
        # Check if this is xarray RHI data
        if self.data_type == 'xarray':
            scan_type = detect_gridded_scan_type(self.data, self.data_type)
            if scan_type == "RHI":
                # Use the specialized xarray RHI method
                self.plot_xarray_rhi(field, azimuth_index, ax, settings)
                return
        
        # PyART Grid cross-section (existing code)
        if self.data_type == 'grid':
            units, vmin, vmax, cmap, _, Nbins = get_grid_field_info(self.data, field)
            
            if settings:
                custom_vmin = settings.get_field_setting(field, 'vmin')
                custom_vmax = settings.get_field_setting(field, 'vmax')
                custom_cmap = settings.get_field_setting(field, 'cmap')
                
                if custom_vmin is not None:
                    vmin = custom_vmin
                if custom_vmax is not None:
                    vmax = custom_vmax
                if custom_cmap:
                    if custom_cmap in _GV_COLORMAPS:
                        cmap = _GV_COLORMAPS[custom_cmap]
                    else:
                        try:
                            cmap = custom_cmap
                        except:
                            pass
            
            if Nbins > 0:
                cmap = discrete_cmap(Nbins, base_cmap=cmap)
            
            display = pyart.graph.GridMapDisplay(self.data)
            
            azimuths = np.linspace(0, 360, 36)
            azimuth = azimuths[azimuth_index % len(azimuths)]
            
            title = f'{field} Cross-section - Azimuth: {azimuth:.1f}°'
            
            try:
                display.plot_cross_section(
                    field, [0, 0], [self.max_range * 1000, 0],
                    ax=ax, vmin=vmin, vmax=vmax, cmap=cmap,
                    colorbar_label=units, title=title
                )
            except:
                ax.text(0.5, 0.5, f'Cross-section not available for {field}', 
                       transform=ax.transAxes, ha='center', va='center')
        else:
            ax.text(0.5, 0.5, f'RHI not implemented for this data type', 
                   transform=ax.transAxes, ha='center', va='center')
                   
    def plot_time_height(self, field, time_index, ax, settings=None):
        """Plot time-height cross-section for MRR/profiler data"""
        
        if field not in self.data.data_vars:
            ax.text(0.5, 0.5, f'Field {field} not found', 
                   transform=ax.transAxes, ha='center', va='center')
            return
        
        # Get field info
        units, vmin, vmax, cmap, title, _ = get_xarray_field_info(self.data, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                if custom_cmap in _GV_COLORMAPS:
                    cmap = _GV_COLORMAPS[custom_cmap]
                else:
                    try:
                        cmap = custom_cmap
                    except:
                        pass
        
        # Get the data variable
        data_var = self.data[field]
        
        # Check dimensions
        if 'time' not in data_var.dims:
            ax.text(0.5, 0.5, f'{field} does not have time dimension', 
                   transform=ax.transAxes, ha='center', va='center')
            return
        
        # Find range/height dimension
        height_dim = None
        for dim_name in ['range', 'height', 'altitude', 'z']:
            if dim_name in data_var.dims:
                height_dim = dim_name
                break
        
        if height_dim is None:
            ax.text(0.5, 0.5, f'{field} does not have height/range dimension', 
                   transform=ax.transAxes, ha='center', va='center')
            return
        
        # Get coordinates
        time_coord = self.data.coords['time']
        height_coord = self.data.coords[height_dim] if height_dim in self.data.coords else self.data[height_dim]
        
        # Handle 3D data (e.g., spectral density with spectral_bins dimension)
        plot_data = data_var
        if len(data_var.dims) > 2:
            # Select only time and height dimensions
            extra_dims = [d for d in data_var.dims if d not in ['time', height_dim]]
            if extra_dims:
                # Take a slice at the given index for extra dimensions
                slice_dict = {extra_dims[0]: min(time_index, data_var.sizes[extra_dims[0]]-1)}
                plot_data = data_var.isel(slice_dict)
        
        # Get data values
        data_vals = plot_data.values
        
        # Convert time to matplotlib dates for better x-axis
        try:
            import pandas as pd
            import matplotlib.dates as mdates
            
            # ==================== SMART TIME CONVERSION (FIXED) ====================
            time_values = time_coord.values
            
            # Check the dtype first
            time_dtype = time_values.dtype
            
            # Method 0: Already datetime64 - just convert to pandas
            if np.issubdtype(time_dtype, np.datetime64):
                time_vals = pd.to_datetime(time_values)
            
            # Method 1: Check if values look like days since epoch (numeric check)
            elif np.issubdtype(time_dtype, np.number):
                if time_values.min() > 1000 and time_values.max() < 50000:
                    # Convert from days to datetime
                    time_vals = pd.to_datetime(time_values, unit='D', origin='unix')
                
                # Method 1b: Check if values are very large (seconds since epoch)
                elif time_values.min() > 1e9:
                    time_vals = pd.to_datetime(time_values, unit='s')
                
                else:
                    # Unknown numeric format, try direct conversion
                    time_vals = pd.to_datetime(time_values)
            
            # Method 2: Check if time has units attribute (CF convention)
            elif 'units' in time_coord.attrs:
                units_str = time_coord.attrs['units']
                
                try:
                    from cftime import num2date
                    # Parse units like "seconds since 2024-01-15 06:00:00"
                    time_vals = num2date(time_values, units=units_str)
                    time_vals = pd.to_datetime([t.strftime('%Y-%m-%d %H:%M:%S') for t in time_vals])
                except Exception as e:
                    print(f"   CF conversion failed: {e}")
                    
                    # Manual parsing of common formats
                    import re
                    match = re.search(r'since\s+(\d{4}-\d{2}-\d{2}(?:\s+\d{2}:\d{2}:\d{2})?)', units_str)
                    if match:
                        reference_time = pd.Timestamp(match.group(1))
                        
                        # Determine the time unit
                        if 'second' in units_str.lower():
                            time_vals = reference_time + pd.to_timedelta(time_values, unit='s')
                        elif 'minute' in units_str.lower():
                            time_vals = reference_time + pd.to_timedelta(time_values, unit='m')
                        elif 'hour' in units_str.lower():
                            time_vals = reference_time + pd.to_timedelta(time_values, unit='h')
                        elif 'day' in units_str.lower():
                            time_vals = reference_time + pd.to_timedelta(time_values, unit='D')
                        else:
                            raise ValueError(f"Unknown time unit in: {units_str}")
                    else:
                        raise ValueError(f"Could not parse units: {units_str}")
            
            # Method 3: Try direct pandas conversion as last resort
            else:
                try:
                    time_vals = pd.to_datetime(time_values)
                except Exception as e:
                    print(f"   Direct conversion failed: {e}")
                    # Give up, use numeric fallback
                    time_vals = None
            
            # Fallback if all conversions failed
            if time_vals is None or len(time_vals) == 0:
                print(f"   ⚠️ All time conversions failed, using numeric fallback")
                time_vals = time_coord.values
                time_numeric = np.arange(len(time_vals))
                time_label = 'Time Index'
                use_time_formatter = False
            else:
                # Convert to matplotlib dates
                time_numeric = mdates.date2num(time_vals)
                time_label = 'Time (UTC)'
                use_time_formatter = True
            # ==================== END SMART CONVERSION ====================
            
            # Convert to matplotlib dates
            time_numeric = mdates.date2num(time_vals)
            
            time_label = 'Time (UTC)'
            use_time_formatter = True
            
        except Exception as e:
            print(f"   ⚠️ Time conversion failed: {e}")
            import traceback
            traceback.print_exc()
            
            # Fallback to numeric time index
            time_vals = time_coord.values
            time_numeric = np.arange(len(time_vals))
            time_label = 'Time Index'
            use_time_formatter = False
            print(f"   Using fallback: time index 0 to {len(time_vals)-1}")
    
        # Convert height to km if needed
        height_vals = height_coord.values
        if height_vals.max() > 100:  # Likely in meters
            height_vals = height_vals / 1000.0
            height_label = 'Height (km AGL)'
        else:
            height_label = 'Height (km AGL)'
        
        # Create the plot
        try:
            # Get data values
            data_vals = plot_data.values
            
            # For pcolormesh: data must be (height, time) not (time, height)
            # Check current orientation
            if data_vals.shape[0] == len(time_vals) and data_vals.shape[1] == len(height_vals):
                # Data is (time, height) - needs transpose
                plot_vals = data_vals.T
            elif data_vals.shape[0] == len(height_vals) and data_vals.shape[1] == len(time_vals):
                # Data is already (height, time) - no transpose needed
                plot_vals = data_vals
            else:
                # Shape mismatch - try transpose anyway
                plot_vals = data_vals.T
                    
            # Use pcolormesh
            im = ax.pcolormesh(time_numeric, height_vals, plot_vals,
                              cmap=cmap, vmin=vmin, vmax=vmax,
                              shading='auto', zorder=2)
            
            # ==================== FIX: Proper time axis formatting ====================
            # Format x-axis for time (like your working code)
            if use_time_formatter:
                import matplotlib.dates as mdates
                
                # Enable date formatting on x-axis
                ax.xaxis_date()
                
                # Calculate time span to choose appropriate formatter
                time_span_hours = (time_vals[-1] - time_vals[0]).total_seconds() / 3600.0
                                
                if time_span_hours < 2:
                    # Less than 2 hours: show every 10 minutes
                    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=10))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=2))
                elif time_span_hours < 6:
                    # 2-6 hours: show every 30 minutes
                    ax.xaxis.set_major_locator(mdates.MinuteLocator(interval=30))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=10))
                elif time_span_hours < 24:
                    # 6-24 hours: show every hour
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=1))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
                    ax.xaxis.set_minor_locator(mdates.MinuteLocator(interval=15))
                else:
                    # More than 24 hours: show every 6 hours with date
                    ax.xaxis.set_major_locator(mdates.HourLocator(interval=6))
                    ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d %H:%M'))
                    ax.xaxis.set_minor_locator(mdates.HourLocator(interval=1))
                
                # Auto-format date labels (rotation, alignment)
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            else:
                # Fallback to numeric time
                print(f"   Using numeric time axis")
            
            # Set labels
            ax.set_xlabel(time_label, fontsize=10)
            ax.set_ylabel(height_label, fontsize=10)
            
            # Set limits
            ax.set_xlim([time_numeric.min(), time_numeric.max()])
            max_height_display = min(height_vals.max(), self.max_height)
            padding_factor = 0.08
            padding = max_height_display * padding_factor
            ax.set_ylim([0, max_height_display + padding])
            
            # Add colorbar
            cb = plt.colorbar(im, ax=ax, label=units, pad=0.02)
            
            # Get location info for title
            location = "Unknown Location"
            try:
                if 'latitude' in self.data.coords or 'latitude' in self.data.data_vars:
                    lat = float(self.data['latitude'].values)
                    lon = float(self.data['longitude'].values)
                    location = f"{lat:.4f}°N, {lon:.4f}°E"
            except:
                pass
            
            # Get time range for title
            try:
                start_time = pd.Timestamp(time_vals[0]).strftime('%Y-%m-%d %H:%M')
                end_time = pd.Timestamp(time_vals[-1]).strftime('%H:%M')
                time_info = f"{start_time} to {end_time} UTC"
            except:
                time_info = "Time Series"
            
            # Add title
            ax.set_title(f'{title}\n{location}\n{time_info}', 
                        fontsize=10, fontweight='bold')
            
            # Set background
            ax.set_facecolor('black')
            
            # Add grid
            ax.grid(True, color='white', linestyle=':', linewidth=0.5, alpha=0.5)
                        
        except Exception as e:
            print(f"   ❌ Error plotting time-height: {e}")
            import traceback
            traceback.print_exc()
            ax.text(0.5, 0.5, f'Error plotting {field}\n{str(e)}', 
                   transform=ax.transAxes, ha='center', va='center')
                   
    def _add_map_features(self, ax, lat, lon):
        """Add map features to the plot"""
        try:
            ax.add_feature(cfeature.COASTLINE, color='white', linewidth=0.5)
            ax.add_feature(cfeature.BORDERS, color='white', linewidth=0.5)
            ax.add_feature(cfeature.STATES, color='white', linewidth=0.5)
            
            grid_lines = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', x_inline=False)
            grid_lines.top_labels = False
            grid_lines.right_labels = False
            grid_lines.xformatter = LONGITUDE_FORMATTER
            grid_lines.yformatter = LATITUDE_FORMATTER
        except:
            pass
            
class RadarPlotter:
    """Class to handle radar plotting using the existing plotting code with settings support"""
    
    def __init__(self, radar, scan_type="PPI", plot_fast=True, max_range=150, 
                 max_height=10, mask_outside=True, show_radials=True, 
                 show_range_rings=True, range_ring_spacing=50, show_grid=True):
        
        self.radar = radar
        self.scan_type = scan_type
        self.plot_fast = plot_fast
        self.max_range = max_range
        self.max_height = max_height
        self.mask_outside = mask_outside
        self.show_radials = show_radials
        self.show_range_rings = show_range_rings
        self.range_ring_spacing = range_ring_spacing
        self.show_grid = show_grid                    
    
        # Initialize caches for expensive operations
        self._cache = PlottingCache()
    
    def plot_ppi_fast(self, field, sweep, ax, settings=None, zoom_xlim=None, zoom_ylim=None):
        """Plot a PPI scan without cartopy (fast) with settings support"""
        # Get field info using your original function
        units, vmin, vmax, cmap, _, Nbins = get_field_info(self.radar, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                # Handle both string names and colormap objects
                if isinstance(custom_cmap, str):
                    # It's a string name - check if it's a GV colormap
                    if custom_cmap in _GV_COLORMAPS:
                        cmap = _GV_COLORMAPS[custom_cmap]
                    else:
                        try:
                            cmap = plt.get_cmap(custom_cmap)
                        except:
                            pass  # Use default if custom cmap fails
                elif hasattr(custom_cmap, 'name'):
                    # It's already a colormap object - use it directly
                    cmap = custom_cmap
        
        # Apply discrete colormap if needed (from your original code)
        if Nbins > 0:
            cmap = discrete_cmap(Nbins, base_cmap=cmap)
        
        # Get radar info for title
        site, mydate, mytime, elv, _, _, _, _, _, _, _ = get_radar_info(self.radar, sweep)
        
        title = f'{site} {field} {mydate} {mytime} UTC PPI Elev: {elv:.1f} deg'
        
        # Set up the display
        display = pyart.graph.RadarDisplay(self.radar)
        ax.set_facecolor('black')
        
        # Handle special rain rate fields with your original processing
        if field in ['RC', 'RP', 'RA']:
            processed_field = self._cache.get_processed_field(self.radar, field)
            if processed_field:
                plot_name = f"{field}_plot"
                self.radar.add_field(plot_name, processed_field, replace_existing=True)
                
                levels = [0, 5, 10, 15, 20, 25, 100, 150, 200, 250, 300]
                midnorm = MidpointNormalize(vmin=0, vcenter=25, vmax=300)
                
                display.plot_ppi(
                    plot_name, sweep=sweep, ax=ax,
                    vmin=vmin, vmax=vmax, 
                    cmap=cmap, 
                    norm=midnorm, 
                    ticks=levels,
                    colorbar_label=units,
                    mask_outside=self.mask_outside, 
                    title=title
                )
            else:
                # Fall back to regular plotting if processing fails
                display.plot_ppi(
                    field, sweep=sweep, ax=ax,
                    vmin=vmin, vmax=vmax, 
                    cmap=cmap,
                    colorbar_label=units,
                    mask_outside=self.mask_outside, 
                    title=title
                )
        else:
            # Regular field plotting
            display.plot_ppi(
                field, sweep=sweep, ax=ax,
                vmin=vmin, vmax=vmax, 
                cmap=cmap,
                colorbar_label=units,
                mask_outside=self.mask_outside, 
                title=title
            )
        
        # Set display limits
        display.set_limits(xlim=[-self.max_range, self.max_range], 
                           ylim=[-self.max_range, self.max_range], ax=ax)
    
        # ==================== APPLY ZOOM IF SET (NEW) ====================
        if zoom_xlim is not None and zoom_ylim is not None:
            ax.set_xlim(zoom_xlim)
            ax.set_ylim(zoom_ylim)        
            
        # Add range rings with custom spacing
        if self.show_range_rings:
            for rng in range(self.range_ring_spacing, self.max_range + self.range_ring_spacing, 
                             self.range_ring_spacing):
                display.plot_range_ring(rng, ax=ax, col="white", ls="-", lw=0.5)
            
        # Add radials for fast plot
        if self.show_radials:
            self._cache.add_radials_fast(ax, self.max_range)
        
        # Add grid lines
        if self.show_grid:
            display.plot_grid_lines(ax=ax, col="white", ls=":")
        
        # FIXED: Set square aspect ratio
        ax.set_aspect('equal')
        
        # Apply your special colorbar adjustments
        if hasattr(display, 'cbs') and len(display.cbs) > 0:
            adjust_special_colorbars(field, display, 0)
    
    def plot_ppi_cartopy(self, field, sweep, ax, projection, settings=None, 
                     annotation_manager=None, zoom_xlim=None, zoom_ylim=None):
        """Plot a PPI scan with cartopy features and settings support"""
        # Get field info using your original function
        units, vmin, vmax, cmap, _, Nbins = get_field_info(self.radar, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                # Handle GV colormaps
                if custom_cmap in _GV_COLORMAPS:
                    cmap = _GV_COLORMAPS[custom_cmap]
                else:
                    try:
                        cmap = custom_cmap
                    except:
                        pass  # Use default if custom cmap fails

        
        # Apply discrete colormap if needed
        if Nbins > 0:
            cmap = discrete_cmap(Nbins, base_cmap=cmap)
        
        # Get radar info for title
        site, mydate, mytime, elv, _, _, _, _, _, _, _ = get_radar_info(self.radar, sweep)
        
        title = f'{site} {field} {mydate} {mytime} UTC PPI Elev: {elv:.1f} deg'
        
        # Get radar coordinates
        radar_lat = self.radar.latitude['data'][0]
        radar_lon = self.radar.longitude['data'][0]
        
        # Get coordinate transform data
        coord_data = self._cache.get_coordinate_transform(radar_lat, radar_lon, self.max_range)
        
        # Set up the display for cartopy
        display = pyart.graph.RadarMapDisplay(self.radar)
        ax.set_facecolor('black')
        
        # Handle special rain rate fields
        if field in ['RC', 'RP', 'RA']:
            processed_field = self._cache.get_processed_field(self.radar, field)
            if processed_field:
                plot_name = f"{field}_plot"
                self.radar.add_field(plot_name, processed_field, replace_existing=True)
                
                levels = [0, 5, 10, 15, 20, 25, 100, 150, 200, 250, 300]
                midnorm = MidpointNormalize(vmin=0, vcenter=25, vmax=300)
                
                display.plot_ppi_map(
                    plot_name, sweep, vmin=vmin, vmax=vmax,
                    resolution='50m', title=title, projection=projection, ax=ax,
                    cmap=cmap, norm=midnorm, ticks=levels, colorbar_label=units,
                    min_lon=coord_data['min_lon'], max_lon=coord_data['max_lon'],
                    min_lat=coord_data['min_lat'], max_lat=coord_data['max_lat'],
                    lon_lines=coord_data['lon_grid'], lat_lines=coord_data['lat_grid'],
                    add_grid_lines=False, lat_0=radar_lat, lon_0=radar_lon,
                    embellish=False, mask_outside=self.mask_outside
                )
            else:
                # Fall back to regular plotting
                display.plot_ppi_map(
                    field, sweep, vmin=vmin, vmax=vmax,
                    resolution='50m', title=title, projection=projection, ax=ax,
                    cmap=cmap, colorbar_label=units,
                    min_lon=coord_data['min_lon'], max_lon=coord_data['max_lon'],
                    min_lat=coord_data['min_lat'], max_lat=coord_data['max_lat'],
                    lon_lines=coord_data['lon_grid'], lat_lines=coord_data['lat_grid'],
                    add_grid_lines=False, lat_0=radar_lat, lon_0=radar_lon,
                    embellish=False, mask_outside=self.mask_outside
                )
        else:
            # Regular field plotting with cartopy
            display.plot_ppi_map(
                field, sweep, vmin=vmin, vmax=vmax,
                resolution='50m', title=title, projection=projection, ax=ax,
                cmap=cmap, colorbar_label=units,
                min_lon=coord_data['min_lon'], max_lon=coord_data['max_lon'],
                min_lat=coord_data['min_lat'], max_lat=coord_data['max_lat'],
                lon_lines=coord_data['lon_grid'], lat_lines=coord_data['lat_grid'],
                add_grid_lines=False, lat_0=radar_lat, lon_0=radar_lon,
                embellish=False, mask_outside=self.mask_outside
            )
        
        # Add map features
        try:
            COUNTIES, STATES, REEFS, MINOR_ISLANDS = self._cache.get_map_features()
            
            # ==================== BASE LAYERS (BEHIND DATA) ====================
            # Ocean and lakes first (zorder 0-1)
            ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor="#414141", zorder=0)
            ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor="#414141", 
                          edgecolor='white', lw=0.25, zorder=1)
            
            # ==================== MINOR ISLANDS (LANDMASS) ====================
            # Show small islands as dark gray landmass (before data, after ocean)
            if MINOR_ISLANDS:
                ax.add_feature(MINOR_ISLANDS, facecolor='#3d3d3d', edgecolor='white', 
                              linewidth=0.3, zorder=2)
            # ==================== END MINOR ISLANDS ====================
            
            # ==================== POLITICAL BOUNDARIES (ON TOP) ====================
            # Coastlines and borders (zorder 10)
            ax.add_feature(cfeature.COASTLINE, color='white', linewidth=0.5, zorder=10)
            ax.add_feature(cfeature.BORDERS, color='white', linewidth=0.5, zorder=10)
            
            # States
            if STATES:
                ax.add_feature(STATES, facecolor='none', edgecolor='white', lw=0.5, zorder=10)
            
            # Counties
            if COUNTIES:
                ax.add_feature(COUNTIES, facecolor='none', edgecolor='white', lw=0.25, zorder=10)
            
            # Reefs (cyan for visibility)
            if REEFS:
                ax.add_feature(REEFS, facecolor='none', edgecolor='cyan', 
                              linewidth=0.4, zorder=10, alpha=0.8)
            
        except Exception as e:
            print(f"Could not add map features: {e}")
            # Fallback to basic features
            try:
                ax.add_feature(cfeature.COASTLINE, color='white', linewidth=0.5)
                ax.add_feature(cfeature.BORDERS, color='white', linewidth=0.5)
                ax.add_feature(cfeature.OCEAN.with_scale('50m'), facecolor="#414141")
                ax.add_feature(cfeature.LAKES.with_scale('50m'), facecolor="#414141", 
                              edgecolor='white', lw=0.25, zorder=0)
            except:
                pass
            
        # Add range rings with custom spacing
        if self.show_range_rings:
            for rng in range(self.range_ring_spacing, self.max_range + self.range_ring_spacing,
                             self.range_ring_spacing):
                display.plot_range_ring(rng, ax=ax, col="white", ls="-", lw=0.5)
            
        # ADD RADIALS
        if self.show_radials:
            coord_data = self._cache.get_coordinate_transform(radar_lat, radar_lon, self.max_range)
            self._cache.add_radials_vectorized(display, radar_lat, radar_lon, self.max_range, coord_data)
            
        # Add cartopy grid lines
        if self.show_grid:
            grid_lines = ax.gridlines(draw_labels=True, linewidth=0.5, color='gray', x_inline=False)
            grid_lines.top_labels = False
            grid_lines.right_labels = False
            grid_lines.xformatter = LONGITUDE_FORMATTER
            grid_lines.yformatter = LATITUDE_FORMATTER
            grid_lines.xlabel_style = {'size': 6, 'color': 'black', 'rotation': 0, 'weight': 'bold', 'ha': 'center'}
            grid_lines.ylabel_style = {'size': 6, 'color': 'black', 'rotation': 90, 'weight': 'bold', 'va': 'bottom', 'ha': 'center'}
        
        try:
            ax.set_aspect('equal')
        except:
            # Some cartopy versions don't like set_aspect on map axes
            pass
            
        if annotation_manager:
            self._add_annotations(ax, annotation_manager, zoom_xlim, zoom_ylim)
        
        # Apply special colorbar adjustments
        if hasattr(display, 'cbs') and len(display.cbs) > 0:
            adjust_special_colorbars(field, display, 0)
            
    def _add_annotations(self, ax, annotation_manager, zoom_xlim=None, zoom_ylim=None):
        """Add annotations to the plot, filtering by zoom bounds"""
        for ann in annotation_manager.get_enabled_annotations():
            lat = ann['lat']
            lon = ann['lon']
            label = ann.get('label', '')
            symbol = ann.get('symbol', 'v')
            size = ann.get('size', 5)
            color = ann.get('color', 'white')
            
            # ==================== SMART ZOOM FILTERING ====================
            if zoom_xlim is not None and zoom_ylim is not None:
                # Detect coordinate system by checking magnitude of zoom bounds
                # Lat/lon are always < 180, x-y coordinates in km are typically larger
                is_latlon_zoom = (abs(zoom_xlim[0]) < 180 and abs(zoom_xlim[1]) < 180 and
                                 abs(zoom_ylim[0]) < 90 and abs(zoom_ylim[1]) < 90)
                
                if is_latlon_zoom:
                    # Zoom is in lat/lon degrees - check if annotation is visible
                    if not (zoom_xlim[0] <= lon <= zoom_xlim[1] and 
                           zoom_ylim[0] <= lat <= zoom_ylim[1]):
                        # Annotation is outside zoom area, skip it
                        continue
         
            # Plot point
            ax.plot(lon, lat, marker=symbol, markersize=size, 
                   color=color, transform=ccrs.PlateCarree(),
                   markeredgecolor='black', markeredgewidth=0.5, zorder=10)
            
            # Add text label if provided
            if label:
                ax.text(lon, lat, f'  {label}', 
                       transform=ccrs.PlateCarree(),
                       fontsize=8, color=color, 
                       fontweight='bold',
                       verticalalignment='center',
                       bbox=dict(boxstyle='round,pad=0.3', 
                                facecolor='black', alpha=0.7, edgecolor=color),
                       zorder=11)
    
    def plot_rhi(self, field, sweep, ax, settings=None):
        """Plot an RHI scan using your original color schemes with settings support"""
        # Get field info using your original function
        units, vmin, vmax, cmap, _, Nbins = get_field_info(self.radar, field)
        
        # Apply custom settings if available
        if settings:
            custom_vmin = settings.get_field_setting(field, 'vmin')
            custom_vmax = settings.get_field_setting(field, 'vmax')
            custom_cmap = settings.get_field_setting(field, 'cmap')
            
            if custom_vmin is not None:
                vmin = custom_vmin
            if custom_vmax is not None:
                vmax = custom_vmax
            if custom_cmap:
                # Handle GV colormaps
                if custom_cmap in _GV_COLORMAPS:
                    cmap = _GV_COLORMAPS[custom_cmap]
                else:
                    try:
                        cmap = custom_cmap
                    except:
                        pass  # Use default if custom cmap fails

        
        # Apply discrete colormap if needed (from your original code)
        if Nbins > 0:
            cmap = discrete_cmap(Nbins, base_cmap=cmap)
        
        # Get radar info for title
        site, mydate, mytime, azi, _, _, _, _, _, _, _ = get_radar_info(self.radar, sweep)
        
        title = f'{site} {field} {mydate} {mytime} UTC RHI Azi: {azi:.1f}'
        
        # Set up the display
        display = pyart.graph.RadarDisplay(self.radar)
        ax.set_facecolor('black')
        
        # Handle special rain rate fields with your original processing
        if field in ['RC', 'RP']:
            processed_field = self._cache.get_processed_field(self.radar, field)
            if processed_field:
                plot_name = f"{field}_plot"
                self.radar.add_field(plot_name, processed_field, replace_existing=True)
                
                levels = [0, 5, 10, 15, 20, 25, 100, 150, 200, 250, 300]
                midnorm = MidpointNormalize(vmin=0, vcenter=25, vmax=300)
                
                display.plot_rhi(
                    plot_name, sweep, ax=ax,
                    vmin=vmin, vmax=vmax, 
                    cmap=cmap, 
                    norm=midnorm, 
                    ticks=levels,
                    colorbar_label=units,
                    mask_outside=self.mask_outside, 
                    title=title
                )
            else:
                # Fall back to regular plotting if processing fails
                display.plot_rhi(
                    field, sweep, ax=ax,
                    vmin=vmin, vmax=vmax, 
                    cmap=cmap,
                    colorbar_label=units,
                    mask_outside=self.mask_outside, 
                    title=title
                )
        else:
            # Regular field plotting
            display.plot_rhi(
                field, sweep, ax=ax,
                vmin=vmin, vmax=vmax, 
                cmap=cmap,
                colorbar_label=units,
                mask_outside=self.mask_outside, 
                title=title
            )
        
        # Set display limits and add grid
        display.set_limits(xlim=[0, self.max_range], ylim=[0, self.max_height], ax=ax)
        display.plot_grid_lines(ax=ax, col="white")
        
        # Apply your special colorbar adjustments
        if hasattr(display, 'cbs') and len(display.cbs) > 0:
            adjust_special_colorbars(field, display, 0)

class NexradDownloader(QThread):
    """Thread for downloading NEXRAD data in background"""
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    
    def __init__(self, site, num_files=1):
        super().__init__()
        self.site = site.upper()
        self.num_files = num_files
        
    def run(self):
        try:
            self.progress.emit(f"Fetching file list for {self.site}...")
            
            # Download realtime data list
            url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/radar/nexrad_level2/{self.site}/dir.list"
            
            response = requests.get(url, timeout=30)
            
            if response.status_code != 200:
                self.error.emit(f"Could not access {self.site} data. Status: {response.status_code}")
                return
            
            # Parse file list - be more flexible with parsing
            lines = response.text.strip().split('\n')
            file_list = []
            
            for line in lines:
                line = line.strip()
                if not line:  # Skip empty lines
                    continue
                    
                parts = line.split()
                
                # Look for files that end with common NEXRAD extensions
                if len(parts) >= 2:
                    filename = parts[-1]  # Usually the last part is filename
                    # NEXRAD files can end with .gz, .bz2, or just be the raw filename
                    if (filename.endswith('.gz') or 
                        filename.endswith('.bz2') or 
                        ('_V06' in filename and len(filename) > 20)):  # Raw NEXRAD filenames are long
                        file_list.append(filename)
                        
            if not file_list:
                # Try alternative: look for any files in the directory
                self.progress.emit("No standard files found, checking for any data files...")
                
                for line in lines:
                    parts = line.split()
                    if len(parts) >= 2 and len(parts[-1]) > 10:  # Assume NEXRAD files are long names
                        file_list.append(parts[-1])
                
                if not file_list:
                    # Provide more detailed error info
                    error_msg = f"No data files found for {self.site}.\n"
                    error_msg += f"Response had {len(lines)} lines.\n"
                    error_msg += "This could mean:\n"
                    error_msg += "1. Site is not currently operational\n"
                    error_msg += "2. Site code is incorrect\n"
                    error_msg += "3. No recent data available\n"
                    error_msg += f"Raw response: {response.text[:200]}..."
                    self.error.emit(error_msg)
                    return
            
            # Get the most recent file(s)
            files_to_download = file_list[-self.num_files:]
            
            # Download the file(s)
            downloaded_files = []
            for i, filename in enumerate(files_to_download):
                self.progress.emit(f"Downloading {filename} ({i+1}/{len(files_to_download)})...")
                
                file_url = f"https://nomads.ncep.noaa.gov/pub/data/nccf/radar/nexrad_level2/{self.site}/{filename}"
                
                file_response = requests.get(file_url, timeout=120)
                
                if file_response.status_code == 200:
                    # Create temp file
                    temp_path = os.path.join(tempfile.gettempdir(), filename)
                    
                    with open(temp_path, 'wb') as f:
                        f.write(file_response.content)
                                        
                    downloaded_files.append(temp_path)
                    self.progress.emit(f"Downloaded {filename} ({len(file_response.content)} bytes)")
                else:
                    self.error.emit(f"Failed to download {filename}. Status: {file_response.status_code}")
                    return
            
            # Return the most recent file
            if downloaded_files:
                self.finished.emit(downloaded_files[-1])
            else:
                self.error.emit("No files were downloaded successfully")
                
        except requests.exceptions.Timeout:
            self.error.emit(f"Timeout connecting to NOAA servers for {self.site}")
        except requests.exceptions.ConnectionError:
            self.error.emit(f"Connection error - check internet connection")
        except Exception as e:
            self.error.emit(f"Download error: {str(e)}")
            print(f"Exception details: {e}")
            import traceback
            traceback.print_exc()

def main():
    app = QApplication(sys.argv)
    window = RadarViewer()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()