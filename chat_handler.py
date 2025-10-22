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

    import re

    # Use tokenized/word-boundary matching to avoid false positives (e.g., 'which' contains 'hi')
    greetings = {"hi", "hello", "hey", "hii"}
    farewells = {"bye", "goodbye", "exit", "quit"}
    thanks = {"thanks", "thank you", "thx", "tnx"}
    creator = {"who created you", "who is your creator", "who made you", "who developed you"}

    tokens = set(re.findall(r"\b\w+\b", user_input.lower()))

    if tokens & greetings:
        bot_reply = "Hello! 👋 How can I help you today?"
    elif any(phrase in user_input.lower() for phrase in creator):
        bot_reply = "Created and managed by Mr. Syed Thouqeer Ahmed A.🚀✨"
    elif tokens & farewells:
        bot_reply = "Goodbye! 👋 Have a great day!"
    elif any(phrase in user_input.lower() for phrase in thanks):
        # 'thank you' is multi-word; keep phrase check for thanks
        bot_reply = "You're welcome! 😊"
    else:
        # Heuristic: detect MCQ-type questions (presence of options like A), B), or 'choose' + options)
        is_mcq = False
        lowered = user_input.lower()
        if any(tok in lowered for tok in [" a)", " b)", " c)", " d)", "a.", "b.", "choose", "which option", "which of the following"]):
            is_mcq = True

        # Helper: robust retriever invocation (fallback chain)
        def fetch_docs(retriever_obj, query, k=4):
            if retriever_obj is None:
                return []
            # Try common LangChain retriever methods in order
            try:
                # Some retrievers support get_relevant_documents(query)
                if hasattr(retriever_obj, "get_relevant_documents"):
                    return retriever_obj.get_relevant_documents(query)
            except Exception:
                pass
            try:
                # Some custom retrievers expose a 'retrieve' method with k
                if hasattr(retriever_obj, "retrieve"):
                    return retriever_obj.retrieve(query, k=k)
            except Exception:
                pass
            try:
                # Some earlier code used 'invoke' — keep as fallback
                if hasattr(retriever_obj, "invoke"):
                    return retriever_obj.invoke(query)
            except Exception:
                pass
            try:
                # Last resort: as_retriever with search kwargs might expose search
                if hasattr(retriever_obj, "search"):
                    return retriever_obj.search(query)
            except Exception:
                pass
            return []

        # Increase retrieval size for MCQ to get more context
        docs = []
        if retriever:
            docs = fetch_docs(retriever, user_input, k=8 if is_mcq else 4)

        print(f"[DEBUG] Retrieved docs: {len(docs)}")
        for i, d in enumerate(docs):
            print(f"[DEBUG] Doc {i}: {getattr(d, 'page_content', str(d))[:200]}")

        if not docs:
            bot_reply = "I couldn't find relevant information in the PDF."
        else:
            # Prefer to include metadata (page/source) to help the LLM ground answers
            enriched_docs = []
            for d in docs:
                meta = getattr(d, "metadata", {}) or {}
                page = meta.get("page")
                source = meta.get("source")
                header = f"[Source: {source} | Page: {page}]\n" if source or page else ""
                enriched_docs.append(header + getattr(d, "page_content", str(d)))

            context = "\n\n".join(enriched_docs)
            print(f"[DEBUG] Context sent to LLM: {context[:1000]}")
            genai.configure(api_key=GOOGLE_API_KEY)
            model = genai.GenerativeModel("gemini-2.0-flash")

            # If MCQ, try to extract explicit options from the user's input
            option_text = ""
            if is_mcq:
                import re
                # Look for patterns like 'A) text', 'A. text', 'A: text' or lines starting with A/B/C
                opts = re.findall(r"([A-D][\)\.:]\s*[^\n]+)", user_input)
                if not opts:
                    # try single-letter options on separate lines
                    opts = re.findall(r"^([A-D])\s+-\s+(.+)$", user_input, flags=re.MULTILINE)
                    opts = [f"{m[0]}) {m[1]}" for m in opts]
                if opts:
                    option_text = "\nOptions:\n" + "\n".join(opts)

            if is_mcq:
                from prompts import get_mcq_prompt
                q_text = user_input + option_text
                prompt = get_mcq_prompt().format(context=context, question=q_text)
            else:
                from prompts import get_prompt
                prompt = get_prompt().format(context=context, question=user_input)

            print(f"[DEBUG] Prompt sent to LLM (truncated): {prompt[:1000]}")
            # Show spinner while generating
            with st.spinner("Generating answer..."):
                try:
                    response = model.generate_content(prompt)
                    print(f"[DEBUG] LLM response: {getattr(response, 'text', str(response))[:500]}")
                    bot_reply = getattr(response, 'text', str(response)).strip()
                except Exception as e:
                    print(f"[ERROR] LLM generation failed: {e}")
                    bot_reply = "Sorry, I couldn't generate a response at this time."
            


    selected_pdf = st.session_state.get("selected_pdf")
    if selected_pdf not in st.session_state.pdf_chats:
        st.session_state.pdf_chats[selected_pdf] = []
    st.session_state.pdf_chats[selected_pdf].append({"user": user_input, "bot": bot_reply})
    st.session_state.input_text = ""
