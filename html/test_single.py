import sys
sys.path.insert(0, '.')
from analyze_photos import encode_image_to_b64, read_exif
import json
import requests
from pathlib import Path

path = Path(r'H:\html\test\15个月.jpg')
print(f'File exists: {path.exists()}')

img_b64 = encode_image_to_b64(path)
print(f'Base64 length: {len(img_b64)}')

exif = read_exif(path)
print(f'EXIF: {exif}')

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

try:
    resp = requests.post('http://192.168.56.1:1234/v1/chat/completions', json=body, timeout=120)
    print(f'Status: {resp.status_code}')
    print(f'Response: {resp.text[:500]}')
except Exception as e:
    print(f'Error: {e}')