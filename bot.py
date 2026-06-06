"""
AI Telegram Task Manager Bot
Powered by Claude AI + python-telegram-bot + SQLite
"""

import logging
import asyncio
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from ai_handler import AIHandler
from database import Database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

db = Database()
ai = AIHandler()


# ── Command Handlers ──────────────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    db.ensure_user(user.id, user.first_name)
    await update.message.reply_text(
        f"👋 Hey {user.first_name}! I'm your AI Task Assistant.\n\n"
        "Just talk to me naturally:\n"
        "• *\"Add buy groceries tomorrow high priority\"*\n"
        "• *\"What's on my list?\"*\n"
        "• *\"Complete the groceries task\"*\n"
        "• *\"Show urgent tasks\"*\n\n"
        "Or use the menu commands:\n"
        "/tasks — view your tasks\n"
        "/summary — today's digest\n"
        "/help — all commands",
        parse_mode="Markdown"
    )


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🤖 *AI Task Assistant — Help*\n\n"
        "*Natural language (just type it):*\n"
        "• \"Add call dentist Friday medium priority\"\n"
        "• \"Mark gym as done\"\n"
        "• \"Show high priority tasks\"\n"
        "• \"Delete the dentist task\"\n"
        "• \"What's due today?\"\n\n"
        "*Commands:*\n"
        "/tasks — all active tasks\n"
        "/summary — daily digest\n"
        "/done — mark tasks complete\n"
        "/clear — delete completed tasks\n"
        "/help — this message",
        parse_mode="Markdown"
    )


async def tasks_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_tasks(user_id, status="pending")
    await update.message.reply_text(
        format_task_list(tasks),
        parse_mode="Markdown",
        reply_markup=task_keyboard(tasks) if tasks else None
    )


async def summary_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    pending = db.get_tasks(user_id, status="pending")
    done_today = db.get_tasks(user_id, status="done", today_only=True)
    overdue = db.get_overdue_tasks(user_id)

    lines = ["📊 *Your Daily Summary*\n"]
    if overdue:
        lines.append(f"🚨 *Overdue ({len(overdue)}):*")
        for t in overdue[:5]:
            lines.append(f"  • {t['title']} (due {t['due_date']})")
        lines.append("")

    high = [t for t in pending if t["priority"] == "high"]
    if high:
        lines.append(f"🔴 *High Priority ({len(high)}):*")
        for t in high[:5]:
            due = f" — due {t['due_date']}" if t["due_date"] else ""
            lines.append(f"  • {t['title']}{due}")
        lines.append("")

    lines.append(f"📋 Total pending: *{len(pending)}*")
    lines.append(f"✅ Completed today: *{len(done_today)}*")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


async def done_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    tasks = db.get_tasks(user_id, status="pending")
    if not tasks:
        await update.message.reply_text("No pending tasks! 🎉")
        return
    await update.message.reply_text(
        "Which task did you complete?",
        reply_markup=task_keyboard(tasks, action="done")
    )


async def clear_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    count = db.clear_done(user_id)
    await update.message.reply_text(f"🗑️ Cleared {count} completed task(s).")


# ── Natural Language Message Handler ─────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    db.ensure_user(user_id, update.effective_user.first_name)

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    tasks = db.get_tasks(user_id, status="pending")
    result = await ai.process(user_id, text, tasks)

    if result["action"] == "add":
        task_id = db.add_task(user_id, **result["task"])
        task = db.get_task(task_id)
        await update.message.reply_text(
            f"✅ Task added!\n\n"
            f"*{task['title']}*\n"
            f"Priority: {priority_emoji(task['priority'])} {task['priority'].title()}\n"
            f"Due: {task['due_date'] or 'No due date'}\n"
            f"Category: {task['category'] or 'General'}",
            parse_mode="Markdown"
        )

    elif result["action"] == "complete":
        matches = result.get("matches", [])
        if len(matches) == 1:
            db.complete_task(matches[0]["id"])
            await update.message.reply_text(f"✅ *{matches[0]['title']}* marked as done!", parse_mode="Markdown")
        elif len(matches) > 1:
            await update.message.reply_text(
                "Which task did you mean?",
                reply_markup=task_keyboard(matches, action="done")
            )
        else:
            await update.message.reply_text("🤔 I couldn't find that task. Try /tasks to see your list.")

    elif result["action"] == "delete":
        matches = result.get("matches", [])
        if len(matches) == 1:
            db.delete_task(matches[0]["id"])
            await update.message.reply_text(f"🗑️ *{matches[0]['title']}* deleted.", parse_mode="Markdown")
        elif len(matches) > 1:
            await update.message.reply_text(
                "Which task to delete?",
                reply_markup=task_keyboard(matches, action="delete")
            )
        else:
            await update.message.reply_text("🤔 Couldn't find that task.")

    elif result["action"] == "list":
        filtered = result.get("tasks", tasks)
        await update.message.reply_text(
            format_task_list(filtered),
            parse_mode="Markdown",
            reply_markup=task_keyboard(filtered) if filtered else None
        )

    elif result["action"] == "summary":
        await summary_cmd(update, context)

    else:
        await update.message.reply_text(result.get("reply", "Sorry, I didn't understand that. Try /help!"))


