import logging

from src.database import Database

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

database = Database()
