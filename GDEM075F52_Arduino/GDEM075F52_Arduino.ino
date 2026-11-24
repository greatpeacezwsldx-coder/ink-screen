#include <SPI.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <time.h>
#include <esp_sleep.h>

//EPD
#include "Display_EPD_W21_spi.h"
#include "Display_EPD_W21.h"
#include "Ap_29demo.h"  

// WiFi配置
const char* ssid = "建霖的iPhone";
const char* password = "zjl11118";

// NTP配置
const char* ntpServer = "pool.ntp.org";
const long  gmtOffset_sec = 8 * 3600;  // UTC+8
const int   daylightOffset_sec = 0;

// 华为云配置
const char* huawei_cloud_url = "http://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/images/";
const char* file_extension = ".h";

// 备用日期（当NTP失败时使用）
const int fallback_month = 6;
const int fallback_day = 16;

// 唤醒时间配置
const int WAKE_HOUR = 6;    // 6点
const int WAKE_MINUTE = 10; // 10分

// 按钮配置
const int BUTTON_PIN = 0;
const int BUTTON_DEBOUNCE = 50;
unsigned long last_button_time = 0;

// 图片数据缓冲区
uint8_t* image_buffer = NULL;
bool download_success = false;

void setup() {
  Serial.begin(115200);
  delay(500);
  
  // 检测唤醒原因
  esp_sleep_wakeup_cause_t wakeup_reason = esp_sleep_get_wakeup_cause();
  Serial.println("========================================");
  Serial.print("Wakeup reason: ");
  switch(wakeup_reason) {
    case ESP_SLEEP_WAKEUP_TIMER:
      Serial.println("Timer wakeup (auto scheduled)");
      break;
    case ESP_SLEEP_WAKEUP_GPIO:
      Serial.println("GPIO wakeup (button pressed)");
      break;
    case ESP_SLEEP_WAKEUP_UNDEFINED:
    default:
      Serial.println("Power on / Reset");
      break;
  }
  Serial.println("========================================");
  
  // 初始化引脚
  Serial.println("Initializing GPIO pins...");
  pinMode(A14, INPUT);  //BUSY
  pinMode(A15, OUTPUT); //RES 
  pinMode(A16, OUTPUT); //DC   
  pinMode(A17, OUTPUT); //CS   
  SPI.beginTransaction(SPISettings(10000000, MSBFIRST, SPI_MODE0)); 
  SPI.begin();
  
  // 初始化按钮引脚（用于手动唤醒）
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  Serial.println("GPIO pins initialized");
  
  // 运行主流程
  runImageUpdate();
}

void runImageUpdate() {
  if(image_buffer != NULL) {
    free(image_buffer);
    image_buffer = NULL;
  }
  download_success = false;
  
  bool wifiOk = connectWiFi();
  
  if(wifiOk) {
    Serial.println("WiFi connected, proceeding to download...");
    downloadDailyImage();
  } else {
    Serial.println("WiFi NOT connected, skipping download");
  }
  
  displayImage();
  scheduleNextWakeup();
}

bool tryConnectWiFi(int maxAttempts, int retryDelayMs) {
  WiFi.mode(WIFI_STA);
  WiFi.begin(ssid, password);
  
  int attempts = 0;
  while(WiFi.status() != WL_CONNECTED && attempts < maxAttempts) {
    delay(500);
    Serial.print(".");
    attempts++;
  }
  
  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("");
    Serial.println("✅ WiFi connected!");
    Serial.print("   IP: ");
    Serial.print(WiFi.localIP());
    Serial.print("  RSSI: ");
    Serial.print(WiFi.RSSI());
    Serial.println(" dBm");
    return true;
  }
  return false;
}

bool connectWiFi() {
  Serial.println("========================================");
  Serial.println("Step 1: Connecting to WiFi...");
  Serial.print("SSID: ");
  Serial.println(ssid);
  
  if(WiFi.status() == WL_CONNECTED) {
    Serial.println("WiFi already connected, reusing");
    Serial.println("========================================");
    return true;
  }
  
  for(int round = 0; round < 3; round++) {
    Serial.printf("Round %d/3: ", round + 1);
    if(tryConnectWiFi(40, 500)) {
      Serial.println("========================================");
      return true;
    }
    Serial.printf(" FAILED, wait %d ms then retry...\n", 2000);
    delay(2000);
  }
  
  Serial.println("❌ WiFi connection FAILED after 3 rounds");
  Serial.println("========================================");
  return false;
}

bool ensureWiFiAlive() {
  if(WiFi.status() == WL_CONNECTED) return true;
  Serial.println("⚠️ WiFi lost, attempting reconnect...");
  WiFi.disconnect(true);
  delay(500);
  return tryConnectWiFi(30, 500);
}

