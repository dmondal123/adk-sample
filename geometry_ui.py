import streamlit as st
import requests
import json
import os
from dotenv import load_dotenv
from openai import OpenAI
import re

# Load environment variables
load_dotenv()
openai_api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=openai_api_key)

st.set_page_config(page_title="Geometry Chatbot", page_icon="📐", layout="wide")

# Initialize session state for chat history
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your geometry assistant. I can help you calculate the area and perimeter of rectangles. What would you like to know?"}
    ]

# Initialize session state for rectangle dimensions
if "length" not in st.session_state:
    st.session_state.length = 5.0
if "width" not in st.session_state:
    st.session_state.width = 3.0

st.title("📐 Geometry Chatbot")

# Add information about running the services in the sidebar
with st.sidebar:
    st.subheader("Service Information")
    st.info("""
    Make sure the following services are running:
    - Area Agent: http://localhost:8004
    - Perimeter Agent: http://localhost:8005

    To start the services, run:
    ```
    python -m agents.area_agent.__main__
    python -m agents.perimeter_agent.__main__
    ```
    """)

# Function to determine which agent to call using LLM
def determine_calculation(query, length, width):
    try:
        # Create a prompt for the LLM
        prompt = f"""
        You are a geometry assistant that helps route calculation requests to the appropriate service.
        
        Available services:
        - Area Agent: Calculates the area of rectangles
        - Perimeter Agent: Calculates the perimeter of rectangles
        
        User query: "{query}"
        Rectangle dimensions: length={length}, width={width}
        
        Determine which calculation(s) the user wants to perform. Respond with one of:
        - "area": if only area calculation is needed
        - "perimeter": if only perimeter calculation is needed
        - "both": if both area and perimeter calculations are needed
        - "none": if no calculation is needed (just a conversation)
        
        Just return the single word answer without explanation.
        """
        
        # Call the OpenAI API using the client
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=10
        )
        
        # Extract the decision
        decision = response.choices[0].message.content.strip().lower()
        
        # Validate the decision
        if decision not in ["area", "perimeter", "both", "none"]:
            print(f"Unexpected LLM response: {decision}. Defaulting to 'none'.")
            return "none"
        
        return decision
    except Exception as e:
        print(f"Error determining calculation type: {str(e)}")
        return "none"  # Default to none if there's an error

# Function to extract dimensions from message
def extract_dimensions(message):
    # Try to find dimensions in the message
    length_pattern = r'length\s*[=:is]*\s*(\d+\.?\d*)'
    width_pattern = r'width\s*[=:is]*\s*(\d+\.?\d*)'
    
    length_match = re.search(length_pattern, message, re.IGNORECASE)
    width_match = re.search(width_pattern, message, re.IGNORECASE)
    
    length = float(length_match.group(1)) if length_match else None
    width = float(width_match.group(1)) if width_match else None
    
    return length, width

# Function to call the appropriate agent(s)
def perform_calculation(calc_type, length, width):
    payload = {
        "length": length,
        "width": width
    }
    
    results = {}
    
    try:
        # Call area agent if needed
        if calc_type in ["area", "both"]:
            area_response = requests.post("http://localhost:8004/run", json=payload)
            if area_response.ok:
                results["area"] = area_response.json()
            else:
                results["area_error"] = f"Error: {area_response.status_code} - {area_response.text}"
        
        # Call perimeter agent if needed
        if calc_type in ["perimeter", "both"]:
            perimeter_response = requests.post("http://localhost:8005/run", json=payload)
            if perimeter_response.ok:
                results["perimeter"] = perimeter_response.json()
            else:
                results["perimeter_error"] = f"Error: {perimeter_response.status_code} - {perimeter_response.text}"
        
        return results
    except Exception as e:
        return {"error": f"Failed to calculate: {str(e)}"}

# Function to generate response based on calculation results
def generate_response(calc_type, results, length, width):
    if "error" in results:
        return results["error"]
    
    response_parts = []
    
    if calc_type in ["area", "both"] and "area" in results:
        response_parts.append(results["area"]["result"])
    elif calc_type in ["area", "both"] and "area_error" in results:
        response_parts.append(results["area_error"])
    
    if calc_type in ["perimeter", "both"] and "perimeter" in results:
        response_parts.append(results["perimeter"]["result"])
    elif calc_type in ["perimeter", "both"] and "perimeter_error" in results:
        response_parts.append(results["perimeter_error"])
    
    if not response_parts:
        return "I'm not sure what calculation you want me to perform. Please specify if you want the area, perimeter, or both."
    
    return "\n\n".join(response_parts)

# Function to generate HTML for rectangle visualization
def generate_rectangle_html(length, width, calc_type):
    # Scale the rectangle for display
    scale = 30
    rect_height = min(width * scale, 200)
    rect_width = min(length * scale, 400)
    
    # Determine styling based on which calculations were performed
    bg_color = "rgba(76, 175, 80, 0.5)" if calc_type in ["area", "both"] else "transparent"
    border = "3px solid #FF5722" if calc_type in ["perimeter", "both"] else "none"
    
    # Create HTML for the rectangle
    html = f"""
    <div style="
        width: {rect_width}px;
        height: {rect_height}px;
        background-color: {bg_color};
        border: {border};
        display: flex;
        align-items: center;
        justify-content: center;
        color: black;
        font-weight: bold;
        margin: 10px 0;
    ">
        {length} × {width}
    </div>
    """
    return html

# Display chat messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        
        # If this is an assistant message with a visualization tag, display the rectangle
        if message["role"] == "assistant" and "[[VISUALIZATION]]" in message["content"]:
            # Extract calculation type from the message
            if "area" in message["content"].lower() and "perimeter" in message["content"].lower():
                calc_type = "both"
            elif "area" in message["content"].lower():
                calc_type = "area"
            elif "perimeter" in message["content"].lower():
                calc_type = "perimeter"
            else:
                calc_type = "none"
            
            # Only show visualization if it's a calculation
            if calc_type != "none":
                html = generate_rectangle_html(st.session_state.length, st.session_state.width, calc_type)
                st.markdown(html, unsafe_allow_html=True)

# Chat input
if prompt := st.chat_input("Ask me about rectangle calculations..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user"):
        st.markdown(prompt)
    
    # Check if user specified new dimensions
    new_length, new_width = extract_dimensions(prompt)
    if new_length:
        st.session_state.length = new_length
    if new_width:
        st.session_state.width = new_width
    
    # Determine which calculation to perform
    calc_type = determine_calculation(prompt, st.session_state.length, st.session_state.width)
    
    # Generate response based on calculation type
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            if calc_type == "none":
                # Just have a conversation without calculation
                response = client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "You are a helpful geometry assistant that specializes in rectangles. Keep responses brief and friendly."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.7,
                    max_tokens=150
                )
                assistant_response = response.choices[0].message.content
            else:
                # Perform calculation and generate response
                results = perform_calculation(calc_type, st.session_state.length, st.session_state.width)
                assistant_response = generate_response(calc_type, results, st.session_state.length, st.session_state.width)
                
                # Add visualization tag if it's a calculation
                assistant_response += "\n\n[[VISUALIZATION]]"
            
            st.markdown(assistant_response)
            
            # If there's a visualization tag, display the rectangle
            if "[[VISUALIZATION]]" in assistant_response:
                html = generate_rectangle_html(st.session_state.length, st.session_state.width, calc_type)
                st.markdown(html, unsafe_allow_html=True)
    
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": assistant_response}) 