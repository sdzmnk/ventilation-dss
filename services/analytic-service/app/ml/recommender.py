import json
import os


class Recommender:
    """Optional LLM-driven advice for ventilation diagnostics.

    Enabled only when BASE_URL, HF_TOKEN and MODEL env vars are set.
    Falls back gracefully (returns None) when configuration is missing
    so the API never depends on the external service.
    """

    def __init__(self):
        base_url = os.getenv("BASE_URL")
        api_key = os.getenv("HF_TOKEN")
        self.model = os.getenv("MODEL")
        self.client = None
        self.enabled = False
        if base_url and api_key and self.model:
            try:
                from openai import OpenAI
                self.client = OpenAI(base_url=base_url, api_key=api_key)
                self.enabled = True
            except ImportError:
                self.enabled = False

    @staticmethod
    def build_prompt(predicted_data: dict) -> str:
        return f"""
Ти — інженер промислової вентиляції чистих приміщень.
Проаналізуй вихід ML-моделі (XGBoost) і дай якісну рекомендацію оператору.

ВХІДНІ ДАНІ:
{json.dumps(predicted_data, indent=2, ensure_ascii=False)}

ФОРМАТ ВІДПОВІДІ — РІВНО 3 СЕКЦІЇ. Структура однакова для OK / WARNING / CRITICAL.
Стан: одне коротке речення про загальний стан системи (без конкретних чисел та відсотків).
Причина: одне коротке речення — який клас каналів виявився визначальним для моделі (тиск / перепад / витрата / параметри гермозони), без числових значень і без точних назв датчиків.
Дія: 2-3 нумеровані пункти "1.", "2.", "3." з якісними рекомендаціями (загальні групи обладнання: приточна/витяжна вентиляція, фільтри, гермозасувки, журнал зміни). Без конкретних позначень обладнання.

СУВОРІ ЗАБОРОНИ:
- Не наводь жодних чисел, відсотків, одиниць виміру (Па, м/с, м³/год), ±діапазонів.
- Не цитуй конкретні значення з ВХІДНИХ ДАНИХ. Використовуй лише якісні слова: "стабільний", "у межах норми", "відхиляється", "знижений", "підвищений".
- Не згадуй конкретних маркувань обладнання (М-1, Ф-102, К-1, ВСРО, тощо). Кажи узагальнено: "приточні вентилятори", "HEPA-фільтри", "гермозасувки".
- Жодного markdown (**, __, `, #), жодних емодзі.
- Кожна секція починається з нового рядка з мітки "Стан:", "Причина:" або "Дія:".

ПРИКЛАД (для status=OK):
Стан: Вентиляція працює у штатному режимі без явних відхилень.
Причина: Визначальним для моделі залишається перепад тиску між зонами та параметри гермозони, які тримаються стабільно.
Дія:
1. Продовжувати штатний моніторинг тиску та витрати.
2. Періодично перевіряти стан фільтрів і герметичність засувок.
3. Фіксувати показання у журналі зміни.
"""

    def generate_advice(self, data: dict) -> str | None:
        if not self.enabled:
            return None
        completion = self.client.chat.completions.create(
            model=self.model,
            temperature=0.2,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Ти — експерт з безпеки HVAC, спеціалізуєшся на діагностиці "
                        "промислової вентиляції. Відповідай українською мовою."
                    ),
                },
                {"role": "user", "content": self.build_prompt(data)},
            ],
        )
        return completion.choices[0].message.content
