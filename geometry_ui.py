import streamlit as st
import requests
import re
import sqlite3
import json
import uuid
import os

# Ensure the db directory exists
os.makedirs("./db", exist_ok=True)

# Function to get or create a user ID
def get_user_id():
    if "user_id" not in st.session_state:
        # Generate a unique user ID if not already present
        st.session_state.user_id = str(uuid.uuid4())
    return st.session_state.user_id

# Function to load chat history from SQLite
def load_chat_history(user_id):
    conn = sqlite3.connect("./db/ui_sessions.db")
    cursor = conn.cursor()
    
    # Create table if it doesn't exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS chat_history (
        user_id TEXT PRIMARY KEY,
        messages TEXT,
        length REAL,
        width REAL
    )
    ''')
    
    # Try to load existing history
    cursor.execute("SELECT messages, length, width FROM chat_history WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    
    if result:
        messages = json.loads(result[0])
        length = result[1]
        width = result[2]
    else:
        # Default values for new users
        messages = [
            {"role": "assistant", "content": "Hello! I'm your geometry assistant. I can help you calculate the area and perimeter of rectangles. Just tell me the dimensions (e.g., 'Calculate the area of a rectangle with length 5 and width 3')."}
        ]
        length = 5.0
        width = 3.0
        
        # Insert default values
        cursor.execute(
            "INSERT INTO chat_history (user_id, messages, length, width) VALUES (?, ?, ?, ?)",
            (user_id, json.dumps(messages), length, width)
        )
        conn.commit()
    
    conn.close()
    return messages, length, width

# Function to save chat history to SQLite
def save_chat_history(user_id, messages, length, width):
    conn = sqlite3.connect("./db/ui_sessions.db")
    cursor = conn.cursor()
    
    cursor.execute(
        "UPDATE chat_history SET messages = ?, length = ?, width = ? WHERE user_id = ?",
        (json.dumps(messages), length, width, user_id)
    )
    
    conn.commit()
    conn.close()

# Set up the Streamlit page
st.set_page_config(page_title="ADK-Powered Geometry Calculator", page_icon="📐")
st.title("📐 ADK-Powered Geometry Calculator")

# Get user ID and load session data
user_id = get_user_id()
messages, length, width = load_chat_history(user_id)

# Initialize session state with loaded values
if "messages" not in st.session_state:
    st.session_state.messages = messages
if "length" not in st.session_state:
    st.session_state.length = length
if "width" not in st.session_state:
    st.session_state.width = width

# Function to extract dimensions from message
def extract_dimensions(message):
    length_pattern = r'length\s*[=:is]*\s*(\d+\.?\d*)'
    width_pattern = r'width\s*[=:is]*\s*(\d+\.?\d*)'
    
    # Also match patterns like "5 by 3" or "rectangle of 5x3"
    rectangle_pattern = r'(\d+\.?\d*)\s*(?:by|x)\s*(\d+\.?\d*)'
    
    length = None
    width = None
    
    # Check for explicit length/width
    length_match = re.search(length_pattern, message, re.IGNORECASE)
    if length_match:
        length = float(length_match.group(1))
    
    width_match = re.search(width_pattern, message, re.IGNORECASE)
    if width_match:
        width = float(width_match.group(1))
    
    # If not found, check for "X by Y" pattern
    if length is None or width is None:
        rect_match = re.search(rectangle_pattern, message, re.IGNORECASE)
        if rect_match:
            length = float(rect_match.group(1))
            width = float(rect_match.group(2))
    
    return length, width

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Add service information in the sidebar
with st.sidebar:
    st.subheader("Service Information")
    st.info("""
    Make sure the following services are running:
    - Area Agent: http://localhost:8004
    - Perimeter Agent: http://localhost:8005
    - Geometry Host Agent: http://localhost:8006
    """)
    
    
    # Display user ID (for debugging)
    st.subheader("Session Information")
    st.write(f"User ID: {user_id}")

# Chat input
if prompt := st.chat_input("Ask me about rectangle calculations..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Extract dimensions from the message
    new_length, new_width = extract_dimensions(prompt)
    
    # Update dimensions if provided in the message
    if new_length is not None:
        st.session_state.length = new_length
    if new_width is not None:
        st.session_state.width = new_width
    
    # Generate response based on user query
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            # Call the host agent
            payload = {
                "request": prompt,
                "parameters": {
                    "length": st.session_state.length,
                    "width": st.session_state.width
                }
            }
            
            try:
                response = requests.post("http://localhost:8006/run", json=payload)
                response.raise_for_status()
                result = response.json()
                
                # Create a visual representation of the rectangle
                scale = 30
                rect_height = min(st.session_state.width * scale, 200)
                rect_width = min(st.session_state.length * scale, 400)
                
                # Format the initial response with placeholders
                assistant_response = f"""
                **Rectangle Calculations:**
                
                For a rectangle with length {st.session_state.length} and width {st.session_state.width}:
                """
                
                # Extract values from the agent response
                if isinstance(result, dict):
                    # Check if we have a summary field (from the host agent)
                    if "summary" in result:
                        assistant_response = result.get("summary", "")
                    else:
                        # Check for area and perimeter in the result
                        if "area" in result:
                            area_value = result.get("area")
                            if area_value and area_value != "No area calculation returned.":
                                assistant_response += f"\nArea: {area_value}"
                            
                        if "perimeter" in result:
                            perimeter_value = result.get("perimeter")
                            if perimeter_value and perimeter_value != "No perimeter calculation returned.":
                                assistant_response += f"\nPerimeter: {perimeter_value}"
                        
                        # If we have a result field (from individual agents)
                        if "result" in result and not ("area" in result or "perimeter" in result):
                            result_text = result.get("result", "")
                            assistant_response = result_text
                
                st.markdown(assistant_response)
                
                # Display rectangle visualization
                rect_html = f"""
                <div style="
                    width: {rect_width}px;
                    height: {rect_height}px;
                    background-color: rgba(76, 175, 80, 0.5);
                    border: 3px solid #FF5722;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    color: black;
                    font-weight: bold;
                    margin: 10px 0;
                ">
                    {st.session_state.length} × {st.session_state.width}
                </div>
                """
                st.markdown(rect_html, unsafe_allow_html=True)
            except Exception as e:
                assistant_response = f"Sorry, I encountered an error: {str(e)}"
                st.error(assistant_response)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": assistant_response})
    
    # Save the updated state to the database
    save_chat_history(
        user_id, 
        st.session_state.messages, 
        st.session_state.length, 
        st.session_state.width
    )