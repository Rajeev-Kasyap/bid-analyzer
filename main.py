import streamlit as st
import PyPDF2
import requests
import os
from dotenv import load_dotenv
import re
import time
from datetime import datetime

# Load environment variables
load_dotenv()
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"

# Page configuration
st.set_page_config(
    page_title="Bid Analyser Pro",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        text-align: center;
        padding: 2rem 0;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        color: white;
        border-radius: 10px;
        margin-bottom: 2rem;
    }
    
    .summary-card {
        background: black;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        margin: 1rem 0;
    }
    
    .question-card {
        background: black;
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        margin: 1rem 0;
    }
    
    .answer-card {
        background: black;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #28a745;
        margin: 1rem 0;
    }
    
    .upload-section {
        background: darkblue;
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
    }
    
    .stats-card {
        background: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        text-align: center;
    }
</style>
""", unsafe_allow_html=True)

def split_text_into_chunks(text, chunk_size=4000, overlap=500):
    """Splits text into overlapping chunks to stay within token limits."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunk = text[start:end]
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def extract_text_from_pdf(pdf_file):
    pdf_reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def clean_text(text):
    return re.sub(r'[^\x00-\x7F]+', '', text)

def ask_llm(question, context):
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on document content."},
        {"role": "user", "content": f"Document: {context}"},
        {"role": "user", "content": f"Question: {question}"}
    ]

    data = {
        "model": "llama3-8b-8192",
        "messages": messages
    }

    for attempt in range(3):
        try:
            response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=data)
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            if response.status_code == 429 and attempt < 2:
                time.sleep(2)  # Wait and retry
                continue
            return f"Error: {e}"

    try:
        response = requests.post(GROQ_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

def display_document_stats(text):
    """Display document statistics"""
    word_count = len(text.split())
    char_count = len(text)
    page_estimate = word_count // 250  # Rough estimate    

def main():
    # Header
    st.markdown("""
    <div class="main-header">
        <h1>📊 Bid Analyser Pro</h1>
        <p>Advanced Document Analysis & Q&A System</p>
    </div>
    """, unsafe_allow_html=True)

    # Sidebar
    with st.sidebar:
        st.header("🔧 Controls")
        
        # File upload section
        st.subheader("📁 Upload Document")
        uploaded_file = st.file_uploader(
            "Choose a PDF or TXT file",
            type=["pdf", "txt"],
            help="Upload your bid document for analysis"
        )
        
        # Quick actions
        st.subheader("⚡ Quick Actions")
        if st.button("🔄 Clear Analysis", use_container_width=True):
            for key in ["summary", "cleaned_text", "user_question", "answer", "last_uploaded_file"]:
                st.session_state.pop(key, None)
            st.rerun()
        
        # Document info
        if "cleaned_text" in st.session_state:
            st.subheader("📊 Document Info")
            st.info(f"Processed: {datetime.now().strftime('%H:%M:%S')}")
            
        # Sample questions
        st.subheader("💡 Sample Questions")
        sample_questions = [
            "What is the tender deadline?",
            "What are the eligibility criteria?",
            "What is the contract value?",
            "What documents are required?",
            "What is the payment terms?"
        ]
        
        for i, question in enumerate(sample_questions):
            if st.button(f"❓ {question}", key=f"sample_{i}", use_container_width=True):
                st.session_state.user_question = question

    # Main content area
    uploaded_filename = uploaded_file.name if uploaded_file else None

    # Detect if a new file is uploaded
    if st.session_state.get("last_uploaded_file") != uploaded_filename:
        st.session_state["last_uploaded_file"] = uploaded_filename
        # Clear old session state values
        for key in ["summary", "cleaned_text", "user_question", "answer"]:
            st.session_state.pop(key, None)

    # File upload section
    if not uploaded_file:
        st.markdown("""
        <div class="upload-section">
            <h2>📤 Upload Your Bid Document</h2>
            <p>Drag and drop a PDF or TXT file to get started with the analysis</p>
            <p><em>Supported formats: PDF, TXT</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Benefits section
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            ### 🎯 Key Information Extraction
            - Tender Number
            - Contract Value
            - Deadlines
            - Eligibility Criteria
            """)
        
        with col2:
            st.markdown("""
            ### 🤖 AI-Powered Analysis
            - Intelligent Q&A
            - Document Summarization
            - Key Insights
            - Risk Assessment
            """)
        
        with col3:
            st.markdown("""
            ### 📊 Comprehensive Reports
            - Structured Summary
            - Document Statistics
            - Export Options
            - Quick Actions
            """)

    # Process the uploaded file
    if uploaded_file and "cleaned_text" not in st.session_state:
        with st.spinner("🔄 Processing document..."):
            progress_bar = st.progress(0)
            
            # Extract text
            progress_bar.progress(25)
            if uploaded_file.type == "application/pdf":
                raw_text = extract_text_from_pdf(uploaded_file)
            else:
                raw_text = uploaded_file.getvalue().decode("utf-8")
            
            # Clean text
            progress_bar.progress(50)
            st.session_state.cleaned_text = clean_text(raw_text)
            
            # Generate summary
            progress_bar.progress(75)

            chunks = split_text_into_chunks(st.session_state.cleaned_text, chunk_size=4000, overlap=500)
            chunk_summaries = []

            with st.spinner("🔍 Summarizing document in chunks..."):
                for i, chunk in enumerate(chunks):
                    summary_prompt = (
                        "Analyze this bid document and provide the following information in a structured format:\n"
                        "1. **Tender Number:** \n"
                        "2. **Name of Work:** \n"
                        "3. **Department/Organization:** \n"
                        "4. **Estimated Contract Value:** \n"
                        "5. **Contract Period:** \n"
                        "6. **EMD (Earnest Money Deposit):** \n"
                        "7. **EMD Exemption:** \n"
                        "8. **Mode of Payment:** \n"
                        "9. **Key Eligibility Criteria:** \n"
                        "10. **Important Deadlines:** \n\n"
                        "Return only relevant information found in this chunk.\n\n"
                        f"Chunk {i+1}:\n{chunk}"
                    )
            
            result = ask_llm(summary_prompt, chunk)
            chunk_summaries.append(result)
            time.sleep(1.2)
            st.session_state.summary = "\n\n".join(chunk_summaries)
            progress_bar.progress(100)
            
        st.success("✅ Document processed successfully!")

    # Display results
    if "cleaned_text" in st.session_state:
        # Document statistics
        # st.subheader("📈 Document Overview")
        # display_document_stats(st.session_state.cleaned_text)
        
        # Summary section
        st.subheader("📋 Extracted Key Information")
        st.markdown(f"""
        <div class="summary-card">
            {st.session_state.summary}
        </div>
        """, unsafe_allow_html=True)
        
        # Export options
        if st.button("📥 Download Summary", use_container_width=True):
            st.download_button(
                label="Download as Text",
                data=st.session_state.summary,
                file_name=f"bid_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain"
            )
        
        # Q&A Section
        st.subheader("🔍 Ask Questions About the Document")
        
        # Create columns for better layout
        col1, col2 = st.columns([3, 1])
        
        with col1:
            user_question = st.text_input(
                "Type your question here:",
                value=st.session_state.get("user_question", ""),
                placeholder="e.g., What is the tender submission deadline?",
                key="question_input"
            )
        
        with col2:
            ask_button = st.button("🔍 Ask", use_container_width=True, type="primary")

        # Process question
        if (ask_button and user_question) or (user_question and user_question != st.session_state.get("last_question", "")):
            st.session_state.last_question = user_question
            
            with st.spinner("Analyzing your question..."):
                # answer = ask_llm(user_question, st.session_state.cleaned_text)
                chunks = split_text_into_chunks(st.session_state.cleaned_text, chunk_size=4000, overlap=500)
                answers = []

                with st.spinner("Scanning document in chunks..."):
                    for i, chunk in enumerate(chunks):
                        response = ask_llm(user_question, chunk)
                        if not response.lower().startswith("error"):
                            answers.append(response)
                        time.sleep(1.2)

                if answers:
                    answer = "\n\n".join(answers)
                else:
                    answer = "No relevant information found in the document."

                
                # Display Q&A
                st.markdown(f"""
                <div class="question-card">
                    <h4>❓ Question:</h4>
                    <p>{user_question}</p>
                </div>
                """, unsafe_allow_html=True)
                
                st.markdown(f"""
                <div class="answer-card">
                    <h4>💡 Answer:</h4>
                    <p>{answer}</p>
                </div>
                """, unsafe_allow_html=True)

        # Previous Q&A history
        if hasattr(st.session_state, 'qa_history') and st.session_state.qa_history:
            with st.expander("📚 Previous Q&A History"):
                for i, (q, a) in enumerate(st.session_state.qa_history):
                    st.markdown(f"**Q{i+1}:** {q}")
                    st.markdown(f"**A{i+1}:** {a}")
                    st.markdown("---")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #666;">
        <p>🚀 Bid Analyser Pro - Powered by AI | Built with Streamlit</p>
        <p><em>Streamline your bid analysis process with intelligent document processing</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
