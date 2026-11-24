# GDEM075F52 墨水屏电子相框固件

ESP32 驱动 **GDEM075F52**（800×480 四色墨水屏）的电子相框固件。设备每天定时从华为云 OBS 下载以当天日期命名的图像头文件，解析后刷屏，然后进入深度睡眠，第二天同一时刻再醒。

它是整条「AI 选片 → 云端分发 → 墨水屏显示」链路的**最后一环**：

| 环节 | 项目 | 职责 |
|---|---|---|
| 选片与渲染 | `D:\project\html` | VLM 打分、四色抖动、生成 `MMDD.h`（96000 字节） |
| 云端分发 | 华为云 OBS | 桶 `mypublicbucket0101`，`/images/MMDD.h` 匿名可读 |
| **屏幕驱动** | **本目录** | 下载 → 解析 → SPI 刷屏 → 深度睡眠 |
| 手机端 | `D:\project\e-ink` | 微信小程序，浏览同一批照片 |
| 平板端 | `D:\project\inkscreen` | HarmonyOS 应用 |

---

## 1. 这是什么项目

- **类型**：Arduino sketch（C++），**不是** ESP-IDF、不是 PlatformIO 工程
- **无** `platformio.ini`、无 `CMakeLists.txt`、无 `sdkconfig`、无 `Makefile`
- **编译方式**：Arduino IDE / arduino-cli 的 sketch 构建器
- **已验证环境**：`esp32:esp32` 核心 **3.3.10**，开发板 **ESP32 Dev Module**

主程序只有 4 个源文件：

| 文件 | 行数 | 作用 |
|---|---|---|
| `GDEM075F52_Arduino.ino` | 431 | 主逻辑：WiFi → NTP → HTTP 下载 → 十六进制解析 → 刷屏 → 深度睡眠 |
| `Display_EPD_W21.cpp` | 300 | 屏幕驱动：初始化序列、颜色映射、刷屏、睡眠 |
| `Display_EPD_W21_spi.cpp` | 24 | SPI 底层：写命令 / 写数据 / 引脚宏 |
| `Ap_29demo.h` | 492 KB | 内置兜底图（下载失败时显示），96000 字节像素数据 |

---

## 2. 硬件与接线

### 2.1 清单

| 项 | 规格 |
|---|---|
| 主控 | ESP32（经典款 Xtensa LX6，**不是** S2/S3/C3） |
| 屏幕 | GDEM075F52，800×480，四色（黑 / 白 / 黄 / 红），SPI 接口 |
| 数据格式 | 2 bpp，4 像素打包成 1 字节，共 96000 字节 |

### 2.2 引脚对照表

代码里用的是 Arduino 的模拟引脚别名 `A14`–`A17`，**必须**换算成真实 GPIO 号才能接线。下表是 `ESP32 Dev Module` + 核心 3.3.10 的实测值（读自 `variants/esp32/pins_arduino.h`）：

| 屏幕信号 | 代码写法 | 方向 | 实际 GPIO |
|---|---|---|---|
| BUSY | `A14` | 输入 | **13** |
| RES（复位） | `A15` | 输出 | **12** ⚠️ |
| DC（数据/命令） | `A16` | 输出 | **14** |
| CS（片选） | `A17` | 输出 | **27** |
| SCK | 默认 | 输出 | **18** |
| MOSI(SDIN) | 默认 | 输出 | **23** |
| MISO | 未使用 | — | 19 |
| VCC / GND | — | — | 3.3V / GND |

换算依据（核心 3.3.10）：

```c
static const uint8_t A14 = 13;
static const uint8_t A15 = 12;
static const uint8_t A16 = 14;
static const uint8_t A17 = 27;
static const uint8_t SCK  = 18;
static const uint8_t MOSI = 23;
```

> ⚠️ **两个坑**
>
> **1. `Display_EPD_W21_spi.h` 里的注释是反的。** 第 6–7 行写的是 `SCK--GPIO23(SCLK)` / `SDIN---GPIO18(MOSI)`，但 ESP32 默认是 **SCK=18、MOSI=23**。按注释接会完全不通，**以本表为准**。
>
> **2. RES 落在 GPIO12（MTDI）上，这是 ESP32 的 strapping 引脚**，上电瞬间它决定 Flash 工作电压。绝大多数模块内部已有下拉，能正常启动；但如果墨水屏模组的 RES 线上带了外部上拉电阻，板子会**直接起不来**（表现为串口无任何输出）。这种情况下要么换引脚，要么把 RES 改到别的 GPIO。
>
> **3. 换开发板或换核心版本后，务必重新核对映射。** `A14`–`A17` 的取值由所选开发板变体决定，不是固定值。加一行自检最省事：
>
> ```cpp
> Serial.printf("BUSY=%d RES=%d DC=%d CS=%d\n", A14, A15, A16, A17);
> ```

