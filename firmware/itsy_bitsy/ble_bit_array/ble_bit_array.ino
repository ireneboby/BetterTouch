#include <ArduinoBLE.h>
#include <Streaming.h>

// #define DEBUG

/********************** Parameters ***********************/

const int LED_ON_TIME = 500; // Each LED is on 0.5s
const int DELAY_TIME = ((float)LED_ON_TIME/512.0)*1000;
const int THRESHOLD = 10;

/* Input Pin Definitions
    A0 ~ mux output from x axis
    A1 ~ mux output from y axis */

// Output Pin Definitions - ITSY 
const int selectPins[3] = {11, 12, 13};  // S0~11, S1~12, S2~13, A~11, B~12, C~13
const int enable_x_low = 9;           // E~9, G2A~10
const int enable_y_low = 10;           // E~9, G2A~10

// const int zOutput = 5; // Connect common (Z) to 5 (PWM-capable) // FOR USING MUX/DEMUX AS DECODER ONLY

/**********************************************************/

bool is_x_axis_enabled = true;    // 0 if x axis is enabled, 1 if y axis is enabled
uint16_t bit_array = 0;           // 16 bit array that denotes touch coordinates
bool bit = 0;                     // digital output after read from currently active x/y photodiode

/************************************************************
  @param analog_input : input from mux for that pair 
  Return 1 if touch is detected on that pair based on mux input
************************************************************/
bool analog_to_digital(uint16_t analog_input) {
  return analog_input < THRESHOLD;
}

/************************************************************
  Set up select signals and enables as outputs 
  Set select signals to low
  Disable all enables by setting to high
************************************************************/
void setup() 
{
  Serial.begin(9600);
  for (int i=0; i<3; i++)
  {
    pinMode(selectPins[i], OUTPUT);
    digitalWrite(selectPins[i], LOW);
  }
  pinMode(enable_x_low, OUTPUT);
  pinMode(enable_y_low, OUTPUT);
  digitalWrite(enable_x_low, HIGH);
  digitalWrite(enable_y_low, HIGH);

  // pinMode(zOutput, OUTPUT); // Set up Z as an output

  if (!BLE.begin()) {
    Serial.println("starting BLE failed!");
    while (1);
  }

  BLE.setLocalName("ItsyBitsy");
  BLE.setAdvertisedService(bitArrayService);
  bitArrayService.addCharacteristic(bitArrayChar);
  BLE.addService(bitArrayService);
  bitArrayChar.writeValue(bit_array);

  BLE.advertise();
  Serial.println("Bluetooth device active, waiting for connections...");
}

/************************************************************
  Cycle through x axis first and then y axis 
  Then serial output bit array from that complete cycle
************************************************************/
void loop() 
{
   enable_x_axis();
   cycleAxis();

   enable_y_axis();    
   cycleAxis();

   #ifdef DEBUG
    printBitArray(); 
   #endif

   Serial << bit_array <<endl;
   bitArrayChar.writeValue((uint8_t*)&bit_array, sizeof(bit_array));
   delay(500);
}

/* Function to enable x axis, disable y axis */
void enable_x_axis()
{
  digitalWrite(enable_x_low, LOW);
  digitalWrite(enable_y_low, HIGH);
  is_x_axis_enabled = true;
}

/* Function to enable y axis, disable x axis */
void enable_y_axis()
{
  digitalWrite(enable_x_low, HIGH);
  digitalWrite(enable_y_low, LOW);
  is_x_axis_enabled = false;
}

/************************************************************
  Cycle through pins 0-7 on that axis
************************************************************/
void cycleAxis()
{
  for (int pin=0; pin<8; pin++)
  {
    setSelectSignals(pin);   
    // analogWrite(zOutput, 255);
    bit = is_x_axis_enabled ? analog_to_digital(analogRead(A0)) : analog_to_digital(analogRead(A1));
    
    #ifdef DEBUG
      if (is_x_axis_enabled) Serial << analogRead(A0) << endl;
      else Serial << analogRead(A1) << endl;
    #endif

    bit_array = (bit_array << 1) | bit;

    #ifdef DEBUG
      delay(500);
    #endif
    // analogWrite(zOutput, 0);
  }
}

/************************************************************
  @param pin : 0-7 denotes which pin to turn on 
  Sets the select signals to turn on pair on that pin
************************************************************/
void setSelectSignals(byte pin)
{
  if (pin > 7) return; // Exit if pin is out of scope
  for (int i=0; i<3; i++)
  {
    if (pin & (1<<i))
      digitalWrite(selectPins[i], HIGH);
    else
      digitalWrite(selectPins[i], LOW);
  }
}

/************************************************************
  Print the bit array in binary representation
************************************************************/
void printBitArray()
{
  Serial << "bit_array: ";
  for (int i = 15; i >= 0; i--)
  {
    Serial << ((bit_array >> i) & 1);
  }
  Serial << endl;
}