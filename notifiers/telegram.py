# notifiers/telegram.py
import logging
from telegram import Bot, InputFile
from telegram.error import TelegramError
from notifiers.base import BaseNotifier

'''
class TelegramNotifier:
    def __init__(self, token, chat_id):
        self.bot = Bot(token=token)
        self.chat_id = chat_id
    def send_message(self, text):
        try:
            self.bot.send_message(chat_id=self.chat_id, text=text)
        except Exception as e:
            print(f"[Telegram Error] {e}")
'''

logger = logging.getLogger(__name__)
class TelegramNotifier(BaseNotifier):
    def __init__(self, token: str, chat_id: str):
        self.chat_id = chat_id
        try:
            self.bot = Bot(token=token)
            # quick sanity-check
            self.bot.get_me()
        except TelegramError as exc:
            logger.warning("Telegram init failed – disabling backend: %s", exc)
            self.bot = None

    def send(self, text: str, image_path: str or None = None) -> None:
        if self.bot is None:
            return
        try:
            if image_path:
                self.bot.send_photo(self.chat_id, photo=InputFile(image_path), caption=text)
            else:
                self.bot.send_message(self.chat_id, text=text, parse_mode="HTML")
        except TelegramError as exc:
            logger.warning("Telegram send failed: %s", exc)
