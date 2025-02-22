#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

#define DEBUG
const int DELAY_DEBUG = 1000;

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

/* Frame Controls */
/****************************************************************************/
const int DELAY_TIME_MICRO = 180;
const int THRESHOLD_X = 90;
const int THRESHOLD_Y = 10;

// Output Pins
const int OUTPUT_X_PIN = A0;
const int OUTPUT_Y_PIN = 10; 

// Mux Selects
const int NUM_SELECT_PINS = 6;
const int SELECT_PINS[NUM_SELECT_PINS] = {5, 7, 9, 11, 12, 13}; // S2-2~5, S0-1~13

// Enable Signals (Active Low)
const int ENABLE_X_PIN = 23;             
const int ENABLE_Y_PIN = 24;  

bool is_x_axis_enabled;                 // true if x axis is enabled, false if y axis is enabled
bool bit_array[72] = {0};                      // bit array that denotes touch coordinates [X1][X2]...[X48][Y1]...[Y24]
bool touch_bit = 0;                     // digital output after read from currently active x/y photodiode
/****************************************************************************/

/* Grid constants */
/****************************************************************************/
const int X_LEN = 48;                   // total pairs on x axis
const int Y_LEN = 24;                   // total pairs on y axis
/****************************************************************************/

void setup()
{
  Serial.begin(115200);
  
  pinMode(OUTPUT_X_PIN, INPUT);
  pinMode(OUTPUT_Y_PIN, INPUT);
  
  for (int i = 0; i < NUM_SELECT_PINS; i++) {
    pinMode(SELECT_PINS[i], OUTPUT);
    digitalWrite(SELECT_PINS[i], LOW);
  }

  pinMode(ENABLE_X_PIN, OUTPUT);
  pinMode(ENABLE_Y_PIN, OUTPUT);
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, HIGH);

  // Set up bluetooth and advertise presence of frame
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
  cycleX();   
  cycleY();

  printBitArray(); 

  // If connection is active, send the count value over BLE
  if (connected) { 
    customChar.notify(connection_handle, bit_array, 72);  // Notify the connected central with the current count
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
  return is_x_axis_enabled ? analog_input < THRESHOLD_X : analog_input < THRESHOLD_Y;
}

/************************************************************
  Cycle through the x axis
************************************************************/
void cycleX()
{
  digitalWrite(ENABLE_X_PIN, LOW);
  digitalWrite(ENABLE_Y_PIN, HIGH);
  is_x_axis_enabled = true;

  for (int i = 0; i < X_LEN; i++) {
    setSelectSignal(i); 

    touch_bit = analog_to_digital(analogRead(OUTPUT_X_PIN));
    #ifdef DEBUG
      Serial << "x = " << i + 1 << ": " << analogRead(OUTPUT_X_PIN) << endl;
      delay(DELAY_DEBUG);
    #endif
    bit_array[i + Y_LEN] = touch_bit; 

    delayMicroseconds(DELAY_TIME_MICRO);
  }
}

/************************************************************
  Cycle through the y axis
************************************************************/
void cycleY()
{
  digitalWrite(ENABLE_X_PIN, HIGH);
  digitalWrite(ENABLE_Y_PIN, LOW);
  is_x_axis_enabled = false;

  for (int i = 0; i < Y_LEN; i++) {
    setSelectSignal(i); 

    touch_bit = analog_to_digital(analogRead(OUTPUT_Y_PIN));
    #ifdef DEBUG
      Serial << "y = " << i + 1 << ": " << analogRead(OUTPUT_Y_PIN) << endl;
      delay(DELAY_DEBUG);
    #endif
    bit_array[i] = touch_bit;

    delayMicroseconds(DELAY_TIME_MICRO);
  }
}

/************************************************************
  @param pin : denotes which pin to turn on 
  Sets the select signals to turn on pair on that pin
************************************************************/
void setSelectSignal(int pin) {
  for (int i = 0; i < NUM_SELECT_PINS; i++) {
    if (pin & (1 << i)) {
      digitalWrite(SELECT_PINS[NUM_SELECT_PINS - 1 - i], HIGH);
    } else {
      digitalWrite(SELECT_PINS[NUM_SELECT_PINS - 1 - i], LOW);
    }
  }
}

/************************************************************
  Print the bit array in binary representation
************************************************************/
void printBitArray()
{
  Serial << "bit_array: ";
  for (int i = 0; i < 72; i++)
  {
    Serial << bit_array[i];
  }
  Serial << endl;
}