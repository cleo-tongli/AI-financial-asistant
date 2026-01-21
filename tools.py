import os
import re
import datetime
import logging
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Define scopes
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/drive'
]

SERVICE_ACCOUNT_FILE = 'service_account.json'

def get_creds():
    """
    Load service account credentials.
    Note: In a production environment, this should be cached to reduce disk I/O.
    """
    try:
        creds = Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=SCOPES
        )
        return creds
    except FileNotFoundError:
        logger.error(f"Credentials file not found: {SERVICE_ACCOUNT_FILE}")
        raise

# --------------------------
# Google Sheets Function Implementation
# --------------------------

def append_to_sheet(item_name, amount, category, date=None, currency="€", note=""):
    """
    Append a consumption record to the specified Google Sheet.
    Parameters are parsed and passed by LLM.
    """
    try:
        creds = get_creds()
        # gspread authorization
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        
        # Open the worksheet, defaulting to the first Sheet
        sheet = client.open_by_key(sheet_id).sheet1
        
        # Get current time or use provided date
        if date:
            # If date is provided (YYYY-MM-DD), use it with current time
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            timestamp = f"{date} {current_time}"
        else:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Build data row
        # Let's save it to the note column to be safe: "Currency: USD" etc.
        # User requested to NOT separate number and currency, even on phone.
        # So we write "50€" into the amount column nicely.
        amount_str = f"{amount}{currency}"
        
        # We can still keep the currency in note for backup if needed, but keeping it clean.
        full_note = note
        
        row_data = [timestamp, item_name, amount_str, category, full_note]
        
        # Calculate Row ID (Values count + 1 for the new row)
        # Note: This is an estimation. If concurrent writes happen, it might be off, 
        # but for a single user bot, it's safe enough.
        # gspread doesn't return the row number on append, so we check first.
        # Actually, appending first then getting len might be safer? 
        # No, len changes.
        # Let's get current len, then append. 
        # Row ID = current_len + 1.
        existing_rows = len(sheet.get_all_values())
        row_id = existing_rows + 1
        
        # Execute append operation
        sheet.append_row(row_data)
        
        amount_str = f"{amount}{currency}"
        # Return format: Saved: YYYY-MM-DD #ID Item Amount (Category)
        date_only = timestamp.split(' ')[0]
        msg = f"Saved: {date_only} #{row_id} {item_name} {amount_str} ({category})"
        logger.info(msg)
        return msg
        
    except Exception as e:
        logger.error(f"Google Sheets operation failed: {e}")
        return f"❌ Recording failed, error details: {str(e)}"

def delete_specific_row(row_id):
    """
    Deletes a specific row by its ID (Row Number).
    """
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id).sheet1
        
        row_int = int(row_id)
        
        # Safety Check
        all_values = sheet.get_all_values()
        if row_int < 1 or row_int > len(all_values) + 5: 
             # Allow Row 1 (in case user has no header)
             return f"⚠️ Invalid Row ID: {row_id}. (Max is {len(all_values)})"
             
        # Gspread delete_rows takes index (1-based)
        sheet.delete_rows(row_int)
        
        return f"✅ Deleted record #{row_id}."
        
    except Exception as e:
        logger.error(f"Delete operation failed: {e}")
        return f"❌ Failed to delete: {str(e)}"

def delete_last_row():
    """
    Deletes the last row of data from the Google Sheet (Undo function).
    """
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id).sheet1
        
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
            return "⚠️ The sheet seems empty (or only has headers)."
            
        last_row_index = len(all_values)
        sheet.delete_rows(last_row_index)
        
        return f"✅ Deleted the last record (Row {last_row_index})."
        
    except Exception as e:
        logger.error(f"Delete operation failed: {e}")
        return f"❌ Failed to delete: {str(e)}"

def update_specific_row(row_id, item_name=None, amount=None, category=None, date=None, currency="€", note=None):
    """
    Updates a specific row by its ID (Row Number).
    Only updates fields that are provided (not None).
    """
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id).sheet1
        
        row_int = int(row_id)
        
        # 1. Get current values to preserve unspecified fields
        # Note: gspread uses 1-based indexing for rows and cols.
        # Column mapping: 1=Date, 2=Item, 3=Amount, 4=Category, 5=Note
        
        # We fetch the specific row range, e.g. "A5:E5"
        # Assuming we stick to 5 columns.
        range_name = f"A{row_int}:E{row_int}"
        cell_values = sheet.get(range_name)
        
        if not cell_values or not cell_values[0]:
            return f"⚠️ Row {row_id} seems empty or invalid."
            
        current_row = cell_values[0] # List of strings
        # Pad with empty strings if row is short
        while len(current_row) < 5:
            current_row.append("")
            
        # 2. Update fields
        # Date (Col 1)
        if date:
            # Append time if needed, or just keep date
            # To keep it simple and consistent with append:
            current_time = datetime.datetime.now().strftime("%H:%M:%S")
            current_row[0] = f"{date} {current_time}"
            
        # Item Name (Col 2)
        if item_name:
            current_row[1] = item_name
            
        # Amount (Col 3) - Special handling for Currency
        if amount is not None:
             # If new amount, overwrite with "{amount}{currency}"
             # Logic: If user says "change amount to 50", we use default currency '€' unless specified?
             # Tools signature has default currency="€".
             current_row[2] = f"{amount}{currency}"
        
        # Category (Col 4)
        if category:
            current_row[3] = category
            
        # Note (Col 5)
        if note:
            current_row[4] = note
            
        # 3. Write back
        # gspread update usage: update(range_name, values=...) or update(range_name, [[...]])
        # Fix: positional arguments for older versions or strictly conform to (range, values)
        sheet.update(range_name, [current_row])
        
        return f"✅ Updated record #{row_id}: {current_row[1]} {current_row[2]} ({current_row[3]})"

    except Exception as e:
        logger.error(f"Update operation failed: {e}")
        return f"❌ Failed to update: {str(e)}"

