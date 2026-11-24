import sqlite3
from pathlib import Path

conn = sqlite3.connect('photos.db')
cur = conn.cursor()

# 查看具体情况
cur.execute("SELECT path FROM photo_scores WHERE path NOT LIKE 'H:%'")
rel_paths = [r[0] for r in cur.fetchall()]

# 检查哪些相对路径有冲突
conflict_count = 0
for rel in rel_paths[:20]:  # 只看前20个
    abs_path = f'H:\\html\\{rel}'
    cur.execute("SELECT COUNT(*) FROM photo_scores WHERE path = ?", (abs_path,))
    count = cur.fetchone()[0]
    cur.execute("SELECT caption FROM photo_scores WHERE path = ?", (rel,))
    rel_caption = cur.fetchone()
    cur.execute("SELECT caption FROM photo_scores WHERE path = ?", (abs_path,))
    abs_caption = cur.fetchone()
    print(f'相对: {rel}')
    print(f'  相对路径caption: {rel_caption}')
    print(f'  绝对路径记录数: {count}, caption: {abs_caption}')
    if count > 0:
        conflict_count += 1
    print()

print(f'\n前20个中有 {conflict_count} 个冲突')
conn.close()
