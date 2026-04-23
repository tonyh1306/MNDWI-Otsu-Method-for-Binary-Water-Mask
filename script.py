import rasterio
import numpy as np
from skimage.filters import threshold_otsu, gaussian
from skimage import morphology
from scipy import ndimage
import warnings

# ============================================================================
# CONFIGURATION - OPTIMIZED FOR SELENGA DELTA
# ============================================================================
input_tif = 'Landsat89.tif'
output_tif = 'landsat_water_mask.tif'

# Band indices (1-based for rasterio)
GREEN_BAND = 3      # Band 3 = Green
SWIR_BAND = 6       # Band 6 = SWIR2

# OPTIMIZED MORPHOLOGICAL PARAMETERS FOR SELENGA
MIN_WATER_SIZE = 200         # Larger: removes sediment noise and small islands
MEDIAN_FILTER_SIZE = 5       # Stronger despeckling for sediment patterns
MORPH_CLOSE_RADIUS = 3       # Larger: fills narrow gaps between water bodies
MORPH_OPEN_RADIUS = 2        # Removes thin noise spikes
GAUSSIAN_SIGMA = 1.5         # Smoothing to reduce MNDWI noise

# Otsu threshold tuning
THRESHOLD_OFFSET = 0.0       # Adjust Otsu: positive=more water, negative=less water
USE_HISTOGRAM_CLIP = True    # Ignore extreme outliers before Otsu (better for deltas)
HISTOGRAM_CLIP_PERCENTILE = 99  # Clip to 99th percentile before Otsu

# ============================================================================
# LOAD DATA
# ============================================================================
print(f"Loading {input_tif}...")
try:
    with rasterio.open(input_tif) as src:
        green_band = src.read(GREEN_BAND).astype(float)
        swir_band = src.read(SWIR_BAND).astype(float)
        meta = src.meta.copy()
        crs = src.crs
        transform = src.transform
        print(f"  CRS: {crs}")
        print(f"  Shape: {green_band.shape}")
except Exception as e:
    print(f"ERROR reading TIFF: {e}")
    exit(1)

# ============================================================================
# COMPUTE MNDWI (Modified Normalized Difference Water Index)
# ============================================================================
print("\nComputing MNDWI...")
np.seterr(divide='ignore', invalid='ignore')

denominator = (green_band + swir_band)
mndwi = np.divide(
    (green_band - swir_band), 
    denominator, 
    out=np.zeros_like(green_band), 
    where=denominator != 0
)

# Get valid MNDWI values
valid_mndwi = mndwi[np.isfinite(mndwi) & (mndwi != 0)]

if len(valid_mndwi) == 0:
    print("ERROR: No valid MNDWI values found.")
    exit(1)

print(f"  MNDWI range: {valid_mndwi.min():.4f} to {valid_mndwi.max():.4f}")
print(f"  MNDWI median: {np.median(valid_mndwi):.4f}")

# ============================================================================
# OPTIMIZED OTSU THRESHOLD WITH HISTOGRAM CLIPPING
# ============================================================================
print("\nCalculating Otsu threshold...")

if USE_HISTOGRAM_CLIP:
    # Clip extreme outliers for more stable Otsu threshold
    clip_value = np.percentile(valid_mndwi, HISTOGRAM_CLIP_PERCENTILE)
    mndwi_clipped = mndwi.copy()
    mndwi_clipped[mndwi > clip_value] = clip_value
    valid_mndwi_clipped = mndwi_clipped[np.isfinite(mndwi_clipped) & (mndwi_clipped != 0)]
    thresh = threshold_otsu(valid_mndwi_clipped)
    print(f"  Histogram clipped at {HISTOGRAM_CLIP_PERCENTILE}th percentile ({clip_value:.4f})")
else:
    thresh = threshold_otsu(valid_mndwi)

# Apply threshold offset for tuning
thresh_original = thresh
thresh = thresh + THRESHOLD_OFFSET
print(f"  Otsu threshold: {thresh_original:.4f}")
if THRESHOLD_OFFSET != 0:
    print(f"  Adjusted threshold: {thresh:.4f} (offset: {THRESHOLD_OFFSET:+.4f})")

# ============================================================================
# CREATE BINARY MASK
# ============================================================================
print("\nCreating binary water mask...")
water_mask = (mndwi > thresh).astype(bool)

# ============================================================================
# OPTIMIZED MORPHOLOGICAL CLEANING FOR SELENGA DELTA
# ============================================================================
print("\nApplying optimized morphological pipeline...")

# 1. Gaussian smoothing to reduce noise in MNDWI
print(f"  1. Gaussian smoothing (σ={GAUSSIAN_SIGMA})...")
mndwi_smooth = gaussian(mndwi, sigma=GAUSSIAN_SIGMA)
water_mask = (mndwi_smooth > thresh).astype(bool)

# 2. Median filter to reduce speckle (sediment patterns)
print(f"  2. Median filter (size={MEDIAN_FILTER_SIZE}x{MEDIAN_FILTER_SIZE})...")
from scipy.ndimage import median_filter
water_filtered = median_filter(water_mask.astype(np.uint8), size=MEDIAN_FILTER_SIZE) > 0

# 3. Remove small noise pixels
print(f"  3. Removing noise (<{MIN_WATER_SIZE} pixels)...")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_cleaned = morphology.remove_small_objects(water_filtered, min_size=MIN_WATER_SIZE)

# 4. Close small gaps (morphological closing)
print(f"  4. Morphological closing (radius={MORPH_CLOSE_RADIUS})...")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_closed = morphology.closing(water_cleaned, footprint=morphology.disk(MORPH_CLOSE_RADIUS))

# 5. Open spiky noise (morphological opening)
print(f"  5. Morphological opening (radius={MORPH_OPEN_RADIUS})...")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_final = morphology.opening(water_closed, footprint=morphology.disk(MORPH_OPEN_RADIUS))

# 6. Final cleanup: remove any remaining small islands
print(f"  6. Final noise removal...")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_final = morphology.remove_small_objects(water_final, min_size=MIN_WATER_SIZE // 2)

water_final = water_final.astype(np.uint8)
print(f"Saving to {output_tif}...")
meta.update(
    count=1,
    dtype=rasterio.uint8,
    nodata=None
)

with rasterio.open(output_tif, 'w', **meta) as dst:
    dst.write(water_final, 1)

# ============================================================================
# STATISTICS
# ============================================================================
water_pixels = np.sum(water_final)
total_pixels = water_final.size
water_percentage = (water_pixels / total_pixels) * 100

print("\n" + "="*60)
print("RESULTS")
print("="*60)
print(f"Water pixels: {water_pixels:,}")
print(f"Land pixels: {total_pixels - water_pixels:,}")
print(f"Water coverage: {water_percentage:.2f}%")
print(f"\nOutput saved to: {output_tif}")
print("="*60)