with open('0615.h', 'r') as f:
    lines_0615 = f.readlines()

with open('0615a.h', 'r') as f:
    lines_0615a = f.readlines()

print(f"0615.h 行数: {len(lines_0615)}, 大小: {sum(len(line) for line in lines_0615)} bytes")
print(f"0615a.h 行数: {len(lines_0615a)}, 大小: {sum(len(line) for line in lines_0615a)} bytes")

print("\n第1行比较:")
print(f"0615.h: {lines_0615[0].strip()}")
print(f"0615a.h: {lines_0615a[0].strip()}")

print("\n第2行长度比较:")
print(f"0615.h 第2行长度: {len(lines_0615[1])}")
print(f"0615a.h 第2行长度: {len(lines_0615a[1])}")

print("\n第2行逗号数量比较:")
print(f"0615.h 第2行逗号数: {lines_0615[1].count(',')}")
print(f"0615a.h 第2行逗号数: {lines_0615a[1].count(',')}")

print("\n文件末尾比较:")
print(f"0615.h 最后一行: {lines_0615[-1][:50]}...")
print(f"0615a.h 最后一行: {lines_0615a[-1][:50]}...")

print("\n换行符类型检查:")
print(f"0615.h 第1行换行符: {'\\r\\n' in lines_0615[0] and 'CRLF' or 'LF'}")
print(f"0615a.h 第1行换行符: {'\\r\\n' in lines_0615a[0] and 'CRLF' or 'LF'}")