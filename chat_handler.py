import streamlit as st
import google.generativeai as genai
from config import GOOGLE_API_KEY
from prompts import get_prompt

def send_message():
    retriever = st.session_state.get("retriever", None)
    user_input = st.session_state.input_text.strip()
    print(f"[DEBUG] User input: {user_input}")
    if not user_input:
        return

    greetings = {"hi", "hello", "hey", "hiya", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx"}

    if any(greet in user_input.lower() for greet in greetings):
        bot_reply = "Hello! 👋 How can I help you today?"
    elif any(farewell in user_input.lower() for farewell in farewells):
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif any(thank in user_input.lower() for thank in thanks):
        bot_reply = "You're welcome! 😊"
    else:
        docs = retriever.invoke(user_input) if retriever else []
        print(f"[DEBUG] Retrieved docs: {len(docs)}")
        if not docs:
            bot_reply = "I couldn't find relevant information in the PDF."
        else:
            context = "\n\n".join([d.page_content for d in docs])
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = get_prompt().format(context=context, question=user_input)
            response = model.generate_content(prompt)
            bot_reply = response.text.strip()

    st.session_state.pdf_chats.append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""
