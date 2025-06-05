#!/usr/bin/env python3
import time
import sys
import select
import termios
import tty

try:
    import pyautogui
except ImportError:
    print("Please install pyautogui:\n    pip install pyautogui")
    sys.exit(1)


def key_pressed():
    """
    Check if any key has been pressed on stdin (non-blocking).
    Returns the character if pressed, otherwise None.
    """
    dr, _, _ = select.select([sys.stdin], [], [], 0)
    if dr:
        return sys.stdin.read(1)
    return None


def main():
    # Read the number of clicks (n) for the second position
    try:
        n = int(input("Enter number of clicks at (646, 2232): ").strip())
        if n < 0:
            raise ValueError
    except ValueError:
        print("Invalid input. Please enter a non-negative integer.")
        return

    # Save original terminal settings so we can restore them later
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)  # Set terminal to cbreak mode (no Enter needed)

    stop = False
    print("\nSequence will begin shortly.")
    print("Press any key at any time to stop.")
    print("Move your mouse away from the target coordinates if needed.")
    # Optional countdown before starting
    for i in range(3, 0, -1):
        print(f"  Clicking begins in {i}...")
        time.sleep(1)

    try:
        # First, click once at (789, 1762)
        if not stop:
            if key_pressed():
                stop = True
            else:
                pyautogui.moveTo(789, 1762)
                pyautogui.click()
                print("Clicked at (789, 1762).")
                # Brief pause to allow for interruption
                elapsed = 0.0
                total_delay = 0.2  # 200 ms pause
                while elapsed < total_delay:
                    if key_pressed():
                        stop = True
                        break
                    time.sleep(0.1)
                    elapsed += 0.1

        # Next, click n times at (646, 2232)
        for i in range(n):
            if stop:
                break
            if key_pressed():
                stop = True
                break
            pyautogui.moveTo(646, 2232)
            pyautogui.click()
            # click again to ensure it registers
            time.sleep(2)  # slight delay to ensure click registers
            pyautogui.click()
            print(f"Clicked at (646, 2232) ({i+1}/{n}).")
            # Brief pause between clicks to check for key press
            elapsed = 0.0
            total_delay = 0.2  # 200 ms pause
            while elapsed < total_delay:
                if key_pressed():
                    stop = True
                    break
                time.sleep(3)
                elapsed += 3

        if not stop and n == 0:
            print("No clicks requested at (646, 2232). Sequence complete.")
        elif not stop:
            print("Completed all clicks. Sequence complete.")
    finally:
        # Restore terminal settings no matter how we exit
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print("Exiting.")


if __name__ == "__main__":
    """
    Dependencies:
      pip install pyautogui

    On macOS:
      • Grant “Accessibility” permissions to your Python environment under
        System Preferences → Security & Privacy → Privacy → Accessibility.

    Usage:
      python3 click_sequence.py
    """
    main()