int parseHexStream(WiFiClient* stream, uint8_t* outBuf, int maxBytes) {
  int data_index = 0;
  char hex_buf[3] = {0};
  int hex_pos = 0;
  bool in_hex = false;
  bool in_comment = false;
  unsigned long last_data_ms = millis();
  
  while(data_index < maxBytes) {
    if(millis() - last_data_ms > 5000) {
      Serial.println("   Stream timeout (5s no data)");
      break;
    }
    if(!stream->available()) {
      delay(5);
      continue;
    }
    last_data_ms = millis();
    char c = stream->read();
    
    if(c == '/' && stream->peek() == '*') {
      in_comment = true;
      stream->read();
      continue;
    }
    if(in_comment && c == '*' && stream->peek() == '/') {
      in_comment = false;
      stream->read();
      continue;
    }
    if(in_comment) continue;
    
    if(c == '0' && (stream->peek() == 'X' || stream->peek() == 'x')) {
      in_hex = true;
      hex_pos = 0;
      stream->read();
    } else if(in_hex && hex_pos < 2) {
      if((c >= '0' && c <= '9') || (c >= 'A' && c <= 'F') || (c >= 'a' && c <= 'f')) {
        hex_buf[hex_pos++] = c;
        if(hex_pos == 2) {
          uint8_t value = 0;
          for(int i=0; i<2; i++) {
            char ch = hex_buf[i];
            if(ch >= '0' && ch <= '9') value = (value << 4) | (ch - '0');
            else if(ch >= 'A' && ch <= 'F') value = (value << 4) | (ch - 'A' + 10);
            else value = (value << 4) | (ch - 'a' + 10);
          }
          outBuf[data_index++] = value;
          in_hex = false;
          if(data_index % 19200 == 0) {
            Serial.printf("   Parsed: %d%%\n", (data_index * 100) / maxBytes);
          }
        }
      } else {
        in_hex = false;
      }
    }
  }
  return data_index;
}

bool ntpSyncTime(int maxRetries) {
  Serial.println("Syncing NTP time...");
  for(int attempt = 0; attempt < maxRetries; attempt++) {
    if(attempt > 0) {
      Serial.printf("  NTP retry %d/%d...\n", attempt + 1, maxRetries);
      if(!ensureWiFiAlive()) {
        Serial.println("  WiFi down during NTP retry, giving up");
        return false;
      }
    }
    configTime(gmtOffset_sec, daylightOffset_sec, ntpServer);
    struct tm timeinfo;
    unsigned long startMs = millis();
    while(millis() - startMs < 3000) {
      if(getLocalTime(&timeinfo)) {
        Serial.print("  Time: ");
        Serial.println(&timeinfo, "%Y-%m-%d %H:%M:%S");
        return true;
      }
      delay(200);
    }
  }
  Serial.println("  NTP sync FAILED");
  return false;
}

void addDateCandidate(char* candidates[3], int* count, int offsetDays, struct tm* base) {
  time_t t = mktime(base);
  t += offsetDays * 86400;
  struct tm tmp;
  localtime_r(&t, &tmp);
  char* name = (char*)malloc(10);
  if(name) {
    sprintf(name, "%02d%02d%s", tmp.tm_mon + 1, tmp.tm_mday, file_extension);
    candidates[(*count)++] = name;
  }
}

void buildDateCandidates(char* candidates[3], int* count) {
  *count = 0;
  struct tm timeinfo;
  bool timeOk = getLocalTime(&timeinfo);
  
  if(timeOk) {
    addDateCandidate(candidates, count, 0, &timeinfo);
    addDateCandidate(candidates, count, -1, &timeinfo);
    addDateCandidate(candidates, count, -2, &timeinfo);
  } else {
    struct tm fallback = {};
    fallback.tm_year = 2026 - 1900;
    fallback.tm_mon = fallback_month - 1;
    fallback.tm_mday = fallback_day;
    fallback.tm_hour = 12;
    addDateCandidate(candidates, count, 0, &fallback);
    addDateCandidate(candidates, count, -1, &fallback);
    addDateCandidate(candidates, count, -2, &fallback);
  }
  
  Serial.printf("Date candidates: ");
  for(int i = 0; i < *count; i++) {
    Serial.print(candidates[i]);
    Serial.print(" ");
  }
  Serial.println();
}

