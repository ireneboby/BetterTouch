#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

const int ENABLE_X_PIN = 5;             
const int ENABLE_Y_PIN = 2;             
const int SELECT_PINS[6] = {13, 12, 11, 10, 9, 7}; // S5/S2-2~13, S0/S0-1~7
const int OUTPUT_PIN = A0;

int testing_x = false; 
int touch_value = 0;  

void setup() {
  Serial.begin(115200);
  pinMode(OUTPUT_PIN, INPUT);

  for (int i=0; i<6; i++) {
    pinMode(SELECT_PINS[i], OUTPUT);
    digitalWrite(SELECT_PINS[i], LOW);
  }

  pinMode(ENABLE_X_PIN, OUTPUT);
  pinMode(ENABLE_Y_PIN, OUTPUT);
  if (testing_x) {
    digitalWrite(ENABLE_X_PIN, LOW);
    digitalWrite(ENABLE_Y_PIN, HIGH);
  } else {
    digitalWrite(ENABLE_X_PIN, HIGH);
    digitalWrite(ENABLE_Y_PIN, LOW);
  }
}

void loop()
{

  // digitalWrite(7, HIGH);   // S0-1
  // digitalWrite(9, HIGH);   // S1-1
  // digitalWrite(10, HIGH);  // S2-1
  // digitalWrite(11, HIGH);  // S0-2
  // digitalWrite(12, LOW);  // S1-2
  // digitalWrite(13, LOW);  // S2-2

  for (int j = 0; j < 48; j++) {

    // sets select signals 
    for (int i = 0; i < 6; i++) {
      if (j & (1 << i)) {
        digitalWrite(SELECT_PINS[5-i], HIGH);
      } else {
        digitalWrite(SELECT_PINS[5-i], LOW);
      }
    }

    touch_value = analogRead(OUTPUT_PIN); 
    Serial << "Pair" << j + 1<< ": " << touch_value << endl; 
    delay(1000);
  }
}