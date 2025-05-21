import sys
import os
import json
import signal
import asyncio
from typing import Dict, Any
from typing import cast
# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.sessions import Session, DatabaseSessionService
from subagents.codewriter.agent import code_writer_agent
from subagents.codereview.agent import code_reviewer_agent
from subagents.coderefactor.agent import code_refactorer_agent

# Define a function to debug agent context
def debug_agent_context(callback_context):
    """Print debug information about the agent context."""
    agent_name = getattr(callback_context, "agent_name", "Unknown")
    print(f"\n[debug_agent_context] Invoking agent: {agent_name}")
    
    # Get and log the state before agent runs
    invocation_context = getattr(callback_context, "_invocation_context", None)
    session = getattr(invocation_context, "session", None) if invocation_context else None
    
    if session and hasattr(session, "state"):
        print(f"[debug_agent_context] Session state before {agent_name}: {session.state}")
    else:
        print(f"[debug_agent_context] No session state found for {agent_name}")
    
    return None  # Always continue with the agent execution

code_pipeline_agent = SequentialAgent(
    name="CodePipelineAgent",
    sub_agents=[code_writer_agent, code_reviewer_agent, code_refactorer_agent],
    description="Executes a sequence of code writing, reviewing, and refactoring.",
    # Add debug callback to monitor which agents are called
    before_agent_callback=debug_agent_context
)

# For ADK tools compatibility, the root agent must be named `root_agent`
root_agent = code_pipeline_agent

from google.adk.cli.utils import logs
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.genai import types


async def main():
  app_name = 'my_app'
  user_id_1 = 'user1'
  session_id = 'code_pipeline_session'
  
  # Create a database session service with the SQLite DB file in the current directory
  db_url = "sqlite:///./code_pipeline.db"  # one tiny file next to this script
  session_service = DatabaseSessionService(db_url=db_url)
  
  runner = Runner(
        agent=root_agent,
        app_name=app_name,
        session_service=session_service,
    )

  async def run_prompt(session: Session, new_message: str) -> Session:
    content = types.Content(
        role='user', parts=[types.Part.from_text(text=new_message)]
    )
    print('** User says:', content.model_dump(exclude_none=True))
    
    # Track the current prompt in session state to enable resumption
    if session.state is None:
      session.state = {}
    
    # Save the current prompt in the session state
    if "current_prompt" not in session.state:
      session.state["current_prompt"] = new_message
      # Update the session with the new state
      # Don't use update_session since it doesn't exist
      # Instead, we'll rely on the fact that session state changes are automatically persisted
      # when the runner.run_async() method completes
      print(f"** Saved current prompt to session: {new_message}")
    
    async for event in runner.run_async(
        user_id=user_id_1,
        session_id=session.id,
        new_message=content,
    ):
      if not event.content or not event.content.parts:
        continue
      if event.content.parts[0].text:
        print(f'** {event.author}: {event.content.parts[0].text}')
      elif event.content.parts[0].function_call:
        print(
            f'** {event.author}: fc /'
            f' {event.content.parts[0].function_call.name} /'
            f' {event.content.parts[0].function_call.args}\n'
        )
      elif event.content.parts[0].function_response:
        print(
            f'** {event.author}: fr /'
            f' {event.content.parts[0].function_response.name} /'
            f' {event.content.parts[0].function_response.response}\n'
        )

    return cast(
        Session,
        runner.session_service.get_session(
            app_name=app_name, user_id=user_id_1, session_id=session.id
        ),
    )

  # Try to get an existing session or create a new one if it doesn't exist
  try:
    session_1 = runner.session_service.get_session(
        app_name=app_name, user_id=user_id_1, session_id=session_id
    )
    if session_1:
      # The session object is already a single Session, no need to access with [0]
      print(f'----Resuming existing session: {session_1.id} ----------------------')
    else:
      session_1 = runner.session_service.create_session(
          app_name=app_name, user_id=user_id_1, session_id=session_id
      )
      print(f'----Created new session: {session_1.id} ----------------------')
  except Exception as e:
    print(f"Error retrieving session: {e}")
    # Check if the session already exists before trying to create it
    try:
      session_1 = runner.session_service.get_session(
          app_name=app_name, user_id=user_id_1, session_id=session_id
      )
      if session_1:
        print(f'----Found existing session: {session_1.id} ----------------------')
      else:
        session_1 = runner.session_service.create_session(
            app_name=app_name, user_id=user_id_1, session_id=session_id
        )
        print(f'----Created new session: {session_1.id} ----------------------')
    except Exception as e2:
      print(f"Error creating session: {e2}")
      raise

  print('-------------------------------------------------------------------')
  print(f"Session state: {session_1.state if hasattr(session_1, 'state') else 'None'}")
  print('-------------------------------------------------------------------')
  
  # Define prompts to process
  prompts = [
    "Write a python function to do quicksort.",
    "Write another python function to do bubble sort."
  ]
  
  # Process all prompts sequentially - the SequentialAgent will automatically
  # handle which agents have run and where to resume thanks to the session state
  for prompt in prompts:
    try:
      print(f"\n{'='*70}")
      print(f"Processing prompt: {prompt}")
      print(f"{'='*70}\n")
      
      session_1 = await run_prompt(session_1, prompt)
      
      print(f"\n{'='*70}")
      print(f"Prompt completed: {prompt}")
      print(f"{'='*70}\n")
    except Exception as e:
      print(f"\nError processing prompt '{prompt}': {e}")
      print("Session is saved. Restart the script to resume from this point.")
      break
  
  print('-------------------------------------------------------------------')
  print("All prompts processed successfully.")


if __name__ == '__main__':
  # Set up signal handling to gracefully shut down
  def signal_handler(sig, frame):
    print("Gracefully shutting down...")
    sys.exit(0)
  
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  
  asyncio.run(main())