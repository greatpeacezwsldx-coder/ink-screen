import sqlite3
conn = sqlite3.connect('photos.db')
cur = conn.cursor()
cur.execute("DELETE FROM photo_scores WHERE caption IS NULL OR caption = ''")
conn.commit()
print(f'删除了 {cur.rowcount} 条记录')

# 确认剩余记录
cur.execute('SELECT COUNT(*) FROM photo_scores')
print(f'剩余 {cur.fetchone()[0]} 条记录')
conn.close()
