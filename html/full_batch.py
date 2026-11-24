import sys
import sqlite3
import time
from pathlib import Path

sys.path.insert(0, '.')
from analyze_photos import list_images, filter_unscored, ensure_table, get_city_resolver, _process_one_photo, _save_result_to_db

def main():
    conn = sqlite3.connect('photos.db', check_same_thread=False)
    ensure_table(conn)
    city_resolver = get_city_resolver()
    
    total_imgs = 453
    processed = 0
    
    while True:
        imgs = list_images()
        targets = filter_unscored(conn, imgs)
        
        if not targets:
            print('所有图片已处理完成!')
            break
        
        print(f'待处理: {len(targets)}')
        
        cur = conn.cursor()
        batch_count = 0
        
        for path in targets[:5]:
            try:
                rec = _process_one_photo(path, city_resolver)
                if rec:
                    _save_result_to_db(cur, conn, rec)
                    batch_count += 1
                    processed += 1
                    print(f'[{processed}/{total_imgs}] OK: {path.name}')
                else:
                    print(f'[{processed+1}/{total_imgs}] FAILED: {path.name}')
            except Exception as e:
                print(f'[{processed+1}/{total_imgs}] ERROR: {path.name} - {e}')
        
        cur.execute('SELECT COUNT(*) FROM photo_scores')
        db_count = cur.fetchone()[0]
        print(f'数据库记录: {db_count}, 本次处理: {batch_count}')
        
        if batch_count == 0:
            print('没有新记录，退出')
            break
    
    conn.close()
    print(f'完成，共处理 {processed} 张')

if __name__ == '__main__':
    main()
