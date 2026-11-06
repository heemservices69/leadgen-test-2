"""Central config: reads Streamlit secrets first, then environment variables."""
import os, json

def get(key, default=None):
    try:
        import streamlit as st
        if key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
    return os.getenv(key, default)

def service_account_info():
    try:
        import streamlit as st
        if "gcp_service_account" in st.secrets:
            return dict(st.secrets["gcp_service_account"])
    except Exception:
        pass
    raw = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    if raw:
        return json.loads(raw)
    with open(os.getenv("GCP_SERVICE_ACCOUNT_FILE", "service_account.json")) as f:
        return json.load(f)

USER_AGENT = "LeadGenBot/1.0 (agency research; contact: you@example.com)"
