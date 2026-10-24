from palette import DEFAULT_PALETTE, classify, is_gray


def count_cells(rows):
    return sum(bin(r).count("1") for r in rows)


def count_gray(colors):
    return sum(1 for color in colors.values() if is_gray(color))


def bit_difference(a, b):
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


def garbage_hole(colors):
    for r in range(20):
        gray = {c for (rr, c), color in colors.items() if rr == r and is_gray(color)}
        if len(gray) == 9:
            return (set(range(10)) - gray).pop()
    return None


def strip_active(rows, colors, current):
    if current is None:
        return rows
    cells = [rc for rc, color in colors.items() if classify(color, DEFAULT_PALETTE) == current]
    cells.sort(key=lambda rc: -rc[0])
    top = cells[:4]
    if len(top) < 4:
        return rows
    rs = [r for r, _ in top]
    cs = [c for _, c in top]
    if max(rs) - min(rs) > 3 or max(cs) - min(cs) > 3:
        return rows
    for r, c in top:
        if r - 1 >= 0 and (rows[r - 1] >> c) & 1 and (r - 1, c) not in top:
            return rows
    out = list(rows)
    for r, c in top:
        out[r] &= ~(1 << c)
    return out


def strip_floating_top(rows):
    out = list(rows)
    for r in (19, 18):
        for c in range(10):
            if (out[r] >> c) & 1 and not (out[r - 1] >> c) & 1:
                out[r] &= ~(1 << c)
    return out


def ascii_board(rows):
    return "\n".join(
        "".join("#" if (rows[r] >> c) & 1 else "." for c in range(10))
        for r in range(len(rows) - 1, -1, -1))