# ── Callback Query Handler (inline buttons) ───────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data.startswith("done:"):
        task_id = int(data.split(":")[1])
        task = db.get_task(task_id)
        if task:
            db.complete_task(task_id)
            await query.edit_message_text(f"✅ *{task['title']}* marked as done!", parse_mode="Markdown")

    elif data.startswith("delete:"):
        task_id = int(data.split(":")[1])
        task = db.get_task(task_id)
        if task:
            db.delete_task(task_id)
            await query.edit_message_text(f"🗑️ *{task['title']}* deleted.", parse_mode="Markdown")

    elif data.startswith("view:"):
        task_id = int(data.split(":")[1])
        task = db.get_task(task_id)
        if task:
            text = (
                f"📌 *{task['title']}*\n"
                f"Priority: {priority_emoji(task['priority'])} {task['priority'].title()}\n"
                f"Due: {task['due_date'] or 'No due date'}\n"
                f"Category: {task['category'] or 'General'}\n"
                f"Created: {task['created_at'][:10]}"
            )
            kb = InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Done", callback_data=f"done:{task_id}"),
                InlineKeyboardButton("🗑️ Delete", callback_data=f"delete:{task_id}")
            ]])
            await query.edit_message_text(text, parse_mode="Markdown", reply_markup=kb)


# ── Helpers ───────────────────────────────────────────────────────────────────

def priority_emoji(p):
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(p, "⚪")


def format_task_list(tasks):
    if not tasks:
        return "🎉 No pending tasks! You're all caught up."
    lines = [f"📋 *Your Tasks ({len(tasks)})*\n"]
    for t in tasks:
        due = f" — {t['due_date']}" if t["due_date"] else ""
        cat = f" [{t['category']}]" if t["category"] else ""
        lines.append(f"{priority_emoji(t['priority'])} *{t['title']}*{due}{cat}")
    return "\n".join(lines)


def task_keyboard(tasks, action="view"):
    if not tasks:
        return None
    buttons = []
    for t in tasks[:10]:  # Telegram limit
        label = f"{priority_emoji(t['priority'])} {t['title'][:30]}"
        buttons.append([InlineKeyboardButton(label, callback_data=f"{action}:{t['id']}")])
    return InlineKeyboardMarkup(buttons)


# ── Daily Reminder ────────────────────────────────────────────────────────────

async def send_daily_digest(context: ContextTypes.DEFAULT_TYPE):
    users = db.get_all_users()
    for user in users:
        user_id = user["id"]
        pending = db.get_tasks(user_id, status="pending")
        overdue = db.get_overdue_tasks(user_id)
        if not pending and not overdue:
            continue
        lines = ["☀️ *Good morning! Here's your daily digest:*\n"]
        if overdue:
            lines.append(f"🚨 *{len(overdue)} overdue task(s):*")
            for t in overdue[:3]:
                lines.append(f"  • {t['title']}")
        high = [t for t in pending if t["priority"] == "high"]
        if high:
            lines.append(f"\n🔴 *{len(high)} high-priority task(s):*")
            for t in high[:3]:
                lines.append(f"  • {t['title']}")
        lines.append(f"\n📋 Total pending: *{len(pending)}*")
        try:
            await context.bot.send_message(user_id, "\n".join(lines), parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Could not send digest to {user_id}: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    import os
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        raise ValueError("Set TELEGRAM_BOT_TOKEN environment variable")

    app = Application.builder().token(token).build()

    # Commands
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("tasks", tasks_cmd))
    app.add_handler(CommandHandler("summary", summary_cmd))
    app.add_handler(CommandHandler("done", done_cmd))
    app.add_handler(CommandHandler("clear", clear_cmd))

    # Natural language
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Inline buttons
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Daily digest at 8:00 AM
    job_queue = app.job_queue
    job_queue.run_daily(send_daily_digest, time=time(hour=8, minute=0))

    logger.info("Bot started!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()