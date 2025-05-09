# @title Import necessary libraries
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import DatabaseSessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts

import warnings
# Ignore all warnings
warnings.filterwarnings("ignore")

import logging
logging.basicConfig(level=logging.ERROR)

print("Libraries imported.")

os.environ['OPENAI_API_KEY'] = ''

MODEL_GPT_4O = "openai/gpt-4o"

# @title Define the get_weather Tool
def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city (e.g., "New York", "London", "Tokyo").

    Returns:
        dict: A dictionary containing the weather information.
              Includes a 'status' key ('success' or 'error').
              If 'success', includes a 'report' key with weather details.
              If 'error', includes an 'error_message' key.
    """
    print(f"--- Tool: get_weather called for city: {city} ---") # Log tool execution
    city_normalized = city.lower().replace(" ", "") # Basic normalization

    # Mock weather data
    mock_weather_db = {
        "newyork": {"status": "success", "report": "The weather in New York is sunny with a temperature of 25°C."},
        "london": {"status": "success", "report": "It's cloudy in London with a temperature of 15°C."},
        "tokyo": {"status": "success", "report": "Tokyo is experiencing light rain and a temperature of 18°C."},
    }

    if city_normalized in mock_weather_db:
        return mock_weather_db[city_normalized]
    else:
        return {"status": "error", "error_message": f"Sorry, I don't have weather information for '{city}'."}

# @title Define the Weather Agent
weather_agent = Agent(
    name="weather_agent_v1",
    model = LiteLlm(model=MODEL_GPT_4O), # Can be a string for Gemini or a LiteLlm object
    description="Provides weather information for specific cities.",
    instruction="You are a helpful weather assistant. "
                "When the user asks for the weather in a specific city, "
                "use the 'get_weather' tool to find the information. "
                "If the tool returns an error, inform the user politely. "
                "If the tool is successful, present the weather report clearly.",
    tools=[get_weather], # Pass the function directly
)

print(f"Agent '{weather_agent.name}' created using model.")

# @title Setup Session Service and Runner

# --- Session Management ---
# Key Concept: SessionService stores conversation history & state.
# Using DatabaseSessionService with SQLite for persistent storage
from google.adk.sessions import DatabaseSessionService

# Create a SQLite database file in the current directory
db_url = "sqlite:///./weather_agent.db"
session_service = DatabaseSessionService(db_url=db_url)

# Define constants for identifying the interaction context
APP_NAME = "weather_tutorial_app"
USER_ID = "user_1"
SESSION_ID = "session_001" # Using a fixed ID for simplicity

# Create the specific session where the conversation will happen
# Check if the session already exists using try/except pattern
try:
    # Try to get the existing session
    session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"Existing session retrieved: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    print(f"Initial state: {session.state}")
except:
    # Create a new session if it doesn't exist
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    print(f"New session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    print(f"Initial state: {session.state}")

# --- Runner ---
# Key Concept: Runner orchestrates the agent execution loop.
runner = Runner(
    agent=weather_agent, # The agent we want to run
    app_name=APP_NAME,   # Associates runs with our app
    session_service=session_service # Uses our session manager
)
print(f"Runner created for agent '{runner.agent.name}'.")

# @title Define Agent Interaction Function

from google.genai import types # For creating message Content/Parts

async def call_agent_async(query: str, runner, user_id, session_id):
  """Sends a query to the agent and prints the final response."""
  print(f"\n>>> User Query: {query}")

  # Prepare the user's message in ADK format
  content = types.Content(role='user', parts=[types.Part(text=query)])

  final_response_text = "Agent did not produce a final response." # Default

  # Key Concept: run_async executes the agent logic and yields Events.
  # We iterate through events to find the final answer.
  async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
      # You can uncomment the line below to see *all* events during execution
      # print(f"  [Event] Author: {event.author}, Type: {type(event).__name__}, Final: {event.is_final_response()}, Content: {event.content}")

      # Key Concept: is_final_response() marks the concluding message for the turn.
      if event.is_final_response():
          if event.content and event.content.parts:
             # Assuming text response in the first part
             final_response_text = event.content.parts[0].text
          elif event.actions and event.actions.escalate: # Handle potential errors/escalations
             final_response_text = f"Agent escalated: {event.error_message or 'No specific message.'}"
          # Add more checks here if needed (e.g., specific error codes)
          break # Stop processing events once the final response is found

  print(f"<<< Agent Response: {final_response_text}")


# @title Run Interactive Conversation

# We need an async function to await our interaction helper
async def run_interactive_conversation():
    print("\n=== Weather Agent Interactive Chat ===")
    print("Type 'exit', 'quit', or 'bye' to end the conversation.")
    
    while True:
        # Get user input
        user_query = input("\nYou: ")
        
        # Check if user wants to exit
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("Ending conversation. Goodbye!")
            break
            
        # Process the query through the agent
        await call_agent_async(
            query=user_query,
            runner=runner,
            user_id=USER_ID,
            session_id=SESSION_ID
        )

# --- OR ---

# Uncomment the following lines if running as a standard Python script (.py file):
import asyncio
if __name__ == "__main__":
    try:
        asyncio.run(run_interactive_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")