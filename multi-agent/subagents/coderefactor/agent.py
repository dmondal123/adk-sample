from google.adk.agents.llm_agent import LlmAgent
from typing import Any, Dict, List, Optional, Sequence
from google.adk.models.lite_llm import LiteLlm
from ...callbacks import skip_completed_agent
import os
from dotenv import load_dotenv
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
MODEL_GPT_4O = "openai/gpt-4o"

# Code Refactorer Agent
# Takes the original code and the review comments (read from state) and refactors the code.
code_refactorer_agent = LlmAgent(
    name="code_refactorer_agent",
    model = LiteLlm(model=MODEL_GPT_4O),
    instruction="""You are a Code Refactorer AI.

Below is the original Python code:

```
{generated_code}
```

Below are the review comments:

{review_comments}

Refactor the code based on the provided feedback.

Output *only* the final, refactored code block.
    """,
    description="Refactors code based on review comments.",
    # Stores its output (the refactored code) into the session state
    # under the key 'refactored_code'.
    output_key="refactored_code",
    before_agent_callback=skip_completed_agent,
)