---

## 3. 编译运行流程

### 3.1 第一步：安装 Arduino IDE 与 ESP32 支持包

1. 安装 **Arduino IDE 2.x**（<https://www.arduino.cc/en/software>）
2. 打开 `文件 → 首选项 → 其他开发板管理器地址`，填入：

   ```
   https://jihulab.com/esp-mirror/espressif/arduino-esp32/-/raw/gh-pages/package_esp32_index_cn.json
   ```

   > 官方地址 `https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json` 在国内基本连不上。上面这个镜像源是本工程实际使用的（见 `%USERPROFILE%\.arduinoIDE\arduino-cli.yaml`）。两个都填上也可以，用逗号分隔。

3. `工具 → 开发板 → 开发板管理器`，搜索 **esp32**，安装 **esp32 by Espressif Systems**（建议 ≥ 3.0；本文档按 3.3.10 实测）
4. 装 USB 串口驱动（CP210x 或 CH340，取决于你的板子），插上板子在设备管理器确认出现 COM 口

### 3.2 第二步：打开工程

直接双击 `GDEM075F52_Arduino.ino`，或用 `文件 → 打开`。

> ⚠️ Arduino 要求 **文件夹名必须与 `.ino` 文件名完全一致**。当前是 `GDEM075F52_Arduino\GDEM075F52_Arduino.ino`，符合。**重命名文件夹会导致工程打不开。**

### 3.3 第三步：改配置（至少改一处）

打开 `GDEM075F52_Arduino.ino` 第 12–31 行：

```cpp
// WiFi配置 —— 必改
const char* ssid     = "建霖的iPhone";
const char* password = "zjl11118";

// NTP配置
const char* ntpServer = "pool.ntp.org";

// 华为云配置
const char* huawei_cloud_url = "http://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/images/";
const char* file_extension   = ".h";

// 备用日期（当NTP失败时使用）
const int fallback_month = 6;
const int fallback_day   = 16;

// 唤醒时间配置
const int WAKE_HOUR   = 6;   // 6点
const int WAKE_MINUTE = 10;  // 10分
```

| 项 | 是否必改 | 说明 |
|---|---|---|
| `ssid` / `password` | ✅ **必改** | 当前硬编码的是作者的手机热点 |
| `huawei_cloud_url` | 视情况 | 换桶或换目录时改；注意是 **`http://` 不是 `https://`** |
| `ntpServer` | 建议改 | `pool.ntp.org` 在国内较慢，建议换成 `ntp.aliyun.com` |
| `fallback_month/day` | 建议改 | NTP 失败时用它拼文件名，应改成一个桶里**确实存在**的日期 |
| `WAKE_HOUR/MINUTE` | 可选 | 默认每天早上 6:10 |

### 3.4 第四步：设置开发板参数

`工具` 菜单：

| 选项 | 取值 |
|---|---|
| Board | **ESP32 Dev Module** |
| Upload Speed | 921600（连不上就降到 115200） |
| CPU Frequency | 240 MHz（默认） |
| Flash Mode | QIO（默认） |
| Flash Size | 4MB (32Mb)（默认） |
| **Partition Scheme** | **Default 4MB with spiffs**（默认即可，实测占用 88%） |
| Core Debug Level | 排障时开 `Info` 或 `Debug`，平时 `None` |
| Port | 选你的 COM 口 |

> Flash 已用 **88%**，余量只有约 143 KB。如果后续想加功能（尤其是把 `http://` 改成 `https://`，TLS 证书栈会吃掉 100 KB 以上），**先把 Partition Scheme 改成 `Huge APP (3MB No OTA/1MB SPIFFS)`**，否则会编译报 `region 'flash' overflowed`。

### 3.5 第五步：编译与上传

1. 点 **√（验证）** 编译
2. 点 **→（上传）** 烧录
3. 上传完成后**立刻**打开 `工具 → 串口监视器`，波特率选 **115200**

> 若上传卡在 `Connecting...`，按住板上的 **BOOT** 键再点上传，看到进度后松开。

### 3.6 第六步：看串口日志确认跑通

正常启动时应该看到（节选，实际每次只走一条分支）：

