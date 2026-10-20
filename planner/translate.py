"""Tool-assisted step 1: turn the student's message into scenario JSON with one LLM call. Owner: Weng Mun."""


def translate(text):
    """Return a scenario dict in the design.md section 5 format, or None if the reply can't be parsed into one
    (scored as no_answer). Call the model through planner.llm.ask so every approach shares one model and cost log."""
    raise NotImplementedError
