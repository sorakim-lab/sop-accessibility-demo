import streamlit as st
import pandas as pd

st.title("SOP Accessibility Demo")

st.write("Search SOP content using indexed keywords.")

query = st.text_input("Enter keyword")

st.write("Demo working!")
