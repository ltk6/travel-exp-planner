import streamlit as st
from .base import get_base_css
from .components import get_components_css

def inject_custom_css():
    """Combines modular CSS files and injects them into the Streamlit app."""
    css = f"""
    <style>
    {get_base_css()}
    {get_components_css()}
    </style>
    """
    st.markdown(css, unsafe_allow_html=True)