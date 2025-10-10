import streamlit as st
from datetime import date

st.set_page_config(page_title="bostonrentals.com (mock)", page_icon="🏙️", layout="wide")

# ---------- Session setup ----------
if "page" not in st.session_state:
    st.session_state.page = "listings"
if "selected_listing" not in st.session_state:
    st.session_state.selected_listing = None

# ---------- Simple styles ----------
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
      .back-btn {
        display: inline-block;
        margin-bottom: 20px;
        color: #1E3A8A;
        text-decoration: none;
        font-weight: 600;
      }
      .chat-bar {
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 16px;
        margin-top: 16px;
        background: #F9FAFB;
        text-align: center;
        color: #374151;
        font-weight: 500;
      }
      .chat-cta {
        color: #1E3A8A; font-weight: 700;
      }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------- Fake data ----------
listings = [
    {
        "id": "backbay-1a",
        "address": "210 Commonwealth Ave #1A",
        "neighborhood": "Back Bay",
        "rent": 3895,
        "beds": 2,
        "baths": 1,
        "img": "https://images.unsplash.com/photo-1501183638710-841dd1904471?q=80&w=1600&auto=format&fit=crop"
    },
    {
        "id": "southend-3f",
        "address": "77 Rutland St #3F",
        "neighborhood": "South End",
        "rent": 3150,
        "beds": 1,
        "baths": 1,
        "img": "https://images.unsplash.com/photo-1494526585095-c41746248156?q=80&w=1600&auto=format&fit=crop"
    },
    {
        "id": "beacon-2b",
        "address": "14 Myrtle St #2B",
        "neighborhood": "Beacon Hill",
        "rent": 4290,
        "beds": 2,
        "baths": 1,
        "img": "https://images.unsplash.com/photo-1502672260266-1c1ef2d93688?q=80&w=1600&auto=format&fit=crop"
    },
    {
        "id": "jp-4c",
        "address": "33 Centre St #4C",
        "neighborhood": "Jamaica Plain",
        "rent": 2750,
        "beds": 2,
        "baths": 1,
        "img": "https://images.unsplash.com/photo-1493809842364-78817add7ffb?q=80&w=1600&auto=format&fit=crop"
    },
    {
        "id": "seaport-19d",
        "address": "131 Seaport Blvd #19D",
        "neighborhood": "Seaport",
        "rent": 5195,
        "beds": 1,
        "baths": 1.5,
        "img": "https://source.unsplash.com/krNjlNf7XrI/1600x900"
    },
]

# ---------- Helper: show listing cards ----------
def render_card(l):
    with st.container(border=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="meta">🛏️ {l["beds"]} bed • 🛁 {l["baths"]} bath</div>', unsafe_allow_html=True)
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        if st.button("💬 Chat about this listing", key=l["id"]):
            st.session_state.selected_listing = l
            st.session_state.page = "chat"
            st.experimental_rerun()

        st.markdown('</div>', unsafe_allow_html=True)

# ---------- Page: listings ----------
def show_listings():
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

# ---------- Page: chat ----------
def show_chat(listing):
    # Back button
    if st.button("⬅️ Back to listings"):
        st.session_state.page = "listings"
        st.experimental_rerun()

    # Listing header
    st.image(listing["img"], use_column_width=True)
    st.markdown(f"### {listing['address']} — {listing['neighborhood']}")
    st.markdown(f"**${listing['rent']:,}/month · {listing['beds']} bed · {listing['baths']} bath**")

    st.markdown("---")

    # Fake chat area
    st.markdown(
        f"""
        <div class="chat-bar">
          <p>💬 <span class="chat-cta">Inquire about this listing by starting a chat with an agent!</span></p>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ---------- Main router ----------
if st.session_state.page == "listings":
    show_listings()
elif st.session_state.page == "chat" and st.session_state.selected_listing:
    show_chat(st.session_state.selected_listing)
else:
    st.session_state.page = "listings"
    show_listings()
