# Watchdog Man

<p align="center">
  <img width="300" height="420" src="imgs/watchdog_man_colored.png">
</p>

Simple library to log and monitor experiments

# How to install

```bash
pip install . --user
```

# How to use

- Follow example_1.py in tests folder

# If you want to send messages to telegram

- Create a telegram bot
- Paste its token into tests/telegram_token.txt
- Send a message to it from your account
- Visit https://api.telegram.org/bot<BOT_TOKEN>/getUpdates to get your id
- Paste your id into tests/chat_id.txt
- (or ignore example_1.py and pass it manually)