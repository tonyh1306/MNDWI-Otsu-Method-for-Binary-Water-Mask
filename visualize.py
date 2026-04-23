"""
Visualization script for optimized MNDWI pipeline.
Shows intermediate processing steps and quality metrics.
"""

import rasterio
import numpy as np
from skimage.filters import threshold_otsu, gaussian
from skimage import morphology
from scipy.ndimage import median_filter
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

# ============================================================================
# MATCH script.py CONFIGURATION
# ============================================================================
input_tif = 'Landsat89.tif'
GREEN_BAND = 3
SWIR_BAND = 6

# Parameters must match script.py
MIN_WATER_SIZE = 200
MEDIAN_FILTER_SIZE = 5
MORPH_CLOSE_RADIUS = 3
MORPH_OPEN_RADIUS = 2
GAUSSIAN_SIGMA = 1.5
THRESHOLD_OFFSET = 0.0
USE_HISTOGRAM_CLIP = True
HISTOGRAM_CLIP_PERCENTILE = 99

# ============================================================================
# LOAD DATA & COMPUTE MNDWI
# ============================================================================
print("Loading and processing data...")
with rasterio.open(input_tif) as src:
    green_band = src.read(GREEN_BAND).astype(float)
    swir_band = src.read(SWIR_BAND).astype(float)

np.seterr(divide='ignore', invalid='ignore')
denominator = (green_band + swir_band)
mndwi = np.divide(
    (green_band - swir_band), 
    denominator, 
    out=np.zeros_like(green_band), 
    where=denominator != 0
)

valid_mndwi = mndwi[np.isfinite(mndwi) & (mndwi != 0)]

# Otsu threshold
if USE_HISTOGRAM_CLIP:
    clip_value = np.percentile(valid_mndwi, HISTOGRAM_CLIP_PERCENTILE)
    mndwi_clipped = mndwi.copy()
    mndwi_clipped[mndwi > clip_value] = clip_value
    valid_mndwi_clipped = mndwi_clipped[np.isfinite(mndwi_clipped) & (mndwi_clipped != 0)]
    thresh = threshold_otsu(valid_mndwi_clipped)
else:
    thresh = threshold_otsu(valid_mndwi)

thresh_adjusted = thresh + THRESHOLD_OFFSET

# ============================================================================
# PROCESS THROUGH PIPELINE
# ============================================================================
# Step 1: Raw threshold
water_raw = (mndwi > thresh_adjusted).astype(bool)

# Step 2: Gaussian smoothing + threshold
mndwi_smooth = gaussian(mndwi, sigma=GAUSSIAN_SIGMA)
water_smooth = (mndwi_smooth > thresh_adjusted).astype(bool)

# Step 3: Median filter
water_filtered = median_filter(water_smooth.astype(np.uint8), size=MEDIAN_FILTER_SIZE) > 0

# Step 4: Remove noise
import warnings
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_cleaned = morphology.remove_small_objects(water_filtered, min_size=MIN_WATER_SIZE)

# Step 5: Closing
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_closed = morphology.closing(water_cleaned, footprint=morphology.disk(MORPH_CLOSE_RADIUS))

# Step 6: Opening
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_final = morphology.opening(water_closed, footprint=morphology.disk(MORPH_OPEN_RADIUS))

