import hmac
import streamlit as st
import config, pipeline, sheets
from sources.osm import CATEGORIES

st.set_page_config(page_title="Agency Lead Finder", layout="wide")

# ---- Access gate: nobody sees the tool (or can spend your API quota) without the password ----
def gate():
    pw = config.get("APP_PASSWORD")
    if not pw:
        st.error("APP_PASSWORD is not set in the server secrets."); st.stop()
    if st.session_state.get("auth"):
        return
    entry = st.text_input("Password", type="password")
    if entry and hmac.compare_digest(entry, str(pw)):
        st.session_state["auth"] = True; st.rerun()
    elif entry:
        st.error("Wrong password")
    st.stop()
gate()

st.title("🌍 Agency Lead Finder")
st.caption("Public map data, anywhere in the world → enrich → AI-scored → Google Sheet")

with st.sidebar:
    place = st.text_input("Place (any city, region, country, area)", "Karachi, Pakistan")
    cat = st.selectbox("Business type", list(CATEGORIES) + ["custom tags"])
    if cat == "custom tags":
        cat = st.text_input("OSM tags, comma separated", "shop=bakery, shop=florist")
    radius = st.slider("Radius around place centre (km, 0 = whole place area)", 0, 50, 0)
    limit = st.slider("Max results", 10, 200, 50, 10)
    enrich = st.checkbox("Enrich from websites / social", True)
    use_ai = st.checkbox("AI scoring & pitch", True)
    st.caption("Tip: for huge places (countries) use a city name + radius.")

if st.button("Find leads", type="primary"):
    bar = st.progress(0)
    def prog(i, n, name):
        bar.progress((i + 1) / max(n, 1), text=f"{i+1}/{n}: {name}")
    try:
        with st.spinner("Working..."):
            st.session_state["df"] = pipeline.run(place, cat, limit, radius, enrich, use_ai, prog)
    except Exception as e:
        st.error(str(e))

if "df" in st.session_state:
    df = st.session_state["df"]
    st.metric("Leads found", len(df))
    if {"lat", "lon"} <= set(df.columns):
        st.map(df.dropna(subset=["lat", "lon"]), latitude="lat", longitude="lon")
    st.dataframe(df.drop(columns=["site_text", "lat", "lon"], errors="ignore"), use_container_width=True)
    c1, c2 = st.columns(2)
    if c1.button("Push to Google Sheet"):
        try:  # Sheet ID comes from server secrets only, never from the UI
            n = sheets.push(df, config.get("GOOGLE_SHEET_ID"))
            st.success(f"Added {n} new rows (duplicates skipped).")
        except Exception as e:
            st.error(f"Sheet error: {e}")
    c2.download_button("Download CSV", df.to_csv(index=False), "leads.csv")
