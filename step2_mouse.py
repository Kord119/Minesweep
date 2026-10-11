import time
import pyautogui

print("Наведи мышь на нужную точку.")
print("Координаты будут считаны через 5 секунд...")

for i in range(5, 0, -1):
    print(i, end="\r")
    time.sleep(1)

x, y = pyautogui.position()

print("\nКоординаты мыши:")
print(f"x = {x}")
print(f"y = {y}")