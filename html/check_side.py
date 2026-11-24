import sqlite3
conn = sqlite3.connect('photos.db')
cur = conn.cursor()

cur.execute("SELECT COUNT(*) FROM photo_scores WHERE side_caption IS NOT NULL AND side_caption <> ''")
with_side = cur.fetchone()[0]

cur.execute("SELECT COUNT(*) FROM photo_scores")
total = cur.fetchone()[0]

print(f"总记录: {total}")
print(f"有side_caption: {with_side}")
print(f"无side_caption: {total - with_side}")

# 查看几个有side_caption的示例
cur.execute("SELECT path, side_caption FROM photo_scores WHERE side_caption IS NOT NULL AND side_caption <> '' LIMIT 5")
rows = cur.fetchall()
print("\n有side_caption的示例:")
for r in rows:
    print(f"  {r[0]}: {r[1]}")

conn.close()