```
========================================
Wakeup reason: Power on / Reset
========================================
Initializing GPIO pins...
GPIO pins initialized
========================================
Step 1: Connecting to WiFi...
SSID: <你的热点>
Waiting for connection.......
✅ WiFi connected successfully!
IP address: 192.168.x.x
Signal strength (RSSI): -58 dBm
========================================
========================================
Step 2: Downloading image from cloud...
Syncing time via NTP...
Current time: 2026-10-28 11:58:03
Using date from NTP: 10/28
Target filename: 1028.h
Full download URL: http://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/images/1028.h
Allocating image buffer (96KB)...
✅ Image buffer allocated
Starting HTTP request...
HTTP response code: 200
Downloading and parsing .h file...
Progress: 10%
Progress: 20%
...
Progress: 100%
✅ Download and parsing COMPLETE!
========================================
========================================
Step 3: Displaying image on EPD...
✅ Using downloaded image from cloud
✅ Display complete!
========================================
========================================
Step 4: Scheduling next wakeup...
Current time: Tue Oct 28 11:58:09 2026
Next wakeup time: Wed Oct 29 06:10:00 2026
Sleep duration: 18.20 hours
Entering deep sleep...
```

之后设备断电式睡眠，**串口断开是正常的**。第二天 6:10 自动重启，日志开头会变成：

```
Wakeup reason: Timer wakeup (auto scheduled)
```

### 3.7 命令行编译（CI / 批量烧录）

等价于 IDE 的 arduino-cli 命令（本文档的编译数据就是用这条命令跑出来的）：

```bash
arduino-cli compile \
  -b esp32:esp32:esp32 \
  --build-path <临时构建目录> \
  "D:/project/GDEM075F52_Arduino"

arduino-cli upload \
  -b esp32:esp32:esp32 \
  -p COM3 \
  --input-dir <临时构建目录> \
  "D:/project/GDEM075F52_Arduino"
```

### 3.8 实测编译结果

在 `esp32:esp32@3.3.10` + `ESP32 Dev Module`（默认 4MB with spiffs 分区）下编译通过：

```
Sketch uses 1162965 bytes (88%) of program storage space. Maximum is 1310720 bytes.
Global variables use 49316 bytes (15%) of dynamic memory, leaving 278364 bytes for local variables.
Maximum is 327680 bytes.
```

各段明细：

| 段 | 大小 | 说明 |
|---|---|---|
| `.flash.text` | 775,960 | 代码（WiFi / TCP / HTTPClient 占大头） |
| `.flash.rodata` | 265,416 | 只读数据，**含 96,000 字节的兜底图片** |
| `.iram0.text` | 94,231 | IRAM 中的中断相关代码 |
| `.flash.rodata_noload` | 23,338 | WiFi/协议栈常量 |
| `.dram0.data` | 26,074 | 已初始化全局变量 |
| `.dram0.bss` | 23,240 | 未初始化全局变量 |

**内存是否够用**：全局占用 49 KB，剩余 **278 KB** 可给堆 → 运行时 `malloc(96000)` 完全没问题（约 34%）。

---

## 4. 固件运行流程

```
上电 / 深度睡眠唤醒
        │
        ▼
   setup()
        │
        ├─ Serial.begin(115200)
        ├─ 打印唤醒原因（Timer / GPIO / 上电）
        ├─ 配置 BUSY/RES/DC/CS 引脚
        ├─ SPI.beginTransaction() → SPI.begin()      ← 顺序写反了，见 §10
        ├─ pinMode(BUTTON_PIN, INPUT_PULLUP)
        │
        ▼
   runImageUpdate()
        │
        ├─ connectWiFi()          最多等 15 秒（30 × 500ms）
        │     └─ 失败也继续往下走
        │
        ├─ downloadDailyImage()
        │     ├─ configTime() + getLocalTime()，最多试 5 次
        │     ├─ 拼文件名 "%02d%02d.h"（如 1028.h）
        │     ├─ malloc(96000)
        │     ├─ HTTP GET，流式解析十六进制
        │     └─ 满 96000 字节才算成功
        │
        ├─ displayImage()
        │     ├─ 成功 → EPD_init() → PIC_display(下载缓冲) → EPD_sleep()
        │     └─ 失败 → EPD_init() → PIC_display(gImage_1) → EPD_sleep()
        │           （gImage_1 是 Ap_29demo.h 里的兜底图）
        │
        ▼
   scheduleNextWakeup()
        ├─ 取不到时间 → 睡 12 小时
        ├─ 取到时间   → 算到明天 6:10 的秒数，睡那么久
        ├─ WiFi.disconnect(true) → WiFi.mode(WIFI_OFF)
        └─ esp_deep_sleep_start()

   loop()  ← 永远执行不到
```

### 关于深度睡眠，必须知道的三件事

1. **`loop()` 是空的，且永远不会执行。** 每次 `esp_deep_sleep_start()` 后，下次唤醒是**整个程序从头重跑**（`setup()` 重新执行），RAM 全部丢失——包括 `image_buffer`。这是设计如此，不是 bug。
2. **没有用 RTC memory。** 日期不跨睡眠保存，所以每次醒来都要重新连 WiFi + 重新对 NTP。
3. **只开了定时器唤醒。** 代码里 `pinMode(BUTTON_PIN, INPUT_PULLUP)` 配了按键，但**从未调用** `esp_sleep_enable_gpio_wakeup()` / `esp_sleep_enable_ext0()`，也从未在循环里读按键状态。**所以按键完全无效**，详见 §10。想手动刷新，按板上的 **EN/RST** 键重启。

