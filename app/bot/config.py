from dotenv import load_dotenv
import os
from pathlib import Path

# Путь до твоего bot.env
env_path = Path(__file__).resolve().parent.parent.parent / "configs" / "env" / "bot.env"
load_dotenv(dotenv_path=env_path)

BOT_TOKEN = os.getenv("BOT_TOKEN")