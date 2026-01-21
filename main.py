import os
import sys

# Check if running in a virtual environment
if sys.prefix == sys.base_prefix:
    print("⚠️  WARNING: You rely on the system Python. Please run with the virtual environment.")
    print("👉 Use: ./run_bot.sh")
    print("   Or: ./venv/bin/python main.py")
    # We continue, but it will likely fail on imports if deps aren't global.

import logging
import asyncio
from datetime import datetime
from dotenv import load_dotenv
from telegram import Update, constants
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters

# Import our AI engine
from ai_engine import get_agent_response

load_dotenv()

import json

# Logger configuration
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Persistent Memory Storage
MEMORY_FILE = "memory.json"
user_conversations = {}

def load_memory():
    """Load conversation history from JSON file."""
    global user_conversations
    try:
        if os.path.exists(MEMORY_FILE):
            with open(MEMORY_FILE, 'r', encoding='utf-8') as f:
                # We need to convert keys back to integers (user_ids) because JSON keys are always strings
                data = json.load(f)
                user_conversations = {int(k): v for k, v in data.items()}
            logger.info(f"✅ Memory loaded from {MEMORY_FILE}")
        else:
            logger.info("ℹ️ No memory file found. Starting fresh.")
            user_conversations = {}
    except Exception as e:
        logger.error(f"❌ Failed to load memory: {e}")
        user_conversations = {}

def save_memory():
    """Save conversation history to JSON file."""
    try:
        with open(MEMORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(user_conversations, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logger.error(f"❌ Failed to save memory: {e}")

# Load memory on startup
load_memory()

# System Prompt - Set AI persona
SYSTEM_PROMPT = """
You are an efficient Financial Assistant. You can manage my Google Calendar and accounting sheets.
Current time: {current_time}
Please reply in the language used by the user. If amounts are involved, keep the original currency (default to Euro if unspecified), do NOT convert to CNY unless explicitly asked.

IMPORTANT Rules:
1. Classification Sensibility:
   - You MUST classify items into one of these specific categories:
     * Food
     * Drinks
     * Clothes (includes underwear, shoes, accessories)
     * Leisure
     * AI Tools
     * Beauty
     * Skincare
     * Gifts
     * Health
     * Travel
     * Transport
     * Pet Care
     * Others
   - Do NOT default to "Food" unless it is actually food.
   - "Culots" -> Clothes
   - "Animalis" -> Pet Care
   - "Psy" -> Health

2. Date Handling:
   - You MUST separate the date from the item description.
   - If the user says "yesterday", "last friday", etc., calculate the exact date based on {current_time}.
   - Pass this 'YYYY-MM-DD' date explicitly to the tool.
   - EXTRACT the currency unit (e.g. €, $, ¥, JPY, CNY) and pass it to the tool's 'currency' field. Default to '€' if none is given.

3. Response Format:
   - Keep it CLEAN and SIMPLE.
   - Just confirm the action: "Saved: [Date] #[ID] [Item] [Amount][Currency] ([Category])".
   - Example: "Saved: 2026-01-21 #5 Lunch 25€ (Food)".
   - The tool will return the ID and Date. Include them exactly as returned.
   - Do NOT add polite fluff like "I have successfully recorded...".

4. Modification & Deletion:
   - If user says "Delete item 5", call 'delete_specific_row'.
   - ALWAYS use the ID provided by the user.

5. Calculation:
   - If user asks for total expenses (e.g., "this week", "last month", "Jan 2026"), YOU must calculate the specific date range based on today's date ({current_time}).
   - Call 'calculate_total' with 'start_date' and 'end_date' (YYYY-MM-DD).
   - Example - "This month": start="2026-01-01", end="2026-01-31".
"""

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user_id = update.effective_user.id
    username = update.effective_user.first_name
    
    # --- Fix Start ---
    # Initialize conversation history, insert system prompt
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    system_message = SYSTEM_PROMPT.format(current_time=current_time)
    
    # Initialize conversation history with system prompt
    user_conversations[user_id] = [{"role": "system", "content": system_message}]
    # --- Fix End ---
    
    await update.message.reply_text(f"Hello {username}! I am My Financial Assistant. I can help you with bookkeeping or scheduling.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all text messages"""
    user_id = update.effective_user.id
    auth_id_str = os.getenv("AUTHORIZED_USER_ID")
    
    # --------------------------
    # Security Interception Layer
    # --------------------------
    # Check if sender is authorized
    if str(user_id) != auth_id_str:
        logger.warning(f"Unauthorized access: User ID {user_id}")
        await update.message.reply_text("🚫 Unauthorized access. Please contact the administrator.")
        return

    user_text = update.message.text
    
    # Ensure user has history, if not initialize it
    if user_id not in user_conversations:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
        system_message = SYSTEM_PROMPT.format(current_time=current_time)
        user_conversations[user_id] = [{"role": "system", "content": system_message}]
        save_memory() # Save after init
        
    # Append user message to history
    user_conversations[user_id].append({"role": "user", "content": user_text})
    save_memory() # Save after user message
    
    # Send "Typing..." action to improve user experience
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action=constants.ChatAction.TYPING)
    
    try:
        # Call AI engine
        ai_reply = await get_agent_response(user_conversations[user_id])
        
        # Append AI reply to history
        user_conversations[user_id].append({"role": "assistant", "content": ai_reply})
        save_memory() # Save after AI reply
        
        # Reply to user
        await update.message.reply_text(ai_reply)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await update.message.reply_text("An internal error occurred while processing your request.")

if __name__ == '__main__':
    # Build application
    token = os.getenv("TELEGRAM_TOKEN")
    if not token:
        print("Error: TELEGRAM_TOKEN environment variable not set")
        exit(1)
        
    application = ApplicationBuilder().token(token).build()
    
    # Register handlers
    start_handler = CommandHandler('start', start)
    # Filter out command messages, handle only text
    message_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message)
    
    application.add_handler(start_handler)
    application.add_handler(message_handler)
    
    print("🤖 Bot is starting and running locally...")
    # Use Polling mode (Suitable for VPS and local development)
    application.run_polling()