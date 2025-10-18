from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = (
    "You are a precise, professional, and concise assistant.\n"
    "Always structure your response neatly and make it easy to read.\n"
    "If the answer is partially available, use what is known and note what is missing.\n"
    "If unsure, briefly explain why. If the answer is not in the context, say:\n"
    '"I don’t know based on the provided PDF."'
)

QA_TEMPLATE = """
{system}

📘 **Context Summary:**
{context}

❓ **User Question:**
{question}

🧭 **Instructions:**
- Write a clear and neatly formatted answer (2–5 sentences).
- Use bullet points if it improves readability.
- Cite the source (page number or filename) if available.
- If the answer is missing or unclear, respond politely that it’s not available in the PDF.

💬 **Answer:**
"""

MCQ_TEMPLATE = """
{system}

📘 **Context Summary:**
{context}

❓ **Question:**
{question}

🧭 **Instructions for Multiple-Choice Questions:**
- Respond **only** in the following format:
    **Answer:** A  
    **Explanation:** [Short 1–2 sentence reasoning with source if available]
- Be clear and structured.
- If the context lacks sufficient info, reply with exactly:
  "Insufficient information in the provided PDF."

💬 **Response:**
"""

def get_prompt():
    print("[DEBUG] get_prompt called")
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
