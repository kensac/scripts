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

# List of (x, y) coordinates to click, in order.
click_positions = [
    (600, 350),
    (665, 725),
    (656, 483),
    (673, 789),
    (736, 750),
    (667, 811),
]

# List of delays (in seconds) to wait AFTER each click, before moving to the next.
delays_between_clicks = [3, 3, 3, 3, 3]  # Modify each entry as needed


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
    # Save original terminal settings so we can restore them later
    fd = sys.stdin.fileno()
    old_settings = termios.tcgetattr(fd)
    tty.setcbreak(fd)  # Set terminal to cbreak mode (no Enter needed)

    stop = False
    print("Starting continuous click loop.")
    print("Press any key to stop at any time.")
    print("Move your mouse away from the target coordinates if needed.")
    # Optional countdown before starting
    for i in range(3, 0, -1):
        print(f"  Clicking begins in {i}...")
        time.sleep(1)

    try:
        while not stop:
            for idx, (x, y) in enumerate(click_positions):
                # Before each click, check if a key was pressed
                if key_pressed():
                    stop = True
                    break

                pyautogui.moveTo(x, y)
                pyautogui.click()
                print(f"Clicked at ({x}, {y}).")

                # Delay after this click, if defined
                if idx < len(delays_between_clicks):
                    total_delay = delays_between_clicks[idx]
                    elapsed = 0.0
                    # Break the delay into 0.1s intervals to check for key presses
                    while elapsed < total_delay:
                        if key_pressed():
                            stop = True
                            break
                        time.sleep(0.1)
                        elapsed += 0.1
                    if stop:
                        break
            # If we finished one full sequence without stopping, loop again
    finally:
        # Restore terminal settings no matter how we exit
        termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    print("Click loop stopped. Exiting.")


if __name__ == "__main__":
    """
    Dependencies:
      pip install pyautogui

    On macOS:
      • Grant “Accessibility” permissions to your Python environment under
        System Preferences → Security & Privacy → Privacy → Accessibility.

    Then run:
      python3 click_loop_until_key.py
    """
    main()
