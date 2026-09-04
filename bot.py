#todo: make a chess engine here.

import json
from pathlib import Path


POSITIONS_PATH = Path(__file__).with_name("frontend") / "positions.json"
LEGAL_MOVES_PATH = Path(__file__).with_name("frontend") / "legalmoves.json"


def read_positions():
    with POSITIONS_PATH.open("r", encoding="utf-8") as positions_file:
        return json.load(positions_file)


def write_positions(positions):
    with POSITIONS_PATH.open("w", encoding="utf-8") as positions_file:
        json.dump(positions, positions_file, indent=4)
        positions_file.write("\n")


def read_legal_moves():
    with LEGAL_MOVES_PATH.open("r", encoding="utf-8") as legal_moves_file:
        return json.load(legal_moves_file)


def write_legal_moves(legal_moves):
    with LEGAL_MOVES_PATH.open("w", encoding="utf-8") as legal_moves_file:
        json.dump(legal_moves, legal_moves_file, indent=4)
        legal_moves_file.write("\n")