import streamlit as st
import PyPDF2
import requests
import os
from dotenv import load_dotenv
import re
import time
from datetime import datetime
import json

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
        background: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #667eea;
        margin: 1.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .summary-card h3 {
        color: #667eea;
        margin-bottom: 1rem;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .summary-card h4 {
        color: #333;
        margin: 1rem 0 0.5rem 0;
        font-size: 1.1rem;
        font-weight: 600;
    }
    
    .summary-card p, .summary-card li {
        color: #555;
        line-height: 1.6;
        margin-bottom: 0.5rem;
    }
    
    .summary-card ul {
        padding-left: 1.5rem;
        margin-bottom: 1rem;
    }
    
    .question-card {
        background: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        margin: 1.5rem 0;
        border-left: 5px solid #007bff;
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .question-card h4 {
        color: #007bff;
        margin-bottom: 1rem;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .question-card p {
        color: #333;
        line-height: 1.6;
        font-size: 1rem;
        font-weight: 500;
    }
    
    .answer-card {
        background: #ffffff;
        padding: 2rem;
        border-radius: 15px;
        border-left: 5px solid #28a745;
        margin: 1.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    }
    
    .answer-card h4 {
        color: #28a745;
        margin-bottom: 1rem;
        font-size: 1.2rem;
        font-weight: 600;
    }
    
    .answer-card p {
        color: #333;
        line-height: 1.8;
        font-size: 1rem;
    }
    
    .upload-section {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 10px;
        text-align: center;
        margin: 1rem 0;
        color: white;
    }
    
    .error-card {
        background: #ffebee;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #f44336;
        margin: 1rem 0;
        border: 1px solid #ffcdd2;
    }
</style>
""", unsafe_allow_html=True)

def split_text_into_chunks(text, chunk_size=3000, overlap=300):
    """Splits text into overlapping chunks to stay within token limits."""
    if not text or len(text.strip()) == 0:
        return []
    
    chunks = []
    start = 0
    text_length = len(text)
    
    while start < text_length:
        end = min(start + chunk_size, text_length)
        chunk = text[start:end].strip()
        
        if chunk:  # Only add non-empty chunks
            chunks.append(chunk)
        
        if end >= text_length:
            break
            
        start += chunk_size - overlap
    
    return chunks

def extract_text_from_pdf(pdf_file):
    """Extract text from PDF file with error handling."""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        
        for page_num, page in enumerate(pdf_reader.pages):
            try:
                page_text = page.extract_text()
                if page_text:
                    text += f"\n--- Page {page_num + 1} ---\n{page_text}\n"
            except Exception as e:
                st.warning(f"Error reading page {page_num + 1}: {str(e)}")
                continue
        
        if not text.strip():
            st.error("No text could be extracted from the PDF. The PDF might be password-protected or contain only images.")
            return None
            
        return text
    except Exception as e:
        st.error(f"Error reading PDF file: {str(e)}")
        return None

def format_summary_for_display(summary_text):
    """Format the summary text for better display with proper HTML formatting."""
    if not summary_text or summary_text.startswith("Error"):
        return summary_text
    
    # Replace markdown-style headers with HTML
    formatted = re.sub(r'\*\*(.*?)\*\*', r'<h4>\1</h4>', summary_text)
    
    # Handle bullet points and lists
    lines = formatted.split('\n')
    formatted_lines = []
    in_list = False
    
    for line in lines:
        line = line.strip()
        if not line:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            formatted_lines.append('<br>')
            continue
            
        # Check if line starts with a dash or bullet
        if line.startswith('- ') or line.startswith('• '):
            if not in_list:
                formatted_lines.append('<ul>')
                in_list = True
            formatted_lines.append(f'<li>{line[2:].strip()}</li>')
        else:
            if in_list:
                formatted_lines.append('</ul>')
                in_list = False
            
            # Handle colon-separated items (like "Tender Number: ABC123")
            if ':' in line and not line.startswith('<h4>'):
                parts = line.split(':', 1)
                if len(parts) == 2:
                    key = parts[0].strip()
                    value = parts[1].strip()
                    if value and value != "Not mentioned" and value != "Not found":
                        formatted_lines.append(f'<p><strong>{key}:</strong> {value}</p>')
                    else:
                        formatted_lines.append(f'<p><strong>{key}:</strong> <em>Not specified</em></p>')
                else:
                    formatted_lines.append(f'<p>{line}</p>')
            else:
                formatted_lines.append(f'<p>{line}</p>')
    
    if in_list:
        formatted_lines.append('</ul>')
    
    return ''.join(formatted_lines)

def format_answer_for_display(answer_text):
    """Format the answer text for better display."""
    if not answer_text or answer_text.startswith("Error"):
        return answer_text
    
    # Clean up the text
    formatted = answer_text.strip()
    
    # Split into paragraphs
    paragraphs = [p.strip() for p in formatted.split('\n') if p.strip()]
    
    # Join paragraphs with proper spacing
    return '<br><br>'.join(paragraphs)

def clean_text(text):
    """Clean and normalize text."""
    if not text:
        return ""
    
    # Remove non-ASCII characters but keep basic punctuation
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    # Remove control characters except newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text.strip()

def ask_llm(question, context, max_retries=3):
    """Ask LLM with proper error handling and retries."""
    if not GROQ_API_KEY:
        return "Error: GROQ_API_KEY not found in environment variables."
    
    if not context or not context.strip():
        return "Error: No context provided for analysis."
    
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {
            "role": "system", 
            "content": "You are an expert document analyst specializing in bid and tender documents. Provide clear, accurate, and structured responses based on the document content. If information is not found, clearly state that."
        },
        {
            "role": "user", 
            "content": f"Document Content:\n{context}\n\nQuestion: {question}\n\nPlease provide a detailed and structured response based on the document content."
        }
    ]

    data = {
        "model": "llama3-8b-8192",
        "messages": messages,
        "temperature": 0.3,
        "max_tokens": 1000
    }

    last_error = None
    
    for attempt in range(max_retries):
        try:
            response = requests.post(GROQ_API_URL, headers=headers, json=data, timeout=30)
            response.raise_for_status()
            
            response_data = response.json()
            
            if 'choices' in response_data and len(response_data['choices']) > 0:
                return response_data["choices"][0]["message"]["content"]
            else:
                return "Error: Invalid response format from API."
                
        except requests.exceptions.HTTPError as e:
            last_error = f"HTTP Error {response.status_code}: {str(e)}"
            if response.status_code == 429:  # Rate limit
                wait_time = min(2 ** attempt, 10)  # Exponential backoff, max 10 seconds
                time.sleep(wait_time)
                continue
            elif response.status_code == 401:
                return "Error: Invalid API key. Please check your GROQ_API_KEY."
            elif response.status_code == 403:
                return "Error: API access forbidden. Please check your API permissions."
            else:
                time.sleep(1)
                continue
                
        except requests.exceptions.RequestException as e:
            last_error = f"Request Error: {str(e)}"
            time.sleep(1)
            continue
            
        except json.JSONDecodeError as e:
            last_error = f"JSON Decode Error: {str(e)}"
            time.sleep(1)
            continue
            
        except Exception as e:
            last_error = f"Unexpected Error: {str(e)}"
            time.sleep(1)
            continue

    return f"Error after {max_retries} attempts: {last_error}"

def generate_comprehensive_summary(text_chunks):
    """Generate a comprehensive summary from multiple text chunks."""
    if not text_chunks:
        return "No content available for summarization."
    
    summary_prompt = """
    Analyze this bid/tender document and extract the following key information. If any information is not found, clearly state "Not mentioned" or "Not found":

    **BASIC INFORMATION:**
    - Tender Number/Reference:
    - Name of Work/Project:
    - Issuing Department/Organization:

    **FINANCIAL DETAILS:**
    - Estimated Contract Value:
    - EMD (Earnest Money Deposit):
    - EMD Exemption (if any):
    - Performance Security:

    **TIMELINE:**
    - Bid Submission Deadline:
    - Technical Bid Opening:
    - Contract Duration:

    **REQUIREMENTS:**
    - Key Eligibility Criteria:
    - Required Documents:
    - Technical Specifications (brief):
    - Payment Terms:


    Provide only the information that is clearly mentioned in the document.
    """
    
    all_summaries = []
    
    with st.spinner("Analyzing document sections..."):
        progress_bar = st.progress(0)
        
        for i, chunk in enumerate(text_chunks):
            try:
                summary = ask_llm(summary_prompt, chunk)
                if not summary.startswith("Error"):
                    all_summaries.append(summary)
                
                progress_bar.progress((i + 1) / len(text_chunks))
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                st.warning(f"Error processing chunk {i+1}: {str(e)}")
                continue
    
    if not all_summaries:
        return "Unable to generate summary due to processing errors."
    
    # Combine and deduplicate information
    final_summary_prompt = f"""
    Based on the following analysis sections from the same document, create a single comprehensive summary by combining and deduplicating the information:

    {chr(10).join([f"Section {i+1}:\n{summary}\n" for i, summary in enumerate(all_summaries)])}

    Provide a final consolidated summary with the same structure, keeping only the most complete and accurate information for each field.
    """
    
    try:
        final_summary = ask_llm(final_summary_prompt, "")
        return final_summary if not final_summary.startswith("Error") else all_summaries[0]
    except:
        return all_summaries[0] if all_summaries else "Summary generation failed."

def answer_question_from_chunks(question, text_chunks):
    """Answer a question by analyzing multiple text chunks."""
    if not text_chunks:
        return "No document content available to answer the question."
    
    relevant_answers = []
    
    with st.spinner("Searching through document..."):
        progress_bar = st.progress(0)
        
        for i, chunk in enumerate(text_chunks):
            try:
                answer = ask_llm(question, chunk)
                
                # Check if the answer contains relevant information
                if (not answer.startswith("Error") and 
                    "not found" not in answer.lower() and 
                    "not mentioned" not in answer.lower() and 
                    len(answer.strip()) > 20):
                    relevant_answers.append(answer)
                
                progress_bar.progress((i + 1) / len(text_chunks))
                time.sleep(1.2)  # Rate limiting
                
            except Exception as e:
                st.warning(f"Error processing chunk {i+1}: {str(e)}")
                continue
    
    if not relevant_answers:
        return "No relevant information found in the document to answer your question."
    
    if len(relevant_answers) == 1:
        return relevant_answers[0]
    
    # Combine multiple relevant answers
    combined_prompt = f"""
    Question: {question}
    
    Multiple relevant sections found:
    {chr(10).join([f"Section {i+1}: {answer}" for i, answer in enumerate(relevant_answers)])}
    
    Provide a comprehensive answer by combining the relevant information from all sections, removing duplicates and contradictions.
    """
    
    try:
        final_answer = ask_llm(combined_prompt, "")
        return final_answer if not final_answer.startswith("Error") else relevant_answers[0]
    except:
        return relevant_answers[0]

def main():
    # Initialize session state
    if 'qa_history' not in st.session_state:
        st.session_state.qa_history = []
    
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
            keys_to_clear = ["summary", "cleaned_text", "text_chunks", "user_question", 
                           "answer", "last_uploaded_file", "qa_history"]
            for key in keys_to_clear:
                st.session_state.pop(key, None)
            st.rerun()
            
        # Sample questions
        st.subheader("💡 Sample Questions")
        sample_questions = [
            "What is the tender deadline?",
            "What are the eligibility criteria?",
            "What is the contract value?",
            "What documents are required?",
            "What are the payment terms?",
            "Who is the contact person?",
            "What is the EMD amount?",
            "Where is the work location?"
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
        keys_to_clear = ["summary", "cleaned_text", "text_chunks", "user_question", "answer"]
        for key in keys_to_clear:
            st.session_state.pop(key, None)

    # File upload section
    if not uploaded_file:
        st.markdown("""
        <div class="upload-section">
            <h2>📤 Upload Your Bid Document</h2>
            <p>Drag and drop a PDF or TXT file to get started with the analysis</p>
            <p><em>Supported formats: PDF, TXT • Max size: 200MB</em></p>
        </div>
        """, unsafe_allow_html=True)
        
        # Benefits section
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            ### 🎯 Key Information Extraction
            - Tender Number & Details
            - Contract Value & EMD
            - Deadlines & Timeline
            - Eligibility Criteria
            """)
        
        with col2:
            st.markdown("""
            ### 🤖 AI-Powered Analysis
            - Intelligent Q&A System
            - Document Summarization
            - Key Insights Extraction
            - Multi-chunk Processing
            """)
        
        with col3:
            st.markdown("""
            ### 📊 Advanced Features
            - Error Handling & Retries
            - Rate Limit Management
            - Progress Tracking
            - Export Capabilities
            """)

    # Process the uploaded file
    if uploaded_file and "cleaned_text" not in st.session_state:
        with st.spinner("🔄 Processing document..."):
            progress_bar = st.progress(0)
            
            try:
                # Extract text
                progress_bar.progress(20)
                if uploaded_file.type == "application/pdf":
                    raw_text = extract_text_from_pdf(uploaded_file)
                    if raw_text is None:
                        st.stop()
                else:
                    try:
                        raw_text = uploaded_file.getvalue().decode("utf-8")
                    except UnicodeDecodeError:
                        try:
                            raw_text = uploaded_file.getvalue().decode("latin-1")
                        except:
                            st.error("Unable to decode the text file. Please check the file encoding.")
                            st.stop()
                
                # Clean text
                progress_bar.progress(40)
                cleaned_text = clean_text(raw_text)
                
                if not cleaned_text or len(cleaned_text.strip()) < 100:
                    st.error("Document appears to be empty or too short for analysis.")
                    st.stop()
                
                st.session_state.cleaned_text = cleaned_text
                
                # Split into chunks
                progress_bar.progress(60)
                text_chunks = split_text_into_chunks(cleaned_text)
                st.session_state.text_chunks = text_chunks
                
                if not text_chunks:
                    st.error("Unable to process document into analyzable chunks.")
                    st.stop()
                
                # Generate summary
                progress_bar.progress(80)
                summary = generate_comprehensive_summary(text_chunks)
                st.session_state.summary = summary
                
                progress_bar.progress(100)
                
            except Exception as e:
                st.error(f"Error processing document: {str(e)}")
                st.stop()
                
        st.success("✅ Document processed successfully!")

    # Display results
    if "cleaned_text" in st.session_state:
        # Summary section
        st.subheader("📋 Document Analysis Summary")
        
        if st.session_state.summary.startswith("Error"):
            st.markdown(f"""
            <div class="error-card">
                <h4>⚠️ Summary Generation Error:</h4>
                <p>{st.session_state.summary}</p>
            </div>
            """, unsafe_allow_html=True)
        else:
            formatted_summary = format_summary_for_display(st.session_state.summary)
            st.markdown(f"""
            <div class="summary-card">
                {formatted_summary}
            </div>
            """, unsafe_allow_html=True)
        
        # Export options
        if st.button("📥 Download Summary", use_container_width=True):
            st.download_button(
                label="💾 Download as Text File",
                data=st.session_state.summary,
                file_name=f"bid_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        
        # Q&A Section
        st.subheader("🔍 Ask Questions About the Document")
        
        # Create columns for better layout
        col1, col2 = st.columns([4, 1])
        
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
            
            if user_question.strip():
                answer = answer_question_from_chunks(user_question, st.session_state.get("text_chunks", []))
                
                # Add to history
                st.session_state.qa_history.append((user_question, answer))
                
                # Display Q&A
                st.markdown(f"""
                <div class="question-card">
                    <h4>Your Question:</h4>
                    <p>{user_question}</p>
                </div>
                """, unsafe_allow_html=True)
                
                if answer.startswith("Error"):
                    st.markdown(f"""
                    <div class="error-card">
                        <h4>⚠️ Error:</h4>
                        <p>{answer}</p>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    formatted_answer = format_answer_for_display(answer)
                    st.markdown(f"""
                    <div class="answer-card">
                        <h4>💡 Answer:</h4>
                        <p>{formatted_answer}</p>
                    </div>
                    """, unsafe_allow_html=True)

        # Previous Q&A history
        if st.session_state.qa_history:
            with st.expander(f"📚 Q&A History ({len(st.session_state.qa_history)} questions)"):
                for i, (q, a) in enumerate(reversed(st.session_state.qa_history[-10:])):  # Show last 10
                    st.markdown(f"**Q{len(st.session_state.qa_history)-i}:** {q}")
                    if a.startswith("Error"):
                        st.error(f"**A:** {a}")
                    else:
                        st.markdown(f"**A:** {a}")
                    st.markdown("---")

    # Footer
    st.markdown("---")
    st.markdown("""
    <div style="text-align: center; padding: 2rem; color: #666;">
        <p>🚀 Bid Analyser Pro v2.0 - Enhanced with Better Error Handling</p>
        <p><em>Intelligent Document Processing • Advanced Q&A System • Export Ready</em></p>
    </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()
