import time

from vision import screenshot, save_png
from actions import perform_actions
from brain import decide

REGION = {
    "left": 826,
    "top": 331,
    "width": 890,
    "height": 886
}

DEBUG = True

print("Агент запущен.")
print("Остановка: Ctrl+C")
print("Экстренная остановка: резко увести мышь в левый верхний угол экрана.")

try:
    while True:
        # 1. Глаза: получаем скриншот области игры
        frame, region = screenshot(REGION)

        if DEBUG:
            save_png(frame, "last_frame.png")

        # 2. Мозг: нейросеть принимает решение
        actions = decide(frame, region)

        if actions:
            print("Действия:", actions)

        # 3. Руки: выполняем клики
        perform_actions(actions)

        # Пауза между ходами
        time.sleep(5.0)

except KeyboardInterrupt:
    print("Агент остановлен пользователем.")