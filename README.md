# Selenga Delta Binary Water Mask - Optimized MNDWI + Otsu Pipeline

This is an **optimized** implementation for creating clean, high-quality binary water masks of the Selenga delta using MNDWI (Modified Normalized Difference Water Index) with automatic Otsu thresholding.

**Key improvements:**
- Gaussian smoothing to reduce spectral noise
- Stronger morphological operators for delta sediment patterns
- Histogram clipping to stabilize Otsu threshold
- Multi-step closing + opening for cleaner edges
- Tunable threshold offset for fine-grained control

## Prerequisites

```bash
pip install -r requirements.txt
```

Required packages:
- `rasterio` - For reading/writing GeoTIFF files
- `numpy` - Array operations
- `scikit-image` - Image processing (filters, morphology)
- `scipy` - Scientific computing
- `matplotlib` - Visualization (optional)

## Quick Start

### 1. Prepare Your Data

Place your Sentinel-2 TIF file in this directory:
```
sentinel2.tif
```

**Important:** Ensure your TIFF has bands in this order:
- Band 3: Green (wavelength ~560 nm)
- Band 11: SWIR (wavelength ~1610 nm)

If your bands are in a different order, edit `script.py` and adjust `GREEN_BAND` and `SWIR_BAND`.

### 2. Run the Main Script

```bash
python3 script.py
```

This will:
- Compute MNDWI
- Calculate Otsu threshold automatically
- Clean the mask (remove noise, fill holes)
- Save output as `selenga_water_mask.tif`

### 3. Visualize Results (Optional)

```bash
python3 visualize.py
```

This creates `mndwi_analysis.png` showing:
- MNDWI heatmap
- MNDWI histogram with Otsu threshold
- Step-by-step mask cleaning process
- Statistics

## Method Overview

### MNDWI (Modified Normalized Difference Water Index)
$$\text{MNDWI} = \frac{\text{Green} - \text{SWIR}}{\text{Green} + \text{SWIR}}$$

**Why MNDWI for deltas?**
- Works well with turbid/sediment-rich water
- Reduces confusion from vegetation and wet soil
- Proven effective for sediment-dominated systems

### Otsu Automatic Thresholding
- Automatically determines optimal threshold from histogram
- Minimizes within-class variance
- Robust to different water types and sediment loads

### Morphological Cleaning (Optimized for Selenga)
1. **Gaussian smoothing** - Reduces spectral noise in MNDWI before thresholding
2. **Median filter** - Removes speckle patterns from sediment
3. **Remove small objects** - Eliminates noisy pixels (< 200 px default)
4. **Morphological closing** - Fills gaps between water bodies (radius 3)
5. **Morphological opening** - Removes thin spike noise (radius 2)
6. **Final cleanup** - Second pass to catch any remaining artifacts

## Output

`selenga_water_mask.tif` contains:
- Single-band GeoTIFF
- 8-bit unsigned integer (0 = land, 1 = water)
- Same CRS and geotransform as input
- Ready for GIS analysis

## Troubleshooting

### "No valid MNDWI values found"
- Check that Green is band 3 and SWIR is band 11
- Verify TIFF file is valid: `gdalinfo sentinel2.tif`

### Mask is too noisy
- Increase `MIN_WATER_SIZE` (e.g., 100-200)
- Increase `MEDIAN_FILTER_SIZE` (e.g., 3-5)
- Try fixed threshold: change line in script from `mndwi > thresh` to `mndwi > 0.1`

### Important water features are missing
- Decrease `MIN_WATER_SIZE`
- Try lower threshold: `mndwi > (thresh * 0.8)`
- Check input data for cloud cover or atmospheric issues

### Wetlands confused with water
- Use advanced script with combined indices
- Add NDVI filter: see `advanced_multi_index.py`

## Advanced Options

For more complex scenarios, see `advanced_multi_index.py`:
- **Multi-temporal compositing** - Average multiple dates for stability
- **Combined indices** - MNDWI + NDVI to exclude vegetation
- **Custom thresholds** - Manual control if Otsu is unstable

## Parameters to Tune

All parameters are in `script.py`:

```python
# CORE MORPHOLOGICAL PARAMETERS
MIN_WATER_SIZE = 200              # Larger = fewer small islands (default: good for 10m pixels)
MEDIAN_FILTER_SIZE = 5            # Larger = smoother, less texture (1-7 typical)
MORPH_CLOSE_RADIUS = 3            # Larger = fills wider gaps
MORPH_OPEN_RADIUS = 2             # Larger = removes thicker noise

# GAUSSIAN SMOOTHING
GAUSSIAN_SIGMA = 1.5              # Smoothness before thresholding (0.5-3.0)

# THRESHOLD TUNING  
THRESHOLD_OFFSET = 0.0            # Positive = more water, Negative = less water
USE_HISTOGRAM_CLIP = True          # Stabilizes Otsu for outliers
HISTOGRAM_CLIP_PERCENTILE = 99     # Ignore top 1% extreme values
```

### Quick Tuning Guide

**Result looks too noisy with speckles:**
- Increase `GAUSSIAN_SIGMA` (e.g., 2.0-3.0)
- Increase `MEDIAN_FILTER_SIZE` (e.g., 7)
- Decrease `THRESHOLD_OFFSET` (e.g., -0.05)

**Missing water bodies or channels are broken:**
- Decrease `MIN_WATER_SIZE` (e.g., 100)
- Increase `MORPH_CLOSE_RADIUS` (e.g., 4-5)
- Increase `THRESHOLD_OFFSET` (e.g., +0.05)

**Too much land included (mudflats as water):**
- Increase `MIN_WATER_SIZE` (e.g., 300-500)
- Increase `THRESHOLD_OFFSET` (e.g., +0.10)
- Decrease `GAUSSIAN_SIGMA`

**Mask edges are jagged:**
- Increase `GAUSSIAN_SIGMA` (e.g., 2.0)
- Increase `MORPH_OPEN_RADIUS` (e.g., 3-4)

## Publications Reference

Method adapted from:
- Herring et al. (2019): Arctic river ice classification with Sentinel-1/2
- Link: https://doi.org/10.1029/2019JF005250

Original paper examples showed similar delta-classification methods but for ice cover. This implementation generalizes to land-water classification.

## Output Validation

Check your results:
```bash
gdalinfo selenga_water_mask.tif
gdal_translate -of PNG selenga_water_mask.tif preview.png  # Visual check
```

## Questions?

If results need refinement:
1. Run `visualize.py` to see histogram and intermediate steps
2. Adjust parameters incrementally
3. Check MNDWI range - should span negative (land) to positive (water)
4. Verify input bands are correct using `gdalinfo`
