const pieceSymbols = {
    white: { pawn: '♙', rook: '♖', knight: '♘', bishop: '♗', queen: '♕', king: '♔' },
    black: { pawn: '♟', rook: '♜', knight: '♞', bishop: '♝', queen: '♛', king: '♚' }
};

const squares = document.querySelectorAll('.blocks');
const messageElement = document.querySelector('#message');
const undoButton = document.querySelector('#undoButton');
const resetButton = document.querySelector('#resetButton');
let positions = { white: [], black: [], last_move: null };
let selectedSquare = null;

function showMessage(message) {
    if (messageElement) messageElement.textContent = message;
}

function parsePiece(piece) {
    const [name, square] = piece.split('-');
    const type = name.replace(/\d+$/, '');
    return { name, type, square };
}

function pieceAt(squareName) {
    for (const color of ['white', 'black']) {
        const piece = positions[color].find((entry) => parsePiece(entry).square === squareName);
        if (piece) return { color, ...parsePiece(piece) };
    }
    return null;
}

function renderBoard() {
    squares.forEach((square, index) => {
        const piece = pieceAt(square.id);

        square.className = `square ${(Math.floor(index / 8) + index % 8) % 2 === 0 ? 'light' : 'dark'}`;
        square.setAttribute('aria-label', square.id);
        square.textContent = piece ? pieceSymbols[piece.color][piece.type] : '';
        square.draggable = Boolean(piece);
        square.classList.toggle('occupied', Boolean(piece));
        square.classList.toggle('selected', square.id === selectedSquare);
        square.classList.toggle('legal-move', Boolean(selectedSquare &&
            positions.legal_moves?.[selectedSquare]?.includes(square.id)));
    });

    const turn = positions.turn === 'white' ? 'White' : 'Black';
    const status = positions.status || 'ongoing';
    showMessage(status === 'ongoing' || status === 'check'
        ? `${turn} to move${status === 'check' ? ' - check' : ''}`
        : status);
}

function selectSquare(squareName) {
    const piece = pieceAt(squareName);
    const selectedMoves = positions.legal_moves?.[selectedSquare] || [];
    const pieceMoves = positions.legal_moves?.[squareName] || [];

    if (selectedSquare && selectedMoves.includes(squareName)) {
        movePiece(selectedSquare, squareName);
        selectedSquare = null;
    } else if (piece && piece.color === positions.turn && pieceMoves.length) {
        selectedSquare = squareName;
    } else {
        selectedSquare = null;
    }
    renderBoard();
}

async function movePiece(from, to) {
    if (!pieceAt(from) || from === to) return;

    let promotion;
    const movingPiece = pieceAt(from);
    const targetRank = to[1];
    if (movingPiece.type === 'pawn' && (targetRank === '1' || targetRank === '8')) {
        promotion = (window.prompt('Promote to: q, r, b, or n', 'q') || 'q').toLowerCase();
        if (!['q', 'r', 'b', 'n'].includes(promotion)) promotion = 'q';
    }

    try {
        const response = await fetch('/api/move', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ from, to, ...(promotion ? { promotion } : {}) })
        });
        const result = await response.json();
            if (!response.ok) throw new Error(result.error || 'illegal move');
            selectedSquare = null;
        positions = result;
        renderBoard();
    } catch (error) {
        showMessage(error.message);
    }
}

async function requestGameAction(endpoint) {
    undoButton.disabled = true;
    resetButton.disabled = true;
    try {
        const response = await fetch(endpoint, { method: 'POST' });
        const result = await response.json();
        if (!response.ok) throw new Error(result.error || 'Could not update game');
        positions = result;
            selectedSquare = null;
        renderBoard();
    } catch (error) {
        showMessage(error.message);
    } finally {
        undoButton.disabled = false;
        resetButton.disabled = false;
    }
}

squares.forEach((square) => {
    square.addEventListener('dragstart', (event) => {
        event.dataTransfer.setData('text/plain', square.id);
        event.dataTransfer.effectAllowed = 'move';
        square.classList.add('dragging');
    });

    square.addEventListener('dragend', () => {
        square.classList.remove('dragging');
        squares.forEach((item) => item.classList.remove('drop-target'));
    });

        square.addEventListener('click', () => selectSquare(square.id));
        square.addEventListener('dragover', (event) => {
        if (event.dataTransfer.types.includes('text/plain')) {
            event.preventDefault();
            square.classList.add('drop-target');
        }
    });

    square.addEventListener('dragleave', () => square.classList.remove('drop-target'));
    square.addEventListener('drop', (event) => {
        event.preventDefault();
        movePiece(event.dataTransfer.getData('text/plain'), square.id);
    });
});

undoButton.addEventListener('click', () => requestGameAction('/api/undo'));
resetButton.addEventListener('click', () => requestGameAction('/api/reset'));

fetch('/api/state')
    .then((response) => {
        if (!response.ok) throw new Error('Could not load game state');
        return response.json();
    })
    .then((state) => {
        positions = state;
        renderBoard();
    })
    .catch((error) => {
        renderBoard();
        showMessage(error.message);
    });
