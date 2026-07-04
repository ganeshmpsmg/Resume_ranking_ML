"""frontend/pages/home.py — Upload resumes and job descriptions."""
import streamlit as st
from services.api_client import upload_resumes, create_jd, upload_jd_file, list_jds, list_resumes


def render():
    st.title("📋 Resume Ranking System")
    st.markdown(
        "Upload resumes and a job description to get AI-powered semantic rankings "
        "using **Sentence-BERT** embeddings, **hybrid BM25 + vector search**, and "
        "a **multi-factor weighted scoring** model."
    )

    col1, col2 = st.columns(2)

    # ── Left: Upload Resumes ─────────────────────────────────────────────
    with col1:
        st.subheader("📄 Upload Resumes")
        uploaded_files = st.file_uploader(
            "Select PDF, DOCX, or TXT files",
            type=["pdf", "docx", "doc", "txt"],
            accept_multiple_files=True,
            key="resume_uploader",
        )
        if st.button("⬆️ Upload Resumes", type="primary", disabled=not uploaded_files):
            files = [(f.name, f.read(), f.type or "application/octet-stream") for f in uploaded_files]
            with st.spinner(f"Parsing and embedding {len(files)} resume(s)…"):
                result = upload_resumes(files)
            st.success(f"✅ Uploaded {len(result)} resume(s) successfully!")
            for r in result:
                st.markdown(f"- **{r.get('name') or r.get('filename')}** | "
                             f"{r.get('years_experience', 0)} yrs | "
                             f"{r.get('education_level') or 'N/A'} | "
                             f"{len(r.get('skills', []))} skills detected")

        st.divider()
        st.subheader("📂 Stored Resumes")
        resumes = list_resumes()
        if resumes:
            st.caption(f"{len(resumes)} resume(s) in database")
            for r in resumes[:10]:
                st.markdown(f"- {r.get('name') or r.get('filename')} "
                             f"| {r.get('years_experience', 0)} yrs "
                             f"| {r.get('education_level') or 'N/A'}")
            if len(resumes) > 10:
                st.caption(f"… and {len(resumes) - 10} more")
        else:
            st.info("No resumes uploaded yet.")

    # ── Right: Job Description ───────────────────────────────────────────
    with col2:
        st.subheader("💼 Add Job Description")
        jd_mode = st.radio("Input method", ["Paste text", "Upload file"], horizontal=True)
        source  = st.selectbox("Source", ["custom", "linkedin", "naukri"])

        if jd_mode == "Paste text":
            jd_text = st.text_area(
                "Paste job description here", height=280,
                placeholder="Paste the full job description…",
            )
            jd_title = st.text_input("Job title (optional, auto-detected if blank)")
            if st.button("➕ Add Job Description", type="primary", disabled=not jd_text):
                with st.spinner("Processing JD…"):
                    result = create_jd(jd_text, title=jd_title or None, source=source)
                st.success(f"✅ JD saved: **{result['title']}** "
                            f"| {len(result.get('required_skills', []))} skills extracted "
                            f"| Min exp: {result.get('min_experience_years', 0)} yrs")
                st.session_state["last_jd_id"] = result["id"]
        else:
            jd_file = st.file_uploader("Upload JD (PDF/DOCX/TXT)", type=["pdf", "docx", "txt"])
            if st.button("➕ Upload & Add JD", type="primary", disabled=not jd_file):
                with st.spinner("Parsing JD file…"):
                    result = upload_jd_file(jd_file.name, jd_file.read(),
                                             jd_file.type or "application/octet-stream", source)
                st.success(f"✅ JD saved: **{result['title']}**")
                st.session_state["last_jd_id"] = result["id"]

        st.divider()
        st.subheader("📋 Stored Job Descriptions")
        jds = list_jds()
        if jds:
            for j in jds[:5]:
                st.markdown(
                    f"- **{j['title']}** | {len(j.get('required_skills', []))} skills "
                    f"| Min {j.get('min_experience_years', 0)} yrs exp "
                    f"| Source: {j.get('source', 'custom')}"
                )
        else:
            st.info("No job descriptions added yet.")

    st.divider()
    st.subheader("🚀 Quick Start")
    st.markdown("""
    1. **Upload resumes** (PDF / DOCX / TXT) — parsed, embedded, and stored automatically.
    2. **Add a job description** — paste text or upload a file.
    3. Go to **📊 Rank & Dashboard** → select the JD → click **Rank Resumes**.
    4. Explore **🔍 Candidate Profile** for per-candidate scores, skills, and ATS feedback.
    5. Use **📈 Evaluation** to measure ranking quality with Precision@K / Recall@K / MRR.
    6. Try **🤖 AI Feedback** for LLM-generated resume improvement suggestions (requires OpenAI key).
    """)
