import sys
sys.path.insert(0, '.')
from analyze_photos import list_images, filter_unscored, ensure_table, call_vlm
import sqlite3
from pathlib import Path

imgs = list_images()
print(f'扫描到 {len(imgs)} 张图片')

conn = sqlite3.connect('photos.db')
ensure_table(conn)
pending = filter_unscored(conn, imgs)
print(f'待处理 {len(pending)} 张')

if pending:
    test_path = pending[0]
    print(f'\n测试处理: {test_path.name}')
    try:
        result, exif = call_vlm(test_path)
        print(f'成功! memory_score: {result.get("memory_score")}')
        print(f'caption: {result.get("caption")[:50]}...')
    except Exception as e:
        print(f'失败: {e}')

conn.close()