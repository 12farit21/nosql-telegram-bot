# NoSQL Telegram Bot

This is a Telegram bot for real estate search and management using MongoDB.

## Features
- Search for real estate listings with multiple filters
- Add new listings
- View and delete your listings
- Uses MongoDB for data storage

## Prerequisites
- Python 3.8+
- A Telegram bot token (from @BotFather)
- A MongoDB database

## Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/12farit21/nosql-telegram-bot.git
   cd nosql-telegram-bot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Create a `.env` file** in the project root and add the following:
   ```env
   TOKEN=your_telegram_bot_token
   MONGO_URI=your_mongodb_connection_string
   COLLECTION_NAME=your_collection_name
   ```

## Running the Bot

Make sure your `.env` file is set up, then run:
```bash
python main.py
```

## Usage
- Start the bot by sending `/start`
- Use inline buttons to filter search queries or manage your listings


