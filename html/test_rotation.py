#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试照片旋转处理流程
"""

from pathlib import Path
from PIL import Image, ImageOps

# 测试照片
TEST_PHOTO = "/Users/zhangwei/Desktop/source/html/test/IMG_3132.JPG"

def main():
    # 1. 读取原始图片
    img = Image.open(TEST_PHOTO)
    print(f"原始图片: {img.size}, mode: {img.mode}")
    
    # 2. 应用 EXIF 旋转
    img_exif = ImageOps.exif_transpose(img)
    print(f"EXIF 旋转后: {img_exif.size}")
    
    # 3. 保存原始和 EXIF 旋转后的图片
    img.save("preview/0605_original.png")
    img_exif.save("preview/0605_exif.png")
    print("已保存: 0605_original.png, 0605_exif.png")
    
    # 4. 模拟渲染流程
    CANVAS_WIDTH = 480
    CANVAS_HEIGHT = 800
    TEXT_AREA_HEIGHT = 100
    
    img_area_w = CANVAS_WIDTH
    img_area_h = CANVAS_HEIGHT - TEXT_AREA_HEIGHT
    
    # 缩放到覆盖区域
    img_w, img_h = img_exif.size
    scale = max(img_area_w / img_w, img_area_h / img_h)
    draw_w = int(img_w * scale)
    draw_h = int(img_h * scale)
    img_resized = img_exif.resize((draw_w, draw_h), Image.LANCZOS)
    
    # 居中裁剪
    left = max(0, (draw_w - img_area_w) // 2)
    top = max(0, (draw_h - img_area_h) // 2)
    right = left + img_area_w
    bottom = top + img_area_h
    img_cropped = img_resized.crop((left, top, right, bottom))
    
    # 创建画布并粘贴
    canvas = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255))
    canvas.paste(img_cropped, (0, 0))
    
    # 保存渲染后的图片（480x800）
    canvas.save("preview/0605_rendered.png")
    print("已保存: 0605_rendered.png (480x800)")
    
    # 5. 顺时针旋转90度（模拟 generate_daily_best.py 的处理）
    canvas_rotated = canvas.rotate(-90, expand=True)  # PIL 的 rotate 正数是逆时针
    print(f"顺时针旋转90度后: {canvas_rotated.size}")
    canvas_rotated.save("preview/0605_rotated.png")
    print("已保存: 0605_rotated.png")
    
    # 6. 逆时针旋转90度（对比）
    canvas_rotated_ccw = canvas.rotate(90, expand=True)
    canvas_rotated_ccw.save("preview/0605_rotated_ccw.png")
    print("已保存: 0605_rotated_ccw.png (逆时针旋转)")

if __name__ == "__main__":
    main()
