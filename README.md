# SubWatch Bot

Track subscriptions with natural language and get payment reminders.

## ✨ Features

- Add subscriptions with natural language
- Get reminders before payments are due
- Track costs and payment history
- Simple commands and natural input
- Self-hosted with Docker

## Prerequisites

- Docker and Docker Compose
- Telegram Bot Token from [@BotFather](https://t.me/botfather)
- GigaChat credentials (Client ID, Scope, Secret Key)

## 🚀 Quick Start

```bash
git clone https://github.com/yourusername/subwatchingbot.git
cd subwatchingbot
cp .env.sample .env  # Edit with your tokens
docker compose up -d --build
```

## 🤖 Commands

- `/start` - Start the bot
- `/help` - Show help
- `/add` - Add subscription
- `/list` - Show subscriptions
- `/delete` - Remove subscription

## 💬 Natural Language Examples

- "Add Netflix 1000₽ monthly"
- "I pay 15$ for Spotify every month"
- "Delete my Netflix subscription"
- "Show my subscriptions"
- "How much do I spend monthly?"

## 🔄 Database Backup

Backup:
```bash
docker compose exec mongo mongodump --archive > backup_$(date +%Y%m%d).archive
```

Restore:
```bash
docker compose exec -T mongo mongorestore --archive < backup_20230704.archive
```

## 📝 .env.sample
```
BOT_TOKEN=your_telegram_bot_token
GIGACHAT_CLIENT_ID=your_gigachat_client_id
GIGACHAT_SCOPE=GIGACHAT_API_PERS
GIGACHAT_SECRET_KEY=your_gigachat_secret_key
MONGODB_URI=mongodb://mongo:27017
DB_NAME=subwatch
TZ=Asia/Jerusalem
```

| `WEBHOOK_PATH` | No | - | Webhook path (if using webhooks) |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [python-telegram-bot](https://python-telegram-bot.org/)
- [MongoDB](https://www.mongodb.com/)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
