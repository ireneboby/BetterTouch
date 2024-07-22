# Arduino IDE Setup for Adafruit ItsyBitsy nRF52840 Express

This guide will help you set up the Arduino IDE for use with the Adafruit ItsyBitsy nRF52840 Express. Follow these steps to add the board manager, select the correct board, and configure the DFU bootloader.

## 1. Add Board Manager

1. Open the Arduino IDE.
2. Go to **File** > **Preferences**.
3. In the **Additional Board Manager URLs** field, add the following URL:
    ```
    http://adafruit.github.io/arduino-board-index/package_adafruit_index.json
    ```
4. Click **OK** and restart the Arduino IDE.

## 2. Select the Correct Board

1. Open the Arduino IDE.
2. Go to **Tools** > **Board** > **Boards Manager**.
3. Search for "Adafruit nRF52" and install the latest version of the **Adafruit nRF52 by Adafruit** package.
4. Go to **Tools** > **Board** and select **Adafruit ItsyBitsy nRF52840 Express** from the list.

## 3. Select the Correct DFU Bootloader

1. Go to **Tools** > **Programmer**.
2. Select **Bootloader DFU** from the list.

## 4. Compile and Upload Code

You can now compile and upload code to your Adafruit ItsyBitsy nRF52840 Express as usual.

### Additional Information

- Make sure you have installed the necessary libraries for your project. You can install libraries via the **Library Manager** in the Arduino IDE (**Sketch** > **Include Library** > **Manage Libraries**).
- If you encounter any issues with uploading code, ensure your ItsyBitsy is in bootloader mode by double-clicking the reset button to see the red LED pulsing.