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

# Define the calculate_perimeter tool
def calculate_perimeter(length: float, width: float) -> dict:
    """Calculates the perimeter of a rectangle.
    
    Args:
        length (float): The length of the rectangle.
        width (float): The width of the rectangle.
        
    Returns:
        dict: A dictionary containing the calculation result.
              Includes 'perimeter' (the calculated perimeter) and 'unit' (units).
    """
    print(f"--- Tool: calculate_perimeter called with length={length}, width={width} ---")
    perimeter = 2 * (length + width)
    return {
        "perimeter": perimeter,
        "unit": "units"
    }

# Define the perimeter agent
perimeter_agent = Agent(
    name="perimeter_agent",
    model=LiteLlm(model=MODEL_GPT_4O),
    description="Calculates the perimeter of rectangles.",
    instruction="You are a specialized agent that calculates the perimeter of rectangles. "
                "When asked about perimeter calculations, use the 'calculate_perimeter' tool. "
                "Only handle questions about calculating perimeter. "
                "Provide clear, concise responses with the calculated perimeter.",
    tools=[calculate_perimeter],
)

# Setup session service and runner
db_url = "sqlite:///./db/perimeter_agent_sessions.db"
session_service = DatabaseSessionService(db_url=db_url)

runner = Runner(
    agent=perimeter_agent,
    app_name="perimeter_app",
    session_service=session_service
)

USER_ID = "user_perimeter"
SESSION_ID = "session_perimeter"

async def execute(request):
    # Ensure session exists
    try:
        session_service.create_session(
            app_name="perimeter_app",
            user_id=USER_ID,
            session_id=SESSION_ID
        )
    except Exception as e:
        # Session might already exist, which is fine
        print(f"Note: {e}")

    # Extract rectangle dimensions from request
    length = request.get('length', 0)
    width = request.get('width', 0)

    prompt = f"Calculate the perimeter of a rectangle with length {length} and width {width}."

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
        if event.is_final_response():
            response_text = event.content.parts[0].text
            try:
                # Try to extract perimeter calculation from response
                # This is a simple approach - you might need more sophisticated parsing
                return {"result": response_text, "raw_response": response_text}
            except Exception as e:
                print(f"❌ Error processing response: {e}")
                return {"result": response_text, "error": str(e)} 