from google.adk.agents.llm_agent import LlmAgent
from typing import Any, Dict, List, Optional, Sequence
from google.adk.models.lite_llm import LiteLlm
import os
from dotenv import load_dotenv
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
MODEL_GPT_4O = "openai/gpt-4o"
# Code Writer Agent
code_writer_agent = LlmAgent(
    name="code_writer_agent",
    model = LiteLlm(model=MODEL_GPT_4O, api_key=os.environ.get('OPENAI_API_KEY')),
    instruction="""You are a Code Writer AI.
    Based on the user's request, write the initial Python code.
    Output *only* the raw code block.
    """,
    description="Writes initial code based on a specification.",
    # Stores its output (the generated code) into the session state
    # under the key 'generated_code'.
    output_key="generated_code",
)