# Step 7: Final cleanup
with warnings.catch_warnings():
    warnings.simplefilter("ignore")
    water_final = morphology.remove_small_objects(water_final, min_size=MIN_WATER_SIZE // 2)

# ============================================================================
# CREATE COMPREHENSIVE VISUALIZATION
# ============================================================================
fig, axes = plt.subplots(3, 3, figsize=(18, 14))

# 1. MNDWI Index
im = axes[0, 0].imshow(mndwi, cmap='RdYlBu_r', vmin=-1, vmax=1)
axes[0, 0].set_title('1. MNDWI Index', fontsize=11, fontweight='bold')
plt.colorbar(im, ax=axes[0, 0])

# 2. MNDWI Histogram
axes[0, 1].hist(valid_mndwi, bins=150, color='blue', alpha=0.7, edgecolor='black')
axes[0, 1].axvline(thresh, color='red', linestyle='--', linewidth=2, label=f'Otsu: {thresh:.3f}')
axes[0, 1].axvline(thresh_adjusted, color='orange', linestyle='--', linewidth=2, label=f'Adjusted: {thresh_adjusted:.3f}')
axes[0, 1].set_xlabel('MNDWI Value')
axes[0, 1].set_ylabel('Frequency')
axes[0, 1].set_title('2. MNDWI Histogram + Thresholds', fontsize=11, fontweight='bold')
axes[0, 1].legend(fontsize=9)
axes[0, 1].grid(alpha=0.3)
if USE_HISTOGRAM_CLIP:
    axes[0, 1].axvline(clip_value, color='purple', linestyle=':', linewidth=1.5, label=f'Clip: {clip_value:.3f}')

# 3. Smoothed MNDWI
im = axes[0, 2].imshow(mndwi_smooth, cmap='RdYlBu_r', vmin=-1, vmax=1)
axes[0, 2].set_title(f'3. Gaussian Smoothed (σ={GAUSSIAN_SIGMA})', fontsize=11, fontweight='bold')
plt.colorbar(im, ax=axes[0, 2])

# 4. Raw threshold
axes[1, 0].imshow(water_raw, cmap='gray')
axes[1, 0].set_title('4. Raw Threshold', fontsize=11, fontweight='bold')

# 5. After smoothing + threshold
axes[1, 1].imshow(water_smooth, cmap='gray')
axes[1, 1].set_title('5. After Smoothing', fontsize=11, fontweight='bold')

# 6. After median filter
axes[1, 2].imshow(water_filtered, cmap='gray')
axes[1, 2].set_title(f'6. After Median Filter ({MEDIAN_FILTER_SIZE}x{MEDIAN_FILTER_SIZE})', fontsize=11, fontweight='bold')

# 7. After noise removal
axes[2, 0].imshow(water_cleaned, cmap='gray')
axes[2, 0].set_title(f'7. After Noise Removal (<{MIN_WATER_SIZE}px)', fontsize=11, fontweight='bold')

# 8. After closing
axes[2, 1].imshow(water_closed, cmap='gray')
axes[2, 1].set_title(f'8. After Closing (r={MORPH_CLOSE_RADIUS})', fontsize=11, fontweight='bold')

# 9. Final result
axes[2, 2].imshow(water_final, cmap='gray')
axes[2, 2].set_title(f'9. Final Mask', fontsize=11, fontweight='bold')

# Remove all axis labels
for ax in axes.flatten():
    ax.set_xticks([])
    ax.set_yticks([])

plt.tight_layout()
plt.savefig('mndwi_optimization_pipeline.png', dpi=150, bbox_inches='tight')
print("✓ Pipeline visualization saved to: mndwi_optimization_pipeline.png")
plt.show()

# ============================================================================
# STATISTICS
# ============================================================================
print("\n" + "="*70)
print("OPTIMIZATION PIPELINE STATISTICS")
print("="*70)
print(f"\nMNDWI Statistics:")
print(f"  Range: {valid_mndwi.min():.4f} to {valid_mndwi.max():.4f}")
print(f"  Mean: {valid_mndwi.mean():.4f}")
print(f"  Median: {np.median(valid_mndwi):.4f}")
print(f"  Std Dev: {valid_mndwi.std():.4f}")

print(f"\nThreshold Calculation:")
print(f"  Otsu (raw): {thresh:.4f}")
if THRESHOLD_OFFSET != 0:
    print(f"  Offset: {THRESHOLD_OFFSET:+.4f}")
    print(f"  Final: {thresh_adjusted:.4f}")
if USE_HISTOGRAM_CLIP:
    print(f"  Histogram clipped at {HISTOGRAM_CLIP_PERCENTILE}%ile: {clip_value:.4f}")

print(f"\nWater Coverage Through Pipeline:")
print(f"  Raw threshold:          {np.sum(water_raw) / water_raw.size * 100:6.2f}%")
print(f"  After smoothing:        {np.sum(water_smooth) / water_smooth.size * 100:6.2f}%")
print(f"  After median filter:    {np.sum(water_filtered) / water_filtered.size * 100:6.2f}%")
print(f"  After noise removal:    {np.sum(water_cleaned) / water_cleaned.size * 100:6.2f}%")
print(f"  After closing:          {np.sum(water_closed) / water_closed.size * 100:6.2f}%")
print(f"  Final mask:             {np.sum(water_final) / water_final.size * 100:6.2f}%")

print(f"\nConfiguration Used:")
print(f"  MIN_WATER_SIZE: {MIN_WATER_SIZE}")
print(f"  MEDIAN_FILTER_SIZE: {MEDIAN_FILTER_SIZE}")
print(f"  GAUSSIAN_SIGMA: {GAUSSIAN_SIGMA}")
print(f"  MORPH_CLOSE_RADIUS: {MORPH_CLOSE_RADIUS}")
print(f"  MORPH_OPEN_RADIUS: {MORPH_OPEN_RADIUS}")
print("="*70)
