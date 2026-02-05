import streamlit as st
import os
import json
import datetime
import pandas as pd
from openai import OpenAI

# --- Configuration & Setup ---
st.set_page_config(page_title="Hey who are you? 👋", layout="wide")

HISTORY_DIR = "chat_history"
if not os.path.exists(HISTORY_DIR):
    os.makedirs(HISTORY_DIR)

# --- Helper Functions ---

def get_history_files():
    """Returns a list of chat history files sorted by modification time (newest first)."""
    files = [f for f in os.listdir(HISTORY_DIR) if f.endswith(".json")]
    # Sort by modification time
    files.sort(key=lambda x: os.path.getmtime(os.path.join(HISTORY_DIR, x)), reverse=True)
    return files

def load_chat(file_name):
    """Loads a chat session from a JSON file."""
    filepath = os.path.join(HISTORY_DIR, file_name)
    try:
        with open(filepath, "r") as f:
            data = json.load(f)
            return data
    except Exception as e:
        st.error(f"Error loading chat: {e}")
        return None

def save_chat(chat_id, messages):
    """Saves the current chat session to a JSON file."""
    if not messages:
        return # Don't save empty chats
    
    filepath = os.path.join(HISTORY_DIR, f"{chat_id}.json")
    data = {
        "id": chat_id,
        "timestamp": str(datetime.datetime.now()),
        "messages": messages
    }
    with open(filepath, "w") as f:
        json.dump(data, f, indent=4)

def delete_chat(file_name):
    """Deletes a chat history file."""
    filepath = os.path.join(HISTORY_DIR, file_name)
    if os.path.exists(filepath):
        os.remove(filepath)
        return True
    return False

def apply_custom_theme(theme):
    """
    Injects CSS to simulate theme switching.
    Since Streamlit is set to base='dark' in config.toml, we only need to forcibly override
    styles if 'Light' is selected.
    """
    if theme == "Light":
        # Force Light Mode styles with higher specificity
        st.markdown("""
            <style>
                /* Main Backgrounds */
                [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
                    background-color: #ffffff;
                    color: #000000;
                }
                [data-testid="stSidebar"] {
                    background-color: #f0f2f6;
                }
                
                /* Text Elements */
                p, h1, h2, h3, h4, h5, h6, li, span, label, .stMarkdown {
                    color: #31333F !important;
                }
                
                /* Buttons */
                button[kind="primary"] {
                    background-color: #ff4b4b !important;
                    color: white !important;
                }
                button[kind="secondary"] {
                    background-color: #ffffff !important;
                    color: #31333F !important;
                    border-color: #d6d6d6 !important;
                }
                
                /* Inputs (Text, Search, etc.) */
                [data-testid="stTextInput"] input, 
                [data-testid="stChatInput"] textarea {
                    background-color: #ffffff !important;
                    color: #31333F !important;
                    border-color: #d6d6d6 !important;
                }
                
                /* Dropdowns / Selectbox */
                [data-testid="stSelectbox"] > div > div {
                    background-color: #ffffff !important;
                    color: #31333F !important;
                    border-color: #d6d6d6 !important;
                }
                
                /* Popover (Dropdown options) - These are often rendered in portals */
                [data-baseweb="popover"], [data-baseweb="menu"] {
                    background-color: #ffffff !important;
                    color: #31333F !important;
                }
                [data-baseweb="menu"] ul, [data-baseweb="menu"] li {
                     background-color: #ffffff !important;
                     color: #31333F !important;
                }
                /* Hover effect for dropdown items */
                [data-baseweb="menu"] li:hover {
                    background-color: #f0f2f6 !important;
                }

                /* Icons/SVGs (Attempt to invert color) */
                [data-testid="stSidebar"] svg, [data-testid="stAppViewContainer"] svg {
                    fill: #31333F !important;
                }

                /* Bottom Container (Where chat input lives) */
                [data-testid="stBottom"] {
                    background-color: #ffffff !important;
                    border-top: 1px solid #ffffff !important;
                }
                [data-testid="stBottom"] > div {
                    background-color: #ffffff !important;
                }
                /* Specific targeting for the chat input container to avoid gaps */
                div[data-testid="stChatInput"] {
                     background-color: #ffffff !important;
                     border-color: #d6d6d6 !important;
                }
                div[data-testid="stChatInput"] > div {
                    background-color: #ffffff !important;
                    border-color: #d6d6d6 !important;
                    color: #31333F !important;
                }
                
                /* Aggressive Popover / Dropdown Fixes */
                [data-baseweb="popover"] {
                    background-color: #ffffff !important;
                }
                [data-baseweb="popover"] > div {
                    background-color: #ffffff !important;
                }
                [data-baseweb="menu"] {
                    background-color: #ffffff !important;
                }
                [data-baseweb="menu"] > ul {
                     background-color: #ffffff !important;
                }
                [data-baseweb="menu"] li {
                     background-color: #ffffff !important;
                     color: #31333F !important;
                }
                /* Fix for the selected value in the box before dropdown */
                [data-baseweb="select"] > div {
                    background-color: #ffffff !important;
                    color: #31333F !important;
                }
                
                /* Input text color inside chat input specifically */
                textarea {
                    color: #31333F !important;
                    caret-color: #31333F !important; 
                }
            </style>
        """, unsafe_allow_html=True)
    else:
        # Dark Mode is default via config.toml, but we can reinforce it or just do nothing.
        # Reinforcing to be safe if sticking with the manual toggle logic.
        pass

