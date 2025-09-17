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

def get_prompt():
    print("[DEBUG] get_prompt called")
    print(f"[DEBUG] Using QA_TEMPLATE: {QA_TEMPLATE}")
    return PromptTemplate(
        template=QA_TEMPLATE,
        input_variables=["system", "context", "question"],
        partial_variables={"system": SYSTEM_PROMPT},
    )
