#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>
#include <Arduino.h>
#include <Streaming.h>
#include <Adafruit_TinyUSB.h>

#define DEBUG

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
// const int LED_ON_TIME_MS = 500; // Each LED is on 1ms // Dont know why we have this in the first place
// const int DELAY_TIME = ((float)LED_ON_TIME_MS/512.0)*1000; // Dont know why we have this in the first place
const int DELAY_TIME_MICRO = 500
const int THRESHOLD_x = 10;
const int THRESHOLD_y = 10;

/*  A0 ~ mux output from x axis
    10 ~ mux output from y axis */

// Level 1 Mux Selects (that control the LED/photodiodes)
const int selectL1[3] = {11, 12, 13};   // S0~11, S1~12, S2~13, A~11, B~12, C~13
// Level 2 Mux Selects (that control the Sub Grids)
const int selectL2[3] = {14, 15, 16};

// Enable Signals (Active Low)
const int enable_x_low = 7;             // E~7, G2A~7
const int enable_y_low = 9;             // E~9, G2A~9

bool is_x_axis_enabled = true;          // 0 if x axis is enabled, 1 if y axis is enabled
uint128_t bit_array = 0;                // 128 bit array that denotes touch coordinates (We only use 72 bits)
bool touch_bit = 0;                     // digital output after read from currently active x/y photodiode

/****************************************************************************/

/* Grid constants */
/****************************************************************************/
const int no_subgrid_pairs = 8;                    // number of pairs on each subgrid
const int x_len = 48;               // total pairs on x axis
const int y_len = 24;               // total pairs on y axis
const int x_subgrids = x_len / no_subgrid_pairs;   // number of x subgrids
const int y_subgrids = y_len / no_subgrid_pairs;   // number of y subgrids
/****************************************************************************/

void setup()
{
  Serial.begin(115200);
  pinMode(A0, INPUT);
  
  for (int i=0; i<3; i++)
  {
    pinMode(selectL1[i], OUTPUT);
    digitalWrite(selectL1[i], LOW);

    pinMode(selectL2[i], OUTPUT);
    digitalWrite(selectL1[i], LOW);
  }

  pinMode(enable_x_low, OUTPUT);
  pinMode(enable_y_low, OUTPUT);
  // To start, x axis is first enabled
  digitalWrite(enable_x_low, LOW);
  digitalWrite(enable_y_low, HIGH);

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
    if is_x_axis_enabled {
        return analog_input < THRESHOLD_x
    }
  return analog_input < THRESHOLD_y;
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
  Cycle through pins on the x axis subgrid
************************************************************/
void cycleSubgrid()
{
  for (int pin=0; pin < no_subgrid_pairs; pin++)
  {
    setL1SelectSignals(pin);
    touch_bit = analog_to_digital(is_x_axis_enabled ? analogRead(A0) : analogRead(10));
    
    #ifdef DEBUG
      Serial << "Pair " << pin << ": " << is_x_axis_enabled ? analogRead(A0) : analogRead(10) << endl;
    #endif
 
    bit_array = (bit_array << 1) | touch_bit;

    #ifdef DEBUG
      delay(1000);
    #endif

    delayMicroseconds(DELAY_TIME_MICRO);
  }
}

/************************************************************
  Cycle through the x axis
************************************************************/
void cycleX()
{
  enable_x_axis();
  for (int mux=0; mux < x_subgrids; mux ++) {
        selectMux(mux, x_subgrids)
        cycleSubgrid();
    }
}

/************************************************************
  Cycle through the y axis
************************************************************/
void cycleY()
{
  enable_y_axis();
  for (int mux=0; mux < y_subgrids; mux ++) {
        selectMux(mux, y_subgrids)
        cycleSubgrid();
    }
}

/************************************************************
  @param pin : 0-7 denotes which pin to turn on 
  Sets the select signals to turn on pair on that pin
************************************************************/
void setL1SelectSignals(byte pin)
{
  if (pin >= no_subgrid_pairs) return; // Exit if pin is out of scope i.e we want pin to be in [0, 7]
  for (int i=0; i<3; i++) 
  {
    if (pin & (1<<i))
      digitalWrite(selectL1[i], HIGH);
    else
      digitalWrite(selectL1[i], LOW);
  }
}

/************************************************************
  @param pin : Denotes which mux to turn on 
  @param n : Denotes number of muxes 
  Sets the select signals to turn on pair on that pin
************************************************************/
void selectMux(byte mux, byte n)
{
  if (mux >= n) return; // Exit if mux index is out of scope i.e we want mux to be in [0, number of muxes - 1]
  for (int i=0; i<3; i++) 
  {
    if (mux & (1<<i))
      digitalWrite(selectL2[i], HIGH);
    else
      digitalWrite(selectL2[i], LOW);
  }
}

/************************************************************
  Print the bit array in binary representation
************************************************************/
void printBitArray()
{
  Serial << "bit_array: ";
  for (int i = 127; i >= 0; i--)
  {
    Serial << ((bit_array >> i) & 1);
  }
  Serial << endl;
}