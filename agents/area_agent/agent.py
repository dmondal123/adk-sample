from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
import json
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
MODEL_GPT_4O = "openai/gpt-4o"

# Ensure the directory exists
os.makedirs("./db", exist_ok=True)

# Define the calculate_area tool
def calculate_area(length: float, width: float) -> dict:
    """Calculates the area of a rectangle.
    
    Args:
        length (float): The length of the rectangle.
        width (float): The width of the rectangle.
        
    Returns:
        dict: A dictionary containing the calculation result.
              Includes 'area' (the calculated area) and 'unit' (square units).
    """
    print(f"--- Tool: calculate_area called with length={length}, width={width} ---")
    area = length * width
    return {
        "area": area,
        "unit": "square units"
    }

# Define the area agent
area_agent = Agent(
    name="area_agent",
    model=LiteLlm(model=MODEL_GPT_4O),
    description="Calculates the area of rectangles.",
    instruction="You are a specialized agent that calculates the area of rectangles. "
                "When asked about area calculations, use the 'calculate_area' tool. "
                "Only handle questions about calculating area. "
                "Provide clear, concise responses with the calculated area.",
    tools=[calculate_area],
)

# Setup session service and runner
db_url = "sqlite:///./db/area_agent_sessions.db"
session_service = DatabaseSessionService(db_url=db_url)

runner = Runner(
    agent=area_agent,
    app_name="area_app",
    session_service=session_service
)

USER_ID = "user_area"
SESSION_ID = "session_area"

async def execute(request):
    # Ensure session exists
    try:
        session_service.create_session(
            app_name="area_app",
            user_id=USER_ID,
            session_id=SESSION_ID
        )
    except Exception as e:
        # Session might already exist, which is fine
        print(f"Note: {e}")

    # Extract rectangle dimensions from request
    length = request.get('length', 0)
    width = request.get('width', 0)

    prompt = f"Calculate the area of a rectangle with length {length} and width {width}."

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
        if event.is_final_response():
            response_text = event.content.parts[0].text
            try:
                # Try to extract area calculation from response
                # This is a simple approach - you might need more sophisticated parsing
                return {"result": response_text, "raw_response": response_text}
            except Exception as e:
                print(f"❌ Error processing response: {e}")
                return {"result": response_text, "error": str(e)} 