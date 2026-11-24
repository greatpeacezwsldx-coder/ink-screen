from PIL import Image
import sys

# Open the image
img = Image.open('4c.png')
print(f"Image size: {img.size}")
print(f"Image mode: {img.mode}")

# Convert to RGB if needed
if img.mode != 'RGB':
    img = img.convert('RGB')

# Resize to 800x480 if different
target_size = (800, 480)
if img.size != target_size:
    img = img.resize(target_size, Image.LANCZOS)
    print(f"Resized to {target_size}")

# Get all pixels
pixels = list(img.getdata())

# Define 4-color palette (white, yellow, red, black)
# These are the actual e-paper 4-color palette
palette = [
    (255, 255, 255),  # 00 - white
    (255, 255, 0),    # 01 - yellow
    (255, 0, 0),      # 10 - red
    (0, 0, 0)         # 11 - black
]

def color_to_2bit(r, g, b):
    """Convert RGB to 2-bit palette index"""
    # Calculate grayscale value
    gray = (r * 299 + g * 587 + b * 114) // 1000

    # Find closest palette color
    min_dist = float('inf')
    best_idx = 0
    for idx, (pr, pg, pb) in enumerate(palette):
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < min_dist:
            min_dist = dist
            best_idx = idx
    return best_idx

# Convert pixels to packed bytes
# Each byte holds 4 pixels (2 bits each)
packed_data = []
for y in range(480):
    row_bytes = []
    for x in range(0, 800, 4):
        byte = 0
        for i in range(4):
            px = x + i
            if px < 800:
                pixel = img.getpixel((px, y))
                color_idx = color_to_2bit(pixel[0], pixel[1], pixel[2])
                byte |= (color_idx << (6 - i * 2))
        row_bytes.append(byte)
    packed_data.extend(row_bytes)

print(f"Total bytes: {len(packed_data)}")

# Write header file
with open('4c_image.h', 'w') as f:
    f.write('const unsigned char gImage_4c[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */\n')

    for i in range(0, len(packed_data), 16):
        chunk = packed_data[i:i+16]
        hex_str = ','.join(f'0X{byte:02X}' for byte in chunk)
        f.write(hex_str + ',\n')

    f.write('};\n')

print("Generated 4c.h")
