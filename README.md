# 🤖 AI Telegram Task Manager

A personal task management bot powered by **Claude AI** + **Telegram** + **SQLite**.  
Talk to it naturally — no rigid commands needed.

---

## ✨ Features

| Feature | Details |
|---|---|
| Natural language | "Add buy milk tomorrow low priority" |
| Priorities | 🔴 High · 🟡 Medium · 🟢 Low |
| Due dates | Understands "tomorrow", "Friday", "next week" |
| Categories | Auto-inferred (Shopping, Health, Work…) |
| Daily digest | Sent every morning at 8:00 AM |
| Inline buttons | Tap to complete or delete tasks |
| Local storage | SQLite — no external DB needed |

---

## 🚀 Setup (5 minutes)

### 1. Get a Telegram Bot Token

1. Open Telegram and message **@BotFather**
2. Send `/newbot` and follow the prompts
3. Copy the token (looks like `123456:ABC-DEF...`)

### 2. Get an Anthropic API Key

1. Go to [console.anthropic.com](https://console.anthropic.com)
2. Create an API key
3. Copy it

### 3. Install & Run

```bash
# Clone / download this folder, then:
cd telegram_task_bot

# Install dependencies
pip install -r requirements.txt

# Set your keys
cp .env.example .env
# Edit .env with your TELEGRAM_BOT_TOKEN and ANTHROPIC_API_KEY

# Run the bot
python bot.py
```

That's it! Open your bot in Telegram and send `/start`.

---

## 💬 Usage Examples

| You type | What happens |
|---|---|
| `Add call dentist Friday high priority` | Creates a high-priority task due Friday |
| `Buy groceries tomorrow` | Adds a medium-priority shopping task |
| `What's on my list?` | Shows all pending tasks |
| `Show urgent tasks` | Filters to high priority |
| `Mark dentist as done` | Completes the task |
| `Delete groceries` | Removes the task |
| `/summary` | Today's full digest |

---

## 📁 File Structure

```
telegram_task_bot/
├── bot.py           # Main bot logic + handlers
├── ai_handler.py    # Claude AI natural language processing
├── database.py      # SQLite storage layer
├── requirements.txt
├── .env.example     # Key template
└── README.md
```

---

## ⚙️ Configuration

All config lives in `.env`:

```
TELEGRAM_BOT_TOKEN=...   # From @BotFather
ANTHROPIC_API_KEY=...    # From console.anthropic.com
```

The database (`tasks.db`) is created automatically on first run.

---

## 🌐 Running 24/7 (Optional)

To keep the bot always online, deploy to any cheap VPS or cloud:

**Railway / Render / Fly.io (free tier):**
- Push to GitHub → connect to Railway → set env vars → deploy

**VPS with systemd:**
```ini
# /etc/systemd/system/taskbot.service
[Unit]
Description=Telegram Task Bot

[Service]
WorkingDirectory=/path/to/telegram_task_bot
ExecStart=/usr/bin/python3 bot.py
EnvironmentFile=/path/to/.env
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable taskbot && sudo systemctl start taskbot
```

---

## 🔒 Privacy

All your tasks are stored **locally** in `tasks.db` on the machine running the bot.  
Nothing is sent to external servers except:
- Your messages → Claude API (for NLP processing)
- Bot responses → Telegram

---

## 🛠 Troubleshooting

| Problem | Fix |
|---|---|
| `TELEGRAM_BOT_TOKEN not set` | Check your `.env` file |
| Bot doesn't respond | Make sure `python bot.py` is running |
| AI misunderstands | Rephrase more clearly, or use `/tasks`, `/done` commands |
| Daily digest not arriving | Bot must be running at 8 AM |
