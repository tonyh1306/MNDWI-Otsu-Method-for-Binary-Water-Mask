"""
Comparison visualization: with and without isolated noise patches
"""

import rasterio
import numpy as np
from skimage.filters import threshold_otsu
from skimage import morphology
from scipy import ndimage
import matplotlib.pyplot as plt

input_tif = 'sentinel2.tif'
GREEN_BAND = 3
SWIR_BAND = 6
MIN_WATER_SIZE = 50
MEDIAN_FILTER_SIZE = 3

print("Loading data...")
with rasterio.open(input_tif) as src:
    green_band = src.read(GREEN_BAND).astype(float)
    swir_band = src.read(SWIR_BAND).astype(float)

# Compute MNDWI
print("Computing MNDWI...")
np.seterr(divide='ignore', invalid='ignore')
mndwi = np.divide(
    (green_band - swir_band),
    (green_band + swir_band + 1e-10),
    out=np.zeros_like(green_band),
    where=(green_band + swir_band) != 0
)

valid_mndwi = mndwi[np.isfinite(mndwi)]
thresh = threshold_otsu(valid_mndwi)

# Step 1: Raw binary
water_raw = (mndwi > thresh).astype(bool)

# Step 2: Median filter
from scipy.ndimage import median_filter
water_median = median_filter(water_raw.astype(np.uint8), size=MEDIAN_FILTER_SIZE) > 0

# Step 3: Remove small objects
labeled, num_features = ndimage.label(water_median)
sizes = ndimage.sum(water_median, labeled, range(num_features + 1))
water_clean = np.zeros_like(water_median, dtype=bool)
for i in range(1, num_features + 1):
    if sizes[i] >= MIN_WATER_SIZE:
        water_clean[labeled == i] = True

# Step 4: Morphological smoothing
water_smooth = morphology.closing(water_clean, footprint=morphology.disk(2))
water_smooth = morphology.opening(water_smooth, footprint=morphology.disk(1))

# Step 5: Keep only largest component (NOISE REMOVAL)
labeled_final, num_final = ndimage.label(water_smooth)
sizes_final = ndimage.sum(water_smooth, labeled_final, range(num_final + 1))
sorted_indices = np.argsort(sizes_final)[::-1]

water_with_noise = water_smooth.copy()
water_without_noise = np.zeros_like(water_smooth, dtype=bool)
water_without_noise[labeled_final == sorted_indices[1]] = True  # Keep largest

# ============================================================================
# VISUALIZATION
# ============================================================================
fig, axes = plt.subplots(1, 2, figsize=(16, 7))

# With isolated noise
axes[0].imshow(water_with_noise, cmap='RdYlBu', vmin=0, vmax=1)
axes[0].set_title('With Isolated Noise Patches', fontsize=14, fontweight='bold')
axes[0].set_xlabel(f'Water coverage: {np.sum(water_with_noise) / water_with_noise.size * 100:.2f}%')
axes[0].set_xticks([])
axes[0].set_yticks([])

# Without isolated noise
axes[1].imshow(water_without_noise, cmap='RdYlBu', vmin=0, vmax=1)
axes[1].set_title('Main Delta Only (Noise Removed)', fontsize=14, fontweight='bold')
axes[1].set_xlabel(f'Water coverage: {np.sum(water_without_noise) / water_without_noise.size * 100:.2f}%')
axes[1].set_xticks([])
axes[1].set_yticks([])

plt.tight_layout()
plt.savefig('mndwi_noise_comparison.png', dpi=150, bbox_inches='tight')
print("Comparison saved to: mndwi_noise_comparison.png")
plt.show()

# ============================================================================
# STATISTICS
# ============================================================================
print("\n" + "="*70)
print("NOISE REMOVAL STATISTICS")
print("="*70)

noise_pixels = np.sum(water_with_noise) - np.sum(water_without_noise)
noise_percentage = noise_pixels / water_with_noise.size * 100

print(f"Water with noise: {np.sum(water_with_noise):,} pixels ({np.sum(water_with_noise) / water_with_noise.size * 100:.2f}%)")
print(f"Main delta only:  {np.sum(water_without_noise):,} pixels ({np.sum(water_without_noise) / water_without_noise.size * 100:.2f}%)")
print(f"Noise removed:    {noise_pixels:,} pixels ({noise_percentage:.2f}%)")
print("="*70)
