# Copyright 2023 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Example of a code pipeline workflow with automatic failure recovery.
"""

import asyncio
import logging
import os
import sys
from typing import Any, Dict, List, Optional, Sequence
from google.adk.models.lite_llm import LiteLlm
#from google.adk import Agent, AgentContext, AgentOutput
from google.adk.runners import Runner
from google.adk.sessions import DatabaseSessionService
from google.adk.agents.llm_agent import LlmAgent
from google.adk.agents.sequential_agent import SequentialAgent
from google.genai.types import Content, Part
from google.adk.events import Event, EventActions
from subagents import code_writer_agent, code_reviewer_agent, code_refactorer_agent
os.environ['OPENAI_API_KEY'] = ''

MODEL_GPT_4O = "openai/gpt-4o"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Session management constants
APP_NAME = "code_pipeline_app"
USER_ID = "user_1"
SESSION_ID = "session_001"

# Initialize session service for persistent state
db_url = "sqlite:///./code_pipeline.db"
session_service = DatabaseSessionService(db_url=db_url)

# Try to get existing session or create a new one
try:
    session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    logger.info(f"Existing session retrieved: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")
    
    # Initialize workflow_checkpoint if it doesn't exist in the state
    if 'workflow_checkpoint' not in session.state:
        # Create an event with actions
        actions_with_update = EventActions(state_delta={"workflow_checkpoint": "start", "last_query": ""})
        event = Event(
            invocation_id="init_workflow",  # Required field
            author="system",                # Required field - who created this event
            actions=actions_with_update     # Include the actions with state_delta
            # No direct app_name, user_id, session_id, or state_update parameters
        )
        session_service.append_event(session, event)
        logger.info("Initialized workflow checkpoint to 'start'")
    else:
        logger.info(f"Current workflow checkpoint: {session.state['workflow_checkpoint']}")
        if 'last_query' in session.state:
            logger.info(f"Last query: {session.state['last_query']}")
except:
    # Create a new session if it doesn't exist
    initial_state = {
        "workflow_checkpoint": "start",
        "last_query": ""
    }
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID,
        state=initial_state
    )
    # Initialize workflow state tracking
    # Create an event with actions
    actions_with_update = EventActions(state_delta={"workflow_checkpoint": "start", "last_query": ""})
    event = Event(
        invocation_id="init_workflow",  # Required field
        author="system",                # Required field - who created this event
        actions=actions_with_update     # Include the actions with state_delta
        # No direct app_name, user_id, session_id, or state_update parameters
    )
    session_service.append_event(session, event)
    logger.info(f"New session created: App='{APP_NAME}', User='{USER_ID}', Session='{SESSION_ID}'")




# --- 2. Create a checkpoint-aware SequentialAgent ---
# This is a custom implementation that adds checkpoint awareness to the standard SequentialAgent

class CheckpointAwareSequentialAgent(SequentialAgent):
    """A sequential agent that is aware of checkpoints for failure recovery."""
    
    def __init__(self, name: str, sub_agents: List[LlmAgent], checkpoint_names: List[str]):
        super().__init__(name=name, sub_agents=sub_agents)
        # Instead of directly setting the attribute, store it in a way that's compatible with Pydantic
        self._checkpoint_names = checkpoint_names
        
    @property
    def checkpoint_names(self) -> List[str]:
        """Get the checkpoint names."""
        return self._checkpoint_names
    
    async def process(self, context, query):
        """Process the query with checkpoint awareness."""
        
        # Special command to reset workflow
        if query.lower() == "reset workflow":
            session = session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            event = Event(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID,
                state_update={
                    "workflow_checkpoint": "start",
                    "last_query": "",
                    "generated_code": None,
                    "review_comments": None,
                    "refactored_code": None
                }
            )
            session_service.append_event(session, event)
            return {"response": "Workflow checkpoint reset to 'start'"}
        
        # Special command to check current checkpoint
        if query.lower() == "checkpoint status":
            session = session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            current_checkpoint = session.state.get('workflow_checkpoint', 'start')
            last_query = session.state.get('last_query', 'None')
            
            # Prepare a detailed status report
            status = f"Current workflow checkpoint: {current_checkpoint}\nLast query: {last_query}\n\n"
            
            if 'generated_code' in session.state:
                status += "Code Writer: ✓ Complete\n"
                status += "Generated code available\n\n"
            else:
                status += "Code Writer: ❌ Not started or incomplete\n\n"
                
            if 'review_comments' in session.state:
                status += "Code Reviewer: ✓ Complete\n"
                status += "Review comments available\n\n"
            else:
                status += "Code Reviewer: ❌ Not started or incomplete\n\n"
                
            if 'refactored_code' in session.state:
                status += "Code Refactorer: ✓ Complete\n"
                status += "Refactored code available\n\n"
            else:
                status += "Code Refactorer: ❌ Not started or incomplete\n\n"
                
            return {"response": status}
        
        # Special command to show the final code
        if query.lower() == "show final code":
            session = session_service.get_session(
                app_name=APP_NAME,
                user_id=USER_ID,
                session_id=SESSION_ID
            )
            
            if 'refactored_code' in session.state:
                return {"response": f"Final refactored code:\n\n```python\n{session.state['refactored_code']}\n```"}
            elif 'generated_code' in session.state:
                return {"response": f"Original generated code (not refactored):\n\n```python\n{session.state['generated_code']}\n```"}
            else:
                return {"response": "No code has been generated yet."}
        
        # Get current checkpoint from session state
        session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        current_checkpoint = session.state.get('workflow_checkpoint', 'start')
        last_query = session.state.get('last_query', '')
        
        # If we're in the middle of a workflow and this is a new query, use the stored query
        if current_checkpoint != 'start' and current_checkpoint != 'complete' and query != "resume workflow":
            print(f"New query received while workflow is in progress at checkpoint: {current_checkpoint}")
            print(f"To resume the workflow with the last query '{last_query}', type 'resume workflow'")
            return {"response": (
                f"A code pipeline is currently in progress at checkpoint '{current_checkpoint}' with query: '{last_query}'\n"
                f"To resume the workflow, type 'resume workflow'\n"
                f"To start a new workflow with your current query, type 'reset workflow' first"
            )}
        
        # If user wants to resume the workflow, use the stored query
        if query == "resume workflow" and last_query:
            print(f"Resuming workflow with query: {last_query}")
            query = last_query
        
        # Store the query for potential recovery
        event = Event(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state_update={"last_query": query}
        )
        session_service.append_event(session, event)
        
        print(f"Starting workflow from checkpoint: {current_checkpoint}")
        
        # Determine which agents to run based on the current checkpoint
        start_index = 0
        if current_checkpoint != 'start':
            try:
                # Find the index of the next agent to run
                checkpoint_index = self.checkpoint_names.index(current_checkpoint)
                start_index = checkpoint_index
                print(f"Resuming from agent at index {start_index}: {self.sub_agents[start_index].name}")
            except ValueError:
                print(f"Unknown checkpoint: {current_checkpoint}, starting from the beginning")
        
        # Copy session state to context for the agents to use
        for key, value in session.state.items():
            if key not in ['workflow_checkpoint', 'last_query']:
                context[key] = value
        
        # Process each agent in sequence, starting from the appropriate checkpoint
        final_response = None
        try:
            for i in range(start_index, len(self.sub_agents)):
                agent = self.sub_agents[i]
                print(f"Running agent: {agent.name}")
                
                # Process the query with the current agent
                result = await agent.process(context, query)
                
                # Update the context with the agent's output
                if agent.output_key and agent.output_key in result:
                    context[agent.output_key] = result[agent.output_key]
                    
                    # Save to session state for recovery
                    session = session_service.get_session(
                        app_name=APP_NAME,
                        user_id=USER_ID,
                        session_id=SESSION_ID
                    )
                    session.state[agent.output_key] = result[agent.output_key]
                    
                    # Update checkpoint to the next agent
                    if i < len(self.sub_agents) - 1:
                        next_checkpoint = self.checkpoint_names[i + 1]
                        session.state['workflow_checkpoint'] = next_checkpoint
                    else:
                        session.state['workflow_checkpoint'] = 'complete'
                    
                    session_service.update_session(session)
                    print(f"Updated checkpoint to: {session.state['workflow_checkpoint']}")
                
                # Keep track of the final response
                if 'response' in result:
                    final_response = result['response']
            
            # Workflow completed successfully
            if final_response is None:
                # If no agent provided a response, create a default one
                if 'refactored_code' in context:
                    final_response = f"Code pipeline completed successfully!\n\n```python\n{context['refactored_code']}\n```"
                else:
                    final_response = "Code pipeline completed successfully!"
            
            return {"response": final_response}
            
        except Exception as e:
            print(f"Workflow failed: {str(e)}")
            # The checkpoint is already saved at each step, so we just report the error
            return {"response": (
                f"Code pipeline failed at checkpoint '{session.state.get('workflow_checkpoint')}'.\n"
                f"Error: {str(e)}\n"
                f"To resume the workflow from this point, type 'resume workflow'"
            )}

# Create the checkpoint-aware sequential agent
code_pipeline_agent = CheckpointAwareSequentialAgent(
    name="code_pipeline_agent",
    sub_agents=[code_writer_agent, code_reviewer_agent, code_refactorer_agent],
    checkpoint_names=['start', 'reviewer_pending', 'refactorer_pending']
)

# Create a runner with our session service
runner = Runner(
    agent=code_pipeline_agent,
    app_name=APP_NAME,
    session_service=session_service
)

async def resume_workflow(session, last_query):
    """Resume the workflow from the last checkpoint."""
    content = Content(role='user', parts=[Part(text="resume workflow")])
    async for event in runner.run_async(
        user_id=USER_ID,
        session_id=SESSION_ID,
        new_message=content
    ):
        if event.is_final_response() and event.content and event.content.parts:
            print(f"\nAgent: {event.content.parts[0].text}")
            break

async def main():
    """Run the workflow agent."""
    # Check if there's a pending workflow
    session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )
    current_checkpoint = session.state.get('workflow_checkpoint', 'start')
    last_query = session.state.get('last_query', '')
    
    print("\n=== Code Pipeline with Automatic Failure Recovery ===")
    print("Type 'exit', 'quit', or 'bye' to end the conversation.")
    print("Type 'reset workflow' to reset the workflow checkpoint.")
    print("Type 'checkpoint status' to check the current checkpoint.")
    print("Type 'resume workflow' to continue a failed workflow.")
    print("Type 'show final code' to display the final code.")
    
    # Check if there's a pending workflow and offer to resume
    if current_checkpoint != 'start' and current_checkpoint != 'complete' and last_query:
        print(f"\n⚠️ A code pipeline is currently in progress at checkpoint '{current_checkpoint}'")
        print(f"Last query: '{last_query}'")
        
        # Ask if the user wants to resume automatically
        print("\nDo you want to resume the workflow? (y/n)")
        choice = input("> ")
        
        if choice.lower() in ['y', 'yes']:
            # Use asyncio.run to properly execute the async function
            asyncio.run(resume_workflow(session, last_query))
    
    # Main interaction loop
    while True:
        # Get user input
        user_query = input("\nYou: ")
        
        # Check if user wants to exit
        if user_query.lower() in ['exit', 'quit', 'bye']:
            print("Ending conversation. Goodbye!")
            break
        
        # Prepare the user's message
        content = Content(role='user', parts=[Part(text=user_query)])
        
        # Process the query
        try:
            async for event in runner.run_async(
                user_id=USER_ID,
                session_id=SESSION_ID,
                new_message=content
            ):
                if event.is_final_response() and event.content and event.content.parts:
                    print(f"\nAgent: {event.content.parts[0].text}")
                    break
        except Exception as e:
            print(f"\nError: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())