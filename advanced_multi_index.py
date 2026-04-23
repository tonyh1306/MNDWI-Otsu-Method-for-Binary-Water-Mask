"""
Advanced water mask script with multi-temporal compositing and combined indices.
Use when basic MNDWI has issues with wetlands, vegetation, or sediment confusion.
"""

import rasterio
import numpy as np
from skimage.filters import threshold_otsu, median
from skimage import morphology
import os
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================
output_dir = 'output'
os.makedirs(output_dir, exist_ok=True)

GREEN_BAND = 3
RED_BAND = 4
NIR_BAND = 8
SWIR_BAND = 11

MIN_WATER_SIZE = 50
MIN_HOLE_SIZE = 50
MEDIAN_FILTER_SIZE = 3

# ============================================================================
# METHOD 1: MNDWI + NDVI combined (best for delta with vegetation)
# ============================================================================
def mndwi_ndvi_mask(tif_path, output_path='delta_mask_mndwi_ndvi.tif'):
    """
    MNDWI for water + NDVI filter to exclude vegetation.
    Water: MNDWI > thresh AND NDVI < 0.3
    """
    print("\n" + "="*60)
    print("METHOD 1: MNDWI + NDVI Combined Index")
    print("="*60)
    
    with rasterio.open(tif_path) as src:
        green = src.read(GREEN_BAND).astype(float)
        red = src.read(RED_BAND).astype(float)
        nir = src.read(NIR_BAND).astype(float)
        swir = src.read(SWIR_BAND).astype(float)
        meta = src.meta.copy()
    
    # MNDWI
    np.seterr(divide='ignore', invalid='ignore')
    mndwi = np.divide(
        (green - swir),
        (green + swir),
        out=np.zeros_like(green),
        where=(green + swir) != 0
    )
    
    # NDVI
    ndvi = np.divide(
        (nir - red),
        (nir + red),
        out=np.zeros_like(nir),
        where=(nir + red) != 0
    )
    
    # Otsu threshold on MNDWI
    valid_mndwi = mndwi[np.isfinite(mndwi) & (mndwi != 0)]
    thresh = threshold_otsu(valid_mndwi)
    
    print(f"MNDWI Otsu threshold: {thresh:.4f}")
    print(f"NDVI vegetation threshold: 0.3 (excludes pixels > 0.3)")
    
    # Combined mask: water AND not vegetation
    water_mask = (mndwi > thresh) & (ndvi < 0.3)
    
    # Clean
    water_clean = morphology.remove_small_objects(water_mask.astype(bool), min_size=MIN_WATER_SIZE)
    water_final = morphology.remove_small_holes(water_clean, area_threshold=MIN_HOLE_SIZE)
    water_final = morphology.binary_closing(water_final, selem=morphology.disk(1))
    
    # Save
    meta.update(count=1, dtype=rasterio.uint8, nodata=None)
    output_full = f"{output_dir}/{output_path}"
    with rasterio.open(output_full, 'w', **meta) as dst:
        dst.write(water_final.astype(np.uint8), 1)
    
    print(f"Output: {output_full}")
    print(f"Water coverage: {np.sum(water_final) / water_final.size * 100:.2f}%")
    return output_full

# ============================================================================
# METHOD 2: MNDWI with fixed threshold (if Otsu is unstable)
# ============================================================================
def mndwi_fixed_threshold(tif_path, threshold=0.1, output_path='delta_mask_mndwi_fixed.tif'):
    """
    Use fixed threshold instead of Otsu (good for very noisy or sediment-rich areas).
    """
    print("\n" + "="*60)
    print(f"METHOD 2: MNDWI with Fixed Threshold ({threshold})")
    print("="*60)
    
    with rasterio.open(tif_path) as src:
        green = src.read(GREEN_BAND).astype(float)
        swir = src.read(SWIR_BAND).astype(float)
        meta = src.meta.copy()
    
    np.seterr(divide='ignore', invalid='ignore')
    mndwi = np.divide(
        (green - swir),
        (green + swir),
        out=np.zeros_like(green),
        where=(green + swir) != 0
    )
    
    water_mask = (mndwi > threshold)
    
    # Clean
    water_clean = morphology.remove_small_objects(water_mask.astype(bool), min_size=MIN_WATER_SIZE)
    water_final = morphology.remove_small_holes(water_clean, area_threshold=MIN_HOLE_SIZE)
    water_final = morphology.binary_closing(water_final, selem=morphology.disk(1))
    
    # Save
    meta.update(count=1, dtype=rasterio.uint8, nodata=None)
    output_full = f"{output_dir}/{output_path}"
    with rasterio.open(output_full, 'w', **meta) as dst:
        dst.write(water_final.astype(np.uint8), 1)
    
    print(f"Output: {output_full}")
    print(f"Water coverage: {np.sum(water_final) / water_final.size * 100:.2f}%")
    return output_full

