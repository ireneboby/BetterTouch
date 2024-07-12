#include <Streaming.h>

const uint16_t THRESHOLD = 25;
const uint16_t MAX_COUNTER = 4;

// set select pins
const uint16_t S0 = 8;
const uint16_t S1 = 7;
const uint16_t Z_OUTPUT = 6;

bool analog_to_digital(uint16_t input) {
  return input < THRESHOLD;
}

void setup() {
  Serial.begin(9600);

  pinMode(A0, INPUT); // TODO: change to digital 
  pinMode(S0, OUTPUT);
  pinMode(S1, OUTPUT);
  pinMode(Z_OUTPUT, OUTPUT);
}

void loop() {

  analogWrite(Z_OUTPUT, 255);

  static uint16_t counter = 0;
  static uint16_t bit_array = 0; 

  digitalWrite(S0, counter & 1);
  digitalWrite(S1, (counter & 2) >> 1); 
  //delay(1000);

  bool bit = analog_to_digital(analogRead(A0));
  Serial << counter << " " << analogRead(A0) << endl;
  bit_array = (bit_array << 1) | bit;
  counter += 1;

  if (counter == MAX_COUNTER) {
    //Serial << bit_array << endl;
    counter = 0;
    bit_array = 0;
  }

}
