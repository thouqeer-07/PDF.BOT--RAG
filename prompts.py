from langchain.prompts import PromptTemplate

SYSTEM_PROMPT = (
    "You are a precise, professional, and concise assistant.\n"
    "Always structure your response neatly using proper Markdown formatting.\n"
    "Avoid unnecessary symbols or raw formatting characters.\n"
    "If the answer is partially available, use what is known and note what is missing.\n"
    "If unsure, briefly explain why. If the answer is not in the context, say:\n"
    '"I don’t know based on the provided PDF."'
)

QA_TEMPLATE = """
{system}

---

### 📘 Context Summary:
{context}

---

### ❓ User Question:
{question}

---

### 🧭 Instructions:
- Write a **clear and neatly formatted answer** (2–5 sentences).
- Use bullet points if it improves readability.
- **Cite the source** (page number or filename) if available.
- If the answer is missing or unclear, respond politely that it’s not available in the PDF.

---

### 💬 Answer:
"""

MCQ_TEMPLATE = """
{system}

---

### 📘 Context Summary:
{context}

---

### ❓ Question:
{question}

---

### 🧭 Instructions for Multiple-Choice Questions:
- Respond **only** in the following clean format:

Answer: <Letter>  
**Explanation:** <1–2 line reasoning>  
**Source:** <Page number or filename, if available>

- Keep your output professional and well-spaced.
- Do not repeat the question or options.
- If there is insufficient context, reply exactly:
  "Insufficient information in the provided PDF."

---

### 💬 Response:
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
