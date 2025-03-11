import asyncio
from bleak import BleakScanner, BleakClient
import pyautogui 
import serial
from typing import Optional
from datetime import datetime
import os
import platform
import sys

DEBUG_MODE = True

# PyAutoGUI settings
pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

# Bluetooth Connection Settings
CUSTOM_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
CUSTOM_CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"
SYSTEM = ""
COM_PORT = ''                       # for Windows
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read

if platform.system() == "Windows":
    SYSTEM = "Win"
    COM_PORT = 'COM7'
elif platform.system() == "Darwin":
    SYSTEM = "Mac"
    COM_PORT = '/dev/cu.usbmodem14201'
else:
    raise Exception("Platform not supported")

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
    consecutives = 1
    for i in range(1, len(x_indices)):
        if x_indices[i] != (x_indices[i-1] + 1) or consecutives > 3:
            num_touches += 1
            consecutives = 1
        else:
            consecutives += 1

    return x_coord, y_coord, num_touches, x_indices[0] - x_indices[-1]

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
    window_size = 8

    def __init__(self, coord):
        self.prev_coords = [coord]

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

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

    zoomed = bool
    scrolled = bool

    def __init__(self, coord):
        self.prev_coord = coord
        self.zoomed = False
        self.scrolled = False

    def on_event(self, event: bytearray) -> Optional[ScreenState]:
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None
        
        prev_x, prev_y, _, prev_diff_x = self.prev_coord
        zoomed_or_scroll = self.zoomed or self.scrolled

        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            if not zoomed_or_scroll:
                pyautogui.click(x=prev_x, y=prev_y, button="left", _pause=False)
            return UntouchedState()

        x, y, num_touches, diff_x = coord
        if num_touches == 1:
            return TapState(coord)

        # Detect gesture type (scrolling or zooming)
        if abs(y - prev_y) > 15 and (not zoomed_or_scroll or self.scrolled):
            scroll_amount = (y - prev_y)*10
            pyautogui.scroll(scroll_amount, _pause=False)
            self.zoomed = True
        elif abs(x - prev_x) > 35 and (not zoomed_or_scroll or self.zoomed):
            zoom_factor = 1.1 if prev_diff_x > diff_x else 0.9
            self.scrolled = True
            if SYSTEM == "Win":
                pyautogui.hotkey("ctrl", "+", _pause=False) if zoom_factor > 1 else pyautogui.hotkey("ctrl", "-", _pause=False)
            elif SYSTEM == "Mac":
                pyautogui.hotkey("command", "+", _pause=False) if zoom_factor > 1 else pyautogui.hotkey("command", "-", _pause=False)  

        self.prev_coord = coord
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

target_frame = None
RECONNECT_TIMEOUT = 30  # in seconds
RECONNECT_DELAY = 4  # in seconds

class ReconnectTimeoutError(Exception):
    """Custom exception raised when reconnection times out."""
    pass

async def connect_and_notify():
    """Attempt connection within a timeout period."""
    global target_frame
    start_time = asyncio.get_event_loop().time()
    
    while asyncio.get_event_loop().time() - start_time <= RECONNECT_TIMEOUT:
        try:
            print(f"Attempting to connect to {target_frame.address}...")
            async with BleakClient(target_frame, disconnected_callback=disconnect_callback) as client:
                if client.is_connected:
                    print(f"Connected to {target_frame.address} successfully. Enabling notifications...")
                    await client.start_notify(CUSTOM_CHAR_UUID, _notification_handler)
                    print("Notifications enabled. Listening for data...")
                    while client.is_connected:
                        await asyncio.sleep(0.015)
                else:
                    print("Failed to establish a connection. Retrying...")
        except Exception as e:
            print(f"Reconnection attempt failed. {e}")
        
        await asyncio.sleep(RECONNECT_DELAY)
    
    # Reconnect timeout
    raise ReconnectTimeoutError

async def main_ble():
    """Scans for and connects to the target frame."""
    global target_frame
    
    if not target_frame:
        devices = await BleakScanner.discover()
        for device in devices:
            print(f"Discovered: {device.name}, Address: {device.address}")
            if CUSTOM_SERVICE_UUID in [str(uuid) for uuid in device.metadata.get("uuids", [])]:
                target_frame = device
                break
        if not target_frame:
            print("No compatible device found.")
            return
    
    try:
        await connect_and_notify()
    except ReconnectTimeoutError:
        print("Reconnection timeout reached. Exiting.")
        return

def disconnect_callback(client):
    """Handles disconnection events and triggers monitored reconnection."""
    global target_frame
    print(f"Disconnected from {client.address}. Attempting to reconnect...")
    if target_frame:
        asyncio.create_task(connect_and_notify())
        
        
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
    try:
        asyncio.run(main_ble())
    except KeyboardInterrupt:
        print("Program interrupted. Exiting.")
        sys.exit(0)