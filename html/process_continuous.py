﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿﻿import sys
import sqlite3
import time
from pathlib import Path
import json
import requests
import traceback

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
    return True

def main():
    conn = sqlite3.connect('photos.db')
    ensure_table(conn)
    cur = conn.cursor()
    
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic', '.heif'}
    all_imgs = sorted([p for p in Path('./test').rglob('*') if p.suffix.lower() in exts])
    total = len(all_imgs)
    
    start_time = time.time()
    processed_count = 0
    
    while True:
        cur.execute('SELECT path FROM photo_scores')
        done = set(r[0] for r in cur.fetchall())
        count = len(done)
        
        if count >= total:
            print(f'\n=== All done! Total: {count} ===')
            break
        
        # Get next pending image
        pending = [p for p in all_imgs if str(p) not in done]
        if not pending:
            print('No more pending images')
            break
        
        path = pending[0]
        t = time.time()
        try:
            process_image(path, cur, conn)
            processed_count += 1
            elapsed = time.time() - start_time
            avg = elapsed / processed_count if processed_count > 0 else 0
            eta = (total - count - 1) * avg / 60
            print(f'[{count+1}/{total}] {path.name} OK ({time.time()-t:.1f}s) ETA: {eta:.1f}min')
        except Exception as e:
            print(f'[{count+1}/{total}] {path.name} ERR: {e}')
            traceback.print_exc()
    
    conn.close()
    total_time = time.time() - start_time
    print(f'\nTotal time: {total_time/60:.1f} minutes')

if __name__ == '__main__':
    main()
