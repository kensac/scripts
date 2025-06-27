import re
import time
import logging
from dataclasses import dataclass
from typing import Sequence, Tuple, Union

import cv2
import numpy as np
import pyautogui
import pytesseract
from mss import mss

# ——— Configuration ———
NUMBER_PATTERN = re.compile(r"^\$?[\d,]+(?:\.\d+)?$")
THRESHOLD = 50_000


@dataclass(frozen=True)
class ClickAction:
    pos: Tuple[int, int]
    delay: float = 0.0


@dataclass(frozen=True)
class TypeAction:
    text: str
    delay: float = 0.0


@dataclass(frozen=True)
class ScrollAction:
    amount: int  # positive scroll up, negative scroll down
    delay: float = 0.0


action_sequences = {
    "buy_gems": [
        ClickAction((477, 300), 1),  # open WR
        ClickAction((565, 570), 1),  # open Diamonds
        ClickAction((669, 134), 1),  # buy menu
        ClickAction((465, 249), 1),  # max button
        ClickAction((582, 333), 1),  # buy gems
        ClickAction((581, 708), 1),  # confirm buy
        ClickAction((713, 137), 1),  # process gems
        ClickAction((594, 550), 185),  # batch process & wait
        ClickAction((458, 186), 3),  # back on WR after process
    ],
    "exit_wr": [
        ClickAction((438, 136), 1),  # back on WR Inventory
        ClickAction((444, 148), 1),  # back on WR to exit
    ],
    "open_WB": [
        ClickAction((477, 551), 3),  # open WB
        ClickAction((583, 765), 1),  # enter menu
    ],
    "create_jewels": [
        ClickAction((571, 678), 3),  # enter WD
        ClickAction((598, 541), 1),  # click create
        ClickAction((655, 184), 1),  # Solitaire
        ClickAction((451, 658), 1),  # sort by value
        ClickAction((582, 463), 1),  # add stone button
        ClickAction((478, 762), 1),  # select max value stone
        ClickAction((730, 144), 1),  # click tick
        ClickAction((471, 199), 1),  # click text area
        TypeAction("1", 1),  # type quantity
        ClickAction((661, 739), 5),  # click create
        ClickAction((611, 702), 1),  # click continue
    ],
    "Jewel Sell": [
        ClickAction((592, 749), 1),  # Click view inventory
        ClickAction((606, 476), 10),  # Click Immediate sell
        ClickAction((575, 732), 1),  # Accept Offer
        ClickAction((446, 149), 1),  # back to WB Menu
    ],
    "Exit WD Menu": [
        ClickAction((444, 152), 1),  # back to main menu
    ],
    "sell_items": [
        ClickAction((581, 551), 1),  # enter Sell
        ClickAction((695, 281), 1),  # select all
        ClickAction((722, 763), 1),  # Sell
        ClickAction((623, 740), 2),  # confirm sell
        ClickAction((592, 528), 1),  # exit confirm sell
        ClickAction((436, 142), 1),  # exit sell
    ],
    "test_scroll": [
        ScrollAction(-1000, 100),  # scroll down list
    ],
}

Actions = Union[ClickAction, TypeAction, ScrollAction]


def initialize_logger():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def perform_sequence(actions: Sequence[Actions]):
    for act in actions:
        if isinstance(act, ClickAction):
            pyautogui.moveTo(*act.pos)
            pyautogui.click()
        elif isinstance(act, ScrollAction):
            scroll_left = act.amount
            while scroll_left != 0:
                step = min(100, abs(scroll_left))
                if scroll_left < 0:
                    pyautogui.scroll(-step)
                    scroll_left += step
                else:
                    pyautogui.scroll(step)
                    scroll_left -= step

        else:  # TypeAction
            pyautogui.write(act.text)

        remaining = act.delay
        while remaining > 0:
            interval = min(5, remaining)
            logging.info(f"Waiting {interval}s (remaining {remaining}s)")
            time.sleep(interval)
            remaining -= interval


def count_large_numbers_on_screen(threshold: float = THRESHOLD) -> int:
    bbox = {"left": 430, "top": 80, "width": 400, "height": 700}
    with mss() as sct:
        img = np.array(sct.grab(bbox))[:, :, :3]
        img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)

    data = pytesseract.image_to_data(img, output_type=pytesseract.Output.DICT)
    count = 0
    for text, conf in zip(data["text"], data["conf"]):
        if int(conf or 0) <= 0:
            continue
        cleaned = text.strip().lstrip("$").replace(",", "")
        if NUMBER_PATTERN.match(cleaned) and float(cleaned) > threshold:
            count += 1
    logging.info(f"Detected {count} values over {threshold}")
    return count


class Automator:
    MIN_JEWEL_INTERVAL = 300  # seconds

    def __init__(self):
        # stamp allowing immediate create_jewels on first run
        self._last_jewel_time = time.time() - self.MIN_JEWEL_INTERVAL

    def _ensure_jewel_interval(self):
        elapsed = time.time() - self._last_jewel_time
        if elapsed < self.MIN_JEWEL_INTERVAL:
            wait = self.MIN_JEWEL_INTERVAL - elapsed
            while wait > 0:
                interval = min(5, wait)
                logging.info(
                    f"Waiting {interval}s before creating jewels (remaining {wait}s)"
                )
                time.sleep(interval)
                wait -= interval

    def run_cycle(self):
        perform_sequence(action_sequences["buy_gems"])
        gem_over_threshold = count_large_numbers_on_screen()
        perform_sequence(action_sequences["exit_wr"])

        perform_sequence(action_sequences["open_WB"])
        for _ in range(max(4, gem_over_threshold)):
            perform_sequence(action_sequences["create_jewels"])
            perform_sequence(action_sequences["Jewel Sell"])
        perform_sequence(action_sequences["Exit WD Menu"])

        perform_sequence(action_sequences["sell_items"])
        time.sleep(1)
        logging.info("Cycle complete")

    def start(self, initial_delay: float = 5.0):
        logging.info(f"Starting in {initial_delay}s...")
        time.sleep(initial_delay)
        while True:
            self.run_cycle()


if __name__ == "__main__":
    initialize_logger()
    Automator().start()
