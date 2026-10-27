"""The one place that calls an LLM, so every approach uses the same model, settings and cost accounting. Owner: Javier."""
import os
import time
from functools import cache

import anthropic

from planner.data import ROOT

MODEL = "claude-sonnet-5-5"
EFFORT = "high"  # Sonnet 5.5's default, set explicitly so a change of default can't change the experiment
# US$ per million tokens for MODEL, keyed by usage field. A cache write costs 1.25x input (5-minute cache).
PRICES = {"input_tokens": 2.00, "cache_creation_input_tokens": 2.50, "cache_read_input_tokens": 0.20,
          "output_tokens": 10.00}
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
    The system prompt is cached, so a long prompt shared by every scenario is billed in full only once."""
    start = time.monotonic()
    with client().messages.stream(
        model=MODEL,
        max_tokens=64000,
        system=[{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}],
        messages=[{"role": "user", "content": user}],
        thinking={"type": "adaptive"},
        output_config={"effort": EFFORT},
    ) as stream:
        message = stream.get_final_message()
    reply = "".join(block.text for block in message.content if block.type == "text")
    usage = {name: getattr(message.usage, name) or 0 for name in PRICES}
    usage["seconds"] = round(time.monotonic() - start, 1)
    CALLS.append({"reply": reply, "usage": usage, "stop_reason": message.stop_reason})
    return reply, usage


def cost(usage):
    """US$ for one call's usage."""
    return sum(usage[name] * price for name, price in PRICES.items()) / 1e6
