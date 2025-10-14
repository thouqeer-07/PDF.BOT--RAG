# ==== db.py ====
from pymongo import MongoClient
import streamlit as st
import os

# Replace this with your MongoDB Atlas connection string
from config import MONGO_URI    
DB_NAME = "rag_chatbot"

client = MongoClient(MONGO_URI)
db = client[DB_NAME]

# === USERS ===
def get_user(username):
    return db.users.find_one({"username": username})

def get_user_by_email(email):
    return db.users.find_one({"email": email})

def insert_user(username, email, password):
    db.users.insert_one({
        "username": username,
        "email": email,
        "password": password
    })

def delete_user(username):
    db.users.delete_one({"username": username})

# === CHATS ===
def get_user_chats(username):
    return db.user_chats.find_one({"username": username}) or {"pdf_chats": {}, "user_collections": [], "pdf_history": []}

def save_user_chats(username, pdf_chats, user_collections, pdf_history=None):
    update_data = {"pdf_chats": pdf_chats, "user_collections": user_collections}
    if pdf_history is not None:
        update_data["pdf_history"] = pdf_history
    db.user_chats.update_one(
        {"username": username},
        {"$set": update_data},
        upsert=True
    )

def delete_user_chats(username):
    db.user_chats.delete_one({"username": username})
