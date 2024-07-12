#include <Streaming.h>

/////////////////////
// Pin Definitions //
/////////////////////
const int selectPins[2] = {2, 3}; // S0~2, S1~3, S2~4
const int zOutput = 5; // Connect common (Z) to 5 (PWM-capable)

const int LED_ON_TIME = 500; // Each LED is on 0.5s
const int DELAY_TIME = ((float)LED_ON_TIME/512.0)*1000;

const int THRESHOLD = 10;

bool analog_to_digital(uint16_t input) {
  return input < THRESHOLD;
}

void setup() 
{
  Serial.begin(9600);

  // Set up the select pins, as outputs
  for (int i=0; i<2; i++)
  {
    pinMode(selectPins[i], OUTPUT);
    digitalWrite(selectPins[i], LOW);
  }
  pinMode(zOutput, OUTPUT); // Set up Z as an output
}

void loop() 
{

   uint16_t bit_array = 0; 
   bool bit;

  // Cycle from pins Y0 to Y7 first
  for (int pin=0; pin<=3; pin++)
  {
    // Set the S0, S1, and S2 pins to select our active
    // output (Y0-Y7):
    selectMuxPin(pin);
    analogWrite(zOutput, 255);

    bit = analog_to_digital(analogRead(A0));
    // Serial << analogRead(A0) << endl;
    bit_array = (bit_array << 1) | bit; 

    analogWrite(zOutput, 0);
  }

  Serial << bit_array << endl;

}

// The selectMuxPin function sets the S0, S1, and S2 pins
// accordingly, given a pin from 0-7.
void selectMuxPin(byte pin)
{
  if (pin > 3) return; // Exit if pin is out of scope
  for (int i=0; i<2; i++)
  {
    if (pin & (1<<i))
      digitalWrite(selectPins[i], HIGH);
    else
      digitalWrite(selectPins[i], LOW);
  }
}
