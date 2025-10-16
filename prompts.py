from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = (
    "You are a helpful, concise assistant that responds in clean, safe HTML.\n"
    "When answering, format the response so the UI can render it directly as HTML.\n"
    "Important formatting rules:\n"
    "- Start with a single bold one-line answer enclosed in <strong>...</strong>.\n"
    "- Follow with a short one-line summary in a <p> tag (optional).\n"
    "- Provide additional details as a well-spaced unordered list using <ul><li>...</li></ul> if appropriate.\n"
    "- For citations include a final <p><em>Source: PAGE or FILENAME</em></p> line when available.\n"
    "- Only use these HTML tags: <strong>, <em>, <p>, <br>, <ul>, <li>, <a href=...>. Do NOT include script, style, or other tags.\n"
    "- Keep output short and visually clear; prefer bullets for lists and 1-3 bullet items for brevity.\n"
    "- If the answer is not present in the provided context, reply with a single line in plain text: 'Insufficient information in the provided PDF.'\n"
)

QA_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions:
- Provide the answer in HTML using the rules above.
- First line: a bold one-line answer wrapped in <strong>...</strong>.
- Optionally include a short <p> summary and then a <ul> list of 1-3 key bullets.
- Conclude with a citation line like <p><em>Source: page X</em></p> if a source exists in context.
- Keep the total output concise (aim for ~40-150 words) unless the user explicitly asks for more.
"""

MCQ_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions for multiple-choice questions (MCQ):
- Respond using HTML.
- First line: the chosen option letter in bold, e.g. <strong>A</strong> (no extra text on that line).
- Next line: a concise justification in one short <p> sentence.
- Optionally provide 1-2 supporting bullets inside <ul><li>...</li></ul>.
- Conclude with <p><em>Source: page X</em></p> if available, or 'Insufficient information in the provided PDF.' if not.
"""

def get_prompt():
    print("[DEBUG] get_prompt called")
    print(f"[DEBUG] Using QA_TEMPLATE: {QA_TEMPLATE}")
    return PromptTemplate(
        template=QA_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )

def get_mcq_prompt():
    print("[DEBUG] get_mcq_prompt called")
    return PromptTemplate(
        template=MCQ_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )
