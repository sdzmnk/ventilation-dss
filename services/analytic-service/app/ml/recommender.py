import json
import os

from openai import OpenAI


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
        self.enabled = bool(base_url and api_key and self.model)
        self.client = OpenAI(base_url=base_url, api_key=api_key) if self.enabled else None

    @staticmethod
    def build_prompt(predicted_data: dict) -> str:
        return f"""
You are an industrial HVAC diagnostics engineer.
Analyze ventilation system ML prediction data.
INPUT DATA:
{json.dumps(predicted_data, indent=2)}

YOUR TASK:
1. Interpret current ventilation system condition
2. Evaluate operational risk
3. Explain possible cause
4. Give practical operator recommendation

RULES:
- 1-2 short sentences
- Use engineering language
- Focus on airflow, overheating, filters, cooling, pressure stability
- Avoid generic phrases
- Be concise and practical
- Answer in English
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
                        "You are an expert HVAC safety engineer "
                        "specialized in ventilation diagnostics."
                    ),
                },
                {"role": "user", "content": self.build_prompt(data)},
            ],
        )
        return completion.choices[0].message.content
