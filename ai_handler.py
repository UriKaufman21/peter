"""
AI Handler — uses Claude to parse natural language task commands.
"""

import json
import re
import os
from anthropic import AsyncAnthropic
from datetime import date, timedelta

client = AsyncAnthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

SYSTEM_PROMPT = """You are an AI task management assistant inside a Telegram bot.
Your job is to parse the user's message and return a JSON action object.

Today's date: {today}

Existing tasks (for matching complete/delete requests):
{tasks_json}

Return ONLY valid JSON — no markdown, no explanation.

Possible actions:

1. ADD a task:
{{"action": "add", "task": {{"title": "...", "priority": "high|medium|low", "due_date": "YYYY-MM-DD or null", "category": "..."}}}}

2. COMPLETE a task (mark done):
{{"action": "complete", "matches": [task objects that match]}}

3. DELETE a task:
{{"action": "delete", "matches": [task objects that match]}}

4. LIST tasks (optionally filtered):
{{"action": "list", "tasks": [filtered task objects]}}

5. SUMMARY:
{{"action": "summary"}}

6. UNKNOWN (can't parse):
{{"action": "unknown", "reply": "friendly message asking for clarification"}}

Rules:
- For "complete" and "delete", fuzzy-match the user's text against existing task titles.
- For "list", filter tasks by priority/category/due date if the user specifies.
- Infer due dates from natural language: "tomorrow", "Friday", "next week", "end of month".
- Default priority is "medium" unless specified.
- Category can be inferred from context (e.g., "buy groceries" → "Shopping", "call dentist" → "Health").
"""


class AIHandler:
    async def process(self, user_id: int, text: str, tasks: list) -> dict:
        today = date.today().isoformat()
        tasks_json = json.dumps(tasks, ensure_ascii=False, default=str)

        try:
            response = await client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=1000,
                system=SYSTEM_PROMPT.format(today=today, tasks_json=tasks_json),
                messages=[{"role": "user", "content": text}]
            )
            raw = response.content[0].text.strip()
            # Strip possible markdown fences
            raw = re.sub(r"^```(?:json)?\n?", "", raw)
            raw = re.sub(r"\n?```$", "", raw)
            result = json.loads(raw)
            return result
        except json.JSONDecodeError:
            return {"action": "unknown", "reply": "I had trouble understanding that. Try rephrasing, or use /help."}
        except Exception as e:
            return {"action": "unknown", "reply": f"Something went wrong: {str(e)}"}
