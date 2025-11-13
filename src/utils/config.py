# src/utils/config.py

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    API_ID = int(os.getenv("API_ID"))
    API_HASH = os.getenv("API_HASH")
    PHONE_NUMBER = os.getenv("PHONE_NUMBER")
    PASSWORD = os.getenv("PASSWORD")
    CHANNEL_ID = int(os.getenv("CHANNEL_ID"))

    BOT_TOKEN = os.getenv("BOT_TOKEN")
    WHITELIST_IDS = set(map(int, os.getenv("WHITELIST_IDS", "").split(",")))


config = Config()