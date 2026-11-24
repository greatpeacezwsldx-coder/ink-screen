#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""预览 Ap_29demo.h 转换后的效果"""

import re
from pathlib import Path
from PIL import Image


def parse_ap29demo_h(filepath: Path) -> list[int]:
    """解析 Ap_29demo.h，提取像素"""
    content = filepath.read_text(encoding='utf-8')
    pixels = []
    for line in content.split('\n'):
        hex_vals = re.findall(r'0[Xx]([0-9a-fA-F]{2})', line)
        pixels.extend([int(v, 16) for v in hex_vals])
    return pixels


def unpack_2bpp(data: list[int], width: int, height: int) -> list[int]:
    """解包 2bpp 数据"""
    COLOR_MAP = {0: (255, 255, 255), 1: (255, 200, 0), 2: (200, 0, 0), 3: (0, 0, 0)}
    
    pixels = []
    for byte in data:
        p0 = (byte >> 6) & 0x03
        p1 = (byte >> 4) & 0x03
        p2 = (byte >> 2) & 0x03
        p3 = byte & 0x03
        pixels.extend([p0, p1, p2, p3])
    
    # 转换为 RGB 图像
    rgb = []
    for p in pixels[:width * height]:
        rgb.append(COLOR_MAP.get(p, (128, 128, 128)))
    
    return rgb


def create_preview(rgb_data: list[tuple], width: int, height: int, output_path: Path):
    """创建预览图"""
    img = Image.new('RGB', (width, height))
    img.putdata(rgb_data)
    img.save(output_path)
    print(f"[OK] 预览图已保存: {output_path}")


def main():
    ap29demo = Path('/Users/zhangwei/Desktop/source/html/Ap_29demo.h')
    output = Path('/Users/zhangwei/Desktop/source/html/output/preview_ap29demo.png')
    
    print("[INFO] 解析 Ap_29demo.h...")
    data = parse_ap29demo_h(ap29demo)
    print(f"[INFO] 读取数据: {len(data)} bytes")
    
    print("[INFO] 解包 2bpp 数据...")
    rgb = unpack_2bpp(data, 800, 480)
    
    print("[INFO] 生成预览图...")
    create_preview(rgb, 800, 480, output)
    
    print(f"\n预览图: {output}")


if __name__ == '__main__':
    main()
