// rising vs falling: two floats in [0,1] over serial -> int8 TFLite -> label + logits

#include <Arduino.h>
#include <cstdio>
#include <math.h>

// Arduino.h defines DEFAULT; tflite headers use the name elsewhere
#ifdef DEFAULT
#undef DEFAULT
#endif

#include "rising_falling_model.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_log.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/system_setup.h"
#include "tensorflow/lite/schema/schema_generated.h"

namespace {

constexpr int kTensorArenaBytes = 8 * 1024;
alignas(16) uint8_t g_tensor_arena[kTensorArenaBytes];

const tflite::Model* g_model = nullptr;
tflite::MicroInterpreter* g_interpreter = nullptr;
TfLiteTensor* g_input = nullptr;
TfLiteTensor* g_output = nullptr;

String g_line;
constexpr size_t kLineCap = 96;

int8_t quantize01(float x, float scale, int32_t zero_point) {
  if (x < 0.0f) x = 0.0f;
  if (x > 1.0f) x = 1.0f;
  int32_t q = (int32_t)lroundf(x / scale) + zero_point;
  if (q < -128) q = -128;
  if (q > 127) q = 127;
  return static_cast<int8_t>(q);
}

bool initTfLite() {
  tflite::InitializeTarget();

  g_model = tflite::GetModel(g_rising_falling_model);
  if (g_model->version() != TFLITE_SCHEMA_VERSION) {
    MicroPrintf("model schema %d != supported %d", g_model->version(), TFLITE_SCHEMA_VERSION);
    return false;
  }

  // this graph is keras-exported fully_connected only (relu fused into weights path)
  static tflite::MicroMutableOpResolver<4> resolver;
  if (resolver.AddFullyConnected() != kTfLiteOk) {
    MicroPrintf("AddFullyConnected failed");
    return false;
  }

  static tflite::MicroInterpreter static_interpreter(
      g_model, resolver, g_tensor_arena, kTensorArenaBytes);
  g_interpreter = &static_interpreter;

  if (g_interpreter->AllocateTensors() != kTfLiteOk) {
    MicroPrintf("AllocateTensors failed (try increasing kTensorArenaBytes)");
    return false;
  }

  g_input = g_interpreter->input(0);
  g_output = g_interpreter->output(0);

  if (g_input->type != kTfLiteInt8 || g_output->type != kTfLiteInt8) {
    MicroPrintf("expected int8 io");
    return false;
  }
  if (g_input->dims->size != 2 || g_input->dims->data[0] != 1 || g_input->dims->data[1] != 2) {
    MicroPrintf("bad input shape");
    return false;
  }
  if (g_output->dims->size != 2 || g_output->dims->data[0] != 1 || g_output->dims->data[1] != 2) {
    MicroPrintf("bad output shape");
    return false;
  }

  return true;
}

bool parseTwoFloats(const String& s, float* a, float* b) {
  // accept "0.1 0.2" or "0.1,0.2" or mixed whitespace
  String t = s;
  t.trim();
  if (t.length() == 0) return false;
  t.replace(',', ' ');
  float x = 0.0f, y = 0.0f;
  int n = sscanf(t.c_str(), "%f %f", &x, &y);
  if (n != 2) return false;
  *a = x;
  *b = y;
  return true;
}

void runInference(float first, float second) {
  int8_t q0 = quantize01(first, g_input->params.scale, g_input->params.zero_point);
  int8_t q1 = quantize01(second, g_input->params.scale, g_input->params.zero_point);
  g_input->data.int8[0] = q0;
  g_input->data.int8[1] = q1;

  if (g_interpreter->Invoke() != kTfLiteOk) {
    Serial.println("invoke failed");
    return;
  }

  int8_t o0 = g_output->data.int8[0];
  int8_t o1 = g_output->data.int8[1];
  float z0 = g_output->params.zero_point;
  float s = g_output->params.scale;
  float logit0 = (static_cast<float>(o0) - z0) * s;
  float logit1 = (static_cast<float>(o1) - z0) * s;
  int pred = (logit1 > logit0) ? 1 : 0;

  Serial.print("pred=");
  Serial.print(pred == 1 ? "rising" : "falling");
  Serial.print(" logits_falling=");
  Serial.print(logit0, 4);
  Serial.print(" logits_rising=");
  Serial.println(logit1, 4);
}

}  // namespace

void setup() {
  Serial.begin(115200);
  delay(500);
  Serial.println();
  Serial.println("embedded rising/falling — send: <first> <second> in [0,1]");

  if (!initTfLite()) {
    Serial.println("tflite init failed — see MicroPrintf on debug uart if enabled");
    while (true) delay(1000);
  }
  Serial.println("ready.");
}

void loop() {
  while (Serial.available() > 0) {
    char c = static_cast<char>(Serial.read());
    if (c == '\n' || c == '\r') {
      if (g_line.length() > 0) {
        float a = 0.0f, b = 0.0f;
        if (parseTwoFloats(g_line, &a, &b)) {
          runInference(a, b);
        } else {
          Serial.println("parse error — need two floats, e.g. 0.2 0.7");
        }
        g_line = "";
      }
      continue;
    }
    if (g_line.length() < kLineCap) g_line += c;
  }
}
