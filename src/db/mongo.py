import pymongo
from typing import Dict, List


class MongoDBUploader:
    """A helper class to upload mongo db embeddings"""

    def __init__(
        self, connection_string: str, database_name: str, collection_name: str
    ):
        self.connection_string = connection_string
        self.database_name = database_name
        self.collection_name = collection_name
        self.client = pymongo.MongoClient(connection_string)
        self.db = self.client[database_name]
        self.collection = self.db[collection_name]
