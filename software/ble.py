import asyncio
from bleak import BleakScanner, BleakClient
import serial
import pyautogui 
from typing import Optional

# Define the custom service and characteristic UUIDs
CUSTOM_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
CUSTOM_CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

# COM_PORT = 'COM7'                       #for Windows
COM_PORT = '/dev/cu.usbmodem142101'    # for MacOS
BAUD_RATE = 115200
N = 8

class ScreenControl:

    # state that indicates whether the screen is currently being touched
    touching: bool

    # serial communication port
    port: serial.Serial

    # screen resolution for the x (width) dimension 
    x_pixels: int

    # screen resolution for the y (height) dimension
    y_pixels: int

    def __init__(self) -> None:
        self.touching = False
        self.port = serial.Serial(COM_PORT, BAUD_RATE)
        self.x_pixels, self.y_pixels = pyautogui.size()

    def data_parsing(self, data: int) -> Optional[tuple[list[bool], list[bool]]]:
        if not data:
            return None
        
        data = int(data)

        # get the horizontal coordinates
        x_bit_array = []
        for _ in range(N):
            x_bit_array.append(data % 2)
            data = data // 2

        # get the vertical coordinates
        y_bit_array = []
        for _ in range(N):
            y_bit_array.append(data % 2)
            data = data // 2

        # check validity of coordinates
        if any(x_bit_array) != any(y_bit_array):
            return None
        
        return x_bit_array, y_bit_array
    
    def coordinate_determination(self, bit_array: tuple[list[bool], list[bool]]) -> Optional[tuple[int, int]]:

        x_bit_array, y_bit_array = bit_array

        x_index = 0
        x_index_count = 0
        for i, bit in enumerate(x_bit_array):
            if bit:
                x_index_count += 1
                x_index += i
        if x_index_count == 0:
            return None
        x_coord = round((1 - x_index/x_index_count/N)*self.x_pixels)

        y_coord = None
        y_index = 0
        y_index_count = 0
        for i, bit in enumerate(y_bit_array):
            if bit:
                y_index_count += 1
                y_index += i
        y_coord = round((y_index/y_index_count/N)*self.y_pixels)

        return x_coord, y_coord
    
    def inject_touch(self, position: Optional[tuple[int, int]] = None):

        if not position:
            if self.touching:
                self.touching = False
                pyautogui.mouseUp(_pause=False)
        
        else:
            x, y = position
            if self.touching:
                pyautogui.moveTo(x, y, _pause=False)
            else:
                self.touching = True
                pyautogui.mouseDown(x, y, _pause=False)

# Initialize ScreenControl instance
screen_control = ScreenControl()

async def notification_handler(sender, data):
    bit_array = int.from_bytes(data, byteorder='little')
    #print(f"Received count: {bit_array}")

    # Parse bit array into coordinates
    parsed_data = screen_control.data_parsing(bit_array)
    if parsed_data is None:
        return

    coord = screen_control.coordinate_determination(parsed_data)
    print(coord)
    if coord is None:
        screen_control.inject_touch()
    else:
        screen_control.inject_touch([coord[0], coord[1]])

async def ble_main():
    devices = await BleakScanner.discover()

    # Find the device advertising the custom service
    target_device = None
    for device in devices:
        print(f"Device found: {device.name}, Address: {device.address}")
        if CUSTOM_SERVICE_UUID in [str(uuid) for uuid in device.metadata.get("uuids", [])]:
            target_device = device
            break

    if not target_device:
        print("Custom service not found in any device.")
        return

    print(f"Connecting to {target_device.address}...")

    async with BleakClient(target_device) as client:
        if not client.is_connected:
            print("Failed to connect.")
            return

        print("Connected. Enabling notifications...")

        await client.start_notify(CUSTOM_CHAR_UUID, notification_handler)

        print("Notifications enabled. Waiting for data...")

        try:
            while True:
                await asyncio.sleep(0.05)
        except KeyboardInterrupt:
            print("Program interrupted")

if __name__ == "__main__":
    asyncio.run(ble_main())