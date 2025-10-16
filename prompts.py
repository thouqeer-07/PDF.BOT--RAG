from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = (
    "You are a precise, concise assistant.\n"
    "If the answer is partially available, use it. If unsure, explain why.\n"
    "If the answer is not in the context, say you don't know based on the provided PDF.\n"
)

QA_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions:
- Answer in 2-5 sentences unless the user asks for more detail.
- Cite the source (page number or filename) if available.
"""


MCQ_TEMPLATE = """
{system}

# Context:
{context}

# Question:
{question}

# Instructions for multiple-choice questions (MCQ):
- If the question is a multiple-choice question, respond with exactly one letter (A, B, C, D, etc.) on the first line indicating the chosen option.
- On the following line, provide a 1-2 sentence concise justification (no chain-of-thought) and cite the source (page number or filename) if available.
- If the context does not contain enough information to choose confidently, respond with "Insufficient information in the provided PDF." on a single line.
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
