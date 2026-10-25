from palette import DEFAULT_PALETTE, classify, is_gray


MAX_RISE = 8
MAX_SEEN_RISE = 12
SPECK_MIN_ROW = 12
SPECK_MAX_SIZE = 3
MAX_DROP = 4
GARBAGE_ROW_CELLS = 8
FULL_ROW = (1 << 10) - 1


def raise_rows(rows, count, hole):
    garbage = FULL_ROW & ~(1 << hole)
    return [garbage] * count + list(rows[:len(rows) - count])


def drop_rows(rows, count):
    return list(rows[count:]) + [0] * count


def raise_with(rows, new_rows):
    return list(new_rows) + list(rows[:len(rows) - len(new_rows)])


def garbage_like(row):
    return bin(row).count("1") in (GARBAGE_ROW_CELLS, 9)


def best_candidate(stack, expected, hole, learn=False):
    best = (bit_difference(stack, expected), expected, False)
    for k in range(1, MAX_DROP + 1):
        if bin(expected[k - 1]).count("1") < GARBAGE_ROW_CELLS:
            break
        cand = drop_rows(expected, k)
        diff = bit_difference(stack, cand)
        if diff < best[0]:
            best = (diff, cand, True)
    if hole is not None:
        for k in range(1, MAX_RISE + 1):
            cand = raise_rows(expected, k, hole)
            diff = bit_difference(stack, cand)
            if diff < best[0]:
                best = (diff, cand, True)
    if learn:
        for k in range(1, MAX_SEEN_RISE + 1):
            if not garbage_like(stack[k - 1]):
                break
            cand = raise_with(expected, stack[:k])
            diff = bit_difference(stack, cand)
            if diff < best[0]:
                best = (diff, cand, True)
    return best


def drop_specks(rows):
    cells = {(r, c) for r in range(len(rows)) for c in range(10) if (rows[r] >> c) & 1}
    seen = set()
    out = list(rows)
    for start in sorted(cells):
        if start in seen:
            continue
        group, todo = {start}, [start]
        while todo:
            r, c = todo.pop()
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    nxt = (r + dr, c + dc)
                    if nxt in cells and nxt not in group:
                        group.add(nxt)
                        todo.append(nxt)
        seen |= group
        if len(group) <= SPECK_MAX_SIZE and min(r for r, _ in group) >= SPECK_MIN_ROW:
            for r, c in group:
                out[r] &= ~(1 << c)
    return out


def clear_cells(rows, cells):
    out = list(rows)
    for r, c in cells:
        out[r] &= ~(1 << c)
    return out


def extra_cells(rows, reference):
    return {(r, c) for r in range(len(reference)) for c in range(10)
            if (rows[r] >> c) & 1 and not (reference[r] >> c) & 1}


def count_cells(rows):
    return sum(bin(r).count("1") for r in rows)


def count_gray(colors):
    return sum(1 for color in colors.values() if is_gray(color))


def bit_difference(a, b):
    return sum(bin(x ^ y).count("1") for x, y in zip(a, b))


MIN_GARBAGE_ROW = 8


def drop_stray_gray(rows, colors):
    per_row = {}
    for (r, c), color in colors.items():
        if is_gray(color):
            per_row.setdefault(r, set()).add(c)
    stray = [(r, c) for r, cs in per_row.items() if len(cs) < MIN_GARBAGE_ROW for c in cs]
    if not stray:
        return rows, colors
    out = list(rows)
    kept = dict(colors)
    for r, c in stray:
        out[r] &= ~(1 << c)
        kept.pop((r, c), None)
    return out, kept


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
