import sys
sys.path.insert(0, '.')

from server import get_photo_meta_by_path

paths = [
    "H:\\html\\test\\15个月.jpg",
    "H:\\html\\test\\16.10.17-家中小红帽.JPG"
]

for path in paths:
    print(f"\nTesting: {path}")
    meta = get_photo_meta_by_path(path)
    if meta:
        print(f"  date: {meta.get('date')}")
        print(f"  side: {meta.get('side')}")
        print(f"  memory: {meta.get('memory')}")
    else:
        print("  meta is None")