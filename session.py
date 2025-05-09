import sqlite3
import json
import os
from tabulate import tabulate

def check_ui_sessions_db():
    """Check all entries in the ui_sessions.db file."""
    
    # Path to the database
    db_path = "./db/ui_sessions.db"
    
    # Check if the database file exists
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get table names
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    if not tables:
        print("No tables found in the database.")
        conn.close()
        return
    
    print(f"Tables in the database: {[table[0] for table in tables]}\n")
    
    # For each table, display its structure and contents
    for table in tables:
        table_name = table[0]
        print(f"Table: {table_name}")
        
        # Get table structure
        cursor.execute(f"PRAGMA table_info({table_name})")
        columns = cursor.fetchall()
        print("Table structure:")
        headers = ["Column ID", "Name", "Type", "NotNull", "DefaultValue", "PK"]
        print(tabulate([list(col) for col in columns], headers=headers))
        print()
        
        # Get table contents
        cursor.execute(f"SELECT * FROM {table_name}")
        rows = cursor.fetchall()
        
        if not rows:
            print("No data in this table.\n")
            continue
        
        print(f"Number of rows: {len(rows)}")
        print("Table contents:")
        
        # Get column names for the headers
        column_names = [col[1] for col in columns]
        
        # Format the data for display
        formatted_rows = []
        for row in rows:
            formatted_row = list(row)
            
            # Pretty-print JSON fields
            for i, value in enumerate(formatted_row):
                if isinstance(value, str) and (value.startswith('{') or value.startswith('[')):
                    try:
                        json_obj = json.loads(value)
                        # For messages, just show the count to avoid cluttering the output
                        if column_names[i] == 'messages':
                            formatted_row[i] = f"[{len(json_obj)} messages]"
                        else:
                            formatted_row[i] = json.dumps(json_obj, indent=2)
                    except json.JSONDecodeError:
                        pass  # Not valid JSON, leave as is
            
            formatted_rows.append(formatted_row)
        
        print(tabulate(formatted_rows, headers=column_names))
        print("\n" + "-"*80 + "\n")
        
        # If this is the chat_history table, show detailed message content for each user
        if table_name == 'chat_history':
            print("Detailed message content:")
            for row in rows:
                user_id = row[0]  # Assuming user_id is the first column
                messages_json = row[1]  # Assuming messages is the second column
                
                try:
                    messages = json.loads(messages_json)
                    print(f"\nUser ID: {user_id}")
                    print(f"Number of messages: {len(messages)}")
                    
                    for i, msg in enumerate(messages):
                        role = msg.get('role', 'unknown')
                        content = msg.get('content', '')
                        print(f"\nMessage {i+1} ({role}):")
                        print(content[:200] + "..." if len(content) > 200 else content)
                    
                    print("\n" + "-"*40)
                except json.JSONDecodeError:
                    print(f"Could not parse messages for user {user_id}")
    
    # Close the connection
    conn.close()

if __name__ == "__main__":
    check_ui_sessions_db()