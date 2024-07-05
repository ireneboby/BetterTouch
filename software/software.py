import serial
import pyautogui 
from typing import Optional

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

COM_PORT = 'COM7'
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read
N = 2

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
        self.port = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
        self.x_pixels, self.y_pixels = pyautogui.size()

    def data_parsing(self) -> Optional[tuple[list[bool], list[bool]]]:
        data = self.port.readline().decode().strip()
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
        x_coord = round(x_index/x_index_count*(self.x_pixels - 500) + 200) # FIXME

        # y_coord = None
        y_index = 0
        y_index_count = 0
        for i, bit in enumerate(y_bit_array):
            if bit:
                y_index_count += 1
                y_index += i
        y_coord = round(y_index/y_index_count*(self.y_pixels - 500) + 200) # FIXME

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

def main():

    screen_control = ScreenControl()
    
    print("Started")

    while True:

        # convert data from firmware to bit arrays
        bit_array = screen_control.data_parsing()
        if bit_array is None:
            continue

        # convert bit arrays into coordinates
        coord = screen_control.coordinate_determination(bit_array)
        if coord is None:
            screen_control.inject_touch()
        else:
            screen_control.inject_touch([coord[0], coord[1]])

if __name__ == "__main__":
    main()