"""The one place that calls an LLM, so every approach uses the same model, settings and cost accounting. Owner: Javier."""
import os
import time
from functools import cache

import anthropic

from planner.data import ROOT

MODEL = "claude-sonnet-5-5"  # run.py --model changes it for one run
EFFORT = "high"  # Sonnet 5.5's default, set explicitly so a change of default can't change the experiment
THINKING = True  # run.py --no-thinking turns it off
THINKING_OFF = {"claude-sonnet-5-5": "between_tools"}  # Sonnet 5.5 rejects "disabled"; with no tools this means none
# US$ per million tokens for each model, keyed by usage field. A cache write costs 1.25x input (5-minute cache).
# Haiku's are its prices for prompts of at most 100K tokens, which every prompt here is.
PRICES = {"claude-sonnet-5-5": {"input_tokens": 2.00, "cache_creation_input_tokens": 2.50,
                                "cache_read_input_tokens": 0.20, "output_tokens": 10.00},
          "claude-haiku-5-5": {"input_tokens": 0.10, "cache_creation_input_tokens": 0.125,
                               "cache_read_input_tokens": 0.01, "output_tokens": 0.50}}
CALLS = []  # every ask() appends {"reply", "usage", "stop_reason"}; run.py reads it to log any approach's calls


def api_key():
    """ANTHROPIC_KEY from the environment, else from the git-ignored .env file (a line like ANTHROPIC_KEY="sk-ant-...")."""
    if os.environ.get("ANTHROPIC_KEY"):
        return os.environ["ANTHROPIC_KEY"]
    env = ROOT / ".env"
    for line in env.read_text().splitlines() if env.exists() else []:
        name, _, value = line.partition("=")
        if name.strip() == "ANTHROPIC_KEY":
            return value.strip().strip('"')
    raise KeyError('ANTHROPIC_KEY is not set: add a line ANTHROPIC_KEY="sk-ant-..." to .env')


@cache
def client():
    return anthropic.Anthropic(api_key=api_key(), max_retries=5)


def ask(system, user):
    """Send one prompt and return (reply_text, usage), usage = {"input_tokens", "output_tokens", "seconds", ...}.
    user is the message, or a list of turns for a conversation (planner/feedback.py).
    The system prompt is cached, so a long prompt shared by every scenario is billed in full only once."""
    start = time.monotonic()
    with client().messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=user if isinstance(user, list) else [{"role": "user", "content": user}],
        thinking={"type": "adaptive" if THINKING else THINKING_OFF.get(MODEL, "disabled")},
        output_config={"effort": EFFORT},
    ) as stream:
        message = stream.get_final_message()
    reply = "".join(block.text for block in message.content if block.type == "text")
    usage = {name: getattr(message.usage, name) or 0 for name in PRICES[MODEL]}
    usage["seconds"] = round(time.monotonic() - start, 1)
    CALLS.append({"reply": reply, "usage": usage, "stop_reason": message.stop_reason})
    return reply, usage


def cost(usage):
    """US$ for one call's usage with the current model."""
    return sum(usage[name] * price for name, price in PRICES[MODEL].items()) / 1e6
