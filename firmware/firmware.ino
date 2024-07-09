#include <Streaming.h>

const uint16_t THRESHOLD = 25;
const uint16_t MAX_COUNTER = 1;
const uint16_t S0 = 8;

void setup() {
  Serial.begin(9600);

  pinMode(A0, INPUT); // TODO: change to digital 
  pinMode(S0, OUTPUT);
}

bool analog_to_digital(uint16_t input) {
  return input < THRESHOLD;
}

void loop() {

  // digitalWrite(S0, 0);

  static uint16_t counter = 0;
  static uint16_t bit_array = 0; 

  //Serial << counter << " " << analogRead(A0) << endl;

  digitalWrite(S0, counter & 1);
  //delay(1000);

  bool bit = analog_to_digital(analogRead(A0));
  bit_array = (bit_array << 1) | bit;

  if (counter == MAX_COUNTER) {
    Serial << bit_array << endl;
    bit_array = 0;
    counter = 0;
  } else {
    counter += 1;
  }

}
