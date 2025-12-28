import asyncio
import time
import streamlit as st
import inngest
import os
import requests
from pathlib import Path
from config import settings


st.set_page_config(
    page_title="RAG System - PDF Intelligence",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="collapsed"
)


@st.cache_resource
def get_inngest_client() -> inngest.Inngest:
    return inngest.Inngest(app_id="rag_app", is_production=False)


def save_uploaded_pdf(file) -> Path:
    uploads_dir = Path("uploads")
    uploads_dir.mkdir(parents=True, exist_ok=True)
    file_path = uploads_dir / file.name
    file_bytes = file.getbuffer()
    file_path.write_bytes(file_bytes)
    return file_path


async def send_rag_ingest_event(pdf_path: Path) -> None:
    client = get_inngest_client()
    await client.send(
        inngest.Event(
            name="rag/ingest_pdf",
            data={
                "pdf_path": str(pdf_path.resolve()),
                "source_id": pdf_path.name,
            },
        )
    )


if "uploaded_files" not in st.session_state:
    st.session_state.uploaded_files = []

st.title(" RAG System")
st.divider()

async def send_rag_query_event(question: str, top_k: int) -> None:
    client = get_inngest_client()
    result = await client.send(
        inngest.Event(
            name="rag/query_pdf_ai",
            data={
                "question": question,
                "top_k": top_k,
            },
        )
    )

    return result[0]


def fetch_runs(event_id: str) -> list[dict]:
    url = f"{settings.INNGEST_API_BAS}/events/{event_id}/runs"
    resp = requests.get(url)
    resp.raise_for_status()
    data = resp.json()
    return data.get("data", [])


def wait_for_run_output(event_id: str, timeout_s: float = 120.0, poll_interval_s: float = 0.5) -> dict:
    start = time.time()
    last_status = None
    while True:
        runs = fetch_runs(event_id)
        if runs:
            run = runs[0]
            status = run.get("status")
            last_status = status or last_status
            if status in ("Completed", "Succeeded", "Success", "Finished"):
                return run.get("output") or {}
            if status in ("Failed", "Cancelled"):
                raise RuntimeError(f"Function run {status}")
        if time.time() - start > timeout_s:
            raise TimeoutError(f"Timed out waiting for run output (last status: {last_status})")
        time.sleep(poll_interval_s)



tab2, tab1 = st.tabs(["📤 Upload Documents", "💬 Query Documents", ])

with tab1:
    st.markdown("#### Ask a question about the information you want to obtain from your files", text_alignment="center")

    with st.container(border=False):
        col1, col2, col3 = st.columns([1, 7, 1])
        with col2:
            with st.form("rag_query_form"):
                question = st.text_area(
                    "Your question",
                    height=120,
                    placeholder="Write your question here, about your files, for example: How many people are there in Mexico?",
                    help="Type any question related to the documents you have uploaded"
                )

                col1 = st.columns([1])[0]
                with col1:
                    top_k = st.slider(
                        "Number of chunks to analyze",
                        min_value=1,
                        max_value=40,
                        value=5,
                        help="Higher number = more context but slower",
                        width=8000
                    )
                submitted = st.form_submit_button("Search Answer", use_container_width=True, type="primary")

                if submitted and question.strip():
                    with st.spinner("Processing your question and generating answer..."):
                        try:
                            event_id = asyncio.run(send_rag_query_event(question.strip(), int(top_k)))
                            output = wait_for_run_output(event_id)
                            answer = output.get("answer", "")
                            sources = output.get("sources", [])

                            st.divider()
                            st.markdown("### Answer")

                            if answer:
                                st.info(answer)
                            else:
                                st.warning("Could not generate an answer. Verify that you have uploaded related documents.")

                            if sources:
                                with st.expander("View Consulted Sources", expanded=False):
                                    for idx, s in enumerate(sources, 1):
                                        st.markdown(f"**{idx}.** {s}")
                        except Exception as e:
                            st.error(f"Error processing the question: {str(e)}")
                elif submitted:
                    st.warning("Please write a question before submitting.")

with tab2:
    st.markdown("#### Add new documents to the system")

    col1, col2 = st.columns([3, 2])

    with col1:
        with st.container(border=True):
            st.markdown("**📁 Select a PDF file**")
            uploaded = st.file_uploader(
                "Drag your file or click to select",
                type=["pdf"],
                accept_multiple_files=False,
                label_visibility="collapsed",
                key="pdf_uploader"
            )

            if uploaded is not None:
                st.divider()
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.caption("**File name:**")
                    st.caption(uploaded.name)
                with col_info2:
                    size_mb = uploaded.size / (1024 * 1024)
                    st.caption("**File size:**")
                    st.caption(f"{size_mb:.2f} MB")

                if st.button("Upload Document", type="primary", use_container_width=True):
                    already_uploaded = any(f["name"] == uploaded.name for f in st.session_state.uploaded_files)

                    if already_uploaded:
                        st.warning(f"⚠️ '{uploaded.name}' has already been uploaded.")
                    else:
                        with st.spinner("Processing and storing document..."):
                            try:
                                path = save_uploaded_pdf(uploaded)
                                asyncio.run(send_rag_ingest_event(path))
                                time.sleep(0.3)

                                st.session_state.uploaded_files.append({
                                    "name": uploaded.name,
                                    "size": f"{size_mb:.2f} MB",
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                })

                                st.success(f"Document '{path.name}' processed successfully!")
                                time.sleep(1)
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error processing the document: {str(e)}")

        if st.session_state.uploaded_files:
            st.divider()
            st.markdown("**📚 Uploaded Documents**")
            with st.container(border=True, height=300):
                for idx, file_info in enumerate(reversed(st.session_state.uploaded_files), 1):
                    with st.container():
                        col_idx, col_name, col_size, col_time = st.columns([0.5, 3, 1.5, 2])
                        with col_idx:
                            st.caption(f"**{len(st.session_state.uploaded_files) - idx + 1}.**")
                        with col_name:
                            st.caption(f"📄 {file_info['name']}")
                        with col_size:
                            st.caption(f"💾 {file_info['size']}")
                        with col_time:
                            st.caption(f"🕐 {file_info['timestamp']}")
                        if idx < len(st.session_state.uploaded_files):
                            st.divider()

    with col2:
        with st.container(border=True):
            st.markdown("**ℹ️ Information**")
            st.markdown("""
            **How does it work?**

            1. Select a PDF file from your computer
            2. Review the file information
            3. Click "Upload Document" to process
            4. The system indexes the content
            5. Your document is ready for queries!

            **Features:**
            - View all uploaded documents with timestamps
            - Duplicate detection prevents re-uploading
            - Uploaded files persist during session

            **Supported formats:**
            - PDF (.pdf)

            **Limits:**
            - Maximum recommended size: 50 MB
            - No limit on number of documents
            """)
