import streamlit as st
from agent import agent

st.set_page_config(page_title="Repo Explorer Agent", page_icon="🔍")
st.title("🔍 Repo Explorer Agent")
st.caption("Load a GitHub repo, then ask questions about its code.")

if "messages" not in st.session_state:
    st.session_state.messages = []

with st.sidebar:
    st.subheader("Load a repository")
    repo_url = st.text_input("GitHub URL", placeholder="https://github.com/user/repo")
    if st.button("Load repo") and repo_url:
        with st.status("Loading repository...", expanded=True) as status:
            st.write("Cloning repository...")
            st.write("Indexing code (this can take a minute for larger repos)...")
            result = agent.invoke({
                "messages": [{"role": "user", "content": f"Load the repo at {repo_url}"}]
            })
            status.update(label="Repository loaded!", state="complete", expanded=False)
        st.session_state.messages.append({"role": "assistant", "content": result["messages"][-1].content})
        st.rerun()

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if prompt := st.chat_input("Ask something about the loaded repo..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ]
            result = agent.invoke({"messages": history})
            answer = result["messages"][-1].content
            st.markdown(answer)

    st.session_state.messages.append({"role": "assistant", "content": answer})