import os
import sys

os.chdir(r'e:\cc servber bot')

files_to_delete = [
    'err.txt', 'out.txt', 'DEPLOYMENT.md', 'IMPLEMENTATION_COMPLETE.md',
    'IMPLEMENTATION_SUMMARY.txt', 'QUICK_REFERENCE.py', 'PROJECT_STRUCTURE.md',
    'check_resolution.py', 'crop_icons.py', 'debug_ocr.py', 'find_loot_pos.py',
    'test_ocr_regions.py', 'verify_loot_regions.py', 'zone_picker.py', 'take_ss.py',
    'checklist.py', 'setup.py', 'test_atlas.py', 'render.yaml', 'railway.json'
]

for f in files_to_delete:
    try:
        if os.path.exists(f):
            os.remove(f)
            print(f"Deleted: {f}")
    except Exception as e:
        print(f"Error deleting {f}: {e}")

# Also delete from server subfolder
server_files = ['render.yaml', 'railway.json']
for f in server_files:
    path = os.path.join('server', f)
    try:
        if os.path.exists(path):
            os.remove(path)
            print(f"Deleted: {path}")
    except Exception as e:
        print(f"Error deleting {path}: {e}")

print("\nCleanup complete!")
os.remove('cleanup.py')  # Self-delete
