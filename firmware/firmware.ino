#include <Streaming.h>

const uint16_t THRESHOLD = 100;
const int S0 = 8; // Connected to pin 8
const int S1 = 9; // Connected to pin 9

void setup() {
  Serial.begin(9600);

  pinMode(A0, INPUT);
  pinMode(S0, OUTPUT);
  pinMode(S1, OUTPUT);
}

bool analog_to_digital(uint16_t input) {
  return input < THRESHOLD;
}

void loop() {

  static int counter = 0;
  static uint16_t bit_array = 0; 

  if (counter == 0) {
    Serial << bit_array << endl;
    bit_array = 0;
  }

  // Calculate the select line states based on the counter
  digitalWrite(S0, counter & 1 ? HIGH : LOW);
  digitalWrite(S1, counter & 2 ? HIGH : LOW);

  bool bit = analog_to_digital(analogRead(A0));
  bit_array = (bit_array << 1) | bit;
  
  counter = (counter + 1) % 4

}
