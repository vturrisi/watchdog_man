# watchdog_man

<p style="text-align: center;"><img src="imgs/watchdog_man_colored.png" width="200" height="250"></p>

A simple library to keep log and track of experiments

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