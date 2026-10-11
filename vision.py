try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    pass

import mss
import cv2
import numpy as np


def screenshot(region=None):
    """
    Делает скриншот экрана или области.

    region может быть:
    None — весь основной монитор
    или словарь вида:
    {
        "left": 100,
        "top": 100,
        "width": 800,
        "height": 600
    }

    Возвращает:
    frame, region
    """
    with mss.mss() as sct:
        if region is None:
            area = sct.monitors[1]
        else:
            area = region

        shot = sct.grab(area)
        frame = cv2.cvtColor(np.array(shot), cv2.COLOR_BGRA2BGR)

    return frame, area


def save_png(frame, path="screen.png"):
    """
    Сохраняет кадр в PNG.
    Используем imencode, чтобы нормально работало с кириллицей в пути.
    """
    ok, buffer = cv2.imencode(".png", frame)

    if ok:
        with open(path, "wb") as f:
            f.write(buffer)
        return True

    return False


def resize(frame, width=None, height=None):
    """
    Изменяет размер кадра.
    Потом это понадобится для нейросети.
    """
    if width is None and height is None:
        return frame

    return cv2.resize(frame, (width, height))