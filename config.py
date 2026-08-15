import os

from dotenv import load_dotenv

load_dotenv()


class Config:
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        "mysql+pymysql://root:23032023@localhost:3306/metka_shop?charset=utf8mb4",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")

    # Telegram-бот — сповіщення про нові замовлення
    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")

    # Nova Poshta API — підказки міст і відділень при оформленні замовлення
    NP_API_KEY = os.environ.get("NP_API_KEY", "")
    NP_API_URL = os.environ.get("NP_API_URL", "https://api.novaposhta.ua/v2.0/json/")
