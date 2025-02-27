import asyncio
from bleak import BleakScanner, BleakClient
import pyautogui 
import serial
from typing import Optional

DEBUG_MODE = True

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

# Define the custom service and characteristic UUIDs
CUSTOM_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
CUSTOM_CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"

COM_PORT = 'COM7'                       # for Windows
# COM_PORT = '/dev/cu.usbmodem14201'    # for MacOS
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read

N = 48
M = 24

X_MIN = 0
Y_MIN = 0
X_MAX, Y_MAX = pyautogui.size()

def data_parsing(data: int) -> Optional[tuple[list[bool], list[bool]]]:
    """Converts recevied data into bit arrays. Returns None if data is invalid."""

    x_bit_array = []
    y_bit_array = []

    for j, byte in enumerate(data):
        for i in range(7, -1, -1):
            if j < 6:
                x_bit_array.append(bool((byte >> i) & 1))
            else:
                y_bit_array.append(bool((byte >> i) & 1))

    # check validity of coordinates
    if any(x_bit_array) != any(y_bit_array):
        return None
    
    return x_bit_array, y_bit_array

def coordinate_determination(x_bit_array: list[bool], y_bit_array: list[bool]) -> Optional[tuple[int, int]]:
        """Converts bit arrays into coordinates of the touch. Returns None if no touch."""

        x_index = 0
        x_index_count = 0
        for i, bit in enumerate(x_bit_array):
            if bit:
                x_index_count += 1
                x_index += i
        if x_index_count == 0:
            return None
        x_coord = round((x_index/x_index_count/N)*(X_MAX-X_MIN) + X_MIN)

        y_coord = None
        y_index = 0
        y_index_count = 0
        for i, bit in enumerate(y_bit_array):
            if bit:
                y_index_count += 1
                y_index += i
        y_coord = round((y_index/y_index_count/M)*(Y_MAX-Y_MIN) + Y_MIN)

        return x_coord, y_coord

class ScreenState(object):
    def on_event(self, event: int):
        raise NotImplementedError

class UntouchedState(ScreenState):

    def on_event(self, event: int) -> Optional[ScreenState]:

        # if invalid data, do nothing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        # if no touch, do nothing
        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return None
        
        # if touch, press mouse "down"
        pyautogui.mouseDown(coord[0], coord[1], _pause=False)
        return SingleTouchState(coord[0], coord[1])

class SingleTouchState(ScreenState):

    prev_coord: tuple[int, int]

    def __init__(self, start_x: int, start_y: int):
        self.prev_coord = (start_x, start_y)

    def on_event(self, event: int) -> Optional[ScreenState]:

        # if invalid data, do nothing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None
        
        # if no touch, mouse button is now "up" and transition to new state
        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            pyautogui.mouseUp(_pause=False)
            return UntouchedState()
    
        # if touch 
        if coord[0] != self.prev_coord[0] or coord[1] != self.prev_coord[1]:
            pyautogui.moveTo(coord[0], coord[1], _pause=False)
            self.prev_coord = coord
        return None

curr_state = UntouchedState()
window = []
WINDOW_SIZE = 10

def main_serial():
    port = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
    global curr_state
    
    while True:
        data = port.readline().decode().strip()
        if data is None:
            continue
        
        next_state = curr_state.on_event(int(data))
        if not next_state is None:
            curr_state = next_state

async def _notification_handler(sender, data):
    global curr_state
    global window 

    # if len(window) == WINDOW_SIZE:
    #     tmp_var = data
    #     data = mode(window)
    #     window = [tmp_var]
    # else:
    #     window.append(data)
    #     return
    
    next_state = curr_state.on_event(data)
    if not next_state is None:
        curr_state = next_state

    if DEBUG_MODE:
        data_bits = ''.join(f'{byte:08b}' for byte in data)
        print(curr_state, data_bits)

async def main_ble():
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

        await client.start_notify(CUSTOM_CHAR_UUID, _notification_handler)

        print("Notifications enabled. Waiting for data...")

        try:
            while True:
                await asyncio.sleep(0.05)
        except KeyboardInterrupt:
            print("Program interrupted")
        

if __name__ == "__main__":
    #main_serial()
    asyncio.run(main_ble())