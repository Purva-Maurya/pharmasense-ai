"""STEP 8: a Streamlit chat UI in front of the router. Run with:
    streamlit run src/app.py
This is the demo interface -- one chat box routes to any of the 5 agents."""
import streamlit as st
from router import route

st.set_page_config(page_title="PharmaSense AI", page_icon="\U0001F9EA")
st.title("\U0001F9EA PharmaSense AI")
st.caption(
    "Ask about trials, literature, adverse events, compound similarity, or "
    "request a full compound picture. Example: 'Which Phase II oncology "
    "trials are below 60% enrollment?'"
)

if "history" not in st.session_state:
    st.session_state.history = []

for turn in st.session_state.history:
    with st.chat_message(turn["role"]):
        st.markdown(turn["content"])

question = st.chat_input("Ask PharmaSense AI...")
if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    with st.chat_message("assistant"):
        with st.spinner("Routing and thinking..."):
            try:
                out = route(question)
                answer = (out.get("answer") or out.get("report")
                          or str(out.get("verdict")) or "(no answer produced)")
                st.caption(f"Routed to: `{out['route']}`")
                st.markdown(answer)
                if out.get("sources"):
                    with st.expander("Sources"):
                        for h in out["sources"]:
                            st.write(f"{h['citation']}  score={h['score']}  {h['title']}")
            except Exception as e:
                answer = f"Something went wrong: {type(e).__name__}: {e}"
                st.error(answer)
    st.session_state.history.append({"role": "assistant", "content": answer})