### 单次唤醒的耗时与功耗

| 阶段 | 大致耗时 |
|---|---|
| WiFi 连接 | 1–15 秒（失败则 15 秒） |
| NTP 对时 | 0–5 秒 |
| 下载 486 KB 文本 | 1–5 秒（取决于网络） |
| 解析 + SPI 传输 | 约 1–2 秒（详见 §10 关于 SPI 速率） |
| 屏幕刷新 | 约 10–30 秒（四色屏全刷较慢，由 `lcd_chkstatus()` 阻塞等待） |
| **合计** | **约 20–60 秒** |

每天只醒一分钟级，其余 24 小时处于深度睡眠，因此电池供电可以撑很久。

---

## 5. 数据契约：OBS 上的 `.h` 文件

固件不吃 PNG/JPG，只认一个非常特殊的格式——**C 语言头文件形式的十六进制数组**，靠文本解析还原成字节流。

### 5.1 文件格式

```
const unsigned char gImage_1[96000] = { /* 0X00,0X02,0X20,0X03,0XE0,0X01, */
0X55,0X55,0X51,0X11,0X11,0X11,0X45,0X55,0X55,0X65,0X65,0X96,0X59,0X96,0X66,0X66,
0X66,0X69,0XA6,0X9A,0X69,0XA6,0X9A,0X6A,0X6A,0XBB,0X7C,0XF3,0X33,0X3C,0XFF,0XEF,
...
};
```

- 第一行注释里的 `0x0320=800`、`0x01E0=480` 是老版本遗留的分辨率头，**固件会跳过注释，不解析**
- 正文每行 16 个字节，格式 `0X` + 两位十六进制（大小写均可）
- 去掉注释后必须**恰好 96000 个字节**

### 5.2 像素打包规则

2 bpp，4 个像素塞进 1 字节，**第一个像素在高 2 位**：

```
bit:  7  6   5  4   3  2   1  0
      px0     px1    px2    px3
```

对应代码 `Display_EPD_W21.cpp`：

```cpp
data_H1 = Color_get(temp1 >> 6 & 0x03) << 6;   // 第 1 个像素
data_H2 = Color_get(temp1 >> 4 & 0x03) << 4;   // 第 2 个像素
data_L1 = Color_get(temp1 >> 2 & 0x03) << 2;   // 第 3 个像素
data_L2 = Color_get(temp1       & 0x03);       // 第 4 个像素
```

扫描顺序：`for(i = 0; i < 480; i++) for(j = 0; j < 200; j++)`，**逐行、从左到右**，一行 200 字节（`Source_BITS/4 = 800/4`）。

### 5.3 颜色映射（容易搞错，已核对）

`.h` 里的 2-bit 索引 → 屏幕寄存器值，由 `Color_get()` 完成：

| `.h` 中的索引 | 含义 | 寄存器值 | 宏 |
|---|---|---|---|
| `0x00` | 白 | `0x01` | `white` |
| `0x01` | 黄 | `0x02` | `yellow` |
| `0x02` | 红 | `0x03` | `red` |
| `0x03` | 黑 | `0x00` | `black` |

屏幕寄存器的硬件编码（`Display_EPD_W21.h` 第 5–9 行）：

```c
#define black   0x00   // 00
#define white   0x01   // 01
#define yellow  0x02   // 10
#define red     0x03   // 11
```

**与 `D:\project\html` 服务端的衔接已经核对过，是对得上的**：服务端 `render_daily_photo.py` 的调色板是 `0=黑, 1=白, 2=红, 3=黄`，生成 `.h` 前用 `COLOR_MAP = {0:3, 1:0, 2:2, 3:1}` 预映射成上表的索引空间，本固件再 `Color_get()` 一次还原成寄存器值——**两级映射正好抵消，颜色一致，不需要改任何一端**。

### 5.4 实测：对象不存在时返回 403，不是 404

华为云 OBS 在匿名请求（无 `ListBucket` 权限）下，访问不存在的对象返回的是 **403 AccessDenied**，而不是 404。实测：

```
http://.../images/0616.h  →  200，486078 字节
http://.../images/1028.h  →  200，486078 字节
http://.../images/0615.h  →  403
http://.../images/0101.h  →  403
http://.../images/1231.h  →  403
```

固件第 216 行的「今天是 404 就试昨天」分支写成 `if (httpCode == HTTP_CODE_NOT_FOUND && !time_ok)`，**这个分支永远不会触发**。详见 §10。

