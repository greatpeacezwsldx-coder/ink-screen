import requests
import json
import re

s = requests.Session()
r = s.post('http://127.0.0.1:8765/login', data={'username':'sit', 'password':'sit'})
r = s.get('http://127.0.0.1:8765/sim?img=/images/15%E4%B8%AA%E6%9C%88.jpg')

# 找到 PHOTOS 变量
match = re.search(r'const PHOTOS = (\[.*?\]);', r.text, re.DOTALL)
if match:
    photos = json.loads(match.group(1))
    print(f"Found {len(photos)} photos")
    for p in photos[:3]:
        print(f"\nPath: {p.get('path', '')[:50]}")
        print(f"Caption: {p.get('caption', '')[:80]}")
        print(f"Reason: {p.get('reason', '')[:80]}")
else:
    print("PHOTOS not found")