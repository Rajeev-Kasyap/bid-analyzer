import streamlit as st
import PyPDF2
import requests
import os
from dotenv import load_dotenv
load_dotenv()
import re

# Load environment variables
load_dotenv()
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"

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
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json"
    }

    messages = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on document content."},
        {"role": "user", "content": f"Document: {context}"},
        {"role": "user", "content": f"Question: {question}"}
    ]

    data = {
        "model": "deepseek-ai/deepseek-r1-0528-qwen3-8b",
        "messages": messages
    }

    try:
        response = requests.post(OPENROUTER_API_URL, headers=headers, json=data)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {e}"

def main():
    st.title("Bid Analyser")
    st.write("Upload a PDF or TXT file to extract key info and ask questions.")

    uploaded_file = st.file_uploader("Upload PDF or TXT", type=["pdf", "txt"])

    if uploaded_file:
        # Step 1: Read and clean document
        if uploaded_file.type == "application/pdf":
            raw_text = extract_text_from_pdf(uploaded_file)
        else:
            raw_text = uploaded_file.getvalue().decode("utf-8")

        cleaned_text = clean_text(raw_text)

        # Step 2: Summarize document
        with st.spinner("Summarizing document..."):
            summary_prompt = (
                "List the following from the document:\n"
                "1. Tender Number\n2. Name of Work\n3. Department Name\n"
                "4. Estimated Contract Value\n5. Contract Period\n6. EMD\n"
                "7. EMD Exemption (yes/no)\n8. Mode of Payment\n9. Eligibility Criteria\n\n"
                f"Document:\n{cleaned_text}"
            )
            summary = ask_llm(summary_prompt, cleaned_text)

        st.subheader("Extracted Summary")
        st.write(summary)

        # Step 3: Ask custom questions
        st.subheader("Ask Questions About the Document")
        user_question = st.text_input("Type your question here and press Enter")

        if user_question:
            with st.spinner("Getting answer..."):
                answer = ask_llm(user_question, cleaned_text)
                st.markdown("**Answer:**")
                st.write(answer)

if __name__ == "__main__":
    main()