### 5.5 传输开销

`.h` 是纯文本，96000 字节的像素数据编码后约 **475–492 KB**（约 5 倍膨胀）。每次唤醒都要完整下载一遍。如果流量或耗时敏感，建议服务端改成提供二进制 `.bin`（可直接套用服务端已有的 `photo_N.bin` 产物），固端端用 `http.writeToStream()` 直写，能省掉解析开销。

---

## 6. 图片转换工具（Python）

目录下的三个 `.py` 是离线做图用的，**与固件运行无关**，只在你想换图时需要。

### 6.1 依赖

```bash
pip install Pillow
```

### 6.2 `convert_new.py` —— 主用脚本

```bash
python convert_new.py
```

流程（硬编码，不带命令行参数）：

1. 读 `new1.png`，缩放到 **800×480**（LANCZOS）
2. 最近邻量化到 4 色，调色板：

   ```python
   palette = [
       (255, 255, 255),  # 0 白
       (255, 255,   0),  # 1 黄
       (255,   0,   0),  # 2 红
       (  0,   0,   0),  # 3 黑
   ]
   ```

3. 左侧 `x = 0–739` 放照片，右侧 `x = 740–799` 画一条 60 像素宽的黑色竖条
4. 在黑条上写竖排白字（当前文案：`万圣节小女巫上线，可爱魔法一键生效`，在第 55 行硬编码），每字逆时针旋转 90°
5. 输出 `new1_4color.png` 预览图，和 `new1_image.h`

> ⚠️ 三处需要注意：
> - **输出文件名前后不一致**：第 110 行 `open('new1_image.h', 'w')`，第 120 行却打印 `Generated new_image.h`。而目录里实际存在的是 **`new_image.h`**（`new1_image.h` 不存在）——说明脚本是生成之后被改过文件名。跑之前先确认你期望的是哪个名字。
> - **数组名是 `gImage_new`**，不是固件兜底用的 `gImage_1`。**不能直接覆盖 `Ap_29demo.h`**，要么把数组名改成 `gImage_1`，要么改 `.ino` 里的引用。
> - 中文字体依次尝试 `simhei.ttf` → `msyh.ttc` → 默认字体。Linux/macOS 上两个都找不到，会退化成默认位图字体（中文变方块），需要自己指定字体路径。

### 6.3 `convert_image.py` —— 早期版本

```bash
python convert_image.py      # 硬编码读 4c.png → 写 4c_image.h
```

功能同上但没有侧边文字栏。**注意第 72 行有个 bug**：注释说输出 `4c_image.h`，`print` 却说 `Generated 4c.h`，实际文件名是 `4c_image.h`。

### 6.4 `analyze_image.py` —— 色彩统计

```bash
python analyze_image.py      # 读 4c.png，写 analyze_result.txt
```

统计图片量化后的主要颜色分布，用来确认 4 色转换是否符合预期。

### 6.5 `compare_files.py`

比对 `0615.h` 与 `0615a.h` 的行数、行长、逗号数、换行符类型（CRLF vs LF），排查「本地生成的图刷出来不对」这类问题。

---

## 7. 目录文件清单

| 文件 | 大小 | 说明 | 建议 |
|---|---|---|---|
| `GDEM075F52_Arduino.ino` | 13 KB | 主程序 | ✅ 保留 |
| `Display_EPD_W21.cpp/.h` | 7 KB | 屏幕驱动 | ✅ 保留 |
| `Display_EPD_W21_spi.cpp/.h` | 1 KB | SPI 底层 | ✅ 保留 |
| `Ap_29demo.h` | 492 KB | **当前在用的兜底图**。MD5 校验确认与根目录 `0615.h`、`aaa/0616.h` 三者完全相同（`b11c3ef4…`） | ✅ 保留 |
| `Ap_29demo_orginal.h` | 492 KB | 厂商原版 demo 图 | 🔸 可留作对照 |
| `0615.h` / `0615a.h` | 492 / 486 KB | 6 月 15 日、6 月 16 日的图 | 🔸 归档 |
| `4c.h` | 492 KB | 由 `4c.png` 转换而来 | 🔸 归档 |
| `new_image.h` | 492 KB | `convert_new.py` 的产物，数组名 `gImage_new` | 🔸 归档 |
| `Ap_29demo.h2` / `.h3` | 492 KB | 手动备份 | 🗑 可删 |
| `Ap_29demo.hbig` | 1.9 MB | 大体积试验文件 | 🗑 可删 |
| `4c.png` / `new.jpg` / `new1.png` / `new1_4color.png` / `new_4color.png` | — | 图源与中间产物 | 🔸 归档 |
| `convert_new.py` / `convert_image.py` / `analyze_image.py` / `compare_files.py` | — | 离线做图工具 | 🔸 保留 |
| `convert_log.txt` / `analyze_result.txt` | — | UTF-16 编码的运行日志 | 🗑 可删 |
| `aaa/` | — | `0615.h`（独立一张图）+ `0616.h`（与 `Ap_29demo.h` 相同）；**不会被编译** | 🔸 归档 |
| `._1.c`、`.AppleDouble/`、`._*.h` 等 | — | **macOS 拷贝残留**（AppleDouble 二进制，`._1.c` 是 4096 字节的二进制垃圾，**不是 C 源码**） | 🗑 可删 |

