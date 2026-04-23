#!/usr/bin/env python3
"""
Setup validation script - checks that all dependencies are installed correctly.
Run this first to ensure your environment is ready.
"""

import sys
import subprocess

def check_package(package_name, import_name=None):
    """Check if a package is installed."""
    if import_name is None:
        import_name = package_name
    
    try:
        __import__(import_name)
        print(f"✓ {package_name:<20} installed")
        return True
    except ImportError:
        print(f"✗ {package_name:<20} NOT installed")
        return False

def check_file(filepath):
    """Check if a required file exists."""
    import os
    if os.path.exists(filepath):
        print(f"✓ {filepath:<30} found")
        return True
    else:
        print(f"✗ {filepath:<30} NOT found")
        return False

def main():
    print("\n" + "="*70)
    print("ENVIRONMENT VALIDATION FOR SELENGA DELTA WATER MASK")
    print("="*70 + "\n")
    
    # Check Python version
    print("Python Environment:")
    print(f"  Version: {sys.version.split()[0]}")
    if sys.version_info >= (3, 8):
        print("  ✓ Version compatible (3.8+)\n")
    else:
        print("  ✗ Python 3.8+ required!\n")
        return False
    
    # Check packages
    print("Required Packages:")
    packages = [
        ('numpy', 'numpy'),
        ('rasterio', 'rasterio'),
        ('scikit-image', 'skimage'),
        ('scipy', 'scipy'),
        ('matplotlib', 'matplotlib'),
    ]
    
    all_installed = True
    for pkg, import_name in packages:
        if not check_package(pkg, import_name):
            all_installed = False
    
    if not all_installed:
        print("\n" + "!"*70)
        print("Missing packages detected. Install with:")
        print("  pip install -r requirements.txt")
        print("!"*70 + "\n")
        return False
    
    print("\n✓ All packages installed!\n")
    
    # Check files
    print("Required/Recommended Files:")
    files = [
        'script.py',
        'visualize.py',
        'advanced_multi_index.py',
        'TUNING_GUIDE.py',
        'README.md',
        'requirements.txt',
    ]
    
    for filepath in files:
        check_file(filepath)
    
    print("\n" + "="*70)
    print("NEXT STEPS:")
    print("="*70)
    print("1. Place your Sentinel-2 TIF file as 'sentinel2.tif' in this directory")
    print("2. Verify band order: Band 3 = Green, Band 11 = SWIR")
    print("   Check with: gdalinfo sentinel2.tif")
    print("3. Run: python3 script.py")
    print("4. (Optional) Visualize: python3 visualize.py")
    print("="*70 + "\n")
    
    return True

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
