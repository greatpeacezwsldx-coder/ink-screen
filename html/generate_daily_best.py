#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评选每一天的最佳照片并生成对应文件：
1. 从 photos.db 按 MM-DD 分组
2. 选择每组回忆度最高的照片作为当日最佳
3. 生成 data/MMDD.h 文件（墨水屏格式）
4. 生成 small/MMDD.jpg 缩略图（500KB左右）
"""

import sqlite3
import json
import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import math

# 配置
DB_PATH = Path('./photos.db')
DATA_DIR = Path('./output')
SMALL_DIR = Path('./small')
FONT_PATH = 'C:\\Windows\\Fonts\\msyh.ttc'

# 墨水屏调色板（4色）
PALETTE = [
    (0, 0, 0),      # 黑
    (255, 255, 255),# 白
    (200, 0, 0),    # 红
    (220, 180, 0),  # 黄
]

# 颜色映射：原始 -> 墨水屏
COLOR_MAP = {0: 3, 1: 0, 2: 2, 3: 1}


def extract_date_from_filename(path_str):
    """从文件路径中提取日期，返回 YYYY-MM-DD 格式"""
    filename = Path(path_str).name

    # 格式1: YYYY.MM.DD-描述 (如 2017.10.11-幼儿园站岗1.JPG)
    m = re.search(r'(\d{4})\.(\d{1,2})\.(\d{1,2})', filename)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"

    # 格式2: YYYYMMDD-描述 (如 20150213-描述.JPG)
    m = re.search(r'(\d{4})(\d{2})(\d{2})-', filename)
    if m:
        return f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    return None


def get_best_photos_by_date():
    """从数据库按 MM-DD 分组，选择每组回忆度最高的照片"""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 获取所有照片数据
    cur.execute("""
        SELECT path, memory_score, beauty_score, side_caption, exif_datetime
        FROM photo_scores
        ORDER BY memory_score DESC
    """)

    rows = cur.fetchall()
    conn.close()

    # 按 MM-DD 分组，取每组第一条（回忆度最高）
    best_by_date = {}
    for path, memory, beauty, caption, datetime in rows:
        # 优先使用 exif_datetime，否则从文件名提取
        if datetime:
            date_str = datetime[:10]
            mmdd = date_str[5:7] + '-' + date_str[8:10]
        else:
            date_str = extract_date_from_filename(path)
            if not date_str:
                continue
            mmdd = date_str[5:7] + '-' + date_str[8:10]

        if mmdd not in best_by_date:
            best_by_date[mmdd] = {
                'path': path,
                'memory_score': memory,
                'beauty_score': beauty,
                'side_caption': caption or '',
                'date': date_str
            }

    return best_by_date


def nearest_palette_color(r, g, b):
    best_idx = 0
    best_dist = float("inf")
    for i, (pr, pg, pb) in enumerate(PALETTE):
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = dr * dr + dg * dg + db * db
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    return best_idx


def apply_four_color_dither(img):
    """Floyd-Steinberg 四色抖动（与 server.py 保持一致）"""
    w, h = img.size
    img = img.convert('RGB')
    pixels = img.load()
    
    err_r = [0.0] * w
    err_g = [0.0] * w
    err_b = [0.0] * w
    next_err_r = [0.0] * w
    next_err_g = [0.0] * w
    next_err_b = [0.0] * w
    
    for y in range(h):
        for x in range(w):
            r, g, b = pixels[x, y]
            r = max(0.0, min(255.0, r + err_r[x]))
            g = max(0.0, min(255.0, g + err_g[x]))
            b = max(0.0, min(255.0, b + err_b[x]))
            
            best_idx = nearest_palette_color(r, g, b)
            pr, pg, pb = PALETTE[best_idx]
            pixels[x, y] = (pr, pg, pb)
            
            er = r - pr
            eg = g - pg
            eb = b - pb
            
            if x + 1 < w:
                err_r[x + 1] += er * (7.0 / 16.0)
                err_g[x + 1] += eg * (7.0 / 16.0)
                err_b[x + 1] += eb * (7.0 / 16.0)
            if y + 1 < h:
                if x > 0:
                    next_err_r[x - 1] += er * (3.0 / 16.0)
                    next_err_g[x - 1] += eg * (3.0 / 16.0)
                    next_err_b[x - 1] += eb * (3.0 / 16.0)
                next_err_r[x] += er * (5.0 / 16.0)
                next_err_g[x] += eg * (5.0 / 16.0)
                next_err_b[x] += eb * (5.0 / 16.0)
                if x + 1 < w:
                    next_err_r[x + 1] += er * (1.0 / 16.0)
                    next_err_g[x + 1] += eg * (1.0 / 16.0)
                    next_err_b[x + 1] += eb * (1.0 / 16.0)
        
        if y + 1 < h:
            for i in range(w):
                err_r[i] = next_err_r[i]
                err_g[i] = next_err_g[i]
                err_b[i] = next_err_b[i]
                next_err_r[i] = 0.0
                next_err_g[i] = 0.0
                next_err_b[i] = 0.0
    return img


def wrap_text_chinese(draw, text, font, max_width, max_lines):
    """按像素宽度计算中文换行（与 server.py 保持一致）"""
    if not text:
        return []
    lines = []
    line = ""
    for ch in text:
        test = line + ch
        w = draw.textlength(test, font=font)
        if w <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = ch
            if len(lines) >= max_lines:
                break
    if line and len(lines) < max_lines:
        lines.append(line)
    return lines


def rotate_cw_90(pixels, width, height):
    """顺时针旋转90度"""
    new_w = height
    new_h = width
    result = [0] * (new_w * new_h)
    
    for row in range(height):
        for col in range(width):
            new_col = row
            new_row = new_h - 1 - col
            old_idx = row * width + col
            new_idx = new_row * new_w + new_col
            result[new_idx] = pixels[old_idx]
    
    return result


def render_photo_to_eink(image_path, caption, date_str):
    """渲染照片为墨水屏格式（480x800，与 server.py 保持一致）"""
    from PIL import ImageOps
    
    CANVAS_WIDTH = 480
    CANVAS_HEIGHT = 800
    TEXT_AREA_HEIGHT = 100
    
    # 打开图片并处理 EXIF 方向
    img = Image.open(image_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    
    img_w, img_h = img.size
    img_area_w = CANVAS_WIDTH
    img_area_h = CANVAS_HEIGHT - TEXT_AREA_HEIGHT
    
    # 等比缩放并居中裁剪
    scale = max(img_area_w / img_w, img_area_h / img_h)
    draw_w = int(img_w * scale)
    draw_h = int(img_h * scale)
    img_resized = img.resize((draw_w, draw_h), Image.LANCZOS)
    
    left = max(0, (draw_w - img_area_w) // 2)
    top = max(0, (draw_h - img_area_h) // 2)
    img_cropped = img_resized.crop((left, top, left + img_area_w, top + img_area_h))
    
    # 创建白色画布
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
    canvas.paste(img_cropped, (0, 0))
    
    draw = ImageDraw.Draw(canvas)
    
    # 字体配置
    try:
        font_big = ImageFont.truetype(FONT_PATH, 22)
        font_small = ImageFont.truetype(FONT_PATH, 20)
    except Exception:
        font_big = ImageFont.load_default()
        font_small = ImageFont.load_default()
    
    # 底部文字区域
    padding_x = 24
    text_area_top = CANVAS_HEIGHT - TEXT_AREA_HEIGHT + 10
    text_width = CANVAS_WIDTH - 2 * padding_x
    
    # 文案：最多两行，黑色
    y = text_area_top
    if caption:
        lines = wrap_text_chinese(draw, caption, font_big, text_width, max_lines=2)
        for line in lines:
            draw.text((padding_x, y), line, font=font_big, fill=(0, 0, 0))
            y += 24
    
    # 日期：黑色，固定在第二行
    second_line_y = text_area_top + 54
    date_display = date_str[:10].replace('-', '.') if date_str else ''
    if date_display:
        draw.text((padding_x, second_line_y), date_display, font=font_small, fill=(0, 0, 0))
    
    # 应用四色抖动
    dithered = apply_four_color_dither(canvas)
    
    return dithered


def image_to_palette_bin(img):
    """将图像转换为调色板索引数组（RGB 图像 -> 调色板索引）"""
    w, h = img.size
    pixels = []
    
    for y in range(h):
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            for i, (pr, pg, pb) in enumerate(PALETTE):
                if r == pr and g == pg and b == pb:
                    pixels.append(i)
                    break
            else:
                pixels.append(nearest_palette_color(r, g, b))
    return pixels


def pack_2bpp(pixels, width, height):
    """打包成2bpp格式"""
    result = bytearray()
    for row in range(height):
        for col in range(0, width, 4):
            idx = row * width + col
            p0 = COLOR_MAP.get(pixels[idx], 0)
            p1 = COLOR_MAP.get(pixels[idx + 1], 0) if col + 1 < width else 0
            p2 = COLOR_MAP.get(pixels[idx + 2], 0) if col + 2 < width else 0
            p3 = COLOR_MAP.get(pixels[idx + 3], 0) if col + 3 < width else 0
            byte = (p0 << 6) | (p1 << 4) | (p2 << 2) | p3
            result.append(byte)
    return bytes(result)


def generate_h_file(data, output_path):
    """生成 .h 文件"""
    lines = []
    lines.append('const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */')
    
    hex_strs = [f'0X{b:02X}' for b in data]
    
    for i in range(0, len(hex_strs), 16):
        chunk = hex_strs[i:i+16]
        lines.append(','.join(chunk) + ',')
    
    lines[-1] = lines[-1].rstrip(',')
    lines.append('};')
    
    output_path.write_text('\n'.join(lines), encoding='utf-8')


def save_small_jpg(image_path, output_path, target_size_kb=500):
    """保存小图，压缩到目标大小"""
    img = Image.open(image_path)
    
    # 处理透明通道（PNG）
    if img.mode == 'RGBA':
        # 用白色背景合成
        bg = Image.new('RGB', img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[3])
        img = bg
    elif img.mode != 'RGB':
        img = img.convert('RGB')
    
    # 先缩小尺寸
    max_dim = 1200
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / max(w, h)
        img = img.resize((int(w * scale), int(h * scale)), Image.LANCZOS)
    
    # 调整质量来控制大小
    quality = 85
    while quality >= 10:
        buffer = []
        img.save(output_path, format='JPEG', quality=quality, optimize=True)
        size_kb = output_path.stat().st_size / 1024
        if size_kb <= target_size_kb or quality <= 10:
            break
        quality -= 5


def main():
    print("[INFO] 读取数据库...")
    best_photos = get_best_photos_by_date()
    print(f"[INFO] 共找到 {len(best_photos)} 天有照片")
    
    count = 0
    for mmdd, info in best_photos.items():
        date_key = mmdd.replace('-', '')  # 0616
        h_path = DATA_DIR / f'{date_key}.h'
        jpg_path = SMALL_DIR / f'{date_key}.jpg'
        
        try:
            print(f"[INFO] 处理 {mmdd} - {info['path']}")
            
            # 渲染墨水屏图片（始终是 480x800 竖屏格式）
            eink_img = render_photo_to_eink(info['path'], info['side_caption'], info['date'])
            
            # 转换为数组
            pixels = image_to_palette_bin(eink_img)
            
            # 顺时针旋转90度（和 convert_to_eink.py 一致）
            rotated = rotate_cw_90(pixels, 480, 800)
            
            # 打包并生成 .h 文件（最终 800x480）
            packed = pack_2bpp(rotated, 800, 480)
            generate_h_file(packed, h_path)
            
            # 生成小图
            save_small_jpg(info['path'], jpg_path)
            
            count += 1
            print(f"[OK] {date_key}.h 和 {date_key}.jpg")
            
        except Exception as e:
            import traceback
            print(f"[ERROR] 处理 {mmdd} 失败: {e}")
            print(f"        Traceback: {traceback.format_exc()[:500]}")
    
    print(f"\n[INFO] 完成！共生成 {count} 组文件")


if __name__ == '__main__':
    main()
