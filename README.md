# Minesweep

Агент, который играет в «Сапёр», анализируя скриншот экрана.

## Два режима

- `main_pro.py` — профессиональный игрок: OpenCV читает поле по пикселям,
  логический solver принимает решения (ограничения, паттерны 1-1/1-2,
  точные вероятности при угадывании).
- `main.py` + `brain.py` — универсальный экранный агент: отправляет скриншот
  в vision-модель (Ollama, qwen2.5vl) и выполняет возвращённые клики.

## Установка

    python -m venv .venv
    .venv\Scripts\Activate.ps1
    pip install -r requirements.txt

## Настройка

1. Скопировать `.env.example` в `.env` и заполнить.
2. Замерить координаты поля через `step2_mouse.py`.
3. Вписать `REGION` и `CFG` (rows, cols, mines) в `main_pro.py`.

## Запуск

    python main_pro.py   # логический игрок
    python main.py       # агент на нейросети