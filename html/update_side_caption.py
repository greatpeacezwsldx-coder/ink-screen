import sys
sys.path.insert(0, '.')
import sqlite3
from pathlib import Path
import json
import requests
from analyze_photos import encode_image_to_b64

conn = sqlite3.connect('photos.db', timeout=60)
cur = conn.cursor()

cur.execute("SELECT path FROM photo_scores WHERE side_caption IS NULL OR side_caption = ''")
pending_paths = [r[0] for r in cur.fetchall()]

if not pending_paths:
    print('All photos already have side_caption!')
    conn.close()
    sys.exit(0)

print(f'Pending photos to update: {len(pending_paths)}')


def generate_side_caption(path_str):
    path = Path(path_str)
    if not path.exists():
        return None

    try:
        img_b64 = encode_image_to_b64(path)
        body = {
            'model': 'qwen/qwen3-vl-4b',
            'messages': [
                {'role': 'system', 'content': '你是一个照片文案专家。为照片生成一句简短、温馨、有感情的一句话文案（15-25字）。只返回文案本身，不要加引号或其他符号。'},
                {'role': 'user', 'content': [
                    {'type': 'text', 'text': '为这张照片生成一句话文案。'},
                    {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
                ]}
            ],
            'temperature': 0.7,
            'max_tokens': 50
        }
        resp = requests.post('http://192.168.56.1:1234/v1/chat/completions', json=body, timeout=120)
        result = resp.json()
        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content'].strip()
            # 清理可能的引号
            content = content.strip('"\'')
            if len(content) > 60:
                content = content[:60]
            return content
        return None
    except Exception as e:
        print(f'Error: {e}')
        return None


count = 0
for i, path_str in enumerate(pending_paths):
    print(f'Processing {i+1}/{len(pending_paths)}: {Path(path_str).name}')
    side_caption = generate_side_caption(path_str)
    if side_caption:
        cur.execute('UPDATE photo_scores SET side_caption = ? WHERE path = ?', (side_caption, path_str))
        conn.commit()
        count += 1
        print(f'OK: {side_caption}')
    else:
        print(f'Failed')

conn.close()
print(f'All done! Updated {count} photos.')