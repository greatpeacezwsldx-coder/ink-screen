import sqlite3
conn = sqlite3.connect('photos.db')
cur = conn.cursor()
cur.execute("SELECT path FROM photo_scores LIMIT 10")
print('路径示例:')
for row in cur.fetchall():
    print(f'  {row[0]}')
conn.close()
