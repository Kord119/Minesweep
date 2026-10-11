try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import pyautogui

pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.05


def click(x, y, button="left"):
    """
    Клик по экранным координатам.
    """
    if button == "right":
        pyautogui.rightClick(x, y)
    elif button == "middle":
        pyautogui.middleClick(x, y)
    else:
        pyautogui.click(x, y)


def move_to(x, y):
    """
    Просто переместить курсор.
    """
    pyautogui.moveTo(x, y)


def perform_actions(actions):
    """
    Выполняет список действий.

    Пример формата действий:
    """
    for action in actions:
        if action.get("type") == "click":
            x = action.get("x")
            y = action.get("y")
            button = action.get("button", "left")

            if x is None or y is None:
                continue

            click(x, y, button)