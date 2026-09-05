"""
Streamlit demo: fetch today's Gmail inbox and tag each email with a local SLM.

Run with:  streamlit run app.py
"""

import streamlit as st

from classifier import TAGS, tag_email
from gmail_client import fetch_todays_emails, get_gmail_service

st.set_page_config(page_title="SLM Email Tagger", page_icon="🏷️", layout="wide")
st.title("🏷️ Today's Emails, Tagged by a Small Language Model")
st.caption("Gmail -> local SLM (Ollama) -> fixed-taxonomy tags")

with st.sidebar:
    st.header("Settings")
    max_results = st.slider("Max emails to fetch", 1, 50, 15)
    debug_mode = st.checkbox("Show raw model output (debug)", value=False)
    st.markdown("**Tag taxonomy** (fixed, given to the model):")
    st.write(", ".join(TAGS))
    run_button = st.button("Fetch + Tag Today's Emails", type="primary")

if "tagged_emails" not in st.session_state:
    st.session_state.tagged_emails = []

if run_button:
    with st.spinner("Connecting to Gmail..."):
        service = get_gmail_service()

    with st.spinner("Fetching today's emails..."):
        emails = fetch_todays_emails(service, max_results=max_results)

    if not emails:
        st.info("No emails found for today.")
    else:
        progress = st.progress(0.0, text="Tagging with SLM...")
        tagged = []
        for i, email in enumerate(emails):
            result = tag_email(email["subject"], email["sender"], email["body"])
            tagged.append({**email, **result})
            progress.progress((i + 1) / len(emails), text=f"Tagged {i + 1}/{len(emails)}")
        progress.empty()
        st.session_state.tagged_emails = tagged

emails = st.session_state.tagged_emails

if emails:
    # quick summary counts per tag
    tag_counts = {}
    parse_failures = 0
    for e in emails:
        for t in e["tags"]:
            tag_counts[t] = tag_counts.get(t, 0) + 1
        if not e.get("parsed_ok", True):
            parse_failures += 1

    st.subheader("Summary")
    cols = st.columns(len(tag_counts) or 1)
    for col, (tag, count) in zip(cols, sorted(tag_counts.items(), key=lambda x: -x[1])):
        col.metric(tag, count)

    if parse_failures:
        st.warning(
            f"⚠️ {parse_failures} email(s) fell back to \"Other\" because the model's output "
            "couldn't be parsed as JSON -- not a real tagging decision. Enable debug mode to see why."
        )

    st.subheader(f"Emails ({len(emails)})")
    tag_filter = st.multiselect("Filter by tag", options=list(tag_counts.keys()))

    for email in emails:
        if tag_filter and not any(t in tag_filter for t in email["tags"]):
            continue
        with st.container(border=True):
            st.markdown(f"**{email['subject']}**  \n*From: {email['sender']}*")
            st.caption(email["snippet"])
            tag_badges = " ".join(f"`{t}`" for t in email["tags"])
            if not email.get("parsed_ok", True):
                tag_badges += "  ⚠️ *parse failure*"
            st.write(tag_badges)
            if debug_mode:
                st.code(email.get("raw_response", ""), language="text")
else:
    st.info("Click **Fetch + Tag Today's Emails** in the sidebar to start.")