import re
import platform
import time
import logging

import cv2
import numpy as np
import pyautogui
import pytesseract
from mss import mss

SCALE = 1.0
if platform.system() == "Darwin":
    try:
        from AppKit import NSScreen
    except Exception:
        logging.warning("Could not detect Retina scale factor; defaulting to 1.0")
        SCALE = 1.0

number_pattern = re.compile(r"^\$?[\d,]+(?:\.\d+)?$")


def capture_and_highlight_numbers(bbox_logical):
    FOUND_OVER_THRESHOLD = False

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

    ph, pw = img.shape[:2]
    cv2.rectangle(img, (0, 0), (pw - 1, ph - 1), (0, 0, 255), 2)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    n_boxes = len(data["text"])
    count_highlights = 0

    logging.info(f"Found {n_boxes} text boxes in the image")
    if n_boxes == 0:
        logging.warning("No text boxes found; exiting function")
        return img

    for i in range(n_boxes):
        raw_text = data["text"][i].strip()
        conf = int(data["conf"][i])
        if number_pattern.match(raw_text) and conf > 0:
            numeric_text = raw_text.replace("$", "").replace(",", "")
            try:
                value = float(numeric_text)
            except ValueError:
                continue

            if value > 10000:
                FOUND_OVER_THRESHOLD = True
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                pyautogui.moveTo(
                    bbox_logical["left"] + x // 2 + w // 4 ,
                    bbox_logical["top"] + y // 2 + h // 4 + 40,
                )
                print("box coordinates:", x, y, w, h)
                print(
                    f"Moving cursor to: ({bbox_logical['left'] + x / 2}, {bbox_logical['top'] + y / 2})"
                )
                pyautogui.click()
                time.sleep(1.5)  # Small delay to ensure cursor moves smoothly
                static_clicker()
                break
                count_highlights += 1
    if not FOUND_OVER_THRESHOLD:
        pyautogui.scroll(-10000)
        time.sleep(0.2)

    logging.info(f"Found {count_highlights} numbers > 10000")
    return img


def static_clicker():
    click_positions = [
        (662, 701),
        (650, 460),
        (673, 789),
        (736, 750),
        (667, 811),
    ]
    delays_between_clicks = [1, 1, 3, 1, 1]

    clicks = zip(click_positions, delays_between_clicks)
    print("Starting static clicker. Press Ctrl+C to stop.")
    try:
        for (x, y), delay in clicks:
            pyautogui.moveTo(x, y)
            pyautogui.click()
            print(f"Clicked at ({x}, {y}).")
            time.sleep(delay)
    except KeyboardInterrupt:
        print("\nStatic clicker stopped.")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    left_pt = 500
    top_pt = 200
    width_pt = 350
    height_pt = 600

    bbox = {
        "left": left_pt,
        "top": top_pt,
        "width": width_pt,
        "height": height_pt,
    }

    window_w = int(width_pt * SCALE)
    window_h = int(height_pt * SCALE)

    win_name = "Live Scan: Red Border + >10K Boxes"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, window_w, window_h)

    logging.info(
        f"Starting scan. Logical region=({left_pt},{top_pt}), size={width_pt}×{height_pt}. "
        f"Scale={SCALE:.2f}, grabbing {window_w}×{window_h} pixels."
    )
    logging.info("Press 'q' or ESC to quit.")
    # 5 second countdown before starting
    for i in range(5, 0, -1):
        logging.info(f"Starting in {i} seconds...")
        time.sleep(1)

    while True:
        start_time = time.time()
        logging.info("Capturing and processing frame")
        frame = capture_and_highlight_numbers(bbox)
        cv2.imshow(win_name, frame)

        elapsed = time.time() - start_time
        logging.info(f"Frame processed in {elapsed:.2f} seconds")

        key = cv2.waitKey(30) & 0xFF
        if key == ord("q") or key == 27:
            logging.info("Exit key pressed; quitting")
            break

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
