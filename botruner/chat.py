#!/usr/bin/env python
"""ChatClass for botrunner."""
from datetime import datetime

class ChatClass():
    """Class for operate with telegram chats"""
    def __init__(self, tg_chat_id, chats_collection):
        super(ChatClass, self).__init__()
        self.tg_chat_id = tg_chat_id
        self.chats_collection = chats_collection
        self.state = {
            "status": "new",
            "tags": [],
            "books_sent_ids": [],
            "last_adv": datetime.now().timestamp(),
            "nickname": "",
        }

        '''
        # Create if new user
        chat_in_db = chats_collection.find_one({"_id": tg_chat_id})
        if chat_in_db is None:
            pass
            # ??????

        if chat_in_db is None:
            chats_collection.insert_one({
                "_id": tg_chat_id,
                "state": self.state,
            })
        # Load from DB
        else:
            self.state = chat_in_db['state']
        '''

    def set_state(self, name, value):
        """Updating user state in DB

        Args:
            name (str): name of item
            value (str): item
        """
        self.state[name] = value
        self.chats_collection.update_one(
            { "_id": self.tg_chat_id },
            { "$set": {"state": self.state }
        })

    def add_item(self, name, item):
        """Adding item to user state in DB

        Args:
            name (str): name of item
            item (str): item
        """
        self.state[name].append(item)
        self.chats_collection.update_one(
            { "_id": self.tg_chat_id },
            { "$set": {"state": self.state }
        })
