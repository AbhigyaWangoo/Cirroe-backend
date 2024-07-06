import streamlit as st
from src.actions.construct import ConstructCFStackAction
import os

import streamlit as st

# Define custom CSS based on your globals.css
custom_css = """
<style>
:root {
  --background: hsl(0, 0%, 100%);
  --foreground: hsl(222.2, 84%, 4.9%);
  --card: hsl(0, 0%, 100%);
  --card-foreground: hsl(222.2, 84%, 4.9%);
  --popover: hsl(0, 0%, 100%);
  --popover-foreground: hsl(222.2, 84%, 4.9%);
  --primary: hsl(222.2, 47.4%, 11.2%);
  --primary-foreground: hsl(210, 40%, 98%);
  --secondary: hsl(210, 40%, 96.1%);
  --secondary-foreground: hsl(222.2, 47.4%, 11.2%);
  --muted: hsl(210, 40%, 96.1%);
  --muted-foreground: hsl(215.4, 16.3%, 46.9%);
  --accent: hsl(210, 40%, 96.1%);
  --accent-foreground: hsl(222.2, 47.4%, 11.2%);
  --destructive: hsl(0, 84.2%, 60.2%);
  --destructive-foreground: hsl(210, 40%, 98%);
  --border: hsl(214.3, 31.8%, 91.4%);
  --input: hsl(214.3, 31.8%, 91.4%);
  --ring: hsl(222.2, 84%, 4.9%);
  --radius: 2rem;
}

.dark {
  --background: hsl(222.2, 84%, 4.9%);
  --foreground: hsl(210, 40%, 98%);
  --card: hsl(222.2, 84%, 4.9%);
  --card-foreground: hsl(210, 40%, 98%);
  --popover: hsl(222.2, 84%, 4.9%);
  --popover-foreground: hsl(210, 40%, 98%);
  --primary: hsl(210, 40%, 98%);
  --primary-foreground: hsl(222.2, 47.4%, 11.2%);
  --secondary: hsl(217.2, 32.6%, 17.5%);
  --secondary-foreground: hsl(210, 40%, 98%);
  --muted: hsl(217.2, 32.6%, 17.5%);
  --muted-foreground: hsl(215, 20.2%, 65.1%);
  --accent: hsl(217.2, 32.6%, 17.5%);
  --accent-foreground: hsl(210, 40%, 98%);
  --destructive: hsl(0, 62.8%, 30.6%);
  --destructive-foreground: hsl(210, 40%, 98%);
  --border: hsl(217.2, 32.6%, 17.5%);
  --input: hsl(217.2, 32.6%, 17.5%);
  --ring: hsl(212.7, 26.8%, 83.9%);
}

body {
  background-color: hsl(var(--background));
  color: hsl(var(--foreground));
}

h1, h2, h3, h4, h5, h6 {
  color: hsl(var(--foreground));
}
</style>
"""

# Inject custom CSS
st.markdown(custom_css, unsafe_allow_html=True)

st.title("Cirrus")

if "messages" not in st.session_state:
    st.session_state.messages = []

for message in st.session_state["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# initialize model
if "model" not in st.session_state:
    st.session_state.model = "gpt-3.5-turbo"

# user input
if user_prompt := st.chat_input("Your prompt"):
    st.session_state.messages.append({"role": "user", "content": user_prompt})
    with st.chat_message("user"):
        st.markdown(user_prompt)

    # generate responses
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        action = ConstructCFStackAction()

        for response_chunk in action.stream_response(user_prompt):
            full_response += response_chunk
            message_placeholder.markdown(full_response)

        message_placeholder.markdown(full_response)

    st.session_state.messages.append({"role": "assistant", "content": full_response})