> 关于 `._1.c` 的安全性：已实测 arduino-cli（与 Arduino IDE 2.x 同一套构建器）**会跳过以点开头的文件**，所以当前不会导致编译失败。但 `._1.c` 会被复制到构建目录，且如果换成别的构建工具或手工 Makefile，它可能真被当成 C 文件编译。建议直接删掉所有 `._*` 与 `.AppleDouble/`。

> ⚠️ `Ap_29demo.h`、`Ap_29demo_orginal.h`、`0615.h`、`4c.h` 里**都**定义了同名数组 `gImage_1`。当前只有 `Ap_29demo.h` 被 `#include`，所以不冲突。**千万别同时 include 两个**，否则重复定义报错。

---

## 8. 配置速查

| 常量 | 位置 | 默认值 | 含义 |
|---|---|---|---|
| `ssid` / `password` | `.ino:13-14` | 作者手机热点 | WiFi 凭据 |
| `ntpServer` | `.ino:17` | `pool.ntp.org` | NTP 服务器，国内建议 `ntp.aliyun.com` |
| `gmtOffset_sec` | `.ino:18` | `8*3600` | 东八区 |
| `huawei_cloud_url` | `.ino:22` | OBS `/images/` | 图床前缀（http） |
| `file_extension` | `.ino:23` | `.h` | 文件后缀 |
| `fallback_month/day` | `.ino:26-27` | `6 / 16` | NTP 失败时的兜底日期 |
| `WAKE_HOUR/MINUTE` | `.ino:30-31` | `6 / 10` | 每日唤醒时刻 |
| `BUTTON_PIN` | `.ino:34` | `0` | 按键引脚（**当前无效**） |
| `Source_BITS` / `Gate_BITS` | `Display_EPD_W21.h:13-14` | `800 / 480` | 屏幕分辨率 |
| `ALLSCREEN_BYTES` | `Display_EPD_W21.h:15` | `96000` | 一屏字节数 = 800×480/4 |
| SPI 速率 | `.ino:70` | `10000000` | 名义 10 MHz（**实际未生效**，见 §10） |

---

## 9. 排障 FAQ

**Q1：编译报 `region 'flash' overflowed`**
Flash 已经用了 88%。把 `工具 → Partition Scheme` 改成 **`Huge APP (3MB No OTA/1MB SPIFFS)`**。

**Q2：串口监视器一片空白 / 全是乱码**
波特率必须是 **115200**（`.ino:43`）。乱码基本都是波特率不对。

**Q3：一直停在 `Waiting for connection.......` 然后 `❌ WiFi connection FAILED`**
- 确认 `ssid`/`password` 已改成你能用的 2.4 GHz 网络
- **ESP32 不支持 5 GHz**，也不支持企业级认证（WPA2-Enterprise）
- 失败不会中断流程，会继续用兜底图刷屏

**Q4：NTP 一直失败，显示 `⚠️ NTP sync failed, using fallback date`**
- 先确认 WiFi 真的连上了（有 IP 才算）
- 换 `ntp.aliyun.com` 或 `ntp.tencent.com`，`pool.ntp.org` 在国内常超时
- 确认防火墙没有拦 UDP 123

**Q5：`❌ File NOT FOUND on server!` 或 `❌ HTTP request FAILED`**
- 先在电脑浏览器打开 `http://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/images/1028.h`（换成今天的日期）确认文件在不在
- **注意：OBS 缺文件时返回 403，固件只认 404**，所以「文件不存在」会走到 `HTTP request FAILED` 这条分支（§5.4）
- 确认 `huawei_cloud_url` 结尾的斜杠 `/` 没漏

**Q6：`❌ Image buffer allocation FAILED!`**
`malloc(96000)` 失败。正常情况剩余堆有 278 KB，不该失败。若出现，检查是否开了 Bluetooth（`工具` 里关掉）、`Core Debug Level` 是否开到 Verbose（会额外吃内存）。

**Q7：`❌ Incomplete: parsed N bytes (expected 96000)`**
流式解析没读满，通常是网络中断。代码在 `data_index >= 95990` 时会容忍（少 10 字节以内照用），差得多才会报这个错。检查 WiFi 信号强度（日志里的 RSSI，低于 -75 dBm 就偏弱了）。可以加一行 `http.setTimeout(15000);` 拉长超时。

