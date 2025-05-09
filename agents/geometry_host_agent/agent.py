from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.genai import types
from area_agent.agent import area_agent
from perimeter_agent.agent import perimeter_agent
import os

# Ensure the directory exists
os.makedirs("./db", exist_ok=True)

geometry_host_agent = Agent(
    name="geometry_host_agent",
    model=LiteLlm("openai/gpt-4o"),
    description="Coordinates geometry calculations by calling specialized geometry agents.",
    instruction="You are the geometry host agent responsible for orchestrating geometry calculation tasks. "
                "You should analyze the user's request carefully and only call the specific agent needed for the task. "
                "If the user asks for area calculation, only call the area_agent. "
                "If the user asks for perimeter calculation, only call the perimeter_agent. "
                "Only call both agents if the user explicitly requests both calculations or doesn't specify which calculation they want. "
                "Be precise in your delegation to ensure efficient processing of geometry requests.",
    sub_agents=[area_agent, perimeter_agent]            
)

# Use the built-in DatabaseSessionService with SQLite
# The db_url is just a connection string - the file will be created if it doesn't exist
db_url = "sqlite:///./db/geometry_host_sessions.db"
session_service = DatabaseSessionService(db_url=db_url)

runner = Runner(
    agent=geometry_host_agent,
    app_name="geometry_host_app",
    session_service=session_service
)

USER_ID = "user_geometry_host"
SESSION_ID = "session_geometry_host"

async def execute(request):
    # Ensure session exists
    try:
        session_service.create_session(
            app_name="geometry_host_app",
            user_id=USER_ID,
            session_id=SESSION_ID
        )
    except Exception as e:
        # Session might already exist, which is fine
        print(f"Note: {e}")

    # Extract the original request text to preserve the user's intent
    request_text = request.get('request', '')
    parameters = request.get('parameters', '')
    
    prompt = (
        f"User request: {request_text}\n"
        f"Parameters: {parameters}\n\n"
        f"Please analyze this request carefully. If it's specifically asking for area calculation, "
        f"only call the area_agent. If it's specifically asking for perimeter calculation, only call "
        f"the perimeter_agent. Only call both agents if both calculations are requested or if the "
        f"request doesn't specify which calculation is needed."
    )

    message = types.Content(role="user", parts=[types.Part(text=prompt)])

    async for event in runner.run_async(user_id=USER_ID, session_id=SESSION_ID, new_message=message):
        if event.is_final_response():
            return {"summary": event.content.parts[0].text} 