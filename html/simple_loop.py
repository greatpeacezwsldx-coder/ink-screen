import sys
import sqlite3
import time
from pathlib import Path
import json
import requests
import base64

sys.path.insert(0, '.')
from analyze_photos import ensure_table, get_city_resolver, read_exif, in_home, encode_image_to_b64

API_URL = 'http://192.168.56.1:1234/v1/chat/completions'
MODEL = 'qwen/qwen3-vl-4b'

def call_vlm_simple(path):
    img_b64 = encode_image_to_b64(path)
    exif_info = read_exif(path)
    
    system_prompt = '你是一个照片评估助手。分析照片并返回JSON格式：{"caption":"描述","type":"类型","memory_score":分数,"beauty_score":分数,"reason":"理由"}'
    user_prompt = '分析这张照片，给出评分(0-100)。'
    
    body = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': [
                {'type': 'text', 'text': user_prompt},
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
            ]}
        ],
        'temperature': 0.2,
        'stream': False
    }
    
    resp = requests.post(API_URL, json=body, timeout=120)
    if not resp.ok:
        raise Exception(f'API error: {resp.status_code}')
    
    data = resp.json()
    content = data['choices'][0]['message']['content']
    result = json.loads(content)
    return result, exif_info

def main():
    conn = sqlite3.connect('photos.db', check_same_thread=False)
    ensure_table(conn)
    city_resolver = get_city_resolver()
    cur = conn.cursor()
    
    exts = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.heic', '.heif'}
    test_dir = Path('./test')
    all_imgs = [p for p in test_dir.rglob('*') if p.is_file() and p.suffix.lower() in exts]
    
    cur.execute('SELECT path FROM photo_scores')
    done = set(row[0] for row in cur.fetchall())
    
    pending = [p for p in all_imgs if str(p) not in done]
    total = len(all_imgs)
    
    print(f'Total: {total}, Done: {len(done)}, Pending: {len(pending)}')
    
    for i, path in enumerate(pending, 1):
        try:
            t = time.time()
            result, exif_info = call_vlm_simple(path)
            
            caption = str(result.get('caption', '')).strip()
            ptype = str(result.get('type', '')).strip()
            memory_score = float(result.get('memory_score', 0.0))
            beauty_score = float(result.get('beauty_score', 0.0))
            reason = str(result.get('reason', '')).strip()
            
            cur.execute('''INSERT OR REPLACE INTO photo_scores
                (path, caption, type, memory_score, beauty_score, reason, width, height, orientation, exif_json, raw_json)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (str(path), caption, ptype, memory_score, beauty_score, reason,
                 exif_info.get('width'), exif_info.get('height'), exif_info.get('orientation'),
                 json.dumps(exif_info, ensure_ascii=False), json.dumps(result, ensure_ascii=False)))
            conn.commit()
            
            done_count = len(done) + i
            print(f'[{done_count}/{total}] {path.name} OK ({time.time()-t:.1f}s)')
        except Exception as e:
            print(f'[{len(done)+i}/{total}] {path.name} ERROR: {e}')
    
    conn.close()
    print('Done!')

if __name__ == '__main__':
    main()
