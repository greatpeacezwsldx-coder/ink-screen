import sys
import sqlite3
import time
from pathlib import Path

sys.path.insert(0, '.')
from analyze_photos import (
    list_images, filter_unscored, ensure_table, get_city_resolver,
    call_vlm, read_exif, in_home, _save_result_to_db
)
import json

def process_one(path, city_resolver):
    try:
        result, exif_info = call_vlm(path)
    except Exception as e:
        print(f'[WARN] call_vlm failed: {e}')
        return None

    caption = str(result.get('caption', '')).strip()
    ptype = str(result.get('type', '')).strip()
    try:
        memory_score = float(result.get('memory_score', 0.0))
    except:
        memory_score = 0.0
    try:
        beauty_score = float(result.get('beauty_score', 0.0))
    except:
        beauty_score = 0.0
    reason = str(result.get('reason', '')).strip()

    width = exif_info.get('width')
    height = exif_info.get('height')
    orientation = exif_info.get('orientation')
    exif_datetime = exif_info.get('datetime')
    exif_make = exif_info.get('make')
    exif_model_val = exif_info.get('model')

    def _to_int(v):
        try: return int(v) if v is not None else None
        except: return None
    def _to_float(v):
        try: return float(v) if v is not None else None
        except: return None

    exif_iso = _to_int(exif_info.get('iso'))
    exif_exposure_time = _to_float(exif_info.get('exposure_time'))
    exif_f_number = _to_float(exif_info.get('f_number'))
    exif_focal_length = _to_float(exif_info.get('focal_length'))
    exif_gps_lat = _to_float(exif_info.get('gps_lat'))
    exif_gps_lon = _to_float(exif_info.get('gps_lon'))
    exif_gps_alt = _to_float(exif_info.get('gps_alt'))

    if exif_gps_lat is not None and exif_gps_lon is not None:
        exif_city = city_resolver(exif_gps_lat, exif_gps_lon)
    else:
        exif_city = ''

    lat = exif_info.get('gps_lat')
    lon = exif_info.get('gps_lon')
    if lat is not None and lon is not None and not in_home(lat, lon):
        memory_score = min(memory_score + 5.0, 100.0)

    return {
        'path': str(path), 'caption': caption, 'type': ptype,
        'memory_score': memory_score, 'beauty_score': beauty_score, 'reason': reason,
        'width': width, 'height': height, 'orientation': orientation,
        'exif_json': json.dumps(exif_info, ensure_ascii=False, default=str),
        'raw_json': json.dumps(result, ensure_ascii=False),
        'exif_datetime': exif_datetime, 'exif_make': exif_make, 'exif_model': exif_model_val,
        'exif_iso': exif_iso, 'exif_exposure_time': exif_exposure_time,
        'exif_f_number': exif_f_number, 'exif_focal_length': exif_focal_length,
        'exif_gps_lat': exif_gps_lat, 'exif_gps_lon': exif_gps_lon, 'exif_gps_alt': exif_gps_alt,
        'side_caption': None, 'exif_city': exif_city,
    }

def main():
    conn = sqlite3.connect('photos.db', check_same_thread=False)
    ensure_table(conn)
    city_resolver = get_city_resolver()
    cur = conn.cursor()

    total = 453
    start_time = time.time()

    while True:
        cur.execute('SELECT COUNT(*) FROM photo_scores')
        count = cur.fetchone()[0]
        remaining = total - count

        if remaining <= 0:
            print(f'\n=== 所有照片已处理完成! 总计: {count} 张 ===')
            break

        elapsed = time.time() - start_time
        avg_time = elapsed / count if count > 0 else 0
        eta = remaining * avg_time

        print(f'\n=== 进度: {count}/{total} ({count*100/total:.1f}%), 剩余: {remaining}, ETA: {eta/60:.1f}分钟 ===')

        imgs = list_images()
        targets = filter_unscored(conn, imgs)

        if not targets:
            print('没有待处理的照片')
            break

        for i, path in enumerate(targets[:10], 1):
            t_start = time.time()
            print(f'[{count+i}/{total}] {path.name}', end=' ', flush=True)
            try:
                rec = process_one(path, city_resolver)
                if rec:
                    _save_result_to_db(cur, conn, rec)
                    print(f'OK ({time.time()-t_start:.1f}s)')
                else:
                    print('FAILED')
            except Exception as e:
                print(f'ERROR: {e}')

    conn.close()
    total_time = time.time() - start_time
    print(f'\n总耗时: {total_time/60:.1f} 分钟')

if __name__ == '__main__':
    main()
