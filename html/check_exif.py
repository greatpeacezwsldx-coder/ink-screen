import sqlite3
import json

conn = sqlite3.connect('photos.db')
cur = conn.cursor()

cur.execute("SELECT path, exif_json FROM photo_scores WHERE path LIKE '%16.10.17-家中小红帽%'")
rows = cur.fetchall()
print(f"Found {len(rows)} records")
for path, exif_json in rows:
    print(f"\nPath: {path}")
    print(f"Exif JSON: {exif_json}")
    if exif_json:
        try:
            data = json.loads(exif_json)
            print(f"Parsed data keys: {list(data.keys())}")
            print(f"datetime: {data.get('datetime')}")
        except Exception as e:
            print(f"JSON parse error: {e}")

conn.close()