"""
Callbacks shared by several agents in the multi-agent pipeline.
"""
from __future__ import annotations

import os
from collections.abc import Mapping
from typing import Dict, Optional, Any

from google.adk.agents.callback_context import CallbackContext
from google.genai import types  # ADK re-exports the Gemini types


# ------------- tweak these two lines if you add new sub-agents -------------
AGENT_NAME_TO_OUTPUT_KEY: Dict[str, str] = {
    "code_writer_agent": "generated_code",
    "code_reviewer_agent": "review_comments",
    "code_refactorer_agent": "refactored_code",
}
# ---------------------------------------------------------------------------


# Emit the attribute list only once.
_ALREADY_DUMPED_CTX_ATTRS = False


def _to_mapping(state_obj: Any) -> Optional[Mapping]:
    """
    Best-effort conversion of ADK 'state' objects to something we can treat
    like a dict.  The google.adk.sessions.state.State class already supports
    Mapping-style access ( __contains__, __getitem__ ), so we simply return it
    as-is if it behaves like a Mapping.
    """
    if isinstance(state_obj, Mapping):
        print(f"State object is a mapping: {state_obj}")
        return state_obj
    # Fallback: some versions expose the real dict via a private attribute.
    inner = getattr(state_obj, "_state", None)
    if isinstance(inner, Mapping):
        print(f"Inner state object is a mapping: {inner}")
        return inner
    return None


def skip_completed_agent(callback_context: CallbackContext) -> Optional[types.Content]:
    """
    BEFORE-AGENT callback implementing "resume at first unfinished agent".

    • If this agent's output is already stored in the session state, immediately
      return it → the parent SequentialAgent will skip the LLM call.
    • Otherwise return None → the agent runs normally.
    """
    global _ALREADY_DUMPED_CTX_ATTRS

    # 1) One-time attribute dump for debugging
    if not _ALREADY_DUMPED_CTX_ATTRS or os.getenv("ADK_DEBUG_CTX") == "1":
        attrs = sorted(a for a in dir(callback_context) if not a.startswith("__"))
        print(f"[skip_completed_agent] CallbackContext attributes: {attrs}")
        _ALREADY_DUMPED_CTX_ATTRS = True

    # 2) Locate the session-state mapping – try all known places
    state = None
    for attr in ("state", "_state", "session_state"):
        candidate = getattr(callback_context, attr, None)
        state = _to_mapping(candidate)
        if state is not None:
            break
    # New fallback: some ADK versions expose it via callback_context.session.state
    if state is None:
        session = getattr(callback_context, "session", None)
        if session is not None:
            state = _to_mapping(getattr(session, "state", None))

    # Define agent_name earlier, before its first potential use in printing
    agent_name: Optional[str] = getattr(callback_context, "agent_name", None)

    print(f"[skip_completed_agent] State for {agent_name}: {state}")
    if state is None:
        print(f"[skip_completed_agent] ({agent_name if agent_name else 'Unknown Agent'}) State object is None. Agent will run.")
        return None  # cannot read state → run the agent normally

    # 3) Which key would this agent have written?
    print(f"[skip_completed_agent] Current agent_name from context: {agent_name}")
    output_key = AGENT_NAME_TO_OUTPUT_KEY.get(agent_name)
    print(f"[skip_completed_agent] ({agent_name}) Determined output_key: {output_key}")

    if not output_key:
        print(f"[skip_completed_agent] ({agent_name}) No output_key found for this agent in AGENT_NAME_TO_OUTPUT_KEY. Agent will run.")
        return None  # no mapping → nothing to skip

    # 4) Skip logic
    print(f"[skip_completed_agent] ({agent_name}) Checking for output_key \'{output_key}\' in state. Keys in state: {list(state.keys()) if state else 'State is None'}")
    if output_key not in state:
        print(f"[skip_completed_agent] ({agent_name}) Output_key \'{output_key}\' not in state. Agent will run.")
        return None  # not yet produced → run the agent

    saved_value = state[output_key]
    print(f"[skip_completed_agent] ({agent_name}) Output_key \'{output_key}\' FOUND in state. Value: \'{str(saved_value)[:100]}...\'. Agent will be SKIPPED.")

    # Ensure downstream agents receive a proper Content object
    if isinstance(saved_value, types.Content):
        return saved_value

    return types.Content(
        role="model",
        parts=[types.Part(text=str(saved_value))],
    ) 