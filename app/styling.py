# app/styling.py
import streamlit as st

def apply_styles():
    # -------------------------
    # Hide built-in pages nav
    # -------------------------
    st.markdown("""
    <style>
    section[data-testid="stSidebar"] div[data-testid="stSidebarNav"] {
        display: none;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------
    # General fonts/colors
    # -------------------------
    st.markdown("""
    <style>
    html, body, [class*="css"] {
        font-family: Arial, sans-serif;
        color: #4D4D4D;
    }
    .main-title {
        font-family: Georgia, serif;
        font-weight: bold;
        font-size: 42px;
        color: #405A8A;
        padding: 20px 0px 10px 0px;
        text-align: center;
    }
    h2, h3 {
        color: #405A8A !important;
        font-family: Georgia, serif;
    }

    /* Add border around the whole app */
    div[data-testid="stAppViewContainer"] {
        border: 4px solid #405A8A;
        border-radius: 15px;
        padding: 20px;
        margin: 10px;
        background-color: #f5f7fb;
    }

    /* Blue top bar highlight */
    header[data-testid="stHeader"] {
        background-color: #5a82c8;
        color: white;
        border-radius: 10px;
        padding: 10px;
    }

    /* Optional: add subtle shadow around app container */
    div[data-testid="stAppViewContainer"] {
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------
    # Fix selectbox text
    # -------------------------
    st.markdown("""
    <style>
    div[data-baseweb="select"] span {
        color: #4D4D4D !important;
    }
    div[data-baseweb="select"] > div {
        background-color: white !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # -------------------------
    # 3D buttons
    # -------------------------
    st.markdown("""
    <style>
    div.stButton > button {
        background: linear-gradient(145deg, #5a82c8, #3f5f9c);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 0.5rem 1.2rem;
        font-weight: bold;
        box-shadow:
            0 4px 0 #2f4b7c,
            0 6px 10px rgba(0, 0, 0, 0.25);
        transition: all 0.1s ease-in-out;
    }
    div.stButton > button:active {
        transform: translateY(3px);
        box-shadow:
            0 1px 0 #2f4b7c,
            0 3px 6px rgba(0, 0, 0, 0.25);
    }
    div.stButton > button:hover {
        filter: brightness(1.05);
        cursor: pointer;
    }
    </style>
    """, unsafe_allow_html=True)
