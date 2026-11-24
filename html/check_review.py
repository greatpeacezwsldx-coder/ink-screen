import requests
import re

s = requests.Session()
r = s.post('http://127.0.0.1:8765/login', data={'username':'sit', 'password':'sit'})
r = s.get('http://127.0.0.1:8765/review')

# 检查是否有caption和reason
print('Has caption div:', '<div class="caption">' in r.text)
print('Has reason div:', '<div class="reason">' in r.text)

# 找一个示例
match = re.search(r'<div class="caption">([^<]+)</div>', r.text)
if match:
    print(f'\nExample caption: {match.group(1)[:100]}')

match = re.search(r'<div class="reason">理由: ([^<]+)</div>', r.text)
if match:
    print(f'Example reason: {match.group(1)[:100]}')