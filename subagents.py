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
)

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
)
