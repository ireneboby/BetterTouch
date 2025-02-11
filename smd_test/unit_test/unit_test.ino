#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

int touch_value = 0;  

// Enable Signals (Active Low) and Mux Selects
const int enable_x_low = 7;             // E~7, G2A~7
const int enable_y_low = 9;             // E~9, G2A~9
const int select_sig[6] = {16, 15, 14, 13, 12, 11}; // S0~11, S1~12, S2~13, S3~14, S4~15, S5~16

// Grid Constants
const int x_len = 48;               // total pairs on x axis
const int y_len = 24;               // total pairs on y axis

// Hard-Coded Variables (for now)
const int ENABLE_X = 0; 
const int SIG = 0;
const int SIGS[6] = {0, 0, 0, 0, 0, 0};

void setup() {
  Serial.begin(115200);
  pinMode(A0, INPUT);

  for (int i=0; i<6; i++)
  {
    pinMode(select_sig[i], OUTPUT);
    digitalWrite(select_sig[i], LOW);
  }

  pinMode(enable_x_low, OUTPUT);
  pinMode(enable_y_low, OUTPUT);
  if (ENABLE_X) {
    digitalWrite(enable_x_low, LOW);
    digitalWrite(enable_y_low, HIGH);
  } else {
    digitalWrite(enable_x_low, HIGH);
    digitalWrite(enable_y_low, LOW);
  }
}

void loop()
{
  for (int i = 0; i < 6; i++) {
    assert(SIGS[i] == (SIG & (1 << i)));
    if (SIG & (1 << i)) {
      digitalWrite(select_sig[i], HIGH);
    } else {
      digitalWrite(select_sig[i], LOW);
    }
  }
  touch_value = analogRead(A0); 
  Serial << "Pair " << SIG << ": " << touch_value << endl; 

  delay(5000); // 5 seconds
}