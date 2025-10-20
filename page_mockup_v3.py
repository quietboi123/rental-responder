#-------------------------------------------------------------
#-------------------------------------------------------------
# 1A. Imports and page setup 
# Imports packages and sets up basic page configuration.

import os 
import streamlit as st
from openai import OpenAI 
from datetime import date

st.set_page_config(page_title = "bostonrentals.com (mock)", page_icon = "🏙️", layout = "wide")

#-------------------------------------------------------------
#-------------------------------------------------------------
# 1B. Secrets 
# Brings in secrete keys for calling of Supabase and OpenAI API

def get_secrets(name_env: str, *secrets_path):
    """
    Prefer flat environment variables (Render, GH Actions, etc.).
    Fall back to nested st.secrets['section']['key'] used on Streamlit Cloud.
    """
    val = os.environ.get(name_env)
    if val:
        return val
    try:
        s = st.secrets
        for k in secrets_path:
            s = s[k]
        return s
    except Exception:
        return None

OPENAI_API_KEY = get_secrets("OPENAI_API_KEY", "openai", "api_key")
SUPABASE_URL = get_secrets("SUPABASE_URL", "supabase", "url")
SUPABASE_SERVICE_KEY = get_secrets("SUPABASE_SERVICE_KEY", "supabase", "service_key")

#-------------------------------------------------------------
#-------------------------------------------------------------
# 1C. OpenAI System Prompt 
# Defines the prompt for interaction with OpenAI LLM

system_prompt = f"""
You are a friendly leasing agent for a Boston rental site. You will receive and respond to inbounds from prospective renters looking to inquire about properties.
Your job is to pre-qualify the prospective renter in a way that is concise and helpful. Always follow the following rules:
1. Always ask one follow-up if it moves the conversation towards scheduling a tour
2. If asked for facts (rent, beds, pets, availability, etc.), offer to connect the user with an agent to confirm
"""

#-------------------------------------------------------------
#-------------------------------------------------------------
# 1D. Helpers
# Several helper functions to use later on

# Creates a unique key for each listing to save chat history
def chat_key(listing_id: str) -> str:
    return f"chat_history_{listing_id}"

# Define the model to use from OpenAI
model_name = "gpt-4o"

# Creates a reply by calling OpenAI's API based on previously defined prompt
def generate_reply(user_message: str, history: list[dict]) -> str:
    """
    Turns chat history of specific listing into an OpenAI chat request. 
    History is defined as st.session_state[key] list of {role, content} messages
    """
    try:
        # Keep the chat history
        recent = history
        
        messages = [{"role": "system", "content": system_prompt}]
        messages.extend(recent)
        messages.append({"role":"user", "content": user_message})
        
        resp = client.chat.completions.create(
            model = model_name,
            messages = messages,
            temperature = 0.4,
        )
        return resp.choices[0].message.content.strip()
    except Exception as e:
        # Fail safe so that the app does not crash
        return ("Sorry, I'm having trouble connecting. Can you please try again in a moment?")
        

#-------------------------------------------------------------
#-------------------------------------------------------------
# 2. CSS styles (visual design) 
# Uses CSS to specify certain style elements on top of Streamlit defaults.

st.markdown(
    """
    <style>
      .site-title {
        font-weight: 800; font-size: 32px; letter-spacing: 0.5px;
        margin: 0 0 8px 0; color: #1F2937;
      }
      .site-sub {
        color: #6B7280; margin-bottom: 24px;
      }
      .card {
        border: 1px solid #E5E7EB;
        border-radius: 16px;
        padding: 16px 16px 14px 16px;
        background: #FFFFFF;
        box-shadow: 0 1px 2px rgba(0,0,0,0.03);
        height: 100%;
      }
      .addr { font-weight: 600; color: #1F2937; margin-bottom: 2px; }
      .neigh { color: #6B7280; margin-bottom: 10px; }
      .meta { display: flex; gap: 10px; color: #374151; margin-top: 8px; }
      .pill {
        display: inline-block; padding: 4px 10px; border-radius: 999px;
        background: #F3F4F6; color: #111827; font-size: 12px; font-weight: 600;
      }
      .price { font-size: 22px; font-weight: 800; color: #111827; }
      .divider { height: 1px; background: #F3F4F6; margin: 10px 0; }
      .btn {
        display: inline-block; text-align: center; padding: 10px 12px; width: 100%;
        border-radius: 10px; font-weight: 700; text-decoration: none;
        background: #1E3A8A; color: #FFFFFF !important;
      }
      .btn:hover { filter: brightness(1.05); color: #FFFFFF !important}
      .thumb {
        width: 100%; height: 160px; border-radius: 12px; object-fit: cover;
        background: #e9eef7;
      }
      @media (max-width: 900px) {
        .thumb { height: 140px; }
      }
    </style>
    """,
    unsafe_allow_html=True,
)


#-------------------------------------------------------------
#-------------------------------------------------------------
# 3. Fake data 
# Creates dummy data to reference in page elements & code 
# This is a Python list of dictionaries. Scalable solution would be to replace this with a real table (e.g., Supabase or Postgres)

