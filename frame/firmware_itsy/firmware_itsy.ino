#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

//#define DEBUG
const int DELAY_DEBUG = 1000;

//#define DATA_COLLECTION_MODE
const int DATA_MODE_DELAY = 5000;

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

/* Grid constants */
/****************************************************************************/
const int X_LEN = 48;                         // total pairs on x axis
const int Y_LEN = 24;                         // total pairs on y axis
const int TOTAL_LEN = X_LEN + Y_LEN;          // total pairs overall
const int BITS_PER_BYTE = 8;                  // number of bits per byte/char
const int CHAR_LEN = TOTAL_LEN/BITS_PER_BYTE;  // total number of bytes of data
/****************************************************************************/

/* Frame Controls */
/****************************************************************************/
const int DELAY_TIME_MICRO = 180;
const int THRESHOLD_X = 50; // usually ~ 100
const int THRESHOLD_Y = 10; // usually ~ 30

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
bool bit_array[72] = {0};               // bit array that denotes touch coordinates [X1][X2]...[X48][Y1]...[Y24]
char char_array[9] = {0};               // char array that we send to software 
bool touch_bit = 0;                     // digital output after read from currently active x/y photodiode
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
  #ifdef DATA_COLLECTION_MODE
    unsigned long start_time = micros();
    unsigned long cycling_time = 0;
    unsigned long ble_latency = 0;
    unsigned long refresh_time = 0;
  #endif

  cycleX();   
  cycleY();
  
  #ifdef DEBUG
    printBitArray(); 
  #endif

  // 
  for (int i = 0; i < CHAR_LEN; i++) {
      char_array[i] = 0;
      for (int j = 0; j < BITS_PER_BYTE; j++) {
        char_array[i] |= bit_array[i*BITS_PER_BYTE + j] << (BITS_PER_BYTE - 1 - j);
      }
  }

  #ifdef DATA_COLLECTION_MODE
    cycling_time = micros() - start_time;
  #endif

  // If connection is active, send the count value over BLE
  if (connected) { 
    customChar.notify(connection_handle, char_array, CHAR_LEN);  // Notify the connected central with the current count
  }
  #ifdef DATA_COLLECTION_MODE
    ble_latency = micros() - start_time;
  #endif

  #ifdef DATA_COLLECTION_MODE
    refresh_time = micros() - start_time;
    Serial << "Cycling time: " << cycling_time << " microseconds." << endl;
    Serial << "Cycling time + Sending array over Bluetooth: " << ble_latency << " microseconds." << endl;
    Serial << "Refresh time: " << refresh_time << " microseconds." << endl;
    delay(DATA_MODE_DELAY);
  #endif
}

/************************************************************
  @param analog_input : input from mux for that pair 
  Return 1 if touch is detected on that pair based on mux input
************************************************************/
bool analog_to_digital(uint16_t analog_input) {
  if (is_x_axis_enabled) {
    return analog_input < THRESHOLD_X;
  } else {
    return analog_input < THRESHOLD_Y;
  }
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
    bit_array[i] = touch_bit; 

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
    bit_array[i + X_LEN] = touch_bit;

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

  Serial << "char_array: ";
  for (int i = 0; i < 9; i++) {
    Serial << (int)char_array[i] << ' ';
  }
  Serial << endl; 
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