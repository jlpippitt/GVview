# GVview - GPM Ground Validation Radar Viewer

A professional, interactive radar data visualization tool built for the NASA GPM Ground Validation program. GVview provides advanced analysis and visualization capabilities for weather radar data with support for multiple formats and real-time NEXRAD data access.

![Python Version](https://img.shields.io/badge/python-3.7%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey)

---

## ✨ Features

### 📊 **Data Format Support**
- **NEXRAD Level II** - Real-time download and visualization from NOAA servers
- **ODIM H5** - European weather radar standard
- **GAMIC HDF5** - Research radar data format
- **D3R** - Dual-frequency Dual-polarized Doppler Radar
- **PyART Grid** - Gridded radar data products
- **xarray Datasets** - NetCDF/HDF gridded data
- **CfRadial** - Climate and Forecast conventions
- **Auto-format detection** - Intelligently detects and loads various formats

### 🎯 **Visualization Modes**
- **PPI (Plan Position Indicator)** - Horizontal cross-sections
- **RHI (Range Height Indicator)** - Vertical cross-sections
- **Fast Mode** - Quick x-y plotting without map projection
- **Map Mode** - Geographic projection with Cartopy integration
- **Multi-field Display** - View up to 9 fields simultaneously

### 🛠️ **Interactive Tools**
- **Zoom Tool** - Click-and-drag box zoom with real-time rectangle preview
- **Annotations** - Add custom markers and labels to plots
- **Field Selector** - Easy switching between radar variables
- **Sweep Selector** - Navigate through elevation angles or vertical levels
- **Range Control** - Adjustable maximum range (10-500 km)
- **Height Control** - Configurable max height for RHI plots (1-25 km)

### 🎨 **Customization**
- **Colorbar Settings** - Custom colormaps, min/max values per field
- **Auto-detection** - Smart range detection for unknown fields using percentiles
- **Layout Tuning** - Fine-tune figure size, margins, spacing, and fonts
- **Platform Optimization** - Automatic DPI and layout scaling for Windows/macOS/Linux
- **Persistent Settings** - Save preferences across sessions

### 🗺️ **Map Features**
- **High-resolution Shapefiles** - US states, counties, coastlines
- **Natural Earth Data** - International boundaries and features
- **Custom Projections** - Lambert Conformal projection centered on radar
- **Grid Lines** - Lat/lon grid with customizable spacing
- **Terrain Features** - Lakes, rivers, and ocean display

### 📡 **NEXRAD Integration**
- **Real-time Download** - Fetch latest scans from 160+ NEXRAD sites
- **Site Checker** - Verify site availability and data status
- **Split-cut Merging** - Automatically combine reflectivity and velocity scans
- **Comprehensive Site List** - All US, Puerto Rico, Guam, and international sites

### 🔬 **Advanced Features**
- **HID Colormaps** - Specialized colormaps for hydrometeor identification
- **Rain Rate Processing** - Special handling for rainfall rate products
- **Discrete Colorbars** - Custom tick labels for categorical data
- **Memory Management** - Efficient caching of expensive operations
- **Multi-threading** - Background data downloads with progress tracking

---

## 📦 Dependencies

### **Required Python Packages**


Core Dependencies
python >= 3.7
numpy >= 1.19.0
matplotlib >= 3.3.0
pyqt5 >= 5.15.0

Radar Data Processing
arm-pyart >= 1.12.0
netCDF4 >= 1.5.0
xarray >= 0.16.0
h5py >= 3.0.0

Geospatial
cartopy >= 0.18.0
shapely >= 1.7.0

Additional
pillow >= 8.0.0
requests >= 2.25.0
cftime >= 1.3.0

### **Optional Dependencies**


For specific radar formats
wradlib >= 1.10.0  # Additional radar utilities

For advanced features
scipy >= 1.5.0     # Scientific computing
pandas >= 1.1.0    # Data analysis

---

## 🚀 Installation

### **1. Clone the Repository**

git clone https://github.com/jlpippitt/gvview.git

cd gvview

### **2. Create Conda Environment (Recommended)

# Create environment with all dependencies
conda create -n gvview python=3.9
conda activate gvview

# Install PyART and dependencies
conda install -c conda-forge arm_pyart

# Install PyQt5
conda install -c conda-forge pyqt

# Install Cartopy
conda install -c conda-forge cartopy

# Install remaining packages
pip install pillow requests cftime

3. Alternative: pip Installation

# Create virtual environment
python -m venv gvview-env
source gvview-env/bin/activate  # On Windows: gvview-env\Scripts\activate

# Install dependencies
pip install numpy matplotlib pyqt5 arm-pyart cartopy pillow requests cftime

4. Optional: County Shapefiles
For high-resolution US county boundaries:

# Download NOAA county shapefiles
mkdir shape_files
cd shape_files
wget https://www.weather.gov/source/gis/Shapefiles/County/countyl010g.zip
unzip countyl010g.zip
cd ..

🎮 Usage
Basic Usage

python GVview.py

Quick Start Guide
Load Local File

Click "Load Radar File"
Select your radar file (.nc, .h5, .hdf5, etc.)
File format is auto-detected
Download NEXRAD Data

Select site from dropdown (e.g., "KDOX - Dover AFB, DE")
Click "Load" to download latest scan
Click "Check" to verify site status
Visualize Data

Select field from dropdown (e.g., CZ, VR, DR)
Choose sweep/elevation angle
Toggle between "Fast" and "Map" plotting modes
Click "Update" to refresh plot
Multi-field Display

Check "Multi-field" checkbox
Click "Select Fields"
Choose multiple fields to display
Click "Update"
Zoom and Pan

Click "Zoom Mode" in toolbar
Click and drag on plot to draw zoom box
Release to apply zoom
Click "Reset Zoom" to return to full view
Save Plot

Click "Save" button
Choose output filename
Plot saved as high-resolution PNG
⚙️ Configuration
Layout Tuning
Access via Layout button in toolbar:

Figure Size - Width and height in inches
Margins - Top, bottom, left, right spacing
Title Position - Vertical placement of main title
Spacing - Horizontal and vertical spacing between subplots
Font Scale - Global font size multiplier
Auto-Calibrate - Automatically optimize layout
Colorbar Settings
Access via Colorbar button in toolbar:

Min/Max Values - Custom data range per field
Colormap - Choose from 40+ colormaps
Reset - Return to default settings
Annotations
Access via Annotations button in toolbar:

Add Points - Custom lat/lon markers
Labels - Text annotations
Symbols - Choose marker style (circle, triangle, etc.)
Colors - Customize marker and label colors
Quick Add - Insert current radar location
📋 Supported Fields
Dual-Polarization Variables
CZ/DZ/DBZH - Reflectivity (dBZ)
VR/VEL - Radial Velocity (m/s)
SW - Spectrum Width (m/s)
DR/ZDR - Differential Reflectivity (dB)
PH/PHIDP - Differential Phase (deg)
KD/KDP - Specific Differential Phase (deg/km)
RH/RHOHV - Correlation Coefficient
Derived Products
FH/FS - Summer Hydrometeor ID
FW/NT - Winter Hydrometeor ID
RC - HIDRO Rain Rate (mm/hr)
RP - Polarimetric Rain Rate (mm/hr)
MW/MI - Water/Ice Mass (g/m³)
DM - Median Drop Diameter (mm)
NW - Normalized Intercept Parameter
Auto-Detection
Unknown fields are automatically analyzed
Smart colormap selection based on field characteristics
Percentile-based range detection (1st-99th)
Diverging colormaps for velocity-like data
🖼️ Screenshots
Main Interface

[Placeholder - Add screenshot of main window]

Multi-field Display

[Placeholder - Add screenshot of 2x2 or 3x3 grid]

Map Mode with Annotations

[Placeholder - Add screenshot with zoom and annotations]

🗺️ Supported NEXRAD Sites
United States
All 160 NEXRAD WSR-88D sites
Organized by state in dropdown menu
Real-time data availability
International
Guam (PGUA)
South Korea (RKSG, RKJK)
Japan (RODN)
Check Site Status
Use the "Check" button to verify:

Site operational status
Available data files
Most recent scan time
🔧 Troubleshooting
Common Issues
"Could not load file"

Ensure file format is supported
Check for corrupted files
Try decompressing .gz files manually
"NEXRAD download failed"

Check internet connection
Verify site code is correct (4 letters)
Some sites may be temporarily offline
"Plots are too small/large"

Use "Layout" button to adjust figure size
Try "Auto-Calibrate" for automatic optimization
Adjust padding factor (0.5-1.0)
"Zoom rectangle is laggy"

This is normal for complex map projections
Use "Fast" mode for smoother interaction
Reduce number of displayed fields
"Colorbar doesn't match data"

Reset field settings via "Colorbar" dialog
Check for masked/missing data
Try auto-detection by loading unknown field name
Platform-Specific
macOS Retina Display

Layouts automatically scale for high-DPI
If fonts are too large, adjust font scale in Layout dialog
Linux

May need to install Qt5 platform plugins
sudo apt-get install python3-pyqt5
Windows

Ensure Visual C++ Redistributable is installed
Some Cartopy features require GEOS library
🤝 Contributing
Contributions are welcome! Please follow these guidelines:

Fork the repository
Create a feature branch (git checkout -b feature/new-feature)
Commit changes (git commit -m 'Add new feature')
Push to branch (git push origin feature/new-feature)
Open a Pull Request
Code Style
Follow PEP 8 guidelines
Use 4 spaces for indentation
Add docstrings to all functions
Comment complex logic
Testing
Test with multiple radar formats
Verify on different platforms (Windows/macOS/Linux)
Check memory usage with large files
📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

🙏 Acknowledgments
NASA GPM Ground Validation - Funding and support
Py-ART - ARM Radar Toolkit for data I/O and processing
NOAA - NEXRAD data and site information
Cartopy - Geospatial plotting capabilities
PyQt5 - GUI framework
📧 Contact
Author: Jason Pippitt
Email: [jason.l.pippitt@nasa.gov]
GitHub: @YOUR_USERNAME
Issues: Report bugs or request features
📚 Documentation
Additional Resources
Py-ART Documentation
NEXRAD Data Archive
Cartopy Documentation
PyQt5 Tutorial
Radar Data Formats
CfRadial Standard
ODIM H5 Specification
NEXRAD Level II Format
🔄 Version History
v1.0.0 (2026-01-XX)
Initial release
Multi-format radar data support
Interactive PPI/RHI visualization
NEXRAD real-time download
Zoom and annotation tools
Custom colorbar settings
Multi-field display
Auto-detection of unknown fields
🚦 Roadmap
Planned Features
 Time series animation
 Volume rendering (3D visualization)
 QVP (Quasi-Vertical Profile) plots
 Dual-radar analysis tools
 Export to GeoTIFF/KML
 Plugin system for custom products
 Batch processing mode
 Web interface option
⭐ Star History
If you find this tool useful, please consider giving it a star! ⭐

Made with ❤️ for the radar community

---
