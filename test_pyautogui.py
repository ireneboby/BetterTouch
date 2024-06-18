import pyautogui 
import time
from typing import Optional

pyautogui.PAUSE = 2.5
pyautogui.FAILSAFE = True

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


if __name__ == "__main__":
    screen_control = ScreenControl()

    # simulate single-finger tap/click
    screen_control.inject_touch(None)
    start_time = time.time()
    screen_control.inject_touch((100, 100))
    screen_control.inject_touch(None)
    end_time = time.time()
    print("Click Time:", end_time - start_time)
    time.sleep(2)

    # simulate single-finger drag
    screen_control.inject_touch(None)
    for i in range(35):
        screen_control.inject_touch((100, 100 + i))
        time.sleep(0.1)
    screen_control.inject_touch(None)


