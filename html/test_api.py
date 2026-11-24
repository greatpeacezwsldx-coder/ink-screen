import requests
import base64
import json
from PIL import Image
import io

img_path = './test/13个半月2.jpg'
with open(img_path, 'rb') as f:
    img_bytes = f.read()

img = Image.open(io.BytesIO(img_bytes))
if img.mode in ("RGBA", "LA"):
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[-1])
    img = bg
elif img.mode != "RGB":
    img = img.convert("RGB")

out = io.BytesIO()
img.save(out, format="JPEG", quality=92, optimize=True)
clean_bytes = out.getvalue()
img_b64 = base64.b64encode(clean_bytes).decode("utf-8")
print(f'图片base64长度: {len(img_b64)}')

body = {
    'model': 'qwen/qwen3-vl-4b',
    'messages': [
        {'role': 'system', 'content': '分析照片返回JSON: {"caption":"描述","type":"类型","memory_score":分数,"beauty_score":分数,"reason":"理由"}'},
        {'role': 'user', 'content': [
            {'type': 'text', 'text': '评分0-100'},
            {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}}
        ]}
    ],
    'temperature': 0.2
}

try:
    resp = requests.post('http://192.168.56.1:1234/v1/chat/completions', json=body, timeout=120)
    print(f'Status: {resp.status_code}')
    print(f'Response: {resp.text[:1000]}')
except Exception as e:
    print(f'Error: {e}')