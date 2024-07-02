import serial
import pyautogui 
from typing import Optional
import time

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

COM_PORT = 'COM7'
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read
N = 2

def data_parsing(ser) -> Optional[list[bool]]:
    bit_array = []

    data = ser.readline().decode().strip()

    if data:
        data = int(data)
        for _ in range(N):
            bit_array.append(data % 2)
            data = data // 2
        return bit_array

    return None

def coordinate_determination(bit_array: list[bool]) -> Optional[int]:
    
    avg_index = 0
    index_count = 0

    for i, bit in enumerate(bit_array):
        if bit:
            index_count += 1
            avg_index += i
    
    if index_count == 0:
        return None
    
    return round(avg_index/index_count*700 + 400)

class ScreenControl:

    # state that indicates whether the screen is currently being touched
    touching: bool

    def __init__(self) -> None:
        self.touching = False

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
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
    print("Started")
    while True:
        bit_array = data_parsing(ser)
        if bit_array is None:
            continue

        coord = coordinate_determination(bit_array)
        
        if coord is None:
            screen_control.inject_touch()
        else:
            screen_control.inject_touch([coord, 400])

if __name__ == "__main__":
    main()