#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 .h 文件还原成4色墨水屏图片

还原步骤：
1. 解析 .h 文件，提取像素数组
2. 解包 2bpp 格式（每字节4个像素）
3. 反向颜色映射
4. 创建图片并保存
"""

import re
from pathlib import Path
from PIL import Image

# 墨水屏调色板（4色）
PALETTE = [
    (0, 0, 0),      # 黑 (原始)
    (255, 255, 255),# 白 (原始)
    (200, 0, 0),    # 红 (原始)
    (220, 180, 0),  # 黄 (原始)
]

# 反向颜色映射：墨水屏格式 -> 原始格式
REVERSE_COLOR_MAP = {0: 1, 1: 3, 2: 2, 3: 0}


def parse_h_file(filepath: Path) -> bytes:
    """解析 .h 文件，提取像素数据"""
    content = filepath.read_text(encoding='utf-8')
    hex_vals = re.findall(r'0[Xx]([0-9a-fA-F]{2})', content)
    return bytes([int(v, 16) for v in hex_vals])


def unpack_2bpp(data: bytes, width: int, height: int) -> list[int]:
    """解包 2bpp 格式，返回像素索引数组"""
    pixels = []
    for byte in data:
        p0 = (byte >> 6) & 0x03
        p1 = (byte >> 4) & 0x03
        p2 = (byte >> 2) & 0x03
        p3 = byte & 0x03
        pixels.extend([p0, p1, p2, p3])
    return pixels[:width * height]


def h_to_image(h_path: Path, output_path: Path, width: int = 800, height: int = 480):
    """将 .h 文件转换为图片"""
    print(f"[INFO] 读取: {h_path}")
    
    # 解析 .h 文件
    packed_data = parse_h_file(h_path)
    print(f"[INFO] 读取字节数: {len(packed_data)}")
    
    # 解包 2bpp
    pixels = unpack_2bpp(packed_data, width, height)
    print(f"[INFO] 解包后像素数: {len(pixels)}")
    
    # 创建调色板图像
    palette_flat = []
    for color in PALETTE:
        palette_flat.extend(color)
    palette_flat.extend([0] * (256 * 3 - len(palette_flat)))
    
    img = Image.new('P', (width, height))
    img.putpalette(palette_flat)
    
    # 应用反向颜色映射并设置像素
    mapped_pixels = [REVERSE_COLOR_MAP.get(p, 1) for p in pixels]
    img.putdata(mapped_pixels)
    
    # 保存图片
    img.save(output_path)
    print(f"[OK] 已保存: {output_path}")
    
    return img


def main():
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python h_to_image.py <h文件路径> [输出图片路径]")
        print("示例: python h_to_image.py data/0616.h preview/0616.png")
        sys.exit(1)
    
    h_path = Path(sys.argv[1])
    
    if len(sys.argv) >= 3:
        output_path = Path(sys.argv[2])
    else:
        output_path = h_path.with_suffix('.png')
    
    if not h_path.exists():
        print(f"错误: 文件不存在 {h_path}")
        sys.exit(1)
    
    h_to_image(h_path, output_path)


if __name__ == '__main__':
    main()
