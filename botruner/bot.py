#!/usr/bin/env python
"""Bot class for botrunner."""
import logging

class BotClass():
    """Class for operate with telegram bots"""
    def __init__(self, bot_name, config):
        # Set up the logger for bot
        FILE_NAME = None
        if 'logtofile' in config and config['logtofile']:
            FILE_NAME = f"bots/{bot_name}.log"
            
        logging.basicConfig(
            level=10,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename=FILE_NAME,
        )
        logger = logging.getLogger(__name__)

        # Check bot is not disabled
        if 'disabled' in config and config['disabled']:
            logger.error(f"Bot {bot_name} is disabled")
            return
        
        logger.info(f"Bot {bot_name} is starting")
        '''
        self.bot_token = bot_token
        self.bot = telegram.Bot(token=self.bot_token)
        self.chats_collection = chats_collection
        self.chat_class = ChatClass(self.bot.get_me().id, self.chats_collection)
        '''

    def get_chat_class(self):
        """Return ChatClass object"""
        return self.chat_class

    def get_bot(self):
        """Return telegram bot object"""
        return self.bot

    def get_bot_token(self):
        """Return bot token"""
        return self.bot_token

    def get_bot_id(self):
        """Return bot id"""
        return self.bot.get_me().id

    def get_bot_username(self):
        """Return bot username"""
        return self.bot.get_me().username

    def get_bot_first_name(self):
        """Return bot first name"""
        return self.bot.get_me().first_name

    def get_bot_last_name(self):
        """Return bot last name"""
        return self.bot.get_me().last_name

    def get_bot_name(self):
        """Return bot name"""
        return self.bot.get_me().name

    def get_bot_link(self):
        """Return bot link"""
        return self.bot.get_me().link

    def get_bot_username(self):
        """Return bot username"""
        return self.bot.get_me().username

    def get_bot_is_bot(self):
        """Return bot is_bot"""
        return self.bot.get_me().is_bot

    def get_bot_first_name(self):
        """Return bot first name"""
        return self.bot.get_me().first_name

    def get_bot_last_name(self):
        """Return bot last name"""
        return self.bot.get_me().last_name
