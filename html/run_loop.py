import subprocess
import sqlite3
import time

def get_count():
    conn = sqlite3.connect('photos.db')
    cur = conn.cursor()
    cur.execute('SELECT COUNT(*) FROM photo_scores')
    count = cur.fetchone()[0]
    conn.close()
    return count

total = 453
last_count = 0
same_count_times = 0

while True:
    count = get_count()
    remaining = total - count
    print(f'=== 进度: {count}/{total} ({count*100/total:.1f}%), 剩余: {remaining} ===')
    
    if remaining <= 0:
        print('所有照片已处理完成!')
        break
    
    if count == last_count:
        same_count_times += 1
        if same_count_times >= 3:
            print('连续3次没有新记录，可能遇到问题，退出')
            break
    else:
        same_count_times = 0
    last_count = count
    
    print(f'运行 analyze_photos.py...')
    result = subprocess.run(['python', '-u', 'analyze_photos.py'], capture_output=False, timeout=3600)
    print(f'退出码: {result.returncode}')
    time.sleep(2)

print('完成!')
