# Run Yourself Like a Company

A **Personal Financial Assistant** bot that helps you track your expenses, manage your budget, and analyze your spending habits using Google Sheets and OpenAI. Treat your personal finance and schedule like a business.

## Features

### 1. Intelligent Expense Tracking
Record your daily expenses using natural language. The bot understands context, extracts key details, and organizes them automatically.

*   **Natural Language Input**: Simply send a message like "Spent 15 EUR on Lunch" or "Paid 50 USD for a taxi yesterday".
*   **Automatic Categorization**: The AI automatically assigns categories based on the item description (e.g., "Cinema" -> Leisure, "Pharmacy" -> Health).
*   **Detailed Parsing**: Splits complex sentences into multiple entries (e.g., "Lunch 15 and Dinner 30" -> Two separate records).
*   **Data Integrity**: All data is saved directly to your private Google Sheet.

### 2. Google Calendar Management
Manage your schedule directly from the chat without switching apps.

*   **Schedule Meetings**: Create events by saying "Schedule a meeting with John tomorrow at 2 PM".
*   **Check Availability**: Ask "What do I have on my calendar for today?" to see your upcoming agenda.
*   **Modify & Update**: Easily change event details by asking "Change the 2 PM meeting to 3 PM".
*   **Delete Events**: Remove cancelled plans with commands like "Delete the meeting with John".

### 3. Financial Analysis & Management
*   **Instant Reporting**: Ask "How much did I spend this week?" or "Total spending on Food in January" for real-time calculations.
*   **Correction & Undo**: If you make a mistake, you can say "Undo" to remove the last entry, or "Delete item #5" to remove a specific row.

## Setup Guide

### 1. Prerequisites
*   Python 3.8+
*   A Telegram Account
*   OpenAI Account (with API credits)
*   Google Cloud Account (Free tier is sufficient)

### 2. Google Cloud Setup (Critical Step)
To allow the bot to read/write your Sheet and Calendar, you need a Service Account.

1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  **Create a New Project** (e.g., "AI-Finance-Bot").
3.  **Enable APIs**:
    *   Search for "Google Sheets API" -> Enable.
    *   Search for "Google Drive API" -> Enable.
    *   Search for "Google Calendar API" -> Enable.
4.  **Create Service Account**:
    *   Go to "IAM & Admin" -> "Service Accounts".
    *   Click "Create Service Account". Give it a name (e.g., "bot-account").
    *   Skip the role assignment (optional).
    *   Click "Done".
5.  **Generate Key**:
    *   Click on the newly created email address (e.g., `bot-account@project-id.iam.gserviceaccount.com`).
    *   Go to the "Keys" tab -> "Add Key" -> "Create new key" -> "JSON".
    *   **Download the JSON file** and rename it to `service_account.json`.
    *   **Move this file** to the root folder of this project.
6.  **Share Resources**:
    *   **Google Sheet**: Create a new Sheet. Click "Share" and add the **Service Account Email** (from step 5) as an **Editor**.
        *   *Tip*: Note down the ID of your Sheet from the URL: `docs.google.com/spreadsheets/d/YOUR_SHEET_ID/edit`
    *   **Google Calendar**: Go to your Calendar settings -> "Share with specific people" -> Add the **Service Account Email** -> "Make changes to events".
        *   *Tip*: You can use your primary calendar or create a dedicated one. Get the "Calendar ID" from settings (usually your email for primary).

### 3. Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/cleo-tongli/AI-financial-asistant.git
    cd AI-financial-asistant
    ```

2.  **Create a virtual environment**:
    ```bash
    python3 -m venv venv
    source venv/bin/activate  # Mac/Linux
    # venv\Scripts\activate   # Windows
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### 4. Configuration (.env)

Duplicate the example config:
```bash
cp .env.example .env
```

Edit the `.env` file with your details:

```ini
# From @BotFather on Telegram
TELEGRAM_TOKEN=123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11

# From OpenAI Platform
OPENAI_API_KEY=sk-proj-xxxxxxxx

# Your Google Sheet ID (from the URL)
GOOGLE_SHEET_ID=1A2B3C...

# Your Calender ID (usually your email, or custom ID)
GOOGLE_CALENDAR_ID=primary

# Your Telegram User ID (to prevent others from using your bot)
# Get it by messaging @userinfobot on Telegram
AUTHORIZED_USER_ID=123456789
```

### 5. Running the Bot

```bash
chmod +x run_bot.sh
./run_bot.sh
```

## Usage Examples

*   **Expense**: "Lunch 15.50" -> Saved to Sheet.
*   **Complex**: "Bought a new mouse for 20€ and a keyboard for 50€ yesterday" -> Splits into two entries with accurate dates.
*   **Calendar**: "Schedule a dentist appointment next Monday at 10am" -> Added to Calendar.

## License
MIT
