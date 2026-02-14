"""
Test color grading filters to verify FFmpeg syntax
"""
import sys
sys.path.append('.')

from core.processing import get_color_grading_filter

presets = ['none', 'cinematic_warm', 'cool_modern', 'vibrant', 'matte_film', 'bw_contrast']

print("Testing all color grading presets:")
print("=" * 60)

for preset in presets:
    filter_str = get_color_grading_filter(preset)
    print(f"\n{preset}:")
    print(f"  Filter: {filter_str if filter_str else '(none)'}")
    
    # Check for problematic characters
    if "'" in filter_str or '"' in filter_str:
        print(f"  ⚠️  WARNING: Contains quotes!")
    if filter_str and ',' in filter_str:
        filters = [f.strip() for f in filter_str.split(',')]
        print(f"  Contains {len(filters)} chained filters")
        for i, f in enumerate(filters, 1):
            print(f"    {i}. {f}")

print("\n" + "=" * 60)
print("✅ All presets loaded successfully")
