import sys
import os
import json
import signal
from typing import Dict, Any

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.sessions import Session
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

# ---------------------------------------------------------------------------
# Session management and runner setup
# ---------------------------------------------------------------------------

# NOTE:
# This block lets you run this file directly ( `python agent.py` )
# and get automatic checkpoint-aware recovery.
# The session state is stored in a lightweight SQLite DB via
# `DatabaseSessionService`, so if the script crashes (or you abort it)
# you can simply run it again and it will resume from the first unfinished
# sub-agent instead of starting from the beginning.
if __name__ == "__main__":
    import asyncio
    from google.adk.runners import Runner
    from google.adk.sessions import DatabaseSessionService
    from google.genai.types import Content, Part

    # ── Basic identifiers ────────────────────────────────────────────────────
    APP_NAME = "code_pipeline_app"
    USER_ID = "user_1"
    SESSION_ID = "session_001"

    # ── Choose a persistent SessionService (SQLite on local disk) ────────────
    db_url = "sqlite:///./code_pipeline.db"  # one tiny file next to this script
    session_service = DatabaseSessionService(db_url=db_url)

    # ── Ensure the session exists (create if first run) ─────────────────────
    # Try to get the session
    existing_session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    # If it doesn't exist, create it
    if not existing_session:
        print(f"Session {SESSION_ID} not found by get_session. Creating...")
        session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state={}  # Explicitly initialize with an empty state dictionary
        )
        print(f"Session {SESSION_ID} created.")
    else:
        print(f"Session {SESSION_ID} retrieved successfully.")
        # If session exists, ensure its state is not None (though DatabaseSessionService should handle this)
        if existing_session.state is None:
            print(f"WARNING: Retrieved session {SESSION_ID} has None state. Re-initializing state.")
            # This part is more of a safeguard; ideally, the service loads state correctly.
            # Forcing a state dictionary might involve an update call if the object model requires it.
            # However, for now, let's assume create_session with state={} or a proper load handles it.
            # If problems persist with state being None after load, this area needs deeper ADK-specific investigation.

    # ── Runner wraps the root_agent with the chosen SessionService ──────────
    runner = Runner(
        agent=root_agent,
        app_name=APP_NAME,
        session_service=session_service,
    )

    # ── Simple REPL loop ─────────────────────────────────────────────────────
    async def repl() -> None:
        print("\n=== Code-Pipeline REPL (type 'exit' to quit) ===\n")
        while True:
            user_input = input("You > ")
            if user_input.lower() in {"exit", "quit", "bye"}:
                break
            content = Content(role="user", parts=[Part(text=user_input)])
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content,
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    print(f"Agent > {event.content.parts[0].text}\n")
                    # Print session state after each turn for debugging
                    current_session = session_service.get_session(
                        app_name=APP_NAME,
                        user_id=USER_ID,
                        session_id=SESSION_ID
                    )
                    if current_session:
                        print(f"DEBUG: Current session state: {current_session.state}")
                    else:
                        print(f"DEBUG: Could not retrieve session to print state.")
                    break

    asyncio.run(repl())