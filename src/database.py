from pymongo import ASCENDING, MongoClient


class Database:
    client: MongoClient = None
    users = None
    settings = None

    def __init__(self) -> None:
        self.database_url = "mongodb://localhost:27017/"
        self.database_name = "standup_bot"

    def connect(self) -> None:
        self.client = MongoClient(self.database_url)

        database = self.client[self.database_name]
        self.users = database["users"]
        self.settings = database["settings"]

        self.users.create_index([("username", ASCENDING)], unique=True)

    def close(self) -> None:
        self.client.close()
