import os
import json
import logging
from dotenv import load_dotenv
from openai import AsyncOpenAI, RateLimitError, AuthenticationError

# Import our tools
import tools

# Load .env
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    logger.error("❌ Fatal Error: OPENAI_API_KEY not found! Please check .env file.")
else:
    logger.info(f"✅ OpenAI Key loaded: {api_key[:8]}...")

# Initialize client
client = AsyncOpenAI(api_key=api_key, max_retries=0)

# --------------------------
# Tool Definitions (Schema)
# --------------------------
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_sheet_url",
            "description": "Get the URL of the Google Accounting Sheet to show to the user.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_to_sheet",
            "description": "Record an expense or income item to the accounting sheet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "item_name": {"type": "string", "description": "Name of the item bought or sold"},
                    "amount": {"type": "number", "description": "Cost or value of the item in Euro (or original currency) (number only)"},
                    "category": {"type": "string", "description": "Category: Food, Drinks, Clothes, Leisure, AI Tools, Skincare, Gifts, Health, Travel, Transport, Pet Care, Others"},
                    "date": {"type": "string", "description": "Date of the expense in 'YYYY-MM-DD' format. If user says 'yesterday', calculate the date."},
                    "currency": {"type": "string", "description": "Currency symbol or code (e.g. €, $, CNY, JPY). Default to '€' if not specified."},
                    "note": {"type": "string", "description": "Optional note or remark"}
                },
                "required": ["item_name", "amount", "category"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_calendar_event",
            "description": "Create a new event in the Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "summary": {"type": "string", "description": "Title of the event"},
                    "start_time_str": {"type": "string", "description": "Start time in 'YYYY-MM-DD HH:MM' format"},
                    "duration_minutes": {"type": "integer", "description": "Duration in minutes (default 60)"}
                },
                "required": ["summary", "start_time_str"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_calendar_events",
            "description": "List upcoming calendar events to check availability or find Event IDs for deletion/modification.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Max number of events to list (default 10)."}
                },
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_calendar_event",
            "description": "Update/Modify an existing calendar event. You MUST list events first to get the Event ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The Event ID to update."},
                    "summary": {"type": "string", "description": "New title (optional)."},
                    "start_time_str": {"type": "string", "description": "New start time 'YYYY-MM-DD HH:MM' (optional)."},
                    "duration_minutes": {"type": "integer", "description": "New duration in minutes (optional)."}
                },
                "required": ["event_id"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_calendar_event",
            "description": "Delete a calendar event. You MUST list events first to get the Event ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "event_id": {"type": "string", "description": "The Event ID to delete."}
                },
                "required": ["event_id"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_last_row",
            "description": "Delete the last recorded expense/row from the sheet (Undo). Use this when user says 'delete', 'undo', 'remove last'.",
            "parameters": {
                "type": "object",
                "properties": {},
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_specific_row",
            "description": "Delete a specific row by its Item ID (row number). Use this when user says 'delete item 5' or 'remove #3'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_id": {"type": "integer", "description": "The row number/ID to delete (e.g. 5, 10)."}
                },
                "required": ["row_id"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "update_specific_row",
            "description": "Modify/Update an existing expense by its Item ID (row number). Use this when user says 'change amount of item 5 to 50' or 'rename #3 to Pizza'.",
            "parameters": {
                "type": "object",
                "properties": {
                    "row_id": {"type": "integer", "description": "The row number/ID to update."},
                    "item_name": {"type": "string", "description": "New item name (optional)."},
                    "amount": {"type": "number", "description": "New amount (number only) (optional)."},
                    "category": {"type": "string", "description": "New category (optional)."},
                    "date": {"type": "string", "description": "New date 'YYYY-MM-DD' (optional)."},
                    "currency": {"type": "string", "description": "Currency symbol if amount is changed (default '€')."},
                    "note": {"type": "string", "description": "New note (optional)."}
                },
                "required": ["row_id"]
            },
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate_total",
            "description": "Calculate total expenses for a specific period. You MUST convert natural language (e.g. 'this week') to actual dates (YYYY-MM-DD).",
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {"type": "string", "description": "Start date (inclusive) in 'YYYY-MM-DD' format."},
                    "end_date": {"type": "string", "description": "End date (inclusive) in 'YYYY-MM-DD' format."}
                },
                "required": ["start_date", "end_date"]
            },
        }
    }
]

async def get_agent_response(conversation_history):
    try:
        logger.info(f"Sending request to OpenAI, history length: {len(conversation_history)}")
        
        # 1. First Call: Send conversation + tools to OpenAI
        response = await client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation_history,
            tools=TOOLS_SCHEMA,
            tool_choice="auto" 
        )
        
        response_message = response.choices[0].message
        
        # 2. Check if OpenAI wants to call a tool
        if response_message.tool_calls:
            logger.info("🛠️  OpenAI decided to use tools!")
            
            # Append the assistant's "thought" (tool call request) to history
            # IMPORTANT: Convert to dict for JSON serialization compatibility
            conversation_history.append(response_message.model_dump())
            
            # Execute each tool call requested
            for tool_call in response_message.tool_calls:
                function_name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                logger.info(f"Testing Tool: {function_name} with args: {args}")
                
                tool_result = "Error: Unknown tool"
                
                # Setup mapping
                if function_name == "get_sheet_url":
                    tool_result = tools.get_sheet_url()
                elif function_name == "append_to_sheet":
                    tool_result = tools.append_to_sheet(**args)
                elif function_name == "create_calendar_event":
                    tool_result = tools.create_calendar_event(**args)
                elif function_name == "list_calendar_events":
                    tool_result = tools.list_calendar_events(**args)
                elif function_name == "update_calendar_event":
                    tool_result = tools.update_calendar_event(**args)
                elif function_name == "delete_calendar_event":
                    tool_result = tools.delete_calendar_event(**args)
                elif function_name == "delete_last_row":
                    tool_result = tools.delete_last_row()
                elif function_name == "delete_specific_row":
                    tool_result = tools.delete_specific_row(**args)
                elif function_name == "update_specific_row":
                    tool_result = tools.update_specific_row(**args)
                elif function_name == "calculate_total":
                    tool_result = tools.calculate_total(**args)
                
                # Add result to conversation
                conversation_history.append({
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": tool_result
                })
            
            # 3. Second Call: Send the tool results back to OpenAI to get the final answer
            logger.info("Sending tool results back to OpenAI...")
            final_response = await client.chat.completions.create(
                model="gpt-4o-mini",
                messages=conversation_history
            )
            reply = final_response.choices[0].message.content
            return reply

        else:
            # Normal text response
            reply = response_message.content
            logger.info("OpenAI response generated successfully (Text only)")
            return reply

    except RateLimitError:
        logger.error("❌ OpenAI API Quota Exceeded")
        return "⚠️ Error: OpenAI API Quota Exceeded (429). Please check your billing details at platform.openai.com."
    
    except AuthenticationError:
        logger.error("❌ OpenAI API Key Invalid")
        return "⚠️ Error: OpenAI API Key is invalid. Please check your .env file."

    except Exception as e:
        logger.error(f"❌ OpenAI call critical error: {e}")
        return f"⚠️ System error: {str(e)}"