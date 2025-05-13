import sys
import os
import signal
import json

# Add the parent directory to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.adk.sessions import Session, DatabaseSessionService
from .subagents.codewriter.agent import code_writer_agent
from .subagents.codereview.agent import code_reviewer_agent
from .subagents.coderefactor.agent import code_refactorer_agent

# Create a DatabaseSessionService with SQLite for persistent storage
# This ensures sessions survive application restarts
db_url = "sqlite:///./agent_sessions.db"
session_service = DatabaseSessionService(db_url=db_url)

# Create or load a session
app_name = "code_pipeline_app"
user_id = "default_user"
session_id = "code_pipeline_session"

# Flag to track if we're resuming from a checkpoint
resuming_from_checkpoint = False

# Try to get an existing session, or create a new one if it doesn't exist
try:
    session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print(f"Resuming existing session: {session_id}")
    # Check if we have a checkpoint
    checkpoint = session.state.get("checkpoint", "")
    if checkpoint:
        print(f"Resuming from checkpoint: {checkpoint}")
        resuming_from_checkpoint = True
    
    # Print the current session state
    print("Current session state:")
    print(json.dumps(session.state, indent=2))
except:
    # Create a new session if one doesn't exist
    session = session_service.create_session(app_name=app_name, user_id=user_id, session_id=session_id)
    print(f"Created new session: {session_id}")
    print("Initial session state:")
    print(json.dumps(session.state, indent=2))

# Handle graceful shutdown to ensure checkpoints are saved
def signal_handler(sig, frame):
    print("\nInterrupted! Saving checkpoint before exiting...")
    # The checkpoint is already saved after each agent completes
    # So we just need to exit gracefully
    sys.exit(0)

# Register the signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)
print("Signal handler registered for SIGINT (Ctrl+C)")

# Create a custom sequential agent that respects checkpoints
class CheckpointedSequentialAgent(SequentialAgent):
    def run(self, session: Session, **kwargs):
        # Get the current checkpoint from the session state
        checkpoint = session.state.get("checkpoint", "")
        print(f"Current checkpoint: {checkpoint}")
        
        # Determine which agents need to run
        agents_to_run = []
        start_running = not checkpoint  # If no checkpoint, start from beginning
        
        for agent in self.sub_agents:
            agent_name = agent.name
            
            # If we've reached or passed the checkpoint, include this agent
            if start_running or checkpoint == agent_name:
                agents_to_run.append(agent)
                start_running = True
        
        print(f"Agents to run: {[agent.name for agent in agents_to_run]}")
        
        # Run only the necessary agents
        for i, agent in enumerate(agents_to_run):
            try:
                print(f"\n--- Starting agent: {agent.name} ---")
                agent.run(session, **kwargs)
                # Update checkpoint after successful completion
                session.state["checkpoint"] = agent.name
                # The session state is automatically persisted by the DatabaseSessionService
                # when events are appended, but we need to explicitly update it here
                session_service.update_session_state(
                    app_name=session.app_name,
                    user_id=session.user_id,
                    session_id=session.id,
                    state=session.state
                )
                print(f"Completed agent: {agent.name}")
                print(f"Checkpoint updated to: {agent.name}")
                
                # Print the full session state after each agent completes
                print(f"\n--- Session state after {agent.name} ---")
                print(json.dumps(session.state, indent=2))
            except Exception as e:
                print(f"Error in agent {agent.name}: {str(e)}")
                # On failure, the checkpoint remains at the last successful agent
                # Re-raise the exception to signal the failure
                raise e
        
        # If we completed all agents successfully, clear the checkpoint
        if agents_to_run and agents_to_run[-1] == self.sub_agents[-1]:
            session.state.pop("checkpoint", None)
            session_service.update_session_state(
                app_name=session.app_name,
                user_id=session.user_id,
                session_id=session.id,
                state=session.state
            )
            print("Pipeline completed successfully")
            print("\n--- Final session state ---")
            print(json.dumps(session.state, indent=2))
        
        return session

# Create the checkpointed sequential agent
code_pipeline_agent = CheckpointedSequentialAgent(
    name="code_pipeline_agent",
    sub_agents=[code_writer_agent, code_reviewer_agent, code_refactorer_agent],
)

# Make sure this is explicitly defined as the root_agent
root_agent = code_pipeline_agent

# This is important - the ADK framework looks for this specific variable
agent = type('', (), {})()
agent.root_agent = root_agent

# If we're resuming from a checkpoint, we need to handle it differently
if resuming_from_checkpoint:
    print("Automatically resuming pipeline from checkpoint...")
    
    # Instead of waiting for user input, directly run the agent
    try:
        # For the first agent (code_writer), we need a user prompt
        # Check which agent we're resuming from
        checkpoint = session.state.get("checkpoint", "")
        
        if not checkpoint:
            # If starting from the beginning, we need a user prompt for code_writer_agent
            print("Please provide a prompt for the code writer agent:")
            user_input = input("> ")
            session.add_user_message(user_input)
        else:
            # If resuming from a checkpoint, we already have the necessary state
            # Just need to continue the pipeline
            print("Continuing pipeline execution...")
            
        # Run the agent with the current session state
        code_pipeline_agent.run(session)
        
        # Exit after running to prevent the normal ADK flow from taking over
        print("Pipeline execution completed or paused. Exiting.")
        sys.exit(0)
    except Exception as e:
        print(f"Error during execution: {str(e)}")
        sys.exit(1)
else:
    # For a new session, we'll let the normal ADK flow handle it
    # The framework will prompt for user input
    print("Starting new pipeline. Please provide input when prompted.")