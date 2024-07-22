import asyncio
from bleak import BleakScanner, BleakClient

# Define the custom service and characteristic UUIDs
CUSTOM_SERVICE_UUID = "00001234-0000-1000-8000-00805f9b34fb"
CUSTOM_CHAR_UUID = "00005678-0000-1000-8000-00805f9b34fb"

async def notification_handler(sender, data):
    bit_array = int.from_bytes(data, byteorder='little')
    print(f"Received count: {bit_array}")

async def main():
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

        await client.start_notify(CUSTOM_CHAR_UUID, notification_handler)

        print("Notifications enabled. Waiting for data...")

        try:
            while True:
                await asyncio.sleep(0.05)
                # print("Waiting...")
        except KeyboardInterrupt:
            print("Program interrupted")

def printBitArray(bit_array):
  for i in range(0, 15):
    print (f"{((bit_array >> i) & 1)}")
  print("\n")

if __name__ == "__main__":
    asyncio.run(main())
