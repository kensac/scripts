import time
import sys

try:
    import pyautogui
except ImportError:
    print("Please install pyautogui first:\n    pip install pyautogui")
    sys.exit(1)

def main():
    print("Press Ctrl+C to stop.")
    print("Screen resolution:", pyautogui.size())
    try:
        while True:
            x, y = pyautogui.position()
            # Print on one line and overwrite (so it doesn’t spam)
            print(f"Cursor at: X={x}, Y={y}", end="\r")
    except KeyboardInterrupt:
        print("\nExiting.")

if __name__ == "__main__":
    main()
