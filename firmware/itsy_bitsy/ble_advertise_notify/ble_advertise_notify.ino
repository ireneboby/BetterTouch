// The provided code advertises the itsy bitsy with a custom service and characteristic
// It counts from 1 to 100 over and over again and sends these values to a connected device
// The connected device can view these values if it tunes into the custom characteristic and looks at the notifications

#include <bluefruit.h>
#include <Adafruit_LittleFS.h>
#include <InternalFileSystem.h>

// BLE Services - may not need all but it is here in case we want to use them
BLEDfu  bledfu;  // OTA DFU service
BLEDis  bledis;  // device information
BLEUart bleuart; // uart over ble
BLEBas  blebas;  // battery

// Custom service and characteristic UUIDs - will change to more complicated hex values in the future
#define CUSTOM_SERVICE_UUID     0x1234  // service UUID
#define CUSTOM_CHAR_UUID        0x5678  // characteristic UUID

BLEService customService(CUSTOM_SERVICE_UUID);
BLECharacteristic customChar(CUSTOM_CHAR_UUID, BLERead | BLENotify);

bool connected = false;  // Flag to track if there is an active connection
uint16_t connection_handle = 0;  // variable to store the connection handle

void setup()
{
  Serial.begin(115200);

  // Setup the BLE LED to be enabled on CONNECT
  // Note: This is actually the default behavior, but provided here in case we want to control this LED manually via PIN 19
  Bluefruit.autoConnLed(true);

  // Config the peripheral connection with maximum bandwidth 
  // more SRAM required by SoftDevice
  // Note: All config***() function must be called before begin()
  Bluefruit.configPrphBandwidth(BANDWIDTH_MAX);

  Bluefruit.begin();
  Bluefruit.setTxPower(4);    // Check bluefruit.h for supported values
  //Bluefruit.setName(getMcuUniqueID()); // useful testing with multiple central connections
  Bluefruit.Periph.setConnectCallback(connect_callback);
  Bluefruit.Periph.setDisconnectCallback(disconnect_callback);

  // To be consistent OTA DFU should be added first if it exists
  bledfu.begin();

  // Configure and Start Device Information Service
  bledis.setManufacturer("Adafruit Industries");
  bledis.setModel("Bluefruit ItsyBitsy");
  bledis.begin();

  // Configure and Start BLE Uart Service
  bleuart.begin();

  // Start BLE Battery Service
  blebas.begin();
  blebas.write(100);

  // Add the custom service and characteristic
  customService.begin();
  customChar.begin();

  // Set up and start advertising
  startAdv();
}

void startAdv(void)
{
  // Advertising packet
  Bluefruit.Advertising.addFlags(BLE_GAP_ADV_FLAGS_LE_ONLY_GENERAL_DISC_MODE);
  Bluefruit.Advertising.addTxPower();

  // Include bleuart 128-bit uuid
  Bluefruit.Advertising.addService(bleuart);

  // Include the custom service in the advertisement
  Bluefruit.Advertising.addService(customService);

  // Secondary Scan Response packet (optional)
  // Since there is no room for 'Name' in Advertising packet
  Bluefruit.ScanResponse.addName();
  
  /* Start Advertising
   * - Enable auto advertising if disconnected
   * - Interval:  fast mode = 20 ms, slow mode = 152.5 ms
   * - Timeout for fast mode is 30 seconds
   * - Start(timeout) with timeout = 0 will advertise forever (until connected)
   * 
   * For recommended advertising interval
   * https://developer.apple.com/library/content/qa/qa1931/_index.html   
   */
  Bluefruit.Advertising.restartOnDisconnect(true);
  Bluefruit.Advertising.setInterval(32, 244);    // in unit of 0.625 ms
  Bluefruit.Advertising.setFastTimeout(30);      // number of seconds in fast mode
  Bluefruit.Advertising.start(0);                // 0 = Don't stop advertising after n seconds  
}

void loop()
{
  // If connection is active, send the count value over BLE
  static uint16_t count = 1;  // Static variable to keep count between calls
  if (connected) 
  { 
    customChar.notify16(connection_handle, count);  // Notify the connected central with the current count
  }
  count++;  // Increment the count
  if (count > 100) count = 1;  // Reset count if it exceeds 100
  delay(1000);  // Send the number every second
}

// callback invoked when central connects
void connect_callback(uint16_t conn_handle)
{
  connection_handle = conn_handle;
  // Get the reference to current connection
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