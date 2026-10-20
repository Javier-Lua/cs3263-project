"""The one place that calls an LLM, so every approach uses the same model, settings and cost accounting. Owner: Javier."""


def ask(system, user):
    """Send one prompt and return (reply_text, usage), usage = {"input_tokens", "output_tokens", "seconds"}.
    Read the API key from the environment (.env is git-ignored). Provider and model: design.md section 11."""
    raise NotImplementedError
