import sys
import sqlite3
import time
from pathlib import Path

sys.path.insert(0, '.')
from analyze_photos import list_images, filter_unscored, ensure_table, get_city_resolver, _process_one_photo, _save_result_to_db

conn = sqlite3.connect('photos.db', check_same_thread=False)
ensure_table(conn)
city_resolver = get_city_resolver()

imgs = list_images()
targets = filter_unscored(conn, imgs)
print(f'待处理: {len(targets)}')

cur = conn.cursor()
count = 0

for path in targets[:10]:
    print(f'[{count+1}] 处理: {path.name}')
    try:
        rec = _process_one_photo(path, city_resolver)
        if rec:
            _save_result_to_db(cur, conn, rec)
            count += 1
            print(f'  OK')
        else:
            print(f'  FAILED')
    except Exception as e:
        print(f'  ERROR: {e}')
        break

conn.close()
print(f'完成，处理了 {count} 张')
