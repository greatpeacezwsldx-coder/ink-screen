import sys
sys.path.insert(0, '.')
import sqlite3
from pathlib import Path
import json
import requests
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from analyze_photos import ensure_table, encode_image_to_b64, read_exif

conn = sqlite3.connect('photos.db', timeout=60)
ensure_table(conn)
cur = conn.cursor()

exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic', '.heif'}
all_imgs = sorted([p.resolve() for p in Path('./test').rglob('*') if p.suffix.lower() in exts])

cur.execute('SELECT path FROM photo_scores')
done = set(r[0] for r in cur.fetchall())
pending = [p for p in all_imgs if str(p) not in done]

if not pending:
    print('All done!')
    conn.close()
    sys.exit(0)

print(f'Pending: {len(pending)}')


def process(path):
    try:
        img_b64 = encode_image_to_b64(path)
        exif = read_exif(path)
        body = {
            'model': 'qwen/qwen3-vl-4b',
            'messages': [
                {'role': 'system', 'content': '你是一个照片评分专家。返回JSON：{"caption":"画面描述(20-50字)","memory_score":0-100,"beauty_score":0-100,"reason":"理由(20字内)"}'},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': '分析照片，返回JSON。'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                ]}
            ],
            'temperature': 0.2,
            'max_tokens': 200
        }
        resp = requests.post('http://192.168.56.1:1234/v1/chat/completions', json=body, timeout=120)
        try:
            result = resp.json()
            if 'choices' not in result or len(result['choices']) == 0:
                data = {'caption': '', 'memory_score': 50, 'beauty_score': 50, 'reason': ''}
            else:
                content = result['choices'][0]['message']['content']
                try:
                    data = json.loads(content)
                except:
                    data = {'caption': '', 'memory_score': 50, 'beauty_score': 50, 'reason': ''}
        except:
            data = {'caption': '', 'memory_score': 50, 'beauty_score': 50, 'reason': ''}

        caption = str(data.get('caption', ''))[:200]
        reason = str(data.get('reason', ''))[:60]
        return str(path), caption, float(data.get('memory_score', 50)), float(data.get('beauty_score', 50)), reason, exif.get('width'), exif.get('height')
    except Exception as e:
        return str(path), '', 50, 50, f'Error: {e}', None, None


# 并行处理（4个并发）
batch_size = 4
for i in range(0, len(pending), batch_size):
    batch = pending[i:i+batch_size]
    with ThreadPoolExecutor(max_workers=batch_size) as executor:
        futures = {executor.submit(process, p): p for p in batch}
        for future in as_completed(futures):
            result = future.result()
            if result:
                path_str, caption, mem, beauty, reason, w, h = result
                cur.execute('INSERT OR REPLACE INTO photo_scores (path, caption, type, memory_score, beauty_score, reason, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                    (path_str, caption, '', mem, beauty, reason, w, h))
                conn.commit()
                print(f'OK: {Path(path_str).name}', flush=True)

conn.close()
print(f'All done!')
