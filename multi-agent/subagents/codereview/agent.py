from google.adk.agents.llm_agent import LlmAgent
from typing import Any, Dict, List, Optional, Sequence
from google.adk.models.lite_llm import LiteLlm
from ...callbacks import skip_completed_agent
import os
from dotenv import load_dotenv
load_dotenv()
os.environ['OPENAI_API_KEY'] = os.environ.get('OPENAI_API_KEY')
MODEL_GPT_4O = "openai/gpt-4o"

# Code Reviewer Agent
code_reviewer_agent = LlmAgent(
    name="code_reviewer_agent",
    model = LiteLlm(model=MODEL_GPT_4O),
    instruction="""You are a Code Reviewer AI.

Review the below Python code.

```
{generated_code}
```

Provide constructive feedback on potential errors, style issues, or improvements.
Focus on clarity and correctness.
Output only the review comments.

    """,
    description="Reviews code and provides feedback.",
    # Stores its output (the review comments) into the session state
    # under the key 'review_comments'.
    output_key="review_comments",
    before_agent_callback=skip_completed_agent,
)