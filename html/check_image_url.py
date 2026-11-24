import sys
sys.path.insert(0, '.')

from pathlib import Path
import config as cfg

ROOT_DIR = Path(__file__).resolve().parent

IMAGE_DIR = Path(str(getattr(cfg, "IMAGE_DIR", "") or "")).expanduser()
if not IMAGE_DIR.is_absolute():
    IMAGE_DIR = (ROOT_DIR / IMAGE_DIR).resolve()

print(f"IMAGE_DIR: {IMAGE_DIR}")

def _make_image_url(path_str: str) -> str:
    try:
        p = Path(path_str).expanduser().resolve()
        rel = p.relative_to(IMAGE_DIR.resolve())
        return "/images/" + str(rel).replace("\\", "/")
    except Exception as e:
        return f"ERROR: {e}"

paths = [
    "H:\\html\\test\\15个月.jpg",
    "H:\\html\\test\\16.10.17-家中小红帽.JPG"
]

for path in paths:
    print(f"\nPath: {path}")
    url = _make_image_url(path)
    print(f"URL: {url}")
    
    p = Path(path)
    print(f"File exists: {p.exists()}")
    if p.exists():
        print(f"File size: {p.stat().st_size} bytes")