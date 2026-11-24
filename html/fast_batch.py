import sys
import sqlite3
import time
from pathlib import Path
import json

sys.path.insert(0, '.')
from analyze_photos import list_images, filter_unscored, ensure_table, get_city_resolver, call_vlm, read_exif, in_home

def process_one_fast(path, city_resolver):
    try:
        result, exif_info = call_vlm(path)
    except Exception as e:
        print(f'[WARN] 调用模型失败: {e}')
        return None

    caption = str(result.get('caption', '')).strip()
    ptype = str(result.get('type', '')).strip()
    try:
        memory_score = float(result.get('memory_score', 0.0))
    except Exception:
        memory_score = 0.0
    try:
        beauty_score = float(result.get('beauty_score', 0.0))
    except Exception:
        beauty_score = 0.0
    reason = str(result.get('reason', '')).strip()

    width = exif_info.get('width')
    height = exif_info.get('height')
    orientation = exif_info.get('orientation')
    exif_datetime = exif_info.get('datetime')
    exif_make = exif_info.get('make')
    exif_model_val = exif_info.get('model')

    def _to_int(v):
        try:
            return int(v) if v is not None else None
        except Exception:
            return None
    def _to_float(v):
        try:
            return float(v) if v is not None else None
        except Exception:
            return None

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
        'path': str(path),
        'caption': caption,
        'type': ptype,
        'memory_score': memory_score,
        'beauty_score': beauty_score,
        'reason': reason,
        'width': width,
        'height': height,
        'orientation': orientation,
        'exif_json': json.dumps(exif_info, ensure_ascii=False, default=str),
        'raw_json': json.dumps(result, ensure_ascii=False),
        'exif_datetime': exif_datetime,
        'exif_make': exif_make,
        'exif_model': exif_model_val,
        'exif_iso': exif_iso,
        'exif_exposure_time': exif_exposure_time,
        'exif_f_number': exif_f_number,
        'exif_focal_length': exif_focal_length,
        'exif_gps_lat': exif_gps_lat,
        'exif_gps_lon': exif_gps_lon,
        'exif_gps_alt': exif_gps_alt,
        'side_caption': None,
        'exif_city': exif_city,
    }

def main():
    conn = sqlite3.connect('photos.db', check_same_thread=False)
    ensure_table(conn)
    city_resolver = get_city_resolver()
    
    imgs = list_images()
    targets = filter_unscored(conn, imgs)
    total = len(targets)
    print(f'待处理: {total}')
    
    if not targets:
        print('所有图片已处理完成')
        conn.close()
        return
    
    cur = conn.cursor()
    processed = 0
    
    for path in targets:
        t_start = time.time()
        print(f'[{processed+1}/{total}] 处理: {path.name}')
        try:
            rec = process_one_fast(path, city_resolver)
            if rec:
                cur.execute('''INSERT OR REPLACE INTO photo_scores
                    (path, caption, type, memory_score, beauty_score, reason,
                     width, height, orientation, used_at,
                     exif_json, raw_json,
                     exif_datetime, exif_make, exif_model,
                     exif_iso, exif_exposure_time, exif_f_number, exif_focal_length,
                     exif_gps_lat, exif_gps_lon, exif_gps_alt, side_caption, exif_city)
                    VALUES (?, ?, ?, ?, ?, ?,
                            ?, ?, ?, NULL,
                            ?, ?,
                            ?, ?, ?,
                            ?, ?, ?, ?,
                            ?, ?, ?, ?, ?)''',
                    (rec['path'], rec['caption'], rec['type'], rec['memory_score'], rec['beauty_score'], rec['reason'],
                     rec['width'], rec['height'], rec['orientation'],
                     rec['exif_json'], rec['raw_json'],
                     rec['exif_datetime'], rec['exif_make'], rec['exif_model'],
                     rec['exif_iso'], rec['exif_exposure_time'], rec['exif_f_number'], rec['exif_focal_length'],
                     rec['exif_gps_lat'], rec['exif_gps_lon'], rec['exif_gps_alt'], rec['side_caption'], rec['exif_city']))
                conn.commit()
                processed += 1
                print(f'  OK ({time.time()-t_start:.1f}s)')
            else:
                print(f'  FAILED')
        except Exception as e:
            print(f'  ERROR: {e}')
            import traceback
            traceback.print_exc()
    
    conn.close()
    print(f'完成，共处理 {processed} 张')

if __name__ == '__main__':
    main()
