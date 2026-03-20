#include <Arduino.h>
#include "esp_camera.h"

// pinout matches espressif arduino CAMERA_MODEL_ESP32S3_EYE (camera_pins.h)

#define PWDN_GPIO_NUM -1
#define RESET_GPIO_NUM -1
#define XCLK_GPIO_NUM 15
#define SIOD_GPIO_NUM 4
#define SIOC_GPIO_NUM 5

#define Y2_GPIO_NUM 11
#define Y3_GPIO_NUM 9
#define Y4_GPIO_NUM 8
#define Y5_GPIO_NUM 10
#define Y6_GPIO_NUM 12
#define Y7_GPIO_NUM 18
#define Y8_GPIO_NUM 17
#define Y9_GPIO_NUM 16

#define VSYNC_GPIO_NUM 6
#define HREF_GPIO_NUM 7
#define PCLK_GPIO_NUM 13

static bool camera_ok = false;

static bool init_camera() {
  camera_config_t config = {};
  config.ledc_channel = LEDC_CHANNEL_0;
  config.ledc_timer = LEDC_TIMER_0;
  config.pin_d0 = Y2_GPIO_NUM;
  config.pin_d1 = Y3_GPIO_NUM;
  config.pin_d2 = Y4_GPIO_NUM;
  config.pin_d3 = Y5_GPIO_NUM;
  config.pin_d4 = Y6_GPIO_NUM;
  config.pin_d5 = Y7_GPIO_NUM;
  config.pin_d6 = Y8_GPIO_NUM;
  config.pin_d7 = Y9_GPIO_NUM;
  config.pin_xclk = XCLK_GPIO_NUM;
  config.pin_pclk = PCLK_GPIO_NUM;
  config.pin_vsync = VSYNC_GPIO_NUM;
  config.pin_href = HREF_GPIO_NUM;
  config.pin_sccb_sda = SIOD_GPIO_NUM;
  config.pin_sccb_scl = SIOC_GPIO_NUM;
  config.pin_pwdn = PWDN_GPIO_NUM;
  config.pin_reset = RESET_GPIO_NUM;
  config.xclk_freq_hz = 20000000;
  config.pixel_format = PIXFORMAT_JPEG;
  config.frame_size = FRAMESIZE_QVGA;
  config.jpeg_quality = 14;
  config.fb_count = 2;
  config.grab_mode = CAMERA_GRAB_LATEST;
  config.fb_location = CAMERA_FB_IN_PSRAM;

  esp_err_t err = esp_camera_init(&config);
  return err == ESP_OK;
}

// stream jpeg as decimal integers so the host can log and parse
static void send_jpeg_over_serial(camera_fb_t *fb) {
  if (!fb || !fb->buf || fb->len == 0) {
    Serial.println("ERR no_frame");
    return;
  }

  Serial.printf(
      "IMG_BEGIN JPEG %u %u %u\n",
      (unsigned)fb->len,
      (unsigned)fb->width,
      (unsigned)fb->height);

  const size_t chunk = 24;
  for (size_t i = 0; i < fb->len; i++) {
    Serial.printf("%u", (unsigned)fb->buf[i]);
    if (i + 1 < fb->len) {
      Serial.print(',');
    }
    if ((i + 1) % chunk == 0) {
      Serial.print('\n');
      if (((i + 1) & 0x3FF) == 0) {
        Serial.flush();
        delay(2);
      }
    }
  }
  if ((fb->len % chunk) != 0) {
    Serial.print('\n');
  }
  Serial.println("IMG_END");
  Serial.flush();
}

void setup() {
  Serial.begin(115200);
  delay(1500);

  Serial.println();
  Serial.println("image_capture — esp32-s3-eye");
  Serial.println("commands: c = capture+send jpeg, h = help");

  camera_ok = init_camera();
  if (!camera_ok) {
    Serial.println("ERR camera_init_failed");
    return;
  }
  Serial.println("OK camera_ready (QVGA JPEG). send 'c' to capture.");
}

void loop() {
  if (!camera_ok) {
    delay(1000);
    return;
  }

  while (Serial.available()) {
    char cmd = (char)Serial.read();
    if (cmd == '\r' || cmd == '\n' || cmd == ' ' || cmd == '\t') {
      continue;
    }
    if (cmd == 'h' || cmd == 'H' || cmd == '?') {
      Serial.println("c = capture one frame and stream as decimal bytes");
      continue;
    }
    if (cmd != 'c' && cmd != 'C') {
      continue;
    }

    camera_fb_t *fb = esp_camera_fb_get();
    if (!fb) {
      Serial.println("ERR capture_failed");
      continue;
    }

    send_jpeg_over_serial(fb);
    esp_camera_fb_return(fb);
  }
}
