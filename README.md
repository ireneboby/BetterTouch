# BetterTouch
A frame to seamlessly transform any laptop into a touchscreen.
[Video Demo](https://youtu.be/HHpmAeaOsxw)
Built by: Irene Boby, Wani Gupta, Subin Lee, Ella Smith and Kristin Wu

## How It's Made 
1. Pairs of infrared LEDs and photodiodes detect interruptions in light beams with the presence of a finger. 
2. A bit array representing where touch was detected on the x and y axes is sent over BlueTooth to the laptop.
3. A Python script processes the type of touch and calls the [PyAutoGUI library](https://github.com/asweigart/pyautogui) for screen control compatible with Windows and macOS. 

## Installation Instructions

### Windows 

In the command prompt, create a virtual environment and activate it.

```
python -m path\to\env
path\to\env\Scripts\activate.bat
```

Then, install the packages in `requirements.txt`. 

```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### Mac

Create a virtual environment and activate it.

```
python -m venv path/to/env
source path/to/env/bin/activate
```

Then, install the packages in `requirements.txt`. 

```
pip install --upgrade pip
pip install -r requirements.txt
```

MAC may need to make changes in the privacy and security setttings:
Settings > Privacy & Security > Accessibility > Switch on for the application running the Python script


