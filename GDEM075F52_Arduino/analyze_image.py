from PIL import Image
from collections import Counter

img = Image.open('4c.png')
print(f'Size: {img.size}, Mode: {img.mode}')

# Count all colors (quantized to reduce noise)
all_colors = Counter()
for y in range(480):
    for x in range(800):
        pixel = img.getpixel((x, y))
        r, g, b = pixel[0], pixel[1], pixel[2]
        # Quantize to 16 levels
        key = (r//16, g//16, b//16)
        all_colors[key] += 1

print('All colors in image (quantized to 16 levels):')
for c, count in sorted(all_colors.items(), key=lambda x: -x[1])[:20]:
    r, g, b = c[0]*16+8, c[1]*16+8, c[2]*16+8
    print(f'  RGB({r},{g},{b}): {count} pixels')

# Save to file
with open('analyze_result.txt', 'w') as f:
    f.write(f'Size: {img.size}, Mode: {img.mode}\n')
    for c, count in sorted(all_colors.items(), key=lambda x: -x[1])[:20]:
        r, g, b = c[0]*16+8, c[1]*16+8, c[2]*16+8
        f.write(f'RGB({r},{g},{b}): {count}\n')
print('Done')
