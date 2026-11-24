import sqlite3
conn = sqlite3.connect('photos.db')
cur = conn.cursor()

photos = [r'H:\html\test\15个月.jpg', r'H:\html\test\16.10.17-家中小红帽.JPG']
for p in photos:
    cur.execute("SELECT caption, memory_score, beauty_score, reason FROM photo_scores WHERE path = ?", (p,))
    row = cur.fetchone()
    if row:
        print(f'{p}:')
        print(f'  caption: {row[0]}')
        print(f'  memory_score: {row[1]}')
        print(f'  beauty_score: {row[2]}')
        print(f'  reason: {row[3]}')
    else:
        print(f'{p}: 未找到')

conn.close()