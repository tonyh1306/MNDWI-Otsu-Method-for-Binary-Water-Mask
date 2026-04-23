"""
Batch processing script for multiple Sentinel-2 dates.
Use when processing time series of Selenga delta imagery.
"""

import os
import glob
import rasterio
import numpy as np
from skimage.filters import threshold_otsu, median
from skimage import morphology
from pathlib import Path
from datetime import datetime

class DeltaMaskProcessor:
    """Batch processor for delta water masks."""
    
    def __init__(self, input_dir='raw_sentinel2', output_dir='processed_masks'):
        self.input_dir = input_dir
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        
        # Parameters (tunable)
        self.green_band = 3
        self.swir_band = 11
        self.min_water_size = 50
        self.min_hole_size = 50
        self.median_size = 3
    
    def process_single(self, tif_path):
        """Process one Sentinel-2 TIF file."""
        basename = Path(tif_path).stem
        output_path = os.path.join(self.output_dir, f"{basename}_watermask.tif")
        
        print(f"\nProcessing: {basename}")
        
        try:
            with rasterio.open(tif_path) as src:
                green = src.read(self.green_band).astype(float)
                swir = src.read(self.swir_band).astype(float)
                meta = src.meta.copy()
            
            # MNDWI
            np.seterr(divide='ignore', invalid='ignore')
            mndwi = np.divide(
                (green - swir),
                (green + swir),
                out=np.zeros_like(green),
                where=(green + swir) != 0
            )
            
            # Otsu
            valid = mndwi[np.isfinite(mndwi) & (mndwi != 0)]
            if len(valid) == 0:
                print(f"  ✗ No valid MNDWI values")
                return False
            
            thresh = threshold_otsu(valid)
            
            # Binary mask and cleaning
            water = (mndwi > thresh).astype(bool)
            water = morphology.remove_small_objects(water, min_size=self.min_water_size)
            water = morphology.remove_small_holes(water, area_threshold=self.min_hole_size)
            water = morphology.binary_closing(water, selem=morphology.disk(1))
            
            # Save
            meta.update(count=1, dtype=rasterio.uint8, nodata=None)
            with rasterio.open(output_path, 'w', **meta) as dst:
                dst.write(water.astype(np.uint8), 1)
            
            water_pct = np.sum(water) / water.size * 100
            print(f"  ✓ Saved ({water_pct:.1f}% water)")
            return True
            
        except Exception as e:
            print(f"  ✗ Error: {e}")
            return False
    
    def process_batch(self, pattern='*.tif'):
        """Process all matching TIF files."""
        files = glob.glob(os.path.join(self.input_dir, pattern))
        
        if not files:
            print(f"No files matching '{pattern}' in {self.input_dir}")
            return
        
        print("="*70)
        print(f"BATCH PROCESSING: {len(files)} files")
        print("="*70)
        
        successful = 0
        for filepath in sorted(files):
            if self.process_single(filepath):
                successful += 1
        
        print("\n" + "="*70)
        print(f"COMPLETE: {successful}/{len(files)} successful")
        print(f"Output: {self.output_dir}/")
        print("="*70)
    
    def set_parameters(self, min_water_size=None, min_hole_size=None, median_size=None):
        """Adjust processing parameters."""
        if min_water_size:
            self.min_water_size = min_water_size
        if min_hole_size:
            self.min_hole_size = min_hole_size
        if median_size:
            self.median_size = median_size

# ============================================================================
# USAGE EXAMPLES
# ============================================================================

if __name__ == '__main__':
    
    # Example 1: Process all TIFs in raw_sentinel2/ directory
    processor = DeltaMaskProcessor(
        input_dir='raw_sentinel2',
        output_dir='processed_masks'
    )
    processor.process_batch(pattern='*.tif')
    
    # Example 2: With custom parameters (if dealing with very noisy data)
    # processor.set_parameters(min_water_size=100, median_size=5)
    # processor.process_batch(pattern='*.tif')
    
    # Example 3: Process specific date range
    # processor.process_batch(pattern='*2023-06*.tif')
    
    # Example 4: Single file
    # processor.process_single('raw_sentinel2/sentinel2_20230615.tif')

# ============================================================================
# NOTES ON BATCH PROCESSING
# ============================================================================

"""
WHEN TO USE BATCH PROCESSING:

1. Time series analysis of Selenga delta
   • Multiple dates across a season
   • Seasonal change analysis
   • Discharge vs. water extent correlation

2. Google Earth Engine exports
   • GEE can export multiple Sentinel-2 scenes
   • Batch script processes them locally
   • Faster than reprocessing through GEE

WORKFLOW:

1. Prepare input directory:
   mkdir raw_sentinel2/
   # Copy all Sentinel-2 TIF files here

2. Run batch processor:
   python3 batch_processor.py

3. Check outputs:
   ls processed_masks/
   # Each TIF gets _watermask.tif suffix

4. Post-processing:
   # Extract statistics (see example below)
   python3 -c "
   import os, rasterio
   import numpy as np
   for f in sorted(os.listdir('processed_masks')):
       with rasterio.open(f'processed_masks/{f}') as src:
           mask = src.read(1)
           pct = np.sum(mask) / mask.size * 100
           print(f'{f}: {pct:.1f}% water')
   "

EXPECTED PROCESSING SPEED:

• Per image: 5-30 seconds (depending on size)
• 10 images: ~1-5 minutes
• 100 images: ~10-50 minutes

If you have many images, consider parallelization:
  from multiprocessing import Pool
  with Pool(4) as pool:
      pool.map(processor.process_single, file_list)

QUALITY CONTROL:

Run visualize.py on a sample output to verify:
  • Threshold is reasonable
  • Mask quality is acceptable
  • If not, adjust parameters and rerun batch

COMBINING RESULTS:

After batch processing, you can:
  • Stack masks into time series cube
  • Calculate water extent vs. time
  • Create animations of delta changes
  • Export to vector polygons for each date

Example: Stack all outputs
  gdal_merge.py -separate processed_masks/*.tif -o delta_timeseries.tif
"""
