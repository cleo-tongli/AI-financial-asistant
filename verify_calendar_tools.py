import tools
import datetime
import time

def verify_calendar_tools():
    print("🚀 Starting Calendar Tools Verification...")
    
    # 1. Create a test event
    print("\n1️⃣ Creating a test event...")
    start_time = (datetime.datetime.now() + datetime.timedelta(days=1)).replace(hour=14, minute=0).strftime('%Y-%m-%d %H:%M')
    result = tools.create_calendar_event("Test Auto-Deletion Event", start_time)
    print(f"   Result: {result}")
    
    # 2. List events to find it
    print("\n2️⃣ Listing upcoming events...")
    events_list_str = tools.list_calendar_events(max_results=5)
    print(f"   Result:\n{events_list_str}")
    
    # Extract ID (This is a simplified extraction, assuming format)
    # Expected format: "- ID: <id> | <time> | <summary>"
    import re
    # We look for the LAST occurrence or just any.
    match = re.search(r"ID: (\w+) \|.*?\| Test Auto-Deletion Event", events_list_str)
    if not match:
        print("❌ Could not find the created event in the list!")
        return
        
    event_id = match.group(1)
    print(f"   ✅ Found Event ID: {event_id}")
    
    # 3. Update the event
    print(f"\n3️⃣ Updating event {event_id}...")
    update_result = tools.update_calendar_event(event_id, summary="Updated Test Event", duration_minutes=90)
    print(f"   Result: {update_result}")
    
    # Verify update by listing again
    print("\n   Verifying update...")
    events_list_str_2 = tools.list_calendar_events(max_results=5)
    if "Updated Test Event" in events_list_str_2:
        print("   ✅ Update verified in list.")
    else:
        print("   ❌ Update NOT found in list.")
        
    # 4. Delete the event
    print(f"\n4️⃣ Deleting event {event_id}...")
    delete_result = tools.delete_calendar_event(event_id)
    print(f"   Result: {delete_result}")
    
    # Verify deletion
    print("\n   Verifying deletion...")
    events_list_str_3 = tools.list_calendar_events(max_results=5)
    if event_id not in events_list_str_3:
         print("   ✅ Deletion verified (ID not found).")
    else:
         print("   ❌ Event ID still found in list!")

if __name__ == "__main__":
    verify_calendar_tools()
