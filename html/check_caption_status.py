import sqlite3

conn = sqlite3.connect('photos.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM photo_scores")
total = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM photo_scores WHERE caption IS NOT NULL AND caption <> ''")
with_caption = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM photo_scores WHERE reason IS NOT NULL AND reason <> ''")
with_reason = cur.fetchone()[0]

print(f"总记录: {total}")
print(f"有caption: {with_caption}")
print(f"无caption: {total - with_caption}")
print(f"有reason: {with_reason}")
print(f"无reason: {total - with_reason}")

cur.execute("SELECT path, caption, reason FROM photo_scores WHERE caption IS NULL OR caption = '' LIMIT 5")
rows = cur.fetchall()
print("\n无caption的示例:")
for r in rows:
    print(f"  {r[0]} - caption: '{r[1]}' - reason: '{r[2]}'")

conn.close()