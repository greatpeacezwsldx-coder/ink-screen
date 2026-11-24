import sys
import sqlite3
import time
from pathlib import Path
import json
import requests

sys.path.insert(0, '.')
from analyze_photos import ensure_table, encode_image_to_b64, read_exif

API_URL = 'http://192.168.56.1:1234/v1/chat/completions'
MODEL = 'qwen/qwen3-vl-4b'

def process_image(path, cur, conn):
    img_b64 = encode_image_to_b64(path)
    exif_info = read_exif(path)
    
    body = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': '分析照片返回JSON: {"caption":"描述","type":"类型","memory_score":分数,"beauty_score":分数,"reason":"理由"}'},
            {'role': 'user', 'content': [
                {'type': 'text', 'text': '评分0-100'},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
            ]}
        ],
        'temperature': 0.2
    }
    
    resp = requests.post(API_URL, json=body, timeout=120)
    data = resp.json()
    content = data['choices'][0]['message']['content']
    result = json.loads(content)
    
    cur.execute('INSERT OR REPLACE INTO photo_scores (path, caption, type, memory_score, beauty_score, reason, width, height) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
        (str(path), result.get('caption',''), result.get('type',''), float(result.get('memory_score',0)), float(result.get('beauty_score',0)), result.get('reason',''),
         exif_info.get('width'), exif_info.get('height')))
    conn.commit()

def main():
    conn = sqlite3.connect('photos.db')
    ensure_table(conn)
    cur = conn.cursor()
    
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic', '.heif'}
    all_imgs = sorted([p for p in Path('./test').rglob('*') if p.suffix.lower() in exts])
    
    cur.execute('SELECT path FROM photo_scores')
    done = set(r[0] for r in cur.fetchall())
    pending = [p for p in all_imgs if str(p) not in done]
    
    print(f'Total: {len(all_imgs)}, Done: {len(done)}, Pending: {len(pending)}')
    
    for i, path in enumerate(pending, 1):
        t = time.time()
        try:
            process_image(path, cur, conn)
            print(f'[{len(done)+i}/{len(all_imgs)}] {path.name} OK ({time.time()-t:.1f}s)')
        except Exception as e:
            print(f'[{len(done)+i}/{len(all_imgs)}] {path.name} ERR: {e}')
    
    conn.close()
    print('Done!')

if __name__ == '__main__':
    main()