def init_session_state():
    """Initializes session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "current_chat_id" not in st.session_state:
        st.session_state.current_chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    if "theme" not in st.session_state:
        # Default to Config setting if possible, or just "Dark" since config says so
        st.session_state.theme = "Dark" 

init_session_state()
apply_custom_theme(st.session_state.theme)

try:
    api_key = st.secrets["OPENROUTER_API_KEY"]
except:
    st.error("OPENROUTER_API_KEY not found in secrets. Please set it in .streamlit/secrets.toml")
    st.stop()

# Initialize OpenAI client
client = OpenAI(
  base_url="https://openrouter.ai/api/v1",
  api_key=api_key,
  default_headers={
        "HTTP-Referer": "http://localhost:8501",  # Optional: shows on OpenRouter rankings
        "X-Title": "My ChatBot",                  # Optional: shows on OpenRouter rankings
    }
)

# --- Sidebar ---
with st.sidebar:
    st.title("Conversations")
    
    # New Chat Button
    if st.button("New Chat", use_container_width=True):
        # Save current if needed (auto-save is generally better on message send, but we can double check)
        if st.session_state.messages:
             save_chat(st.session_state.current_chat_id, st.session_state.messages)
        
        # Reset state
        st.session_state.messages = []
        st.session_state.current_chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        st.rerun()

    st.markdown("### Chat History")
    history_files = get_history_files()
    st.caption(f"Total: {len(history_files)} conversations")
    
    if not history_files:
        st.caption("No previous conversations.")
    else:
        for file_name in history_files:
            # Display format: clean timestamp or custom title if we had one
            display_name = file_name.replace(".json", "")
            
            col1, col2 = st.columns([0.8, 0.2])
            with col1:
                if st.button(f"📄 {display_name}", key=f"load_{file_name}", use_container_width=True):
                    # Load chat
                    chat_data = load_chat(file_name)
                    if chat_data:
                        st.session_state.messages = chat_data.get("messages", [])
                        st.session_state.current_chat_id = chat_data.get("id", display_name)
                        st.rerun()
            with col2:
                if st.button("🗑️", key=f"del_{file_name}", help="Delete this chat"):
                    if delete_chat(file_name):
                        # If deleted current chat, reset
                        if st.session_state.current_chat_id == file_name.replace(".json", ""):
                             st.session_state.messages = []
                             st.session_state.current_chat_id = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                        st.rerun()
    
    st.markdown("---")
    st.title("Settings")
    
    # Theme Toggle 
    # Logic: toggle on = Dark, toggle off = Light.
    is_dark = st.session_state.theme == "Dark"
    
    # Dynamic Label based on current state
    toggle_label = "Dark Mode" if is_dark else "Light Mode"
    
    # We use a fixed key so Streamlit tracks the widget instance correctly
    # even if we change the label (though changing label can sometimes reset state, 
    # we are controlling value explicitly).
    dark_mode_on = st.toggle(toggle_label, value=is_dark, key="theme_toggle")
    
    new_theme = "Dark" if dark_mode_on else "Light"
    if new_theme != st.session_state.theme:
        st.session_state.theme = new_theme
        st.rerun()
    
    # Apply custom CSS
    apply_custom_theme(st.session_state.theme)

    # Clear Current Chat
    if st.button("Clear Current Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()


# --- Main Interface ---

st.title("Hey who are you? 👋")

# Summarize Dropdown
summary_options = ["None", "Summarize in 1 sentence", "Summarize in 3 bullet points", "Extract keywords"]
summary_selection = st.selectbox("Summarize Conversation", summary_options)

if summary_selection != "None":
    if st.session_state.messages:
        try:
            with st.spinner(f"Generating summary ({summary_selection})..."):
                # Construct the prompt based on selection
                if summary_selection == "Summarize in 1 sentence":
                    system_prompt = "Summarize the following conversation in a single concise sentence."
                elif summary_selection == "Summarize in 3 bullet points":
                    system_prompt = "Summarize the key points of the following conversation in exactly 3 bullet points."
                elif summary_selection == "Extract keywords":
                    system_prompt = "Extract the top 5 most important keywords or topics from the conversation, separated by commas."
                
                # Context from messages
                conversation_text = "\n".join([f"{m['role']}: {m['content']}" for m in st.session_state.messages])
                
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"Here is the conversation:\n\n{conversation_text}"}
                ]
                
                response = client.chat.completions.create(
                    model="openai/gpt-4o-mini",
                    messages=messages
                )
                summary_result = response.choices[0].message.content
                st.success(summary_result)
        except Exception as e:
            st.error(f"Summarization failed: {e}")
    else:
        st.warning("No conversation to summarize yet.")

# Chat Interface
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# User Input
if prompt := st.chat_input("Say something..."):
    # Add user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Get AI response
    try:
        # Client is already initialized globally at start of script

        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = client.chat.completions.create(
                  model="openai/gpt-4o-mini",
                  messages=[{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]
                )
                assistant_message = response.choices[0].message.content
                st.markdown(assistant_message)
    
        st.session_state.messages.append({"role": "assistant", "content": assistant_message})
    
        # Auto-save after every exchange
        save_chat(st.session_state.current_chat_id, st.session_state.messages)
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
