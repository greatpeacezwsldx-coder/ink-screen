from PIL import Image, ImageDraw, ImageFont

# 4色定义
WHITE = 0    # 00
YELLOW = 1   # 01
RED = 2      # 10
BLACK = 3    # 11

# 调色板
palette = [
    (255, 255, 255),  # WHITE
    (255, 255, 0),    # YELLOW
    (255, 0, 0),      # RED
    (0, 0, 0)         # BLACK
]

def rgb_to_4color(r, g, b):
    """将RGB颜色转换为4色索引"""
    min_dist = float('inf')
    best_idx = 0
    for idx, (pr, pg, pb) in enumerate(palette):
        dist = (r - pr) ** 2 + (g - pg) ** 2 + (b - pb) ** 2
        if dist < min_dist:
            min_dist = dist
            best_idx = idx
    return best_idx

# 1. 读取原图
img = Image.open('new1.png')
print(f'Original size: {img.size}')

# 2. 调整尺寸到 800x480
img = img.resize((800, 480), Image.LANCZOS)

# 3. 转换为RGB
if img.mode != 'RGB':
    img = img.convert('RGB')

# 4. 创建4色图片
img_4color = Image.new('RGB', (800, 480))

# 5. 将原图转换为4色（左侧 0-739 列）
for y in range(480):
    for x in range(740):
        r, g, b = img.getpixel((x, y))
        idx = rgb_to_4color(r, g, b)
        img_4color.putpixel((x, y), palette[idx])

# 6. 右侧黑色条 (x=740-800，加宽到60像素)
for y in range(480):
    for x in range(740, 800):
        img_4color.putpixel((x, y), palette[BLACK])

# 7. 在黑色条上写竖排文字（每个字逆时针旋转90度）
text = "万圣节小女巫上线，可爱魔法一键生效"
# 创建一个临时图像来绘制旋转后的文字
text_img = Image.new('RGB', (60, 480), palette[BLACK])

try:
    font = ImageFont.truetype('simhei.ttf', 20)
except:
    try:
        font = ImageFont.truetype('msyh.ttc', 20)
    except:
        font = ImageFont.load_default()

# 计算文字高度
char_height = 28
total_height = len(text) * char_height
start_y = (480 - total_height) // 2

# 从下往上绘制每个字符（每个字符逆时针旋转90度）
y = start_y + total_height - char_height
for char in text:
    # 为每个字符创建临时图像
    char_img = Image.new('RGB', (char_height, char_height), palette[BLACK])
    char_draw = ImageDraw.Draw(char_img)
    # 绘制字符（居中）
    char_draw.text((2, 2), char, font=font, fill=palette[WHITE])
    # 逆时针旋转90度
    char_img_rotated = char_img.rotate(90, expand=True)
    # 粘贴到文字图像（居中）
    text_img.paste(char_img_rotated, (15, y))
    y -= char_height

# 将文字图像粘贴到主图像
img_4color.paste(text_img, (740, 0))

# 8. 保存新图片
img_4color.save('new1_4color.png')
print('Saved new1_4color.png')

# 9. 生成 .h 文件
packed_data = []
for y in range(480):
    for x in range(0, 800, 4):
        byte = 0
        for i in range(4):
            px = x + i
            if px < 800:
                r, g, b = img_4color.getpixel((px, y))
                # 找到颜色索引
                for idx, (pr, pg, pb) in enumerate(palette):
                    if r == pr and g == pg and b == pb:
                        byte |= (idx << (6 - i * 2))
                        break
        packed_data.append(byte)

# 写入 .h 文件
with open('new1_image.h', 'w') as f:
    f.write('const unsigned char gImage_new1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */\n')
    
    for i in range(0, len(packed_data), 16):
        chunk = packed_data[i:i+16]
        hex_str = ','.join(f'0X{byte:02X}' for byte in chunk)
        f.write(hex_str + ',\n')
    
    f.write('};\n')

print('Generated new_image.h')
print(f'Total bytes: {len(packed_data)}')