import asyncio
from bleak import BleakScanner, BleakClient
import pyautogui 
import serial
from typing import Optional, Tuple
from dataclasses import dataclass

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

@dataclass 
class LocationSet: 
    """A class to represent x and y coordinates

    Attributes:
        x ([Tuple[int, Optional[int]]): 
            A tuple containing one or two x-values. 
            - Example: (x1, x2) or (x1, None).
    
        y (Tuple[int, Optional[int]]): 
            A tuple containing one or two y-values. 
            - Example: (y1, y2) or (y1, None).
    """

    x: Tuple[int, Optional[int]]
    y: Tuple[int, Optional[int]]

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

def coordinate_determination(x_bit_array: list[bool], y_bit_array: list[bool]) -> Optional[LocationSet]:
    """Converts bit arrays into coordinates of the touch. 
    
    Params: 
        x_bit_array: In order of left to right i.e. first element corresponds to the left-most section of the screen.
        y_bit_array: In order of top to bottom i.e. first element corresponds to the top-most section of the screen.
    
    Returns:
        None if no touch.
        CoordinateSet with either a single x and y value for a single touch or two x values and two y values.
    """

    def get_coordinates(bit_array: list[bool], max_value: int, min_value: int) -> Optional[list[int]]:
        """Helper function to determine x or y coordinates."""
        bits = [i for i, bit in enumerate(bit_array) if bit]
        
        if len(bits) == 0:
            return None
        
        locs = []
        
        # TODO make sure the averaging is okay 
        i = 0
        while i < len(bits):
            if i + 1 < len(bits) and bits[i + 1] == bits[i] + 1:  # Adjacent "on" bits
                # Average the two adjacent "on" bits
                avg_index = (bits[i] + bits[i + 1]) / 2
                locs.append(round((avg_index / len(bits)) * (max_value - min_value) + min_value))
                i += 2  
            else:
                locs.append(round((bits[i] / len(bits)) * (max_value - min_value) + min_value))
                i += 1  
        return locs

    # Get x coordinates
    x_coords = get_coordinates(x_bit_array, X_MAX, X_MIN)
    if x_coords is None:
        return None

    # Get y coordinates
    y_coords = get_coordinates(y_bit_array, Y_MAX, Y_MIN)
    if y_coords is None:
        return None

    # Return the coordinates as a CoordinateSet
    return LocationSet(x=x_coords, y=y_coords)


class ScreenState(object):
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

        # if no touch, do nothing
        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return None
        
        if coord.x[1] and coord.y[1]:
            return MultiTouchWaitState(coord)
        
        # if touch, press mouse "down"
        pyautogui.mouseDown(coord[0], coord[1], _pause=False)
        return SingleTouchState(coord[0], coord[1])

class SingleTouchState(ScreenState):
    """State representing single-finger touch."""

    prev_coord: tuple[int, int]

    def __init__(self, start_x: int, start_y: int):
        self.prev_coord = (start_x, start_y)

    def on_event(self, event: bytearray) -> Optional[ScreenState]:

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
    
class MultiTouchWaitState(ScreenState):
    """State representing the initial detection of multi touch."""

    prev_locs: LocationSet

    def __init__(self, start_locs: LocationSet):
        self.prev_locs = start_locs

    def on_event(self, event: bytearray) -> Optional[ScreenState]:

        # if invalid data, do nothing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None

        # if no touch, return to untouched state
        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return UntouchedState()
        
        prev_x_avg = (self.prev_locs.x[0] + self.prev_locs.x[1]) // 2
        curr_x_avg = (coord.x[0] + coord.x[1]) // 2

        # if x is staying similar and y for both fingers is similar 
        # TODO experiment with these threshold values 
        if abs(prev_x_avg - curr_x_avg) <= 2 and abs(coord.y[0] - coord.y[1]) <= 2:

            # check if y is increasing or decreasing
            # TODO experiment with click amounts, check that comparing y in this way is okay 
            prev_y_avg = (self.prev_locs.y[0] + self.prev_locs.y[0]) // 2
            curr_y_avg = (coord.y[0] + coord.y[1]) // 2

            # fingers moved down, scroll up
            if prev_y_avg < curr_y_avg: 
                pyautogui.scroll(3)
            # fingers moved up, scroll down
            else:
                pyautogui.scroll(-3)  
                
            return ScrollState(curr_y_avg)
    
        # if touch and not scroll, find new area and determine whether zoom in or out 
        prev_area = abs(self.prev_locs.x[1] - self.prev_locs.x[0]) * abs(self.prev_locs.y[1] - self.prev_locs.y[0])
        curr_area = abs(coord.x[1] - coord.x[0]) * abs(coord.y[1] - coord.y[0])
        if curr_area < prev_area:
            pyautogui.keyDown('ctrl') 
            pyautogui.press('-')     
            pyautogui.keyUp('ctrl')
        else:
            pyautogui.keyDown('ctrl')
            pyautogui.press('+')
            pyautogui.keyUp('ctrl')
        
        return UntouchedState()

class ScrollState(ScreenState):
    """State representing single-finger touch."""

    prev_y_avg: int

    def __init__(self, avg_y: int):
        self.prev_y_avg = avg_y

    def on_event(self, event: bytearray) -> Optional[ScreenState]:

        # if invalid data, do nothing
        bit_arrays = data_parsing(event)
        if bit_arrays is None:
            return None
        
        # if no touch, return to untouched
        coord = coordinate_determination(bit_arrays[0], bit_arrays[1])
        if coord is None:
            return UntouchedState()
    
        # if scroll continued
        curr_y_avg = (coord.y[0] + coord.y[1]) // 2
        if curr_y_avg != self.prev_y_avg:
            # fingers moved down, scroll up
            if self.prev_y_avg < curr_y_avg: 
                pyautogui.scroll(3)
            # fingers moved up, scroll down
            else:
                pyautogui.scroll(-3)  
            self.prev_y_avg = curr_y_avg 
        return None
    
async def _notification_handler(sender, data):
    global curr_state
    global window 
    
    next_state = curr_state.on_event(data)
    if not next_state is None:
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