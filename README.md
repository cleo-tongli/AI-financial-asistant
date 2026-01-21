# AI Financial Assistant 🤖💸

A smart Telegram bot that helps you track your expenses, manage your budget, and analyze your spending habits using Google Sheets and OpenAI.

## Features 🚀

*   **Natural Language Expense Tracking**: Just say "Spent 15€ on Lunch" and it's saved.
*   **Google Sheets Integration**: All data is stored in your own Google Sheet for full control.
*   **Smart Categorization**: Automatically categorizes items (e.g., "Psy" -> Health, "Burger" -> Food).
*   **Editing & Deletion**:
    *   "Undo" to remove the last entry.
    *   "Delete item #5" to remove specific rows.
    *   "Change item #5 to 20€" to modify entries.
*   **Calculations**: Ask "Total spending this week" or "How much in January?" for instant analysis.
*   **Calendar Integration**: Can schedule events via Google Calendar (optional).

## Setup 🛠️

### 1. Prerequisites
*   Python 3.8+
*   A Telegram Bot Token (from @BotFather)
*   OpenAI API Key
*   Google Cloud Service Account (for Sheets/Calendar API)

### 2. Installation

1.  Clone this repository:
    ```bash
    git clone https://github.com/YOUR_USERNAME/AI-financial-asistant.git
    cd AI-financial-asistant
    ```

2.  Create a virtual environment:
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  Install dependencies:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Configuration

1.  Create a `.env` file in the root directory:
    ```ini
    TELEGRAM_TOKEN=your_telegram_bot_token
    OPENAI_API_KEY=sk-your_openai_key
    GOOGLE_SHEET_ID=your_google_sheet_id
    GOOGLE_CALENDAR_ID=your_calendar_id (optional)
    ALLOWED_USER_ID=your_telegram_user_id
    ```

2.  Place your Google Service Account JSON key in the root folder (e.g., `credentials.json`).

### 4. Running the Bot

```bash
./run_bot.sh
```

## Usage 📱

*   **Track**: "Taxi 15" -> `Saved: Transport 15€`
*   **Analyze**: "Total this month?" -> `Your total is 450€`
*   **Edit**: "Change #3 to 10€" -> `Updated #3`

## License
MIT
