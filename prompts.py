from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = (
    "You are a helpful, friendly assistant that responds concisely and attractively.\n"
    "When appropriate, format answers using simple HTML tags only (e.g., <strong>, <em>, <ul>, <li>, <p>, <br>) so they render nicely in the chat UI. Do NOT use complex markdown or scripts.\n"
    "If the answer is partially available, use it and indicate confidence. If unsure, explain briefly why.\n"
    "If the answer is not in the context, say you don't know based on the provided PDF.\n"
)

QA_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions:
- Provide a short, friendly answer (1-3 sentences) followed by a 1-3 bullet key points list when helpful.
- Use simple HTML tags only (<strong>, <em>, <ul>, <li>, <p>, <br>) to make the answer look neat in the chat UI.
- Begin the answer with a short one-line summary in bold (<strong>).</n+- If you cite sources, include them at the end in parentheses (e.g., (p. 12)).
- If the answer is not present in the context, reply: "I don't see that information in the provided PDF." inside a single <p> tag.
"""


MCQ_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions for multiple-choice questions (MCQ):
- Respond using simple HTML. On the first line provide the chosen option letter in <strong> (for example: <strong>A</strong>).
- On the next line give a concise justification (1-2 sentences) inside a <p> tag. Keep it factual and avoid chain-of-thought.
- If the context does not contain enough information to choose confidently, reply with <p>Insufficient information in the provided PDF.</p>
- If possible, include a short citation in parentheses (e.g., (p. 5)).
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
