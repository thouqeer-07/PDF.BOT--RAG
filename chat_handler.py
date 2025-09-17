import streamlit as st
import google.generativeai as genai
from config import GOOGLE_API_KEY
from prompts import get_prompt

def send_message(retriever):
    user_input = st.session_state.input_text.strip()
    print(f"[DEBUG] User input: {user_input}")
    if not user_input:
        return
    greetings = {"hi", "hello", "hey", "hiya", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx"}
    if any(greet in user_input.lower() for greet in greetings):
        print("[DEBUG] Detected greeting")
        bot_reply = "Hello! 👋 How can I help you today?"
    elif any(farewell in user_input.lower() for farewell in farewells):
        print("[DEBUG] Detected farewell")
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif any(thank in user_input.lower() for thank in thanks):
        print("[DEBUG] Detected thanks")
        bot_reply = "You're welcome! 😊"
    else:
        docs = retriever.invoke(user_input) if retriever else []
        print(f"[DEBUG] Retrieved docs: {len(docs)}")
        if not docs:
            bot_reply = "I couldn't find relevant information in the PDF."
        else:
            context = "\n\n".join([d.page_content for d in docs])
            print(f"[DEBUG] Context for LLM: {context[:200]}...")
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = get_prompt().format(context=context, question=user_input)
            print(f"[DEBUG] Prompt sent to LLM: {prompt}")
            response = model.generate_content(prompt)
            print(f"[DEBUG] LLM response: {response.text.strip()}")
            bot_reply = response.text.strip()
    print(f"[DEBUG] Bot reply: {bot_reply}")
    st.session_state.pdf_chats.append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""