**Q8：程序卡死不动了，串口停在某一行**
大概率卡在 `lcd_chkstatus()`（第 171 行）——它是个 `while(1)` 死循环，只有 BUSY 引脚变高才退出。检查 BUSY 接线（GPIO13）。屏幕没接、没供电、SPI 线序错都会导致永久卡死。

**Q9：屏幕刷出来是纯白 / 纯黑 / 花屏**
- 先确认 SPI 线序：**SCK=18、MOSI=23**（头文件注释写反了）
- 确认 `.h` 文件确实是 96000 字节、按 §5.2 的规则打包
- 用 `Display_All_White()` / `Display_All_Black()` / `Display_All_Yellow()` / `Display_All_Red()` 做全屏测试，先排除硬件问题

**Q10：按了板上的 BOOT 键没有反应**
符合预期。BOOT 键接在 GPIO0，就是代码里的 `BUTTON_PIN`，但代码**从未配置 GPIO 唤醒，也从未读取按键**（`esp_sleep_enable_gpio_wakeup` 一次都没调用）。想手动刷新按 **EN/RST** 重启。

**Q11：想让它别睡，方便调试**
把 `scheduleNextWakeup()` 的调用（`.ino:105`）注释掉，设备就会停在 `loop()` 里（此时 `loop()` 为空，相当于空转）。

**Q12：为什么每天都刷同一张图？**
NTP 失败时会一直用 `fallback_month/day`（默认 6/16）。看日志里是 `Using date from NTP` 还是 `Using fallback date` 就能判断。

---

## 10. 已知问题清单

按严重程度排列，均已核实。

| # | 严重度 | 问题 | 位置 | 说明 |
|---|---|---|---|---|
| 1 | 🔴 高 | **SPI 速率设置被静默丢弃** | `.ino:70-71` | `SPI.beginTransaction(SPISettings(10000000,...))` 写在了 `SPI.begin()` **之前**。此时内部句柄 `_spi` 还是 `NULL`，`spiTransaction()` 开头 `if (!spi) return;` 直接返回，10 MHz 设置根本没生效；随后 `SPI.begin()` 用**默认的 1 MHz** 初始化总线。又因为 `_inTransaction` 被置为 `true` 且从未 `endTransaction()`，之后所有 `SPI.transfer()` 都走 `spiTransferByteNL`（无锁路径，不再重新配置时钟）。**结果：SPI 实际跑在 1 MHz。** 模式（MODE0/MSBFIRST）恰好与默认值一致，所以功能正常，只是 96000 字节的传输从约 0.1 秒变成约 1 秒。**修复：把第 71 行的 `SPI.begin();` 移到第 70 行之前。** |
| 2 | 🔴 高 | **`lcd_chkstatus()` 是无限循环** | `Display_EPD_W21.cpp:171-177` | `while(1) { if (isEPD_W21_BUSY == 1) break; }` 无超时、不喂看门狗。屏幕没接好就永久卡死，且不会触发硬件看门狗复位。建议加 `unsigned long t = millis(); while(millis() - t < 5000) { if (isEPD_W21_BUSY == 1) return; }` 并打印超时错误。 |
| 3 | 🟠 中 | **「文件不存在就试昨天」分支永不触发** | `.ino:216` | 条件是 `httpCode == HTTP_CODE_NOT_FOUND`，但华为云 OBS 匿名请求下缺对象返回 **403**（已实测，见 §5.4）。所以该分支进不去，只会打印 `❌ HTTP request FAILED`。**修复：把判断改成 `if ((httpCode == 404 \|\| httpCode == 403) && !time_ok)`。** |
| 4 | 🟠 中 | **按键是死代码** | `.ino:34-36, 74` | `BUTTON_PIN=0`、`BUTTON_DEBOUNCE=50`、`last_button_time` 各只出现一次（仅声明），`pinMode(BUTTON_PIN, INPUT_PULLUP)` 之后再无任何读取，`esp_sleep_enable_gpio_wakeup()` / `ext0` 从未调用。按键既不能唤醒也不能刷新。代码注释写着「只使用定时器，不使用 GPIO 唤醒避免误触发」，说明是有意为之，但相关变量留着容易误导。 |
| 5 | 🟠 中 | **SPI 引脚注释写反** | `Display_EPD_W21_spi.h:6-7` | 注释称 `SCK--GPIO23` / `SDIN--GPIO18`，实际 ESP32 默认是 **SCK=18 / MOSI=23**。按注释接线必然不通。 |
| 6 | 🟠 中 | **WiFi 密码硬编码且已入库** | `.ino:13-14` | 明文写死了 SSID 和密码。建议改成首次启动走 `WiFiManager` 配网，或至少放到不提交的 `secrets.h` 里。 |
| 7 | 🟠 中 | **RES 占用 strapping 引脚 GPIO12** | `Display_EPD_W21_spi.h:11` | `A15 = GPIO12 = MTDI`，上电时决定 Flash 工作电压。若屏幕模组 RES 端有外部上拉，ESP32 会无法启动。 |
| 8 | 🟡 低 | **HTTP 无超时设置** | `.ino:208-209` | 未调用 `http.setTimeout()`，使用默认 5 秒。下载 486 KB 文本在弱信号下容易失败。建议加 `http.setConnectTimeout(10000); http.setTimeout(20000);` |
| 9 | 🟡 低 | **`Acep_color()` 只声明未定义** | `Display_EPD_W21.h:31` | 头文件里声明了，`.cpp` 里没有实现。当前无人调用所以能编译过，一调用就是链接错误。 |
| 10 | 🟡 低 | **Flash 余量只剩 12%** | — | 实测占用 1,162,965 / 1,310,720 字节（88%）+ `Ap_29demo.h` 的 96 KB 图片。加功能（尤其 TLS）前先换 `Huge APP` 分区。 |
| 11 | 🟡 低 | **`.h` 文本传输 5 倍膨胀** | `.ino:206-293` | 96 KB 像素 → 约 486 KB 文本，还要逐字符状态机解析。建议服务端直接提供二进制，固件改用 `http.writeToStream()`。 |
| 12 | 🟡 低 | **Python 脚本输出文件名与打印不一致** | `convert_new.py:110/120`、`convert_image.py:72` | 打印 `Generated new_image.h` / `4c.h`，实际写盘 `new1_image.h` / `4c_image.h`。 |
| 13 | 🟡 低 | **`new_image.h` 数组名不兼容** | `new_image.h:1` | 定义的是 `gImage_new`，固件兜底用的是 `gImage_1`。直接覆盖 `Ap_29demo.h` 会报 `gImage_1 was not declared`。 |
| 14 | 🟡 低 | **macOS AppleDouble 残留** | 根目录 `._*`、`.AppleDouble/` | 已实测 arduino-cli 会跳过点文件，不影响编译，但 `._1.c` 是 4096 字节二进制垃圾，建议清理。 |
| 15 | 🟡 低 | **兜底图已被替换** | `Ap_29demo.h` | 内容与 `0615.h` 完全一致的生成图，不是厂商原版（原版另存为 `Ap_29demo_orginal.h`）。改兜底图时注意别改错文件。 |
| 16 | 🟡 低 | **日期回退逻辑简化过度** | `.ino:222` | `day--` 后若 `day < 1` 直接取 `day = 28`，不区分月份天数（2 月只有 28 天是巧合对上，其他月会跳过 29/30/31 日）。 |

