# -*- coding: utf-8 -*-
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
    
    imgs = list_images()
    print(f'总图片数: {len(imgs)}')
    
    targets = filter_unscored(conn, imgs)
    print(f'待处理: {len(targets)}')
    
    if not targets:
        print('所有图片已处理完成')
        conn.close()
        return
    
    # 每次处理 10 张
    batch_size = 10
    batches = [targets[i:i+batch_size] for i in range(0, len(targets), batch_size)]
    
    cur = conn.cursor()
    total_processed = 0
    
    for batch_idx, batch in enumerate(batches, 1):
        print(f'\n=== 批次 {batch_idx}/{len(batches)} ===')
        for i, path in enumerate(batch, 1):
            t_start = time.time()
            print(f'[{i}/{len(batch)}] 处理: {path.name}')
            try:
                rec = _process_one_photo(path, city_resolver)
                if rec:
                    _save_result_to_db(cur, conn, rec)
                    total_processed += 1
                    print(f'  OK ({time.time() - t_start:.1f}s)')
                else:
                    print(f'  FAILED')
            except Exception as e:
                print(f'  ERROR: {e}')
        
        # 更新进度
        cur.execute('SELECT COUNT(*) FROM photo_scores WHERE path LIKE ?', ('H:%',))
        count = cur.fetchone()[0]
        print(f'已处理 Windows 路径照片: {count}/453')
        
        if total_processed >= 50:
            print('已处理 50 张，暂停')
            break
    
    conn.close()
    print(f'\n完成，共处理 {total_processed} 张')

if __name__ == '__main__':
    main()
