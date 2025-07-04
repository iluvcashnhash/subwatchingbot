# Telegram Subscription Tracker Bot

A Telegram bot to help you track and manage your subscriptions with reminders for upcoming renewals.

## Features

- 📅 Track subscription renewals
- 🔔 Get reminders before subscriptions renew
- 💰 Monitor monthly expenses
- 📊 View subscription statistics
- 🤖 Natural language processing for easy interaction

## Prerequisites

- Docker and Docker Compose
- Python 3.12 (if running without Docker)
- A Telegram Bot Token from [@BotFather](https://t.me/botfather)

## Quick Start with Docker (Recommended)

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd subwatch_bot
   ```

2. Create a `.env` file in the project root with your configuration:
   ```env
   # Required
   BOT_TOKEN=your_telegram_bot_token
   ADMIN_IDS=123456789,987654321  # Comma-separated list of admin user IDs
   
   # Optional
   MONGODB_URL=mongodb://mongo:27017
   DB_NAME=subwatch_bot
   GIGACHAT_CREDENTIALS=your_gigachat_credentials  # Optional for enhanced NLP
   ```

3. Build and start the services:
   ```bash
   docker compose up -d --build
   ```

4. The bot should now be running. Open Telegram and start a chat with your bot.

## Running Without Docker

1. Install Python 3.12 and MongoDB

2. Create and activate a virtual environment:
   ```bash
   python3.12 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file as shown above

5. Run the bot:
   ```bash
   python -m app.main
   ```

## Available Commands

- `/start` - Start the bot and show welcome message
- `/help` - Show help information
- `/add` - Add a new subscription
- `/list` - List all your subscriptions
- `/delete` - Delete a subscription
- `/stats` - Show subscription statistics

## Development

### Running Tests

```bash
pytest tests/
```

### Code Style

This project uses `black` for code formatting and `isort` for import sorting.

```bash
black .
isort .
```

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BOT_TOKEN` | Yes | - | Your Telegram bot token |
| `ADMIN_IDS` | Yes | - | Comma-separated list of admin user IDs |
| `MONGODB_URL` | No | `mongodb://mongo:27017` | MongoDB connection URL |
| `DB_NAME` | No | `subwatch_bot` | Database name |
| `GIGACHAT_CREDENTIALS` | No | - | GigaChat API credentials for enhanced NLP |
| `WEBHOOK_URL` | No | - | Webhook URL (if using webhooks) |
| `WEBHOOK_PATH` | No | - | Webhook path (if using webhooks) |

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [python-telegram-bot](https://python-telegram-bot.org/)
- [MongoDB](https://www.mongodb.com/)
- [APScheduler](https://apscheduler.readthedocs.io/)
- [Pydantic](https://pydantic-docs.helpmanual.io/)
