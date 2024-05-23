import RPi.GPIO as GPIO
from gpiozero import Button
import time

# Use BCM GPIO numbering
GPIO.setmode(GPIO.BCM)

# Define the GPIO pins for the relay and button
RELAY_PIN = 18
BUTTON_PIN = 17

# Set up the relay pin as an output
GPIO.setup(RELAY_PIN, GPIO.OUT)

# Initially, make sure the relay is off
GPIO.output(RELAY_PIN, GPIO.HIGH)
print("Initial State: Relay On (Locked)")

# Variable to keep track of the lock state
is_locked = True

# Function to lock
def lock():
    global is_locked
    GPIO.output(RELAY_PIN, GPIO.HIGH)  # Activate relay
    is_locked = True
    print("Locked: GPIO HIGH")

# Function to unlock
def unlock():
    global is_locked
    GPIO.output(RELAY_PIN, GPIO.LOW)  # Deactivate relay
    is_locked = False
    print("Unlocked: GPIO LOW")

# Initialize the button
button = Button(BUTTON_PIN)



# Main loop to wait for button press and toggle lock
try:
    while True:
        button.wait_for_press()
        if is_locked:
            unlock()
        else:
            lock()
        # Debounce delay
        time.sleep(0.3)

except KeyboardInterrupt:
    print("Program stopped")

finally:
    # Clean up the GPIO pins on exit
    GPIO.cleanup()
    print("GPIO cleanup done")