bool downloadAndParseOneFile(const String& url) {
  Serial.printf("  HTTP GET %s\n", url.c_str());
  
  for(int attempt = 0; attempt < 3; attempt++) {
    if(attempt > 0) {
      delay(1000L * (1 << (attempt - 1)));
      if(!ensureWiFiAlive()) {
        Serial.println("  WiFi lost during retry, skipping");
        return false;
      }
      Serial.printf("  HTTP retry %d/3...\n", attempt + 1);
    }
    
    HTTPClient http;
    http.setTimeout(8000);
    http.begin(url);
    
    int httpCode = http.GET();
    
    if(httpCode == HTTP_CODE_OK) {
      int contentLen = http.getSize();
      Serial.printf("  HTTP 200, content length: %d\n", contentLen);
      
      WiFiClient* stream = http.getStreamPtr();
      if(!stream || !stream->connected()) {
        Serial.println("  Stream not available");
        http.end();
        continue;
      }
      
      if(image_buffer == NULL) {
        image_buffer = (uint8_t*)malloc(96000);
      }
      if(image_buffer == NULL) {
        Serial.println("  malloc FAILED!");
        http.end();
        return false;
      }
      
      Serial.println("  Parsing hex stream...");
      int parsed = parseHexStream(stream, image_buffer, 96000);
      http.end();
      
      if(parsed >= 95990) {
        Serial.printf("  ✅ Parsed %d bytes\n", parsed);
        return true;
      } else {
        Serial.printf("  ❌ Only parsed %d/96000 bytes\n", parsed);
        free(image_buffer);
        image_buffer = NULL;
      }
    } else if(httpCode == HTTP_CODE_NOT_FOUND) {
      Serial.println("  404 Not Found");
      http.end();
      return false;
    } else {
      Serial.printf("  HTTP error %d: %s\n", httpCode, http.errorToString(httpCode).c_str());
      http.end();
    }
  }
  return false;
}

void downloadDailyImage() {
  Serial.println("========================================");
  Serial.println("Step 2: Downloading image from cloud...");
  
  bool timeOk = ntpSyncTime(3);
  
  if(!timeOk) {
    Serial.println("⚠️ NTP failed, using fallback date candidates");
  }
  
  char* dateCandidates[3];
  int candidateCount = 0;
  buildDateCandidates(dateCandidates, &candidateCount);
  
  for(int i = 0; i < candidateCount; i++) {
    String url = String(huawei_cloud_url) + dateCandidates[i];
    Serial.printf("Trying candidate %d/%d: %s\n", i + 1, candidateCount, dateCandidates[i]);
    
    if(downloadAndParseOneFile(url)) {
      download_success = true;
      break;
    }
    
    free(dateCandidates[i]);
    dateCandidates[i] = NULL;
  }
  
  if(!download_success) {
    Serial.println("❌ All download attempts failed");
  }
  Serial.println("========================================");
}

void displayImage() {
  Serial.println("========================================");
  Serial.println("Step 3: Displaying image on EPD...");
  
  if(download_success && image_buffer != NULL) {
    Serial.println("✅ Using downloaded image from cloud");
    EPD_init();
    PIC_display((const unsigned char*)image_buffer);
    EPD_sleep();
    free(image_buffer);
    image_buffer = NULL;
    Serial.println("✅ Display complete!");
  } else {
    Serial.println("⚠️ Using DEFAULT image (Ap_29demo.h)");
    EPD_init();
    PIC_display(gImage_1);
    EPD_sleep();
    Serial.println("✅ Display complete!");
  }
  Serial.println("========================================");
}

void scheduleNextWakeup() {
  Serial.println("========================================");
  Serial.println("Step 4: Scheduling next wakeup...");
  
  // 获取当前时间
  struct tm timeinfo;
  if(!getLocalTime(&timeinfo)) {
    Serial.println("⚠️ Cannot get current time, using 12 hours sleep");
    esp_sleep_enable_timer_wakeup(12LL * 60 * 60 * 1000000);
    Serial.println("Sleeping for 12 hours...");
    WiFi.disconnect(true);
    WiFi.mode(WIFI_OFF);
    esp_deep_sleep_start();
    return;
  }
  
  // 计算当前时间（秒）
  time_t now = mktime(&timeinfo);
  Serial.print("Current time: ");
  Serial.println(ctime(&now));
  
  // 计算目标唤醒时间（明天6:10）
  struct tm wakeup_time = timeinfo;
  wakeup_time.tm_hour = WAKE_HOUR;
  wakeup_time.tm_min = WAKE_MINUTE;
  wakeup_time.tm_sec = 0;
  
  // 如果当前时间已经超过6:10，就设定为明天的6:10
  if(mktime(&wakeup_time) <= now) {
    wakeup_time.tm_mday += 1;
  }
  
  time_t wakeup_timestamp = mktime(&wakeup_time);
  Serial.print("Next wakeup time: ");
  Serial.println(ctime(&wakeup_timestamp));
  
  // 计算睡眠时长（微秒）
  long long sleep_duration_us = (wakeup_timestamp - now) * 1000000LL;
  Serial.printf("Sleep duration: %.2f hours\n", sleep_duration_us / 1000000.0 / 3600.0);
  
  // 设置定时器唤醒（只使用定时器，不使用GPIO唤醒避免误触发）
  esp_sleep_enable_timer_wakeup(sleep_duration_us);
  
  // 关闭WiFi以节省电力
  WiFi.disconnect(true);
  WiFi.mode(WIFI_OFF);
  
  // 进入深度睡眠
  Serial.println("Entering deep sleep...");
  Serial.flush();
  esp_deep_sleep_start();
}

void loop() {
  // loop()不会执行，因为程序会进入深度睡眠
}