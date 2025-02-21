#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

const int X_LEN = 48;
const int Y_LEN = 24;
const int DELAY = 1000; // 1 second
const int NUM_SELECT = 6;

const int ENABLE_X_PIN = 5;             
const int ENABLE_Y_PIN = 2;             
const int SELECT_PINS[NUM_SELECT] = {13, 12, 11, 10, 9, 7}; // S5/S2-2~13, S0/S0-1~7
const int OUTPUT_PIN = A0;

int touch_value = 0;  

void setup() {
  Serial.begin(115200);
  pinMode(OUTPUT_PIN, INPUT);

  for (int i = 0; i < NUM_SELECT; i++) {
    pinMode(SELECT_PINS[i], OUTPUT);
    digitalWrite(SELECT_PINS[i], LOW);
  }

  pinMode(ENABLE_X_PIN, OUTPUT);
  pinMode(ENABLE_Y_PIN, OUTPUT);
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, HIGH);
}

void setSelectSignal(int pin) {
  for (int i = 0; i < NUM_SELECT; i++) {
    if (pin & (1 << i)) {
      digitalWrite(SELECT_PINS[NUM_SELECT - 1 - i], HIGH);
    } else {
      digitalWrite(SELECT_PINS[NUM_SELECT - 1 - i], LOW);
    }
  }
}

void cycleX() {
  digitalWrite(ENABLE_X_PIN, LOW);
  digitalWrite(ENABLE_Y_PIN, HIGH);
  for (int i = 0; i < X_LEN; i++) {
    setSelectSignal(i); 
    touch_value = analogRead(OUTPUT_PIN); 
    Serial << "x = " << i + 1<< ": " << touch_value << endl; 
    delay(DELAY);
  }
}

void cycleY() {
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, LOW);
  for (int i = 0; i < Y_LEN; i++) {
    setSelectSignal(i); 
    touch_value = analogRead(OUTPUT_PIN); 
    Serial << "y = " << i + 1<< ": " << touch_value << endl; 
    delay(DELAY);
  }
}

void loop()
{
  cycleX();
  cycleY();
}