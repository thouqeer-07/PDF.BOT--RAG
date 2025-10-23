# 📄 PDF BOT — AI-Powered PDF Assistant  

An AI chatbot that lets users **upload PDFs**, store them in **Google Drive**, and **chat with their documents** using **RAG Pipeline** and **Google Generative AI**   

---

## 🌐 Live Demo  
🚀 Try it on Streamlit Cloud → [https://pdfbot7.streamlit.app](https://pdf-bot7.streamlit.app/)  

---

## ⚙️ Tech Stack  

- **Frontend:** Streamlit  
- **AI Model:** Google Generative AI (`text-embedding-004`)  
- **Vector DB:** Qdrant  
- **Storage:** Google Drive API  
- **Auth:** OAuth 2.0  
- **Database:** MongoDB Atlas  
- **Language:** Python  
- **Deploy:** Streamlit Cloud  

---

## 🧠 How It Works  

1. User Creats account and login.
2. Doing OAuth For Connecting with Google Drive.  
3. Uploads a **PDF**, stored securely in Google Drive.  
4. Text is extracted → embeddings generated via **Google Generative AI**.  
5. Embeddings stored in **Qdrant** for retrieval.  
6. Chat responses generated using **RAG** and saved in **MongoDB**.  


---

## 🌱 Future Enhancements  

- Multi-format RAG (Sheets, Docs)  
- Role-based access control  
- Multi-cloud sync (AWS, Azure)  
- Analytics dashboard  

---

#  **Thank You for Visiting!**

