import asyncio
from bleak import BleakScanner, BleakClient
import pyautogui 
import serial
from typing import Optional
from datetime import datetime
import os

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

is_os_executing = False # Global variable to track of pyautogui call is in progress

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

def coordinate_determination(x_bit_array: list[bool], y_bit_array: list[bool]) -> Optional[tuple[int, int, int]]:
    """Converts bit arrays into touch coordinates and detects number of touches."""
    x_index = sum(i for i, bit in enumerate(x_bit_array) if bit)
    x_indices = [i for i, bit in enumerate(x_bit_array) if bit]
    x_count = sum(x_bit_array)
    if x_count == 0:
        return None
    x_coord = round((x_index / x_count / N) * (X_MAX - X_MIN) + X_MIN)

    y_index = sum(i for i, bit in enumerate(y_bit_array) if bit)
    y_count = sum(y_bit_array)
    if y_count == 0:
        return None
    y_coord = round((y_index / y_count / M) * (Y_MAX - Y_MIN) + Y_MIN)

    # Determine number of touches
    num_touches = 1
    for i in range(1, len(x_indices)):
        if x_indices[i] != (x_indices[i-1] + 1):
            num_touches += 1

    # if x_count >= 6:
    #     num_touches = 3
    # elif x_count >= 3:
    #     num_touches = 2

    return x_coord, y_coord, num_touches

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

        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return None

        return TapState(coord)

class TapState(ScreenState):
    """Intermediate state to prevent misclassification of two-finger touches."""

    prev_coords: list
    window_size = 5

    def __init__(self, coord):
        self.prev_coords = [coord]

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None
        
        global is_os_executing

        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            last_touch = self.prev_coords[-1]
            if last_touch[2] <= 2:
                pyautogui.click(x=last_touch[0], y=last_touch[1], button="left" if last_touch[2] == 1 else "right", _pause=False)
            else:
                img = pyautogui.screenshot()
                desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                filename = f"screenshot_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
                img.save(os.path.join(desktop_path, filename))
            return UntouchedState()

        if len(self.prev_coords) < self.window_size:
            self.prev_coords.append(coord)
            return None
        elif coord[2] == 1:
            pyautogui.mouseDown(x=coord[0], y=coord[1], button="left", _pause=False)
            return OneTouchDragState()
        else:
            return TwoFingerTouchState(coord)

class OneTouchDragState(ScreenState):
    """Single-finger drag (mouse down & move)."""

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            pyautogui.mouseUp(button="left", _pause=False)
            return UntouchedState()

        pyautogui.moveTo(x=coord[0], y=coord[1], _pause=False)
        return None

class TwoFingerTouchState(ScreenState):
    """Handles two-finger gestures (scroll & zoom)."""
    prev_coords = list
    window = 5
    
    def __init__(self, coord):
        self.prev_coords = [coord]

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        global is_os_executing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return UntouchedState()

        x, y, num_touches = coord
        if num_touches == 1:
            return TapState(coord)
        prev_x, prev_y, _ = self.prev_coords[0]

        # is_os_executing = True

        try:
            # Detect gesture type (scrolling or zooming)
            if abs(y - prev_y) > 3:
                scroll_amount = (y - prev_y) // 4
                pyautogui.scroll(scroll_amount, _pause=False)
            elif abs(x - prev_x) > 20:
                zoom_factor = 1.1 if x > prev_x else 0.9
                pyautogui.hotkey("ctrl", "+", _pause=False) if zoom_factor > 1 else pyautogui.hotkey("ctrl", "-", _pause=False)
        finally:
            is_os_executing = False
        if len(self.prev_coords) >= window:
            self.prev_coords.pop(0)
        self.prev_coords.append(coord)
        return None

curr_state = UntouchedState()

async def _notification_handler(sender, data):
    if is_os_executing:  # Ignore new events while an action is happening
        return
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