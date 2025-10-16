import streamlit as st
import google.generativeai as genai
from config import GOOGLE_API_KEY
from prompts import get_prompt

def send_message():
    retriever = st.session_state.get("retriever", None)
    user_input = st.session_state.input_text.strip()
    print(f"[DEBUG] User input: {user_input}")
    print(f"[DEBUG] Selected PDF: {st.session_state.get('selected_pdf')}")
    print(f"[DEBUG] Retriever: {retriever}")
    if not user_input:
        return

    greetings = {"hi", "hello", "hey", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx", "tnx"}

    if any(greet in user_input.lower() for greet in greetings):
        bot_reply = "Hello! 👋 How can I help you today?"
    elif any(farewell in user_input.lower() for farewell in farewells):
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif any(thank in user_input.lower() for thank in thanks):
        bot_reply = "You're welcome! 😊"
    else:
        # Heuristic: detect MCQ-type questions (presence of options like A), B), or 'choose' + options)
        is_mcq = False
        lowered = user_input.lower()
        if any(tok in lowered for tok in [" a)", " b)", " c)", " d)", "a.", "b.", "choose", "which option", "which of the following"]):
            is_mcq = True

        # Increase retrieval size for MCQ to get more context
        docs = []
        if retriever:
            if is_mcq:
                docs = retriever.search(query=user_input, search_type="similarity", k=8)
            else:
                docs = retriever.invoke(user_input)

        print(f"[DEBUG] Retrieved docs: {len(docs)}")
        for i, d in enumerate(docs):
            print(f"[DEBUG] Doc {i}: {getattr(d, 'page_content', str(d))[:200]}")
        if not docs:
            bot_reply = "I couldn't find relevant information in the PDF."
        else:
            context = "\n\n".join([d.page_content for d in docs])
            print(f"[DEBUG] Context sent to LLM: {context[:500]}")
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            if is_mcq:
                from prompts import get_mcq_prompt
                prompt = get_mcq_prompt().format(context=context, question=user_input)
            else:
                from prompts import get_prompt
                prompt = get_prompt().format(context=context, question=user_input)
            print(f"[DEBUG] Prompt sent to LLM: {prompt}")
            response = model.generate_content(prompt)
            print(f"[DEBUG] LLM response: {response.text.strip()}")
            bot_reply = response.text.strip()

    selected_pdf = st.session_state.get("selected_pdf")
    if selected_pdf not in st.session_state.pdf_chats:
        st.session_state.pdf_chats[selected_pdf] = []
    st.session_state.pdf_chats[selected_pdf].append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""
