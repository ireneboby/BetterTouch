#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

//#define DEBUG

/* BLE */
/****************************************************************************/
BLEDfu  bledfu;  // OTA DFU service
BLEDis  bledis;  // device information
BLEUart bleuart; // uart over ble
BLEBas  blebas;  // battery

#define CUSTOM_SERVICE_UUID     0x1234  // service UUID
#define CUSTOM_CHAR_UUID        0x5678  // characteristic UUID

BLEService customService(CUSTOM_SERVICE_UUID);
BLECharacteristic customChar(CUSTOM_CHAR_UUID, BLERead | BLENotify);

bool connected = false;  // Flag to track if there is an active connection
uint16_t connection_handle = 0;  // variable to store the connection handle
/****************************************************************************/

/* Frame */
/****************************************************************************/
const int LED_ON_TIME = 500; // Each LED is on 0.5s
const int DELAY_TIME = ((float)LED_ON_TIME/512.0)*1000;
const int THRESHOLD = 10;
/*  A0 ~ mux output from x axis
    10 ~ mux output from y axis */
const int selectPins[3] = {11, 12, 13}; // S0~11, S1~12, S2~13, A~11, B~12, C~13
const int enable_x_low = 7;             // E~7, G2A~7
const int enable_y_low = 9;             // E~9, G2A~9
bool is_x_axis_enabled = true;          // 0 if x axis is enabled, 1 if y axis is enabled
uint16_t bit_array = 0;                 // 16 bit array that denotes touch coordinates
bool bit = 0;                           // digital output after read from currently active x/y photodiode
/****************************************************************************/

void setup()
{
  Serial.begin(115200);
  
  for (int i=0; i<3; i++)
  {
    pinMode(selectPins[i], OUTPUT);
    digitalWrite(selectPins[i], LOW);
  }
  pinMode(enable_x_low, OUTPUT);
  pinMode(enable_y_low, OUTPUT);
  digitalWrite(enable_x_low, HIGH);
  digitalWrite(enable_y_low, HIGH);

  bleSetup();
  startAdv();
}

void bleSetup() 
{
  Bluefruit.autoConnLed(true);
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);
  Bluefruit.begin();
  Bluefruit.setTxPower(4);    // Check bluefruit.h for supported values
  //Bluefruit.setName(getMcuUniqueID()); // useful testing with multiple central connections
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);
  bledfu.begin();
  bledis.setManufacturer("Adafruit Industries");
  bledis.setModel("Bluefruit ItsyBitsy");
  bledis.begin();

  bleuart.begin();
  blebas.begin();
  blebas.write(100);
  customService.begin();
  customChar.begin();
}

void startAdv(void)
{
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();
  Bluefruit.Advertising.addService(bleuart);
  Bluefruit.Advertising.addService(customService);
  Bluefruit.ScanResponse.addName();
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds  
}

void loop()
{
  enable_x_axis();
  cycleAxis();
  enable_y_axis();    
  cycleAxis();

  Serial << bit_array <<endl;

  #ifdef DEBUG
    printBitArray(); 
   #endif

  // If connection is active, send the count value over BLE
  if (connected) { 
    customChar.notify16(connection_handle, bit_array);  // Notify the connected central with the current count
  }
}

// callback invoked when central connects
void connect_callback(uint16_t conn_handle)
{
  connection_handle = conn_handle;
  BLEConnection* connection = Bluefruit.Connection(conn_handle);
  char central_name[32] = { 0 };
  connection->getPeerName(central_name, sizeof(central_name));
  Serial.print("Connected to ");
  Serial.println(central_name);
  connected = true;
}

/**
 * Callback invoked when a connection is dropped
 * @param conn_handle connection where this event happens
 * @param reason is a BLE_HCI_STATUS_CODE which can be found in ble_hci.h
 */
void disconnect_callback(uint16_t conn_handle, uint8_t reason)
{
  (void) conn_handle;
  (void) reason;
  Serial.println();
  Serial.print("Disconnected, reason = 0x"); Serial.println(reason, HEX);
  connected = false;  // Stop counting when disconnected
}

/************************************************************
  @param analog_input : input from mux for that pair 
  Return 1 if touch is detected on that pair based on mux input
************************************************************/
bool analog_to_digital(uint16_t analog_input) {
  return analog_input < THRESHOLD;
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
    bit = is_x_axis_enabled ? analog_to_digital(analogRead(A0)) : analog_to_digital(analogRead(10));
    
    #ifdef DEBUG
      if (is_x_axis_enabled) Serial << analogRead(A0) << endl;
      else Serial << analogRead(10) << endl;
    #endif

    bit_array = (bit_array << 1) | bit;

    #ifdef DEBUG
      delay(300);
    #endif
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
