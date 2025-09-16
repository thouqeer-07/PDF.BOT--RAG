import streamlit as st
import google.generativeai as genai
from config import GOOGLE_API_KEY
from prompts import get_prompt

def send_message(retriever):
    print("[DEBUG] send_message called")
    user_input = st.session_state.input_text.strip()
    print(f"[DEBUG] Raw user input: {st.session_state.input_text}")
    print(f"[DEBUG] Stripped user input: {user_input}")
    if not user_input:
        print("[DEBUG] No user input provided, returning early.")
        return
    greetings = {"hi", "hello", "hey", "hiya", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx"}
    user_input_lower = user_input.lower()
    print(f"[DEBUG] user_input_lower: {user_input_lower}")
    if any(greet in user_input_lower for greet in greetings):
        print("[DEBUG] Detected greeting")
        bot_reply = "Hello! 👋 How can I help you today?"
    elif any(farewell in user_input_lower for farewell in farewells):
        print("[DEBUG] Detected farewell")
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif any(thank in user_input_lower for thank in thanks):
        print("[DEBUG] Detected thanks")
        bot_reply = "You're welcome! 😊"
    else:
        print(f"[DEBUG] Querying retriever: {retriever}")
        docs = retriever.invoke(user_input) if retriever else []
        print(f"[DEBUG] Retrieved docs: {len(docs)}")
        if docs:
            st.markdown("**Top 4 Retrieved Chunks:**")
            for i, d in enumerate(docs[:4]):
                # Map 'text' field to page_content if present
                page_content = getattr(d, 'page_content', None)
                if not page_content and hasattr(d, 'metadata') and isinstance(d.metadata, dict):
                    page_content = d.metadata.get('text', None)
                if page_content and page_content.strip():
                    st.markdown(f"**Doc {i+1}:**\n{page_content[:500]}{'...' if len(page_content) > 500 else ''}")
                else:
                    st.markdown(f"**Doc {i+1}:** _No text found. Full object:_\n`{repr(d)}`")
        if not docs:
            print("[DEBUG] No relevant docs found.")
            bot_reply = "I couldn't find relevant information in the PDF."
        else:
            # Use mapped text for LLM context, ensuring no None values
            context = "\n\n".join([
                (
                    getattr(d, 'page_content', None)
                    or (d.metadata.get('text') if hasattr(d, 'metadata') and isinstance(d.metadata, dict) else str(d))
                    or ""
                )
                for d in docs
            ])
            print(f"[DEBUG] Context for LLM (first 300 chars): {context[:300]}")
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")
            prompt = get_prompt().format(context=context, question=user_input)
            print(f"[DEBUG] Prompt sent to LLM: {prompt}")
            response = model.generate_content(prompt)
            print(f"[DEBUG] LLM response: {response.text.strip()}")
            bot_reply = response.text.strip()
    print(f"[DEBUG] Appending chat: user='{user_input}', bot='{bot_reply}'")
    st.session_state.pdf_chats.append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""
    print("[DEBUG] send_message completed")
