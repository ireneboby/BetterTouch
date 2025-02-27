#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

const int X_LEN = 48;
const int Y_LEN = 24;
const int DELAY = 1000; // 1 second
const int NUM_SELECT_PINS = 6;

const int ENABLE_X_PIN = 23;             
const int ENABLE_Y_PIN = 24;             
const int SELECT_PINS[NUM_SELECT_PINS] = {5, 7, 9, 11, 12, 13}; // 5-9 L2 (Top Level Mux)
const int OUTPUT_X_PIN = A0;
const int OUTPUT_Y_PIN = 10; 

int touch_value = 0;  

void setup() {
  Serial.begin(115200);
  pinMode(OUTPUT_X_PIN, INPUT);
  pinMode(OUTPUT_Y_PIN, INPUT);

  for (int i = 0; i < NUM_SELECT_PINS; i++) {
    pinMode(SELECT_PINS[i], OUTPUT);
    digitalWrite(SELECT_PINS[i], LOW);
  }

  pinMode(ENABLE_X_PIN, OUTPUT);
  pinMode(ENABLE_Y_PIN, OUTPUT);
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, HIGH);
}

void setSelectSignal(int pin) {
  for (int i = 0; i < NUM_SELECT_PINS; i++) {
    if (pin & (1 << i)) {
      digitalWrite(SELECT_PINS[NUM_SELECT_PINS - 1 - i], HIGH);
    } else {
      digitalWrite(SELECT_PINS[NUM_SELECT_PINS - 1 - i], LOW);
    }
  }
}

void cycleX() {
  digitalWrite(ENABLE_X_PIN, LOW);
  digitalWrite(ENABLE_Y_PIN, HIGH);
  for (int i = 0; i < X_LEN; i++) {
    setSelectSignal(i); 
    touch_value = analogRead(OUTPUT_X_PIN); 
    Serial << "x = " << i + 1<< ": " << touch_value << endl; 
    delay(DELAY);
  }
}

void cycleY() {
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, LOW);
  for (int i = 0; i < Y_LEN; i++) {
    setSelectSignal(i); 
    touch_value = analogRead(OUTPUT_Y_PIN); 
    Serial << "y = " << i + 1<< ": " << touch_value << endl; 
    delay(DELAY);
  }
}

void loop()
{
  cycleX();
  cycleY();
}