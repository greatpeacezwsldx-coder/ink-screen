import sqlite3

conn = sqlite3.connect('photos.db')
cur = conn.cursor()

cur.execute("SELECT * FROM photo_scores WHERE path LIKE '%15个月%'")
rows = cur.fetchall()
print(f"Found {len(rows)} records")
for r in rows:
    print(r)

conn.close()