listings = [
  {
    "id": "medford-1a",
    "address": "105 Burget Ave",
    "neighborhood": "Medford",
    "rent": 3200,
    "beds": 2,
    "baths": 1,
    "img": "https://images.unsplash.com/photo-1501183638710-841dd1904471?q=80&w=1600&auto=format&fit=crop"
  },
  {
    "id": "southend-5",
    "address": "146 Warren Ave",
    "neighborhood": "South End",
    "rent": 4500,
    "beds": 2,
    "baths": 1,
    "img": "https://images.unsplash.com/photo-1494526585095-c41746248156?q=80&w=1600&auto=format&fit=crop"
  },
  {
    "id": "dedham-74",
    "address": "74 Martin Bates St",
    "neighborhood": "Dedham",
    "rent": 6000,
    "beds": 3,
    "baths": 4,
    "img": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=1600&auto=format&fit=crop"
  },
  {
    
    "id": "newton-85",
    "address": "85 Halcyon Rd",
    "neighborhood": "Newton",
    "rent": 5500,
    "beds": 3,
    "baths": 2,
    "img": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?q=80&w=1600&auto=format&fit=crop"
  },
]


#-------------------------------------------------------------
#-------------------------------------------------------------
# 4. "Routing" with query parameters
# Uses URL parameters to manually change what the page looks like. This is not ideal as Streamlit is not built for multi-page sites.
# New version of Streamlit has st.page feature which may work as a page router. Worth exploring instead of using URL parameters

params = st.query_params #creates a dictionary equal to the current URL parameters
current_page = params.get("page", "home") #gets the current page from URL parameters. If none, defaults to "home"
selected_id = params.get("id", None) #gets the current id from URL parameters. If non, defaults to "none"


#-------------------------------------------------------------
#-------------------------------------------------------------
# 5. Navigation helpers
# These mutate the URL query parameters and trigger Streamlit to re-run the script and render a different branch

def go_to_chat(lid):
  st.query_params["page"] = "chat"
  st.query_params["id"] = lid

def go_home():
  st.query_params.clear()


#-------------------------------------------------------------
#-------------------------------------------------------------
# 6. Card renderer
# A single funciton that takes a "row" (l) from "Listings" and renders the styled card. Uses configurations by class as defined in section 2 above.

def render_card(l):
    with st.container(border=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta">🛏️ ' + str(l["beds"]) + ' bed &nbsp; • &nbsp; 🛁 ' + str(l["baths"]) + ' bath</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # Keep same blue button style (exact). This button is actually an HTML link to be able to format it in a custom way.
        st.markdown(
            f"""
            <a class="btn" href="?page=chat&id={l['id']}" target="_self">Chat about this listing</a>
            """,
            unsafe_allow_html=True
        )

        st.markdown('</div>', unsafe_allow_html=True)


#-------------------------------------------------------------
#-------------------------------------------------------------
# 7A. Home page
# Creates a 3-column grid, with two rows (top and bottom) each showing listings using render_card function defined above. Title and sub-title are HTML blocks styled by CSS

if current_page == "home":
    st.markdown('<div class="site-title">bostonrentals.com</div>', unsafe_allow_html=True)
    st.markdown('<div class="site-sub">Hand-picked apartments across Boston — mock demo</div>', unsafe_allow_html=True)

    cols_top = st.columns(3)
    for i, l in enumerate(listings[:3]):
        with cols_top[i]:
            render_card(l)

    cols_bottom = st.columns(3)
    for i, l in enumerate(listings[3:]):
        with cols_bottom[i]:
            render_card(l)

    st.caption(f"© {date.today().year} bostonrentals.com — mock UI for demo purposes only.")


#-------------------------------------------------------------
#-------------------------------------------------------------
# 7B. Chat page
# Creates a chat page based on the listing which is clicked

elif current_page == "chat" and selected_id: #if current_page = "chat" AND selected_id is not blank
    l = next((x for x in listings if x["id"] == selected_id), None) #takes first listing for which id = selected_id

    if st.button("⬅ Back to listings"): #creates the button which runs the go home function.
        go_home()
        st.rerun()

    if l: # Renders the current chat page based on the CSS defined in section 2 and the data from Listings.
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta">🛏️ ' + str(l["beds"]) + ' bed &nbsp; • &nbsp; 🛁 ' + str(l["baths"]) + ' bath</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("### Inquire about your listing")

        
        # Create a unique key for this listing's chat
        key = chat_key(l["id"])

        # If this is the first time opening this listing, start with a greeting message
        if key not in st.session_state:
            st.session_state[key] = [
                {
                    "role": "assistant",
                    "content": (
                        f"Hi! Thanks for your interest in **{l['address']}**.\n\n "
                        "Chat here to get started on scheduling a tour."
                    ),
                }
            ]

        # Show all messages as chat bubbles
        for msg in st.session_state[key]:
            #msg["role"] is either "assistant" or "user"
            with st.chat_message(msg["role"]):
                #msg["content"] is the text to display
                st.markdown(msg["content"])

        # Chat input at the bottom of the page
        user_msg = st.chat_input(placeholder = "Hi, I'm interested in this apartment!")

        # If the user types a message and hit enter
        if user_msg:
            # 1 - Save the user's message to history
            st.session_state[key].append({"role": "user", "content": user_msg})

            # 2 - Create the automatic reply & save to history
            assistant_reply = generate_reply(user_msg, st.session_state[key])
            st.session_state[key].append({"role": "assistant", "content": assistant_reply})

            # 3 - Immediately re-run so the new bubble appears above
            st.rerun()





