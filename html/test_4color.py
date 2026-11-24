#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测试四色墨水屏效果"""

from PIL import Image, ImageOps
from pathlib import Path

# 四色墨水屏调色板
PALETTE = [
    (0, 0, 0),         # 0 = 黑
    (255, 255, 255),   # 1 = 白
    (200, 0, 0),       # 2 = 红
    (220, 180, 0),     # 3 = 黄
]

def nearest_palette_color(r, g, b):
    best_idx = 0
    best_dist = float('inf')
    for i, (pr, pg, pb) in enumerate(PALETTE):
        dr = r - pr
        dg = g - pg
        db = b - pb
        dist = dr*dr + dg*dg + db*db
        if dist < best_dist:
            best_dist = dist
            best_idx = i
    pr, pg, pb = PALETTE[best_idx]
    return best_idx, pr, pg, pb

def apply_four_color_dither(img):
    img = img.convert('RGB')
    w, h = img.size
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

            idx, pr, pg, pb = nearest_palette_color(r, g, b)
            pixels[x, y] = (pr, pg, pb)

            er, eg, eb = r - pr, g - pg, b - pb

            if x + 1 < w:
                err_r[x+1] += er * (7.0/16.0)
                err_g[x+1] += eg * (7.0/16.0)
                err_b[x+1] += eb * (7.0/16.0)
            if y + 1 < h:
                if x > 0:
                    next_err_r[x-1] += er * (3.0/16.0)
                    next_err_g[x-1] += eg * (3.0/16.0)
                    next_err_b[x-1] += eb * (3.0/16.0)
                next_err_r[x] += er * (5.0/16.0)
                next_err_g[x] += eg * (5.0/16.0)
                next_err_b[x] += eb * (5.0/16.0)
                if x + 1 < w:
                    next_err_r[x+1] += er * (1.0/16.0)
                    next_err_g[x+1] += eg * (1.0/16.0)
                    next_err_b[x+1] += eb * (1.0/16.0)

        if y + 1 < h:
            for i in range(w):
                err_r[i] = next_err_r[i]
                err_g[i] = next_err_g[i]
                err_b[i] = next_err_b[i]
                next_err_r[i] = 0.0
                next_err_g[i] = 0.0
                next_err_b[i] = 0.0

    return img

if __name__ == "__main__":
    # 加载测试图片
    test_img = Path('/Users/zhangwei/Desktop/source/html/test/IMG_2958.JPG')
    img = Image.open(test_img)
    img = ImageOps.exif_transpose(img).convert('RGB')

    # 缩放到墨水屏尺寸 480x800
    img = img.resize((480, 800), Image.LANCZOS)

    # 应用四色抖动
    print("正在应用四色 Floyd-Steinberg 抖动...")
    img_dithered = apply_four_color_dither(img)

    # 保存结果
    output_path = Path('/Users/zhangwei/Desktop/source/html/output/test_4color.png')
    output_path.parent.mkdir(parents=True, exist_ok=True)
    img_dithered.save(output_path)
    print(f'已保存四色墨水屏效果图: {output_path}')
