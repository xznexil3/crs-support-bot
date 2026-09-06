#!/bin/bash
set -e
if [ ! -f .env ]; then
  echo "❌ .env не найден! Скопируй .env.example -> .env и вставь BOT_TOKEN"
  cp .env.example .env
  echo "Отредактируй .env и запусти снова"
  exit 1
fi
if ! grep -q "BOT_TOKEN=.*:" .env; then
  echo "⚠️ Вставь токен от @BotFather в .env"
  nano .env || vi .env
fi
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt
python src/bot.py
