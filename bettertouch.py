import serial
import pyautogui 
from typing import Optional
import time

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

VOLTAGE_THRESH = 100

COM_PORT = 'COM7'
BAUD_RATE = 9600
TIMEOUT = 0.1 # 1/timeout is the frequency at which the port is read

def data_parsing(ser):
    data = ser.readline().decode().strip()
    if data:
        if int(data) >= VOLTAGE_THRESH:
            return 1
        else:
            return 0
    
    return None

def coordinate_determination(bit_array):

    if bit_array is None:
        return None
    elif bit_array == 0:
        return 0
    
    return round(bit_array/1*1)

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
    average_sum = 0
    average_num = 0

    screen_control = ScreenControl()
    ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=TIMEOUT)
    while True:
        start = time.time()
        bit_array = data_parsing(ser)
        coord = coordinate_determination(bit_array)
        #print(bit_array)
        
        if coord is None:
            continue
        elif coord == 0:
            screen_control.inject_touch()
        else:
            screen_control.inject_touch([None, None])
        end = time.time()
        print(end - start)

if __name__ == "__main__":
    main()