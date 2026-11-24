﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import sys
sys.path.insert(0, '.')
import sqlite3
from pathlib import Path
import json
import requests
from analyze_photos import ensure_table, encode_image_to_b64, read_exif

conn = sqlite3.connect('photos.db')
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

path = pending[0]
print(f'Processing: {path.name}')

img_b64 = encode_image_to_b64(path)
exif = read_exif(path)

body = {
    'model': 'qwen/qwen3-vl-4b',
    'messages': [
        {'role': 'system', 'content': '你是一个照片评分专家。请分析照片并返回JSON格式：{"caption":"画面描述","type":"类型","memory_score":0-100,"beauty_score":0-100,"reason":"简短理由"}。caption要详细描述画面内容，20-50字。'},
        {'role': 'user', 'content': [
            {'type': 'text', 'text': '请分析这张照片，返回JSON格式的评分和描述。'},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
        ]}
    ],
    'temperature': 0.2
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

caption = str(data.get('caption', ''))[:200]  # 限制长度
reason = str(data.get('reason', ''))[:60]

cur.execute('INSERT OR REPLACE INTO photo_scores (path, caption, type, memory_score, beauty_score, reason, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
    (str(path), caption, '', float(data.get('memory_score', 50)), float(data.get('beauty_score', 50)), reason, exif.get('width'), exif.get('height')))
conn.commit()
conn.close()
print(f'OK: {len(done)+1}/{len(all_imgs)}')
