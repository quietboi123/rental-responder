import streamlit as st
from datetime import date

st.set_page_config(page_title="bostonrentals.com (mock)", page_icon="🏙️", layout="wide")

# ---------- Simple styles for prettier cards ----------
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

# ---------- Fake data (Boston area) ----------
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
]

# ---------- Header ----------
st.markdown('<div class="site-title">bostonrentals.com</div>', unsafe_allow_html=True)
st.markdown('<div class="site-sub">Hand-picked apartments across Boston — mock demo</div>', unsafe_allow_html=True)

# ---------- Grid renderer ----------
def render_card(l):
    with st.container(border=False):
        st.markdown('<div class="card">', unsafe_allow_html=True)

        # Thumbnail
        st.markdown(f'<img class="thumb" src="{l["img"]}" alt="Listing photo">', unsafe_allow_html=True)

        # Address + neighborhood
        st.markdown(f'<div class="addr">📍 {l["address"]}</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="neigh">{l["neighborhood"]}</div>', unsafe_allow_html=True)

        # Price + meta
        st.markdown(f'<div class="price">${l["rent"]:,}/mo</div>', unsafe_allow_html=True)
        st.markdown('<div class="meta">🛏️ ' + str(l["beds"]) + ' bed &nbsp; • &nbsp; 🛁 ' + str(l["baths"]) + ' bath</div>', unsafe_allow_html=True)

        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # CTA (placeholder for now)
        # In later steps we'll route to a per-listing chat
        st.markdown(f'<a class="btn" href="#" onclick="return false;">Chat about this listing</a>', unsafe_allow_html=True)

        st.markdown('</div>', unsafe_allow_html=True)


# Layout: 3 cards on the first row, 2 on the second
cols_top = st.columns(3)
for i, l in enumerate(listings[:3]):
    with cols_top[i]:
        render_card(l)

cols_bottom = st.columns(3)
for i, l in enumerate(listings[3:]):
    with cols_bottom[i]:
        render_card(l)

# Footer
st.caption(f"© {date.today().year} bostonrentals.com — mock UI for demo purposes only.")
