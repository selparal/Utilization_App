# app/sidebar.py
import streamlit as st

def sidebar_navigation():
    st.sidebar.title("Pages")
    if st.sidebar.button("Home"):
        st.switch_page("Home")  # your Home page filename without .py
    if st.sidebar.button("Project & Client Hours"):
        st.switch_page("Project_and_Client_Hours")
