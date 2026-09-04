from flask import Flask, jsonify, request, send_from_directory
import chess
from pathlib import Path

from bot import read_positions, write_legal_moves, write_positions


FRONTEND_DIRECTORY = Path(__file__).resolve().parent / "frontend"
app = Flask(__name__, static_folder=FRONTEND_DIRECTORY, static_url_path="/static")
board = chess.Board()
last_move = None
history = []


def load_saved_board():
    global last_move, history
    try:
        saved_positions = read_positions()
        saved_fen = saved_positions.get("fen")
        if saved_fen:
            board.set_fen(saved_fen)
        last_move = saved_positions.get("last_move")
        history = saved_positions.get("history", [])
    except (OSError, ValueError, TypeError):
        pass


def board_status():
    if board.is_checkmate():
        return "checkmate"
    if board.is_stalemate():
        return "stalemate"
    if board.is_insufficient_material() or board.can_claim_fifty_moves() or board.can_claim_threefold_repetition():
        return "draw"
    if board.is_check():
        return "check"
    return "ongoing"


def piece_identifier(name, piece_number, piece_count):
    if name == "king" or (name == "queen" and piece_count == 1):
        return name
    return f"{name}{piece_number}"


def legal_moves_payload():
    moves = {}
    for move in board.legal_moves:
        from_square = chess.square_name(move.from_square)
        moves.setdefault(from_square, []).append(chess.square_name(move.to_square))
    for destinations in moves.values():
        destinations.sort()
    return moves


def save_legal_moves():
    write_legal_moves({
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "moves": legal_moves_payload(),
    })


def state_payload():
    positions = {"white": [], "black": [], "last_move": last_move}
    piece_numbers = {"white": {}, "black": {}}
    for square, piece in board.piece_map().items():
        color = "white" if piece.color == chess.WHITE else "black"
        piece_type = chess.piece_name(piece.piece_type)
        piece_numbers[color].setdefault(piece_type, []).append(square)

    for color in ("white", "black"):
        for piece_type, squares in piece_numbers[color].items():
            for piece_number, square in enumerate(sorted(squares), start=1):
                positions[color].append(
                    f"{piece_identifier(piece_type, piece_number, len(squares))}-{chess.square_name(square)}"
                )
        positions[color].sort(key=lambda piece: chess.parse_square(piece.rsplit("-", 1)[1]))

    state = {
        "fen": board.fen(),
        "turn": "white" if board.turn == chess.WHITE else "black",
        "status": board_status(),
        **positions,
    }
    state["legal_moves"] = legal_moves_payload()
    return state


@app.get("/")
def index():
    return send_from_directory(FRONTEND_DIRECTORY, "index.html")


@app.get("/api/state")
def get_state():
    return jsonify(state_payload())


@app.post("/api/move")
def make_move():
    global last_move
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify(error="invalid request"), 400

    from_square = data.get("from")
    to_square = data.get("to")
    promotion = data.get("promotion")
    if not isinstance(from_square, str) or not isinstance(to_square, str):
        return jsonify(error="from and to are required"), 400
    if promotion is not None and promotion not in {"q", "r", "b", "n"}:
        return jsonify(error="invalid promotion"), 400

    try:
        move = chess.Move.from_uci(from_square + to_square + (promotion or ""))
    except ValueError:
        return jsonify(error="invalid move"), 400

    if move not in board.legal_moves:
        return jsonify(error="illegal move"), 400

    moving_piece = board.piece_at(move.from_square)
    moving_piece_type = chess.piece_name(moving_piece.piece_type)
    same_type_squares = sorted(
        square
        for square, piece in board.piece_map().items()
        if piece.color == moving_piece.color and chess.piece_name(piece.piece_type) == moving_piece_type
    )
    moving_piece_name = piece_identifier(
        moving_piece_type,
        same_type_squares.index(move.from_square) + 1,
        len(same_type_squares),
    )
    history.append({"fen": board.fen(), "last_move": last_move})
    board.push(move)
    last_move = {
        "from": from_square,
        "to": to_square,
        "piece": moving_piece_name,
        "color": "white" if moving_piece.color == chess.WHITE else "black",
    }
    state = state_payload()
    state["history"] = history
    write_positions(state)
    save_legal_moves()
    return jsonify(state)


@app.post("/api/undo")
def undo_move():
    global last_move
    if not history:
        return jsonify(error="Nothing to undo"), 400

    previous_state = history.pop()
    board.set_fen(previous_state["fen"])
    last_move = previous_state.get("last_move")
    state = state_payload()
    state["history"] = history
    write_positions(state)
    save_legal_moves()
    return jsonify(state)


@app.post("/api/reset")
def reset_game():
    global last_move, history
    board.reset()
    last_move = None
    history = []
    state = state_payload()
    state["history"] = history
    write_positions(state)
    save_legal_moves()
    return jsonify(state)


load_saved_board()
save_legal_moves()


if __name__ == "__main__":
    app.run(debug=True)