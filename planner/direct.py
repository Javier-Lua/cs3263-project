"""The direct approach: the LLM reads the message and the course data and writes the plan itself. Owner: Javier."""


def plan_direct(text):
    """Return a plan dict in the design.md section 5 format, or None if the reply can't be parsed (scored as no_answer).
    Prompt contents: design.md section 6.1."""
    raise NotImplementedError
