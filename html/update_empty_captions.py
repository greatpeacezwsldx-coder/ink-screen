import sys
sys.path.insert(0, '.')
import sqlite3
from pathlib import Path
import json
import requests
from analyze_photos import ensure_table, encode_image_to_b64, read_exif

conn = sqlite3.connect('photos.db', timeout=60)
ensure_table(conn)
cur = conn.cursor()

cur.execute("SELECT path FROM photo_scores WHERE caption IS NULL OR caption = ''")
pending_paths = [r[0] for r in cur.fetchall()]

if not pending_paths:
    print('All photos already have captions!')
    conn.close()
    sys.exit(0)

print(f'Pending photos to update: {len(pending_paths)}')


def process(path_str):
    path = Path(path_str)
    if not path.exists():
        print(f'File not found: {path.name}')
        return path_str, '', 50, 50, 'File not found', None, None
    
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
        print(f'Error processing {path.name}: {e}')
        return str(path), '', 50, 50, f'Error: {e}', None, None


count = 0
for i, path_str in enumerate(pending_paths):
    print(f'Processing {i+1}/{len(pending_paths)}: {Path(path_str).name}')
    result = process(path_str)
    if result:
        path_str, caption, mem, beauty, reason, w, h = result
        if caption:
            cur.execute('UPDATE photo_scores SET caption = ?, type = ?, memory_score = ?, beauty_score = ?, reason = ?, width = ?, height = ? WHERE path = ?',
                (caption, '', mem, beauty, reason, w, h, path_str))
            conn.commit()
            count += 1
            print(f'OK: {Path(path_str).name} - {caption[:30]}...')
        else:
            print(f'Empty caption: {Path(path_str).name}')

conn.close()
print(f'All done! Updated {count} photos.')