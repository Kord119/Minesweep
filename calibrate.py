import cv2

from vision import screenshot

# !!! вставь сюда измеренные координаты большого поля !!!
REGION = {
    "left": 15,
    "top": 35,
    "width": 2530,
    "height": 1400,
}

frame, _ = screenshot(REGION)
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY).astype(int)

row_mean = gray.mean(axis=1)
col_mean = gray.mean(axis=0)


def count_lines(profile, thresh=210):
    bright = profile > thresh
    groups = 0
    prev = False
    for v in bright:
        if v and not prev:
            groups += 1
        prev = v
    return groups


h_lines = count_lines(row_mean)
v_lines = count_lines(col_mean)

print("Светлых горизонтальных линий:", h_lines)
print("Светлых вертикальных линий:", v_lines)
print()
print("Оценка: rows ~", h_lines, ", cols ~", v_lines)
print("Размер клетки ~", round(REGION["height"] / max(h_lines, 1), 1),
      "x", round(REGION["width"] / max(v_lines, 1), 1))