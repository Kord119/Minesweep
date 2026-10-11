import os
import re
import json
import base64

import cv2
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_KEY = os.getenv("OPENAI_API_KEY", "ollama")
BASE_URL = os.getenv("OPENAI_BASE_URL", "http://localhost:11434/v1")
MODEL = os.getenv("VISION_MODEL", "qwen2.5vl:7b")

MAX_IMAGE_SIDE = int(os.getenv("AGENT_MAX_IMAGE_SIDE", "1024"))
MAX_ACTIONS = int(os.getenv("AGENT_MAX_ACTIONS", "1"))
DEBUG_BRAIN = os.getenv("DEBUG_BRAIN", "1") == "1"

TASK_FILE = "task.txt"

# Память кликов, чтобы модель не повторяла один и тот же ход
CLICK_HISTORY = []
MAX_HISTORY = 20

SYSTEM_PROMPT = """Ты — агент, который играет в Сапёр по скриншоту.

Ты получаешь:
1. изображение игрового поля;
2. текстовую задачу.

Ты должен вернуть ТОЛЬКО один JSON-объект, без markdown и без пояснений.

Формат ответа:
{
  "thought": "краткое объяснение",
  "actions": [
    {
      "type": "click",
      "button": "left" или "right",
      "x": целое число,
      "y": целое число,
      "reason": "почему именно этот клик"
    }
  ]
}

Важные правила:
- Кликай ТОЛЬКО по закрытым клеткам (серые выпуклые квадраты).
- НИКОГДА не кликай по открытым клеткам (плоские, с цифрой или пустые).
- Красные круги на изображении — это точки, по которым ты УЖЕ кликал. Никогда не кликай по ним снова.
- Координаты x и y указывай в пикселях присланного изображения.
- Не выходи за пределы изображения.
- Если не уверен, верни "actions": [].
- Возвращай не больше одного действия.
"""

client = OpenAI(
    api_key=API_KEY,
    base_url=BASE_URL,
    timeout=180.0
)


def read_task():
    if os.path.exists(TASK_FILE):
        with open(TASK_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()

    return """Посмотри на экран и коротко опиши, что видно.
Верни только JSON:
{
  "thought": "описание экрана",
  "actions": []
}"""


def _to_float(value):
    try:
        return float(value)
    except Exception:
        return None


def encode_frame(frame):
    h, w = frame.shape[:2]

    scale = min(1.0, MAX_IMAGE_SIDE / max(h, w))

    if scale < 1.0:
        small = cv2.resize(
            frame,
            (int(w * scale), int(h * scale)),
            interpolation=cv2.INTER_AREA
        )
    else:
        small = frame.copy()

    if DEBUG_BRAIN:
        ok_debug, buffer_debug = cv2.imencode(
            ".jpg",
            small,
            [int(cv2.IMWRITE_JPEG_QUALITY), 85]
        )

        if ok_debug:
            with open("model_input.jpg", "wb") as f:
                f.write(buffer_debug)

        print("Мозг: размер картинки для модели:", small.shape[1], "x", small.shape[0])

    ok, buffer = cv2.imencode(
        ".jpg",
        small,
        [int(cv2.IMWRITE_JPEG_QUALITY), 80]
    )

    if not ok:
        raise RuntimeError("Не удалось закодировать изображение")

    b64 = base64.b64encode(buffer).decode("utf-8")

    return b64, small.shape[1], small.shape[0], scale


def extract_json(text):
    text = (text or "").strip()

    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)

    try:
        return json.loads(text)
    except Exception:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except Exception:
            pass

    return {
        "thought": text,
        "actions": []
    }


def parse_actions(data, scale, region, img_w, img_h):
    if not isinstance(data, dict):
        return []

    raw_actions = data.get("actions", [])

    if not isinstance(raw_actions, list):
        return []

    result = []

    left = 0
    top = 0

    if isinstance(region, dict):
        left = int(region.get("left", 0))
        top = int(region.get("top", 0))

    for action in raw_actions[:MAX_ACTIONS]:
        if not isinstance(action, dict):
            continue

        if action.get("type") != "click":
            continue

        x = _to_float(action.get("x"))
        y = _to_float(action.get("y"))

        if x is None or y is None:
            continue

        if max(abs(x), abs(y)) <= 1.0 and (x != int(x) or y != int(y)):
            x = x * img_w
            y = y * img_h

        if x < 0 or y < 0 or x > img_w or y > img_h:
            continue

        x = int(x / scale)
        y = int(y / scale)

        x += left
        y += top

        button = action.get("button", "left")

        if button not in ("left", "right", "middle"):
            button = "left"

        result.append({
            "type": "click",
            "button": button,
            "x": x,
            "y": y,
            "reason": action.get("reason", "")
        })

    return result


def decide(frame, region):
    global CLICK_HISTORY

    if DEBUG_BRAIN:
        print("Мозг: начинаю анализ скриншота")
        print("Мозг: модель =", MODEL)
        print("Мозг: адрес =", BASE_URL)

    task = read_task()

    left0 = 0
    top0 = 0

    if isinstance(region, dict):
        left0 = int(region.get("left", 0))
        top0 = int(region.get("top", 0))

    # Рисуем красные круги на местах прошлых кликов
    frame_marked = frame.copy()

    for hx, hy in CLICK_HISTORY[-10:]:
        cv2.circle(frame_marked, (int(hx), int(hy)), 10, (0, 0, 255), 2)

    try:
        b64, img_w, img_h, scale = encode_frame(frame_marked)
    except Exception as e:
        print("Ошибка подготовки изображения:", e)
        return []

    user_prompt = f"""Размер изображения: {img_w}x{img_h} пикселей.

Задача:
{task}"""

    if CLICK_HISTORY:
        user_prompt += """

Красные круги на изображении — это твои прошлые клики.
Не кликай по ним снова и не кликай по открытым клеткам."""

    user_prompt += """

Верни только JSON-объект."""

    if DEBUG_BRAIN:
        print("Мозг: отправляю запрос в нейросеть...")

    try:
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0.2,
            max_tokens=700,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": user_prompt
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{b64}"
                            }
                        }
                    ]
                }
            ]
        )
    except Exception as e:
        print("Ошибка запроса к нейросети:", e)
        return []

    if not response.choices:
        print("Нейросеть вернула пустой ответ")
        return []

    raw_text = response.choices[0].message.content or ""

    if DEBUG_BRAIN:
        print("Мозг: получен ответ от нейросети")
        print("Сырой ответ:", raw_text)

    data = extract_json(raw_text)

    if isinstance(data, dict) and data.get("thought"):
        print("Нейросеть думает:", data["thought"])

    actions = parse_actions(data, scale, region, img_w, img_h)

    # Запоминаем клики в координатах изображения
    for a in actions:
        CLICK_HISTORY.append((a["x"] - left0, a["y"] - top0))

    if len(CLICK_HISTORY) > MAX_HISTORY:
        del CLICK_HISTORY[:-MAX_HISTORY]

    if DEBUG_BRAIN:
        print("Итоговые действия:", actions)

    return actions