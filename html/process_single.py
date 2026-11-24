#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
单独处理单张照片，调试旋转问题
"""

import sqlite3
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps
import math

# 配置
DB_PATH = Path('/Users/zhangwei/Desktop/source/html/photos.db')
FONT_PATH = '/System/Library/Fonts/Hiragino Sans GB.ttc'

# 墨水屏尺寸
CANVAS_WIDTH = 480
CANVAS_HEIGHT = 800
TEXT_AREA_HEIGHT = 100

# 调色板
PALETTE = [
    (0, 0, 0),      # 黑
    (255, 255, 255),# 白
    (200, 0, 0),    # 红
    (220, 180, 0),  # 黄
]

COLOR_MAP = {0: 3, 1: 0, 2: 2, 3: 1}


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
    return best_idx, PALETTE[best_idx][0], PALETTE[best_idx][1], PALETTE[best_idx][2]


def apply_four_color_dither(img):
    w, h = img.size
    img = img.convert('RGB')
    
    palette_flat = []
    for color in PALETTE:
        palette_flat.extend(color)
    palette_flat.extend([0] * (256 * 3 - len(palette_flat)))
    
    result = Image.new('P', (w, h))
    result.putpalette(palette_flat)
    
    for y in range(h):
        for x in range(w):
            r, g, b = img.getpixel((x, y))
            
            best_idx, pr, pg, pb = nearest_palette_color(r, g, b)
            result.putpixel((x, y), best_idx)
            
            # 误差扩散（简化版）
            r_err = r - pr
            g_err = g - pg
            b_err = b - pb
            
            if x + 1 < w:
                nr, ng, nb = img.getpixel((x + 1, y))
                img.putpixel((x + 1, y), (
                    int(min(255, max(0, nr + r_err * 7 / 16))),
                    int(min(255, max(0, ng + g_err * 7 / 16))),
                    int(min(255, max(0, nb + b_err * 7 / 16)))
                ))
            if y + 1 < h:
                if x - 1 >= 0:
                    nr, ng, nb = img.getpixel((x - 1, y + 1))
                    img.putpixel((x - 1, y + 1), (
                        int(min(255, max(0, nr + r_err * 3 / 16))),
                        int(min(255, max(0, ng + g_err * 3 / 16))),
                        int(min(255, max(0, nb + b_err * 3 / 16)))
                    ))
                nr, ng, nb = img.getpixel((x, y + 1))
                img.putpixel((x, y + 1), (
                    int(min(255, max(0, nr + r_err * 5 / 16))),
                    int(min(255, max(0, ng + g_err * 5 / 16))),
                    int(min(255, max(0, nb + b_err * 5 / 16)))
                ))
                if x + 1 < w:
                    nr, ng, nb = img.getpixel((x + 1, y + 1))
                    img.putpixel((x + 1, y + 1), (
                        int(min(255, max(0, nr + r_err * 1 / 16))),
                        int(min(255, max(0, ng + g_err * 1 / 16))),
                        int(min(255, max(0, nb + b_err * 1 / 16)))
                    ))
    
    return result


def render_photo_to_eink(photo_path, caption, date_display):
    img = Image.open(photo_path)
    img = ImageOps.exif_transpose(img).convert("RGB")
    
    # 缩放到覆盖区域
    img_w, img_h = img.size
    img_area_w = CANVAS_WIDTH
    img_area_h = CANVAS_HEIGHT - TEXT_AREA_HEIGHT
    
    scale = max(img_area_w / img_w, img_area_h / img_h)
    draw_w = int(img_w * scale)
    draw_h = int(img_h * scale)
    img_resized = img.resize((draw_w, draw_h), Image.LANCZOS)
    
    # 居中裁剪
    left = max(0, (draw_w - img_area_w) // 2)
    top = max(0, (draw_h - img_area_h) // 2)
    img_cropped = img_resized.crop((left, top, left + img_area_w, top + img_area_h))
    
    # 创建画布
    canvas = Image.new('RGB', (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
    canvas.paste(img_cropped, (0, 0))
    
    # 添加文字
    draw = ImageDraw.Draw(canvas)
    try:
        font = ImageFont.truetype(FONT_PATH, 22)
    except:
        font = ImageFont.load_default()
    
    text_y = CANVAS_HEIGHT - 60
    if date_display:
        draw.text((20, text_y - 30), date_display, fill=(200, 0, 0), font=font)
    
    if caption:
        max_chars_per_line = 18
        lines = [caption[i:i+max_chars_per_line] for i in range(0, len(caption), max_chars_per_line)]
        for i, line in enumerate(lines[:2]):
            draw.text((20, text_y + i * 28), line, fill=(200, 0, 0), font=font)
    
    # 抖动
    dithered = apply_four_color_dither(canvas)
    return dithered


def image_to_palette_bin(img):
    w, h = img.size
    pixels = []
    for y in range(h):
        for x in range(w):
            idx = img.getpixel((x, y))
            pixels.append(idx)
    return pixels


def rotate_cw_90(old_pixels, old_w, old_h):
    """顺时针旋转90度"""
    new_w = old_h
    new_h = old_w
    new_pixels = [0] * (new_w * new_h)
    
    for old_row in range(old_h):
        for old_col in range(old_w):
            new_col = old_row
            new_row = new_h - 1 - old_col
            old_idx = old_row * old_w + old_col
            new_idx = new_row * new_w + new_col
            new_pixels[new_idx] = old_pixels[old_idx]
    
    return new_pixels


def pack_2bpp(pixels, width, height):
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
    lines = []
    lines.append('const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */')
    
    hex_strs = [f'0X{b:02X}' for b in data]
    
    for i in range(0, len(hex_strs), 16):
        chunk = hex_strs[i:i+16]
        lines.append(','.join(chunk) + ',')
    
    lines[-1] = lines[-1].rstrip(',')
    lines.append('};')
    
    output_path.write_text('\n'.join(lines), encoding='utf-8')


def main(mmdd):
    # 获取照片信息
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT path, side_caption, exif_datetime 
        FROM photo_scores 
        WHERE exif_datetime LIKE ? 
        ORDER BY memory_score DESC 
        LIMIT 1
    """, (f'%:{mmdd[:2]}:{mmdd[2:]}%',))
    row = cur.fetchone()
    conn.close()
    
    if not row:
        print(f"未找到 {mmdd} 的照片")
        return
    
    path, caption, datetime = row
    print(f"处理 {mmdd}: {path}")
    
    # 渲染墨水屏图片
    eink_img = render_photo_to_eink(path, caption, datetime[:10] if datetime else "")
    
    # 保存中间结果
    eink_img.save(f"preview/{mmdd}_eink.png")
    print(f"已保存: {mmdd}_eink.png")
    
    # 转换为数组
    pixels = image_to_palette_bin(eink_img)
    
    # 顺时针旋转90度
    rotated = rotate_cw_90(pixels, 480, 800)
    
    # 打包并生成 .h 文件
    packed = pack_2bpp(rotated, 800, 480)
    generate_h_file(packed, Path(f"data/{mmdd}.h"))
    print(f"已生成: data/{mmdd}.h")


if __name__ == "__main__":
    main("0605")
