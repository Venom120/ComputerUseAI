import sounddevice as sd

print("Querying audio devices...")
try:
    devices = sd.query_devices()
    print(devices)
    
    print("\n--- Recommended Input Devices ---")
    for i, device in enumerate(devices):
        if device['max_input_channels'] > 0: # type: ignore
            print(f"Device ID: {i}, Name: {device['name']}") # type: ignore
            
    print(f"\nYour default input device ID is: {sd.default.device[0]}")
    
except Exception as e:
    print(f"An error occurred: {e}")
    print("Is sounddevice installed? (pip install sounddevice)")