# ============================================================================
# METHOD 3: NDBI (Normalized Difference Built-in Index) for mudflats/exposed area
# ============================================================================
def ndbi_mask(tif_path, output_path='delta_mask_ndbi.tif'):
    """
    NDBI highlights built-in/exposed areas (useful for mudflats separate from water).
    """
    print("\n" + "="*60)
    print("METHOD 3: NDBI (For mudflat/exposed area detection)")
    print("="*60)
    
    with rasterio.open(tif_path) as src:
        swir1 = src.read(SWIR_BAND).astype(float)
        nir = src.read(NIR_BAND).astype(float)
        meta = src.meta.copy()
    
    np.seterr(divide='ignore', invalid='ignore')
    ndbi = np.divide(
        (swir1 - nir),
        (swir1 + nir),
        out=np.zeros_like(swir1),
        where=(swir1 + nir) != 0
    )
    
    valid_ndbi = ndbi[np.isfinite(ndbi) & (ndbi != 0)]
    thresh = threshold_otsu(valid_ndbi)
    
    print(f"NDBI Otsu threshold: {thresh:.4f}")
    
    exposed_mask = (ndbi > thresh)
    
    # Clean
    exposed_clean = morphology.remove_small_objects(exposed_mask.astype(bool), min_size=MIN_WATER_SIZE)
    exposed_final = morphology.remove_small_holes(exposed_clean, area_threshold=MIN_HOLE_SIZE)
    
    # Save
    meta.update(count=1, dtype=rasterio.uint8, nodata=None)
    output_full = f"{output_dir}/{output_path}"
    with rasterio.open(output_full, 'w', **meta) as dst:
        dst.write(exposed_final.astype(np.uint8), 1)
    
    print(f"Output: {output_full}")
    print(f"Exposed area coverage: {np.sum(exposed_final) / exposed_final.size * 100:.2f}%")
    return output_full

# ============================================================================
# METHOD 4: Three-way classification (water, exposed, land)
# ============================================================================
def three_way_classification(tif_path, output_path='delta_mask_3way.tif'):
    """
    Create three-class map: 0=land, 1=exposed/mudflat, 2=water
    """
    print("\n" + "="*60)
    print("METHOD 4: Three-Way Classification")
    print("="*60)
    
    with rasterio.open(tif_path) as src:
        green = src.read(GREEN_BAND).astype(float)
        red = src.read(RED_BAND).astype(float)
        nir = src.read(NIR_BAND).astype(float)
        swir = src.read(SWIR_BAND).astype(float)
        meta = src.meta.copy()
    
    np.seterr(divide='ignore', invalid='ignore')
    
    mndwi = np.divide((green - swir), (green + swir), 
                      out=np.zeros_like(green), where=(green + swir) != 0)
    ndvi = np.divide((nir - red), (nir + red), 
                     out=np.zeros_like(nir), where=(nir + red) != 0)
    ndbi = np.divide((swir - nir), (swir + nir), 
                     out=np.zeros_like(swir), where=(swir + nir) != 0)
    
    valid_mndwi = mndwi[np.isfinite(mndwi) & (mndwi != 0)]
    valid_ndbi = ndbi[np.isfinite(ndbi) & (ndbi != 0)]
    
    thresh_mndwi = threshold_otsu(valid_mndwi)
    thresh_ndbi = threshold_otsu(valid_ndbi)
    
    # Classification logic
    classification = np.zeros_like(mndwi, dtype=np.uint8)
    
    # Water: MNDWI high
    classification[mndwi > thresh_mndwi] = 2
    
    # Exposed: NDBI high but MNDWI low
    classification[(ndbi > thresh_ndbi) & (mndwi < thresh_mndwi)] = 1
    
    # Land: everything else (0)
    
    print(f"MNDWI threshold: {thresh_mndwi:.4f}")
    print(f"NDBI threshold: {thresh_ndbi:.4f}")
    
    # Save
    meta.update(count=1, dtype=rasterio.uint8, nodata=0)
    output_full = f"{output_dir}/{output_path}"
    with rasterio.open(output_full, 'w', **meta) as dst:
        dst.write(classification, 1)
    
    print(f"Output: {output_full}")
    print(f"Land: {np.sum(classification == 0) / classification.size * 100:.2f}%")
    print(f"Exposed: {np.sum(classification == 1) / classification.size * 100:.2f}%")
    print(f"Water: {np.sum(classification == 2) / classification.size * 100:.2f}%")
    return output_full

# ============================================================================
# MAIN
# ============================================================================
if __name__ == '__main__':
    input_tif = 'sentinel2.tif'
    
    if not os.path.exists(input_tif):
        print(f"ERROR: {input_tif} not found!")
        exit(1)
    
    print(f"\nProcessing: {input_tif}")
    print(f"Output directory: {output_dir}/")
    
    # Run all methods
    mndwi_ndvi_mask(input_tif)
    mndwi_fixed_threshold(input_tif, threshold=0.1)
    ndbi_mask(input_tif)
    three_way_classification(input_tif)
    
    print("\n" + "="*60)
    print("All methods completed. Compare results in 'output/' directory")
    print("="*60)
