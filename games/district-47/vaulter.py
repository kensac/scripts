import re
import time
import logging

import cv2
import numpy as np
import pyautogui
import pytesseract
from mss import mss

NUMBER_PATTERN = r"^\$?[\d,]+(?:\.\d+)?$"
THRESHOLD = 10000


def initialize_logger():
    logging.basicConfig(
        level=logging.DEBUG,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        # send to terminal
    )


def perform_click_sequence(coordinates, delays):
    for (x, y), delay in zip(coordinates, delays):
        pyautogui.moveTo(x, y)
        pyautogui.click()
        logging.info(f"Clicked at ({x}, {y}); sleeping for {delay} sec")
        time.sleep(delay)


def long_sleep(duration):
    logging.info(f"Sleeping for {duration} seconds")
    for i in range(int(duration)):
        logging.info(f"{i + 1}/{int(duration)} seconds elapsed")
        time.sleep(1)


def count_large_numbers_on_screen():
    SCALE = 1.0
    left_pt = 500
    top_pt = 200
    width_pt = 350
    height_pt = 600

    bbox_logical = {
        "left": left_pt,
        "top": top_pt,
        "width": width_pt,
        "height": height_pt,
    }
    bbox_pixels = {
        "left": int(bbox_logical["left"] * SCALE),
        "top": int(bbox_logical["top"] * SCALE),
        "width": int(bbox_logical["width"] * SCALE),
        "height": int(bbox_logical["height"] * SCALE),
    }

    with mss() as sct:
        screenshot = sct.grab(bbox_pixels)
        img = np.array(screenshot)[:, :, :3]
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    count = 0
    for raw_text, conf in zip(data["text"], data["conf"]):
        text = raw_text.strip()
        try:
            conf_val = int(conf)
        except (ValueError, TypeError):
            continue
        if conf_val <= 0:
            continue

        if re.match(NUMBER_PATTERN, text):
            try:
                value = float(text.replace("$", "").replace(",", ""))
            except ValueError:
                continue
            if value > THRESHOLD:
                count += 1
    logging.info(f"Found {count} instances > {THRESHOLD}")
    return count


def main():

    # First click sequence
    seq1_coords = [
        (559, 422),
        (727, 456),
        (587, 416),
        (706, 269),
        (763, 413),
        (713, 762),
        (678, 751),
        (668, 783),
        (727, 456),
        (587, 416),
        (706, 269),
        (763, 413),
        (713, 762),
        (678, 751),
        (533, 192),
        (561, 333),
        (736, 643),
        (783, 175),
        (652, 598),
    ]
    seq1_delays = [3] * len(seq1_coords)  # 3 seconds delay for each click
    perform_click_sequence(seq1_coords, seq1_delays)

    # Long sleep before next step
    long_sleep(120.0)

    # Single click
    pyautogui.moveTo(661, 663)
    pyautogui.click()
    logging.info("Clicked at (661, 663)")

    time.sleep(5)  # Wait for 3 seconds

    # Count instances > 10000
    n = count_large_numbers_on_screen()
    time.sleep(3)  # Wait for 3 seconds after counting

    # Next click
    pyautogui.moveTo(759, 177)
    pyautogui.click()
    logging.info("Clicked at (759, 177)")
    time.sleep(3)  # Wait for 3 seconds
    for i in range(n):
        pyautogui.moveTo(647, 223)
        pyautogui.click()
        time.sleep(3)
        logging.info(f"Clicked at (647, 223) for instance {i + 1} of {n}")
    # Wait for 3 seconds
    time.sleep(3)

    seq2_coords = [
        (521, 177),
        (526, 193),
        (554, 594),
        (784, 317),
        (808, 802),
        (717, 789),
    ]
    seq2_delays = [3] * len(seq2_coords)  # 3 seconds delay for each click
    perform_click_sequence(seq2_coords, seq2_delays)

    # Long wait (10 seconds)
    long_sleep(10.0)

    # Final two clicks at the same coordinate
    final_coords = [(525, 191), (525, 191)]
    final_delays = [3, 3]  # 3 seconds delay for each click
    perform_click_sequence(final_coords, final_delays)

    logging.info("Automation sequence complete.")


if __name__ == "__main__":
    initialize_logger()
    # 5 seconds delay before starting
    logging.info("Starting automation sequence in 5 seconds...")
    time.sleep(5)
    main()