def get_sheet_url():
    """
    Returns the URL of the Google Sheet.
    """
    sheet_id = os.getenv("GOOGLE_SHEET_ID")
    if not sheet_id:
        return "❌ Error: GOOGLE_SHEET_ID not found in .env"
    return f"https://docs.google.com/spreadsheets/d/{sheet_id}"

# --------------------------
# Google Calendar Function Implementation
# --------------------------

def create_calendar_event(summary, start_time_str, duration_minutes=60):
    """
    Create a calendar event.
    start_time_str must be in 'YYYY-MM-DD HH:MM' format.
    """
    try:
        creds = get_creds()
        # Build Calendar Service
        service = build('calendar', 'v3', credentials=creds)
        calendar_id = os.getenv("GOOGLE_CALENDAR_ID")
        
        # Parse time format
        try:
            start_dt = datetime.datetime.strptime(start_time_str, "%Y-%m-%d %H:%M")
        except ValueError:
            return "❌ Invalid time format. Please use 'YYYY-MM-DD HH:MM' format."

        # Calculate end time
        end_dt = start_dt + datetime.timedelta(minutes=duration_minutes)
        
        # Define Event Body - Following Google API specifications
        event_body = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'Asia/Shanghai', # Modify time zone as needed
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'Asia/Shanghai',
            },
        }
        
        # Call API to insert event
        event_result = service.events().insert(
            calendarId=calendar_id, 
            body=event_body
        ).execute()
        
        link = event_result.get('htmlLink')
        return f"📅 Schedule created: '{summary}' \nTime: {start_time_str}\nLink: {link}"
        
    except Exception as e:
        logger.error(f"Google Calendar operation failed: {e}")
        return f"❌ Failed to create schedule, error details: {str(e)}"

def calculate_total(start_date=None, end_date=None):
    """
    Calculate total expenses within a date range (inclusive).
    start_date, end_date: 'YYYY-MM-DD' strings.
    """
    try:
        creds = get_creds()
        client = gspread.authorize(creds)
        sheet_id = os.getenv("GOOGLE_SHEET_ID")
        sheet = client.open_by_key(sheet_id).sheet1
        
        all_values = sheet.get_all_values()
        if len(all_values) <= 1:
             return "0.00 (Sheet empty)"
             
        total = 0.0
        row_count = 0
        
        # Convert range to datetime for comparison
        # Defaults: if start is None, assume ancient past. If end is None, assume future.
        # But usually AI passes them.
        
        start_dt = None
        end_dt = None
        
        if start_date:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
        if end_date:
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            # Set end_dt to end of that day
            end_dt = end_dt.replace(hour=23, minute=59, second=59)

        # Iterate ALL rows (User might not have a header)
        for row in all_values:
            # Expected Row: [Date, Item, Amount, Category, Note]
            if len(row) < 3:
                continue
                
            date_str = row[0] 
            amount_str = row[2]
            
            # 1. Check Date
            # Date format in sheet might be "YYYY-MM-DD" or "YYYY-MM-DD HH:MM:SS"
            try:
                # Take first 10 chars for YYYY-MM-DD
                # If date_str is "Date" (Header), this raises ValueError -> Skipped correctly
                row_date_dt = datetime.datetime.strptime(date_str[:10], "%Y-%m-%d")
                
                if start_dt and row_date_dt < start_dt:
                    continue
                if end_dt and row_date_dt > end_dt:
                    continue
                    
            except ValueError:
                # Skip invalid dates (including Header row "Date")
                continue
                
            # 2. Parse Amount (remove currency like €, $, USD)
            try:
                # Use regex to find number (integer or float)
                # Matches "12.34", "12", "12,34" 
                # Limitation: European style 1.000,00 might need care.
                # Assuming simple float with dot or comma.
                # Remove everything except digits, dot, comma, minus
                clean_str = re.sub(r'[^\d.,-]', '', amount_str).replace(',', '.')
                val = float(clean_str)
                total += val
                row_count += 1
            except ValueError:
                continue
                
        return f"{total:.2f}"
    
    except Exception as e:
        logger.error(f"Calculation failed: {e}")
        return f"Error: {e}"