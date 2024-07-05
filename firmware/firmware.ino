#include <Streaming.h>

uint16_t THRESHOLD = 100;
bool digital0;
bool digital1;
uint16_t val; 

void setup() {
  Serial.begin(9600);
  pinMode(A0,INPUT);
  pinMode(A1,INPUT);
}

bool analog_to_digital(uint16_t input) {
  return input < THRESHOLD;
}

void loop() {

  // Serial.println(analogRead(A0));

  digital0 = analog_to_digital(analogRead(A0));
  digital1 = analog_to_digital(analogRead(A1));
  val = (digital0 << 1) | digital1;

  Serial << val << endl;

}