import sqlite3
conn = sqlite3.connect('photos.db')
cur = conn.cursor()
cur.execute("SELECT COUNT(*) FROM photo_scores WHERE caption IS NOT NULL AND caption <> ''")
print(cur.fetchone()[0])
conn.close()