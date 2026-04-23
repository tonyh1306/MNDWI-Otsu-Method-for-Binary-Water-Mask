"""
QUICK REFERENCE GUIDE - Parameter Tuning for Delta Water Masks

Run this to understand what each parameter does and how to adjust them.
"""

PARAMETER_GUIDE = """
╔════════════════════════════════════════════════════════════════════════════╗
║                   WATER MASK PARAMETER TUNING GUIDE                       ║
╚════════════════════════════════════════════════════════════════════════════╝

═══════════════════════════════════════════════════════════════════════════════
1. MIN_WATER_SIZE (default: 50)
═══════════════════════════════════════════════════════════════════════════════
   What: Minimum number of pixels for a water body to keep
   Default: 50 pixels
   
   Effects:
   • Too small (20): Includes speckle noise, noisy output
   • Too large (200): Misses small channels, rivers, ponds
   
   Recommended by scenario:
   ┌──────────────────────────────────────┬─────────────────────┐
   │ Scenario                             │ MIN_WATER_SIZE      │
   ├──────────────────────────────────────┼─────────────────────┤
   │ Large main channel only              │ 200-500             │
   │ Channel + some tributaries           │ 50-100              │
   │ All water features (noisy)           │ 20-30               │
   │ Very noisy input (high sediment)     │ 100-200             │
   │ Mudflats + water confusion           │ 150-300             │
   └──────────────────────────────────────┴─────────────────────┘
   
   Try: Start with 50, increase if noise appears, decrease if features disappear

═══════════════════════════════════════════════════════════════════════════════
2. MIN_HOLE_SIZE (default: 50)
═══════════════════════════════════════════════════════════════════════════════
   What: Minimum hole size to fill inside water bodies
   Default: 50 pixels
   
   Effects:
   • Fills gaps inside water areas (islands, sandbars)
   • Larger values = more aggressive filling
   
   For deltas:
   ┌──────────────────────────────────────┬─────────────────────┐
   │ Feature                              │ MIN_HOLE_SIZE       │
   ├──────────────────────────────────────┼─────────────────────┤
   │ Keep all islands/sandbars            │ 10-20               │
   │ Remove small detritus/noise          │ 50-100              │
   │ Fill channels between islands        │ 100-200             │
   └──────────────────────────────────────┴─────────────────────┘
   
   Selenga tip: Use 50 for braided channels, 100+ for deltaic fans

═══════════════════════════════════════════════════════════════════════════════
3. MEDIAN_FILTER_SIZE (default: 3)
═══════════════════════════════════════════════════════════════════════════════
   What: Size of median filter for despeckling (1=disabled)
   Default: 3 (kernel size 3x3)
   
   Effects:
   • Removes salt-and-pepper noise
   • Smooths edges
   • Higher values = more smoothing but risk losing detail
   
   Values:
   ┌──────────────────────────────────────┬─────────────────────┐
   │ Input Quality                        │ MEDIAN_FILTER_SIZE  │
   ├──────────────────────────────────────┼─────────────────────┤
   │ Clean (low noise)                    │ 1 (disabled)        │
   │ Moderate noise                       │ 3 (default)         │
   │ High noise/sediment confusion        │ 5-7                 │
   └──────────────────────────────────────┴─────────────────────┘
   
   Sentinel-2 note: 3 is usually sufficient, don't go above 5

═══════════════════════════════════════════════════════════════════════════════
4. OTSU THRESHOLD (automatic, but replaceable)
═══════════════════════════════════════════════════════════════════════════════
   What: Threshold that separates water from land on MNDWI values
   Default: Calculated automatically using Otsu's method
   
   When Otsu fails:
   • Very sediment-rich water: might threshold in middle of spectrum
   • Mixed water/wetland: may include vegetation as water
   → Use fixed threshold: water_mask = (mndwi > 0.1)
   
   Fixed threshold guide:
   ┌──────────────────────────────────────┬─────────────────────┐
   │ Water Type                           │ Fixed Threshold     │
   ├──────────────────────────────────────┼─────────────────────┤
   │ Clear water (lakes, oceans)          │ 0.05                │
   │ Normal sediment-rich (deltas)        │ 0.10 (Selenga!)     │
   │ Very turbid/muddy                    │ 0.00 to 0.05        │
   │ Extreme turbidity                    │ -0.05 to 0.00       │
   └──────────────────────────────────────┴─────────────────────┘

═══════════════════════════════════════════════════════════════════════════════
SCENARIOS & SOLUTIONS
═══════════════════════════════════════════════════════════════════════════════

PROBLEM: Output is too noisy with many small spots
DIAGNOSIS: Speckle noise not adequately removed
SOLUTIONS (in order):
  1. Increase MIN_WATER_SIZE → 100-150
  2. Increase MEDIAN_FILTER_SIZE → 5
  3. Lower Otsu threshold → use mndwi > (thresh * 0.9)
  4. Use Method 2 fixed threshold → mndwi > 0.1

PROBLEM: Missing important water channels/features
DIAGNOSIS: Threshold too high or cleaning too aggressive
SOLUTIONS:
  1. Decrease MIN_WATER_SIZE → 20-30
  2. Decrease MEDIAN_FILTER_SIZE → 1 (disable)
  3. Raise Otsu threshold → use mndwi > (thresh * 1.1)
  4. Use fixed lower threshold → mndwi > 0.05

PROBLEM: Wetlands/vegetation being classified as water
DIAGNOSIS: MNDWI alone not discriminating well
SOLUTIONS:
  1. Use advanced script: advanced_multi_index.py
  2. Use Method 1 (MNDWI + NDVI combined)
  3. Add vegetation filter → (mndwi > thresh) & (ndvi < 0.3)

PROBLEM: Sediment plumes extending far beyond delta
DIAGNOSIS: Turbid water with low MNDWI values
SOLUTIONS:
  1. Use higher fixed threshold → 0.15 or 0.20
  2. Reduce MIN_WATER_SIZE to eliminate plume noise
  3. Use Method 3 (NDBI) for exposed areas only

═══════════════════════════════════════════════════════════════════════════════
WORKFLOW FOR SELENGA DELTA
═══════════════════════════════════════════════════════════════════════════════

Step 1: Run basic script with defaults
        python3 script.py
        → visualize.py
        
Step 2: Examine output
        • Is main channel captured? YES → continue
        • Tributaries showing? Depends on needs
        • Noise acceptable? YES → Done!
        
Step 3: If adjustments needed, try:
        • Noisy → increase MIN_WATER_SIZE to 75-100
        • Missing features → decrease MIN_WATER_SIZE to 30
        • Sediment confusion → use fixed threshold 0.15
        
Step 4: If still problematic, use advanced_multi_index.py
        • Method 1 for vegetation discrimination
        • Method 3 for exposed mudflats
        • Method 4 for three-way classification

═══════════════════════════════════════════════════════════════════════════════
QUALITY CHECKS
═══════════════════════════════════════════════════════════════════════════════

After generating mask, check:

☐ Main channel properly classified as water
☐ Major tributaries captured (if desired)
☐ Deltaic islands/bars properly separated
☐ No large isolated noise spots (single/few pixels)
☐ Smooth, continuous water boundaries
☐ Water percentage reasonable for season
   - Typical range for Selenga: 5-15% of delta area
   - Varies with discharge and time of year

Visual validation:
  gdalinfo selenga_water_mask.tif      # Check metadata
  gdal_translate -of PNG {your_mask}.tif preview.png  # Quick visualization

═══════════════════════════════════════════════════════════════════════════════
ADVANCED: COMBINING MULTIPLE INDICES
═══════════════════════════════════════════════════════════════════════════════

If one index insufficient, combine them:

MNDWI + NDVI:
  water = (mndwi > 0.1) & (ndvi < 0.3)  → removes vegetation
  
MNDWI + NDBI:
  water = (mndwi > 0.1) & (ndbi < 0.05)  → removes exposed areas
  
Three-way:
  water = 2: mndwi > 0.1
  exposed = 1: ndbi > 0.1 & mndwi < 0.1
  land = 0: everything else

Implementation: See advanced_multi_index.py for full code

═══════════════════════════════════════════════════════════════════════════════
"""

print(PARAMETER_GUIDE)

# Quick reference table
print("\n" + "="*80)
print("QUICK ADJUSTMENT TABLE")
print("="*80)

adjustments = [
    ("Symptom", "Try This Change", "Expected Result"),
    ("-" * 25, "-" * 30, "-" * 25),
    ("Too much noise", "MIN_WATER_SIZE: 50→100", "Cleaner mask"),
    ("Missing channels", "MIN_WATER_SIZE: 50→25", "More features"),
    ("Speckle pattern", "MEDIAN_FILTER_SIZE: 3→5", "Smoother result"),
    ("Edge artifacts", "MIN_HOLE_SIZE: 50→100", "Better boundaries"),
    ("Weird threshold", "Use fixed: mndwi>0.1", "More stable"),
    ("Vegetation as water", "Use MNDWI+NDVI method", "Cleaner water/land"),
]

for row in adjustments:
    print(f"{row[0]:<25} | {row[1]:<30} | {row[2]:<25}")

print("="*80)
