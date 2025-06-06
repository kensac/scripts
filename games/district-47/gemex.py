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
    if len(coordinates) != len(delays):
        raise ValueError("Coordinates and delays must have the same length.")
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

DIAMOND = (706, 269)  # Diamond coordinates for reference
EMERALD = (686,330)
SAPPHIRE = (689, 390)

def main():
    mode = DIAMOND

    # First click sequence
    seq1_coords = [
        # cycle 1
        (559, 422),  # open gemex
        (727, 456),  # Trade Button
        (587, 416),  # Buy Gems
        mode,  # Diamond
        (763, 413),  # QTY
        (713, 762),  # Buy
        (678, 751),  # place order
        (664, 538),  # close error
        (535, 194),  # close app
        # cycle 2
        (559, 422),  # open gemex
        (727, 456),  # Trade Button
        (587, 416),  # Buy Gems
        mode,  # Diamond
        (763, 413),  # QTY
        (713, 762),  # Buy
        (678, 751),  # place order
        (664, 538),  # close error
        (535, 194),  # close app
        # cycle 3
        (559, 422),  # open gemex
        (727, 456),  # Trade Button
        (587, 416),  # Buy Gems
        mode,  # Diamond
        (763, 413),  # QTY
        (713, 762),  # Buy
        (678, 751),  # place order
        (664, 538),  # close error
        (535, 194),  # close app
        # process
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

    seq2_coords = [
        # wr loop
        (541, 228),  # Exit WR
        (519, 176),  # Actually exit WR
        (530, 194),  # who has 3 back buttons
        (557, 599),  # enter Sell
        # sell loop 1
        (756, 313),  # select all
        (806, 800),  # Sell
        (716, 785),  # confirm sell
        (716, 785),  # exit confirm sell
        # sell loop 2
        (756, 313),  # select all
        (806, 800),  # Sell
        (716, 785),  # confirm sell
        (716, 785),  # exit confirm sell
        # sell loop 3
        (756, 313),  # select all
        (806, 800),  # Sell
        (716, 785),  # confirm sell
        (716, 785),  # exit confirm sell
        # reset loop
        (527, 190),  # exit sell
    ]
    seq2_delays = [3, 3, 3, 3, # wr loop
                    3, 3, 10, 3,  # sell loop 1
                    3, 3, 10, 3,  # sell loop 2
                    3, 3, 10, 3,  # sell loop 3
                    3] # reset loop
    perform_click_sequence(seq2_coords, seq2_delays)
    # Wait for 3 seconds
    time.sleep(3)

    logging.info("Automation sequence complete.")


if __name__ == "__main__":
    initialize_logger()
    # 5 seconds delay before starting
    logging.info("Starting automation sequence in 5 seconds...")
    time.sleep(5)
    # run 3 times
    for _ in range(3):
        logging.info("Running automation sequence...")
        main()
