import re
import platform
import threading
import time
import cv2
import numpy as np
import pytesseract

try:
    from mss import mss
except ImportError:
    raise ImportError("Please install mss: pip install mss")

# On macOS, handle Retina scaling by querying AppKit
SCALE = 1.0
if platform.system() == "Darwin":
    try:
        from AppKit import NSScreen
        #SCALE = float(NSScreen.mainScreen().backingScaleFactor())
    except Exception:
        print("Warning: could not detect Retina scale factor. Defaulting to 1.0.")
        SCALE = 1.0

# Regex to match:
#  • Optional leading '$'
#  • Digits and commas (e.g. "1,234" or "$12,345")
#  • Optionally a decimal portion (e.g. "$1,234.56")
number_pattern = re.compile(r"^\$?[\d,]+(?:\.\d+)?$")

def capture_and_highlight_numbers(bbox_logical):
    """
    bbox_logical: dict with keys 'left','top','width','height' in logical points.
    We multiply by SCALE (on macOS Retina) to get actual device pixels.
    Returns a BGR image with:
      - a red border around the entire ROI
      - green boxes around any numeric value > 10,000
    """
    # Convert logical‐point coordinates to device pixels
    bbox_pixels = {
        "left": int(bbox_logical["left"] * SCALE),
        "top": int(bbox_logical["top"] * SCALE),
        "width": int(bbox_logical["width"] * SCALE),
        "height": int(bbox_logical["height"] * SCALE),
    }

    with mss() as sct:
        screenshot = sct.grab(bbox_pixels)
        # mss returns an array in RGB + alpha. Convert to BGR for OpenCV.
        img = np.array(screenshot)[:, :, :3]
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    # Draw a red border around the entire captured area
    ph, pw = img.shape[:2]
    cv2.rectangle(img, (0, 0), (pw - 1, ph - 1), (0, 0, 255), 2)

    # Run Tesseract OCR and get word‐level data
    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    n_boxes = len(data["text"])

    for i in range(n_boxes):
        raw_text = data["text"][i].strip()
        conf = int(data["conf"][i])
        # Only proceed if the OCR text matches our number pattern and confidence > 0
        if number_pattern.match(raw_text) and conf > 0:
            # Strip '$' and commas, then parse to float
            numeric_text = raw_text.replace("$", "").replace(",", "")
            try:
                value = float(numeric_text)
            except ValueError:
                continue  # if parsing fails, skip

            # Draw green box only if the numeric value is strictly greater than 10,000
            if value > 10000:
                x = data["left"][i]
                y = data["top"][i]
                w = data["width"][i]
                h = data["height"][i]
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)

    return img


def main():
    # Define the region to scan in logical points (e.g., a 350×500 box at (500, 300)).
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

    # Determine window size in pixels so the display matches exactly what we capture
    window_w = int(width_pt * SCALE)
    window_h = int(height_pt * SCALE)

    win_name = "macOS Live Scan: Red Border + >10K Number Boxes"
    cv2.namedWindow(win_name, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(win_name, window_w, window_h)

    print(
        f"Starting continuous scan.\n"
        f"Logical region = ({left_pt}, {top_pt}), size = {width_pt}×{height_pt} points.\n"
        f"Retina SCALE = {SCALE:.2f}, grabbing {window_w}×{window_h} pixels.\n"
        f"Highlighting only numbers > 10,000."
    )
    print("Press 'q' or ESC to quit.")

    # Shared state between threads
    annotated_frame = {"img": None}
    frame_lock = threading.Lock()
    stop_event = threading.Event()

    def ocr_thread():
        """Continuously captures & processes frames, writing to annotated_frame."""
        while not stop_event.is_set():
            processed = capture_and_highlight_numbers(bbox)
            with frame_lock:
                annotated_frame["img"] = processed
            # No explicit sleep: capture_and_highlight itself takes time (~100ms+).
        # Thread will exit when stop_event is set

    # Start OCR thread
    t = threading.Thread(target=ocr_thread, daemon=True)
    t.start()

    # Main display loop
    while True:
        with frame_lock:
            frame = annotated_frame["img"].copy() if annotated_frame["img"] is not None else None

        if frame is not None:
            cv2.imshow(win_name, frame)

        key = cv2.waitKey(30) & 0xFF
        if key == ord("q") or key == 27:  # 'q' or ESC
            stop_event.set()
            break

    t.join()
    cv2.destroyAllWindows()


if __name__ == "__main__":
    """
    Dependencies (install via pip):
      pip install mss opencv-python pytesseract numpy pyobjc-framework-AppKit

    On macOS, also ensure:
      • Terminal (or your Python interpreter) has Screen Recording permission under
        System Preferences → Security & Privacy → Screen Recording.
      • Tesseract is installed (e.g. `brew install tesseract`).

    Then run:
      python3 threaded_live_scan.py
    """
    main()
