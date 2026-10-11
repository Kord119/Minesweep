import math

import cv2
import numpy as np

# Цвета цифр в BGR (как в классическом Сапёре)
DIGIT_COLORS_BGR = {
    1: (255, 0, 0),
    2: (0, 128, 0),
    3: (0, 0, 255),
    4: (128, 0, 0),
    5: (0, 0, 128),
    6: (128, 128, 0),
    7: (0, 0, 0),
    8: (128, 128, 128),
}


def classify_cell(cell):
    h, w = cell.shape[:2]
    if h < 8 or w < 8:
        return "closed"

    center = cell[h // 4:h - h // 4, w // 4:w - w // 4]
    px = center.reshape(-1, 3).astype(int)
    total = px.shape[0]

    red_m = (center[:, :, 2] > 150) & (center[:, :, 0] < 100) & (center[:, :, 1] < 100)
    black_m = (center[:, :, 0] < 80) & (center[:, :, 1] < 80) & (center[:, :, 2] < 80)
    red = int(red_m.sum())
    black = int(black_m.sum())

    # Взрыв: клетка залита красным
    px_all = cell.reshape(-1, 3).astype(int)
    red_all = int(
        ((px_all[:, 2] > 150) & (px_all[:, 0] < 100) & (px_all[:, 1] < 100)).sum()
    )
    if red_all > px_all.shape[0] * 0.4:
        return "boom"

    # Флажок: красный ВЕРХ и чёрный НИЗ (флаг над ножкой)
    if red > 3 and black > 3:
        ry = float(np.where(red_m)[0].mean())
        by = float(np.where(black_m)[0].mean())
        if by - ry > center.shape[0] * 0.15:
            return "flag"

    # Цифра по цвету (включая красную 3 с тенью)
    best, best_cnt = None, 0
    for d, c in DIGIT_COLORS_BGR.items():
        cnt = int(
            (
                (abs(px[:, 0] - c[0]) < 50) &
                (abs(px[:, 1] - c[1]) < 50) &
                (abs(px[:, 2] - c[2]) < 50)
            ).sum()
        )
        if cnt > best_cnt:
            best, best_cnt = d, cnt

    if best_cnt >= 3:
        return str(best)

    # 3D-рамка: верх+лево светлые, низ+право тёмные
    tb = max(2, h // 8)

    top = cell[1:1 + tb, tb:w - tb].astype(float).mean()
    left = cell[tb:h - tb, 1:1 + tb].astype(float).mean()
    bottom = cell[h - 1 - tb:h - 1, tb:w - tb].astype(float).mean()
    right = cell[tb:h - tb, w - 1 - tb:w - 1].astype(float).mean()

    score = (top + left) - (bottom + right)

    if score > 60:
        return "closed"

    return "open"


def read_board(frame, cfg):
    rows, cols = cfg["rows"], cfg["cols"]
    cw = cfg["width"] / cols
    ch = cfg["height"] / rows

    board = []
    for r in range(rows):
        row = []
        for c in range(cols):
            x0 = int(c * cw)
            y0 = int(r * ch)
            x1 = int((c + 1) * cw)
            y1 = int((r + 1) * ch)
            row.append(classify_cell(frame[y0:y1, x0:x1]))
        board.append(row)
    return board


def board_to_text(board):
    out = []
    for row in board:
        line = ""
        for v in row:
            if v == "closed":
                line += ". "
            elif v == "open":
                line += "_ "
            elif v == "flag":
                line += "F "
            elif v == "boom":
                line += "X "
            else:
                line += v + " "
        out.append(line)
    return "\n".join(out)


def draw_board(frame, board, cfg):
    dbg = frame.copy()
    cw = cfg["width"] / cfg["cols"]
    ch = cfg["height"] / cfg["rows"]
    for r, row in enumerate(board):
        for c, v in enumerate(row):
            x = int(c * cw)
            y = int(r * ch)
            if v == "closed":
                color = (0, 255, 0)
            elif v == "flag":
                color = (255, 0, 255)
            elif v in "12345678":
                color = (0, 0, 255)
            else:
                color = (255, 0, 0)
            cv2.putText(
                dbg, v, (x + 5, y + int(ch) - 8),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2
            )
    return dbg


def neighbors(r, c, rows, cols):
    for dr in (-1, 0, 1):
        for dc in (-1, 0, 1):
            if dr == 0 and dc == 0:
                continue
            rr, cc = r + dr, c + dc
            if 0 <= rr < rows and 0 <= cc < cols:
                yield rr, cc


def solve(board, cfg):
    """
    Возвращает (actions, info):
    actions — список ("open"/"flag", r, c)
    info — строка для лога
    """
    rows, cols = cfg["rows"], cfg["cols"]
    total_mines = cfg["mines"]

    flags_cnt = sum(
        1 for r in range(rows) for c in range(cols) if board[r][c] == "flag"
    )
    closed = set(
        (r, c) for r in range(rows) for c in range(cols) if board[r][c] == "closed"
    )

    # Первое движение: всё закрыто — кликаем в центр
    if len(closed) == rows * cols:
        return [("open", rows // 2, cols // 2)], "первый ход — центр"

    # Ограничения: (множество закрытых соседей, оставшиеся мины)
    constraints = []
    for r in range(rows):
        for c in range(cols):
            if board[r][c] in "12345678":
                if r == rows - 1 or c == cols - 1:
                    continue
                n = int(board[r][c])
                unk = set()
                fl = 0
                for rr, cc in neighbors(r, c, rows, cols):
                    if board[rr][cc] == "closed":
                        unk.add((rr, cc))
                    elif board[rr][cc] == "flag":
                        fl += 1
                rem = n - fl
                if unk and rem >= 0:
                    constraints.append((unk, rem))

    known_safe = set()
    known_mine = set()

    # Логика: базовые правила + вычитание множеств (паттерны 1-1, 1-2)
    changed = True
    while changed:
        changed = False

        new_constraints = []
        for s, rem in constraints:
            m = len(s & known_mine)
            s = s - known_safe - known_mine
            rem = rem - m
            if rem < 0 or not s:
                continue
            if rem == 0:
                known_safe |= s
                changed = True
                continue
            if rem == len(s):
                known_mine |= s
                changed = True
                continue
            new_constraints.append((s, rem))
        constraints = new_constraints

        seen = set((frozenset(s), rem) for s, rem in constraints)
        added = []
        for a, ra in constraints:
            for b, rb in constraints:
                if a < b:
                    diff = b - a
                    drem = rb - ra
                    key = (frozenset(diff), drem)
                    if 0 < drem < len(diff) and key not in seen:
                        added.append((diff, drem))
                        seen.add(key)
        if added:
            constraints += added
            changed = True

    actions = []
    for r, c in sorted(known_mine):
        actions.append(("flag", r, c))
    for r, c in sorted(known_safe):
        actions.append(("open", r, c))

    if actions:
        return actions, f"логика: безопасных={len(known_safe)}, мин={len(known_mine)}"

    # Нет точных ходов → вероятности перебором
    boundary = set()
    for s, rem in constraints:
        boundary |= s

    unknowns = closed - known_safe - known_mine
    outside = unknowns - boundary
    R = total_mines - flags_cnt - len(known_mine)

    guess = None

    if boundary and len(boundary) <= 20:
        cells = sorted(boundary)
        cons = [(set(s), rem) for s, rem in constraints]
        results = []
        assign = {}

        def ok():
            for s, rem in cons:
                done = 0
                m = 0
                for cell in s:
                    if cell in assign:
                        done += 1
                        m += assign[cell]
                if m > rem or rem - m > len(s) - done:
                    return False
                if done == len(s) and m != rem:
                    return False
            return True

        def bt(k):
            if k == len(cells):
                results.append(dict(assign))
                return
            cell = cells[k]
            for val in (0, 1):
                assign[cell] = val
                if ok():
                    bt(k + 1)
                del assign[cell]

        bt(0)

        O = len(outside)
        weights = []
        for sol in results:
            mb = sum(sol.values())
            if O and 0 <= R - mb <= O:
                w = math.comb(O, R - mb)
            elif not O and R == mb:
                w = 1
            else:
                w = 0
            weights.append(w)

        tot = sum(weights)
        if tot > 0 and results:
            prob = {}
            for cell in cells:
                prob[cell] = sum(
                    w for sol, w in zip(results, weights) if sol[cell] == 1
                ) / tot

            p_off = 1.0
            if O:
                p_off = sum(
                    w * (R - sum(sol.values())) / O
                    for sol, w in zip(results, weights)
                ) / tot

            best_cell = min(prob, key=prob.get)
            best_p = prob[best_cell]

            if O and p_off < best_p:
                guess = (next(iter(outside)), p_off)
            else:
                guess = (best_cell, best_p)

    if guess is None:
        best_p = 1.0
        best_cell = None
        for s, rem in constraints:
            p = rem / len(s)
            if p < best_p:
                best_p = p
                best_cell = min(s)
        if best_cell is None:
            if unknowns:
                best_cell = sorted(unknowns)[0]
                best_p = 0.5
            else:
                return [], "нет ходов"
        guess = (best_cell, best_p)

    (r, c), p = guess
    return [("open", r, c)], f"гадание: клетка ({r},{c}) риск={p:.2f}"