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

code_pipeline_agent = SequentialAgent(
    name="CodePipelineAgent",
    sub_agents=[code_writer_agent, code_reviewer_agent, code_refactorer_agent],
    description="Executes a sequence of code writing, reviewing, and refactoring.",
    # The agents will run in the order provided: Writer -> Reviewer -> Refactorer
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
    session_1 = runner.session_service.get_sessions(
        app_name=app_name, user_id=user_id_1
    )
    if session_1:
      session_1 = session_1[0]  # Use the most recent session
      print(f'----Resuming existing session: {session_1.id} ----------------------')
    else:
      session_1 = runner.session_service.create_session(
          app_name=app_name, user_id=user_id_1
      )
      print(f'----Created new session: {session_1.id} ----------------------')
  except Exception as e:
    print(f"Error retrieving session: {e}")
    session_1 = runner.session_service.create_session(
        app_name=app_name, user_id=user_id_1
    )
    print(f'----Created new session: {session_1.id} ----------------------')

  session_1 = await run_prompt(
      session_1, 'Write a python function to do quicksort.'
  )
  session_1 = await run_prompt(
      session_1, 'Write another python function to do bubble sort.'
  )
  print('-------------------------------------------------------------------')


if __name__ == '__main__':
  # Set up signal handling to gracefully shut down
  def signal_handler(sig, frame):
    print("Gracefully shutting down...")
    sys.exit(0)
  
  signal.signal(signal.SIGINT, signal_handler)
  signal.signal(signal.SIGTERM, signal_handler)
  
  asyncio.run(main())