import asyncio
from bleak import BleakScanner, BleakClient
import pyautogui 
import serial
from typing import Optional

DEBUG_MODE = True

# PyAutoGUI settings
pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

# Bluetooth Connection Settings
CUSTOM_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
CUSTOM_CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"
COM_PORT = 'COM7'                       # for Windows
# COM_PORT = '/dev/cu.usbmodem14201'    # for MacOS
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read

# Frame Constants
N = 48
M = 24
X_MIN = 0
Y_MIN = 0
X_MAX, Y_MAX = pyautogui.size()

def data_parsing(data: bytearray) -> Optional[tuple[list[bool], list[bool]]]:
    """Converts recevied data into bit arrays. Returns None if data is invalid.

    Params:
        data: 
            Array of bytes with each bit corresponding to a photodiode-LED pair. 
            1 represents that an interception has been detected. 
            Order of bytes and bits correspond to left -> right for x-axis and top -> bottom for y-axis. 
            This means the first byte in the array corresponds to the left-most section of the screen,
            and the MSB corresponds to the left-most pixel of that section of the screen. 
            i.e. [00000100, 00000000, ..., 00000000, 01000000].

    Returns: 
        None for invalid data.
        (x_bit_array, y_bit_array) in order of left -> right for x and top -> bottom for y. 
        i.e. the first element in x_bit_array corresponds to the left-most section of the screen. 
    """

    x_bit_array = []
    y_bit_array = []

    for j, byte in enumerate(data):
        for i in range(7, -1, -1): # extract in order from MSB to LSB 
            if j < 6: # first six bytes (6 bytes * 8 bits/byte = 48 bits) belong to x-axis
                x_bit_array.append(bool((byte >> i) & 1))
            else:
                y_bit_array.append(bool((byte >> i) & 1))

    # check validity of coordinates
    if any(x_bit_array) != any(y_bit_array):
        return None
    
    return x_bit_array, y_bit_array

def find_touch_regions(bit_array):
    """Finds up to two distinct touch regions in bit array."""
    indices = [i for i, bit in enumerate(bit_array) if bit]
    if not indices:
        return None
    if len(indices) > 1 and (indices[-1] - indices[0] > 3):  # Gap threshold
        mid = len(indices) // 2
        return [indices[:mid], indices[mid:]]
    return [indices]

def coordinate_determination(x_bit_array: list[bool], y_bit_array: list[bool]) -> Optional[list[tuple[int, int]]]:
    """Detects up to two touch points and returns their coordinates."""
    x_regions = find_touch_regions(x_bit_array)
    y_regions = find_touch_regions(y_bit_array)

    if not x_regions or not y_regions:
        return None

    touches = []
    for x_group, y_group in zip(x_regions, y_regions):
        x_avg = sum(x_group) / len(x_group)
        y_avg = sum(y_group) / len(y_group)
        x_coord = round((x_avg / N) * (X_MAX - X_MIN) + X_MIN)
        y_coord = round((y_avg / M) * (Y_MAX - Y_MIN) + Y_MIN)
        touches.append((x_coord, y_coord))

    return touches if touches else None

class ScreenState:
    def on_event(self, event: bytearray):
        """Handling when data from microcontroller has been sent to software."""
        raise NotImplementedError

class UntouchedState(ScreenState):
    """State representing no touch."""

    def on_event(self, event: bytearray) -> Optional[ScreenState]:

        # if invalid data, do nothing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        touches = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if not touches:
            return None

        if len(touches) == 1:
            pyautogui.mouseDown(touches[0][0], touches[0][1], _pause=False)
            return SingleTouchState(touches[0][0], touches[0][1])
        elif len(touches) == 2:
            return MultiTouchState(touches[0], touches[1])

        return None

class SingleTouchState(ScreenState):
    """Single-finger touch (click/drag)."""

    def __init__(self, start_x: int, start_y: int):
        self.prev_coord = (start_x, start_y)

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        touches = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if not touches:
            pyautogui.mouseUp(_pause=False)
            return UntouchedState()

        if touches[0] != self.prev_coord:
            pyautogui.moveTo(touches[0][0], touches[0][1], _pause=False)
            self.prev_coord = touches[0]

        return None

class MultiTouchState(ScreenState):
    """Handles two-finger gestures (scroll & zoom)."""

    def __init__(self, coord1: tuple[int, int], coord2: tuple[int, int]):
        self.prev_coord1 = coord1
        self.prev_coord2 = coord2

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        touches = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if not touches or len(touches) < 2:
            return UntouchedState()

        coord1, coord2 = touches

        # Detect gesture type
        y_diff_prev = abs(self.prev_coord1[1] - self.prev_coord2[1])
        y_diff_now = abs(coord1[1] - coord2[1])

        if abs(coord1[1] - self.prev_coord1[1]) > 5 and abs(coord2[1] - self.prev_coord2[1]) > 5:
            scroll_amount = (coord1[1] - self.prev_coord1[1]) // 2
            pyautogui.scroll(-scroll_amount)  # Scroll

        elif abs(y_diff_now - y_diff_prev) > 3:
            zoom_factor = 1.1 if y_diff_now > y_diff_prev else 0.9
            pyautogui.hotkey("ctrl", "+") if zoom_factor > 1 else pyautogui.hotkey("ctrl", "-")

        self.prev_coord1 = coord1
        self.prev_coord2 = coord2
        return None

curr_state = UntouchedState()

async def _notification_handler(sender, data):
    global curr_state
    global window 
    
    next_state = curr_state.on_event(data)
    if next_state:
        curr_state = next_state

    if DEBUG_MODE:
        data_bits = ''.join(f'{byte:08b}' for byte in data)
        print(curr_state, data_bits)

async def main_ble():
    """Handles data communication over bluetooth."""
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
        
def main_serial():
    """Handles data communication serially."""

    port = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
    global curr_state
    
    while True:
        data = port.readline().decode().strip()
        if data is None:
            continue
        
        next_state = curr_state.on_event(int(data))
        if not next_state is None:
            curr_state = next_state


if __name__ == "__main__":
    asyncio.run(main_ble())