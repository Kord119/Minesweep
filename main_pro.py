import time

from vision import screenshot
from actions import click
from mines import read_board, board_to_text, solve

# !!! ЗАМЕНИ НА СВОИ ИЗМЕРЕНИЯ !!!
REGION = {
    "left": 35,
    "top": 193,
    "width": 2494,
    "height": 1181
}

CFG = {
    "rows": 32,
    "cols": 67,
    "mines": 442,
}

CFG["width"] = REGION["width"]
CFG["height"] = REGION["height"]

print("Профессиональный агент запущен.")
print("Остановка: Ctrl+C")

try:
    while True:
        frame, region = screenshot(REGION)

        board = read_board(frame, CFG)

        print("\n" + board_to_text(board))

        # Проигрыш
        if any("boom" in row for row in board):
            print("ВЗРЫВ! Игра проиграна.")
            break

        # Победа
        if not any("closed" in row for row in board):
            print("ПОБЕДА! Все клетки открыты.")
            break

        actions, info = solve(board, CFG)
        print("Решение:", info)

        if not actions:
            print("Нет ходов. Пауза.")
            time.sleep(2)
            continue

        cw = REGION["width"] / CFG["cols"]
        ch = REGION["height"] / CFG["rows"]

        for kind, r, c in actions:
            x = int(REGION["left"] + (c + 0.5) * cw)
            y = int(REGION["top"] + (r + 0.5) * ch)

            if kind == "flag":
                click(x, y, "right")
            else:
                click(x, y, "left")

            time.sleep(0.1)

        time.sleep(0.2)

except KeyboardInterrupt:
    print("Агент остановлен.")