import numpy as np

from palette import DEFAULT_PALETTE

CELL = 30
PIECE_CELLS = {
    "I": [(0, 1), (1, 1), (2, 1), (3, 1)],
    "O": [(1, 0), (2, 0), (1, 1), (2, 1)],
    "T": [(1, 0), (0, 1), (1, 1), (2, 1)],
    "L": [(2, 0), (0, 1), (1, 1), (2, 1)],
    "J": [(0, 0), (0, 1), (1, 1), (2, 1)],
    "S": [(1, 0), (2, 0), (0, 1), (1, 1)],
    "Z": [(0, 0), (1, 0), (1, 1), (2, 1)],
}


def paint(img, x, y, letter, cell=CELL):
    for dx, dy in PIECE_CELLS[letter]:
        x0, y0 = x + dx * cell, y + dy * cell
        img[y0 + 1:y0 + cell - 1, x0 + 1:x0 + cell - 1] = DEFAULT_PALETTE[letter]


def make_frame(width=1000, height=800, cell=CELL, board_x=300, board_y=60, upcoming="TOZLS", hold="J", meter=0):
    img = np.full((height, width, 3), 70, dtype=np.uint8)
    img[:, :] = np.linspace(40, 110, width, dtype=np.uint8)[None, :, None]
    img[board_y:board_y + 20 * cell, board_x:board_x + 10 * cell] = 8
    mx0, mx1 = board_x - int(0.8 * cell), board_x - int(0.2 * cell)
    img[board_y:board_y + 20 * cell, mx0 - 4:board_x] = 220
    img[board_y:board_y + 20 * cell, mx0:mx1] = 0
    if meter:
        img[board_y + (20 - meter) * cell:board_y + 20 * cell, mx0:mx1] = (210, 70, 70)
    nx = board_x + 10 * cell + 2 * cell
    for i, letter in enumerate(upcoming):
        img[board_y + i * 3 * cell:board_y + (i + 1) * 3 * cell, nx - cell // 2:nx + 4 * cell + cell // 2] = 5
        paint(img, nx, board_y + i * 3 * cell + cell // 2, letter, cell)
    hx = board_x - 5 * cell
    img[board_y:board_y + 3 * cell, hx - cell // 2:hx + 4 * cell + cell // 2] = 5
    if hold:
        paint(img, hx, board_y + cell // 2, hold, cell)
    return img, (board_x, board_y, board_x + 10 * cell, board_y + 20 * cell)