---

## 11. 版本管理提示

目录下**没有 `.git` 仓库**，上传前建议先 `git init`，并至少忽略：

```
.AppleDouble/
._*
*.h2
*.h3
*.hbig
convert_log.txt
analyze_result.txt
```

> ⚠️ 有两类文件**建议不要提交**（当前无 `.gitignore` 保护）：
> - **WiFi 凭据**：`GDEM075F52_Arduino.ino` 第 13–14 行的明文 SSID / 密码
> - **个人照片**：`Ap_29demo.h` 及各 `.h` 里是真实家庭照片的像素数据，`new.jpg` / `new1*.png` / `4c.png` 是原图

---

## 12. 快速开始（一页版）

```bash
# 1. Arduino IDE 2.x → 首选项填入镜像源 → 开发板管理器装 esp32 (≥3.0)
#    镜像源：https://jihulab.com/esp-mirror/espressif/arduino-esp32/-/raw/gh-pages/package_esp32_index_cn.json

# 2. 改配置（必做）
#    GDEM075F52_Arduino.ino 第 13-14 行：改成你自己的 WiFi

# 3. 工具菜单
#    Board = ESP32 Dev Module
#    Partition Scheme = Default 4MB with spiffs（加功能则改 Huge APP）
#    Port = 你的 COM 口

# 4. 按接线表接线
#    BUSY→13  RES→12  DC→14  CS→27  SCK→18  MOSI→23  VCC→3.3V  GND→GND
#    （头文件里 SCK/MOSI 的注释是反的，别照抄）

# 5. 点 → 上传，然后开串口监视器 115200

# 6. 想换掉内置兜底图
pip install Pillow
python convert_new.py            # 读 new1.png，输出 new1_4color.png + new1_image.h
#    把 new1_image.h 里的 gImage_new 改名为 gImage_1，再覆盖 Ap_29demo.h
```
