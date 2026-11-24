#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
将 latest.h 转换为 Ap_29demo.h 格式（4色墨水屏，800x480）

转换步骤：
1. 读取 latest.h 的 480x800 像素数据（每像素1 byte）
2. 逆时针旋转90度 -> 800x480
3. 颜色映射：0(黑)->3, 1(白)->0, 2(红)->2, 3(黄)->1
4. 每4像素打包成1 byte（2bpp）
"""

import re
from pathlib import Path


def parse_latest_h(filepath: Path) -> list[int]:
    """解析 latest.h，提取像素数组（0=黑,1=白,2=红,3=黄）"""
    content = filepath.read_text(encoding='utf-8')
    pixels = []
    for line in content.split('\n'):
        hex_vals = re.findall(r'0[Xx]([0-9a-fA-F]{2})', line)
        pixels.extend([int(v, 16) for v in hex_vals])
    return pixels[:480*800]


def rotate_cw_90(old_pixels: list[int], old_w: int, old_h: int) -> list[int]:
    """顺时针旋转90度"""
    new_w = old_h  # 800
    new_h = old_w  # 480
    new_pixels = [0] * (new_w * new_h)
    
    for old_row in range(old_h):
        for old_col in range(old_w):
            new_col = old_row
            new_row = new_h - 1 - old_col
            old_idx = old_row * old_w + old_col
            new_idx = new_row * new_w + new_col
            new_pixels[new_idx] = old_pixels[old_idx]
    
    return new_pixels


def shift_horizontal(pixels: list[int], width: int, height: int, shift: int) -> list[int]:
    """水平偏移（向右移动）"""
    if shift == 0:
        return pixels
    
    result = [0] * (width * height)
    
    for row in range(height):
        for col in range(width):
            src_col = (col - shift) % width
            src_idx = row * width + src_col
            dst_idx = row * width + col
            result[dst_idx] = pixels[src_idx]
    
    return result


def color_map(pixel: int) -> int:
    """颜色映射"""
    mapping = {0: 3, 1: 0, 2: 2, 3: 1}
    return mapping.get(pixel, 0)


def pack_2bpp(pixels: list[int], width: int, height: int) -> bytes:
    """打包成2bpp格式"""
    result = bytearray()
    for row in range(height):
        for col in range(0, width, 4):
            idx = row * width + col
            p0 = color_map(pixels[idx])
            p1 = color_map(pixels[idx + 1]) if col + 1 < width else 0
            p2 = color_map(pixels[idx + 2]) if col + 2 < width else 0
            p3 = color_map(pixels[idx + 3]) if col + 3 < width else 0
            byte = (p0 << 6) | (p1 << 4) | (p2 << 2) | p3
            result.append(byte)
    return bytes(result)


def generate_ap29demo_h(data: bytes, output_path: Path) -> None:
    """生成 Ap_29demo.h 格式"""
    lines = []
    lines.append('const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */')
    
    hex_strs = [f'0X{b:02X}' for b in data]
    
    for i in range(0, len(hex_strs), 16):
        chunk = hex_strs[i:i+16]
        lines.append(','.join(chunk) + ',')
    
    lines[-1] = lines[-1].rstrip(',')
    lines.append('};')
    
    output_path.write_text('\n'.join(lines), encoding='utf-8')
    print(f"[OK] 已生成: {output_path}")


def main():
    latest_h = Path('/Users/zhangwei/Desktop/source/html/output/latest.h')
    output_h = Path('/Users/zhangwei/Desktop/source/html/Ap_29demo.h')
    
    pixels = parse_latest_h(latest_h)
    print(f"[INFO] 读取像素: {len(pixels)}")
    
    # 顺时针旋转90度
    rotated = rotate_cw_90(pixels, 480, 800)
    print(f"[INFO] 旋转后: {len(rotated)} pixels (800x480)")
    
    # 打包
    packed = pack_2bpp(rotated, 800, 480)
    print(f"[INFO] 打包后: {len(packed)} bytes")
    
    generate_ap29demo_h(packed, output_h)


if __name__ == '__main__':
    main()
