import sqlite3

conn = sqlite3.connect('photos.db')
cur = conn.cursor()

# 先查看要删除的记录数
cur.execute("SELECT COUNT(*) FROM photo_scores WHERE path NOT LIKE 'H:%'")
count = cur.fetchone()[0]
print(f'将删除 {count} 条相对路径记录')

# 删除所有相对路径的记录
cur.execute("DELETE FROM photo_scores WHERE path NOT LIKE 'H:%'")
conn.commit()
print(f'已删除 {cur.rowcount} 条记录')

# 验证
cur.execute("SELECT COUNT(*) FROM photo_scores")
total = cur.fetchone()[0]
print(f'剩余 {total} 条记录')

cur.execute("SELECT COUNT(*) FROM photo_scores WHERE path NOT LIKE 'H:%'")
remaining = cur.fetchone()[0]
print(f'剩余 {remaining} 条相对路径记录')

conn.close()
