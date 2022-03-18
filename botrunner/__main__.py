#!/usr/bin/env python
"""This application provides the launch of a telegram bot"""
import yaml
import os
import logging
from pymongo import MongoClient
from bot import BotClass
from threading import Timer

# Basic configuration
MAIN_LOOP_INTERVAL = 1
BOTS_PATH = 'bots/'
LOG_FILE = None # 'botrunner.log' - if you want to log to a file

# Global variables
Bots = {}
MAIN_LOOP_IS_RUNNING = False


# Set up main logger
FILE_NAME = None 
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=LOG_FILE,
    filemode='a'
)
logger = logging.getLogger(__name__)

# Connect to MongoDB
try:
    conn = MongoClient()
    logger.info("MongoDB connected!")
    db = conn.database
except:
    logger.error("Could not connect to MongoDB")
    exit()

def MainLoop():
    """Main loop for all bots."""
    # Set up main loop timer
    Timer(MAIN_LOOP_INTERVAL, MainLoop).start()
    
    # Check if MainLoop is running
    global MAIN_LOOP_IS_RUNNING
    if MAIN_LOOP_IS_RUNNING:
        logger.debug("MainLoop is already running")
        return
    else:
        MAIN_LOOP_IS_RUNNING = True
        logger.debug("MainLoop started")
        
    # Load all bot configurations from files
    for bot_name in os.listdir(os.path.dirname(BOTS_PATH)):
        # Loading configuration
        try:
            config = yaml.safe_load(open(f"bots/{bot_name}/config.yml", "r", encoding="utf-8"))
            config_modified = os.path.getmtime(f"bots/{bot_name}/config.yml")
        except FileNotFoundError:
            logger.error(f"Fail to open bots/{bot_name}/config.yml")
            continue
        else:
            # check modification time if bot is already loaded
            if bot_name in Bots:
                if Bots[bot_name].config_modified == config_modified:
                    continue
                else:
                    logger.info(f"Bot {bot_name}: New config detected")
                    Bots[bot_name].event({'type': 'system', 'name': 'shutdown'})
                    #remove bot from Bots
                    Bots[bot_name].stop()
                    del Bots[bot_name]
            
            logger.info(f"Bot {bot_name}: bots/{bot_name}/config.yml - loaded")
            # Create bot instance
            Bots[bot_name] = BotClass(bot_name, config, db)
            Bots[bot_name].config_modified = config_modified
            Bots[bot_name].event({'type': 'system', 'name': 'start'})
    
    # Running all bot's cronjobs
    for bot_name in Bots:
        Bots[bot_name].cron_jobs()
    
    MAIN_LOOP_IS_RUNNING = False       

def main():
    """Load & start all configured bots."""
    # Mainlloop starting
    MainLoop()

if __name__ == '__main__':
    main()