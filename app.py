import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import PyPDF2
import io
import json
import re
from datetime import datetime

# Configure the page
st.set_page_config(
    page_title="T&C Privacy Analyzer",
    page_icon="🔒",
    layout="wide"
)

# Initialize session state
if "gemini_api_key" not in st.session_state:
    st.session_state.gemini_api_key = ""

def setup_gemini(api_key):
    """Configure Gemini AI"""
    try:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    except Exception as e:
        st.error(f"Error setting up Gemini: {str(e)}")
        return None

def extract_text_from_pdf(pdf_file):
    """Extract text from uploaded PDF file"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {str(e)}")
        return ""

def analyze_terms_conditions(model, tc_text):
    """Analyze T&C using Gemini AI"""
    prompt = f"""
    Analyze the following Terms and Conditions document and provide a structured analysis:

    TERMS AND CONDITIONS:
    {tc_text}

    Please provide your analysis in the following JSON format:
    {{
        "summary": "A concise 2-3 sentence summary of the main points",
        "permissions": [
            {{"permission": "specific permission", "description": "what this allows"}},
        ],
        "privacy_risks": {{
            "high_risk": ["list of high risk privacy concerns"],
            "medium_risk": ["list of medium risk privacy concerns"], 
            "low_risk": ["list of low risk privacy concerns"]
        }},
        "data_access": [
            "list of what data/files the software can access"
        ],
        "sharing_practices": [
            "what data is shared with third parties"
        ],
        "key_concerns": [
            "top 3-5 most important things users should know"
        ]
    }}
    
    Focus on privacy implications, data collection, file access permissions, and any concerning clauses.
    """
    
    try:
        response = model.generate_content(prompt)
        # Try to extract JSON from response
        text_response = response.text
        json_match = re.search(r'\{.*\}', text_response, re.DOTALL)
        if json_match:
            return json.loads(json_match.group())
        else:
            # If no JSON found, return structured text response
            return {"error": "Could not parse structured response", "raw_response": text_response}
    except Exception as e:
        return {"error": f"Analysis failed: {str(e)}"}

def search_security_news(software_name):
    """Search for security news about the software"""
    search_queries = [
        f"{software_name} security breach 2024",
        f"{software_name} vulnerability data breach",
        f"{software_name} privacy concerns security"
    ]
    
    results = []
    for query in search_queries[:2]:  # Limit to 2 queries to avoid rate limits
        try:
            # Using DuckDuckGo Instant Answer API (free)
            url = f"https://api.duckduckgo.com/?q={query}&format=json&no_html=1&skip_disambig=1"
            response = requests.get(url, timeout=5)
            if response.status_code == 200:
                data = response.json()
                if data.get('Abstract'):
                    results.append({
                        'query': query,
                        'result': data['Abstract'],
                        'source': data.get('AbstractURL', 'DuckDuckGo')
                    })
        except Exception:
            continue
    
    return results

def display_risk_badge(risk_level):
    """Display colored risk level badges"""
    colors = {
        "high_risk": "🔴",
        "medium_risk": "🟡", 
        "low_risk": "🟢"
    }
    return colors.get(risk_level, "⚪")

def main():
    st.title("🔒 Terms & Conditions Privacy Analyzer")
    st.markdown("**Protect your privacy by understanding what you're agreeing to!**")
    st.markdown("---")
    
    # Sidebar for API configuration
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        gemini_api_key = st.text_input(
            "Gemini API Key",
            type="password",
            value=st.session_state.gemini_api_key,
            help="Get your free API key from https://makersuite.google.com/app/apikey"
        )
        st.session_state.gemini_api_key = gemini_api_key
        
        if not gemini_api_key:
            st.warning("⚠️ Please enter your Gemini API key to use the analyzer")
            st.markdown("[Get your free Gemini API key here](https://makersuite.google.com/app/apikey)")
        
        st.markdown("---")
        st.markdown("### About")
        st.markdown("This app helps you understand privacy implications of software Terms & Conditions using AI analysis.")
    
    # Main interface
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.header("📄 Upload Terms & Conditions")
        
        # Input options
        input_method = st.radio("Choose input method:", ["📋 Copy & Paste", "📁 Upload File"])
        
        tc_text = ""
        
        if input_method == "📋 Copy & Paste":
            tc_text = st.text_area(
                "Paste Terms & Conditions text here:",
                height=300,
                placeholder="Copy and paste the Terms & Conditions text here..."
            )
        
        else:  # File upload
            uploaded_file = st.file_uploader(
                "Choose a file",
                type=['pdf', 'txt'],
                help="Upload PDF or TXT file containing Terms & Conditions"
            )
            
            if uploaded_file:
                if uploaded_file.type == "application/pdf":
                    tc_text = extract_text_from_pdf(uploaded_file)
                else:
                    tc_text = str(uploaded_file.read(), "utf-8")
                
                if tc_text:
                    st.success(f"✅ File uploaded successfully! ({len(tc_text)} characters)")
    
    with col2:
        st.header("🔍 Security Check")
        st.markdown("**Optional: Check for security breaches**")
        
        software_name = st.text_input(
            "Software Name",
            placeholder="e.g., Adobe Reader, Chrome, etc.",
            help="Enter software name to check for recent security issues"
        )
        
        check_security = st.button("🔍 Check Security News", disabled=not software_name)
    
    # Analysis section
    if tc_text and gemini_api_key:
        st.markdown("---")
        
        if st.button("🔍 Analyze Terms & Conditions", type="primary"):
            with st.spinner("🤖 Analyzing Terms & Conditions..."):
                model = setup_gemini(gemini_api_key)
                if model:
                    analysis = analyze_terms_conditions(model, tc_text)
                    
                    if "error" in analysis:
                        st.error(f"Analysis Error: {analysis['error']}")
                        if "raw_response" in analysis:
                            st.text(analysis["raw_response"])
                    else:
                        # Display results
                        st.success("✅ Analysis Complete!")
                        
                        # Summary
                        st.header("📋 Summary")
                        st.write(analysis.get("summary", "No summary available"))
                        
                        # Permissions
                        st.header("🔑 Permissions Requested")
                        permissions = analysis.get("permissions", [])
                        if permissions:
                            for perm in permissions:
                                st.write(f"• **{perm.get('permission', 'Unknown')}**: {perm.get('description', 'No description')}")
                        else:
                            st.write("No specific permissions identified")
                        
                        # Privacy Risks
                        st.header("⚠️ Privacy Risk Assessment")
                        risks = analysis.get("privacy_risks", {})
                        
                        for risk_level, items in risks.items():
                            if items:
                                st.subheader(f"{display_risk_badge(risk_level)} {risk_level.replace('_', ' ').title()}")
                                for item in items:
                                    st.write(f"• {item}")
                        
                        # Data Access
                        st.header("📁 Data Access")
                        data_access = analysis.get("data_access", [])
                        if data_access:
                            for access in data_access:
                                st.warning(f"⚠️ {access}")
                        else:
                            st.info("No specific data access permissions identified")
                        
                        # Sharing Practices
                        st.header("🔄 Data Sharing")
                        sharing = analysis.get("sharing_practices", [])
                        if sharing:
                            for practice in sharing:
                                st.write(f"• {practice}")
                        else:
                            st.info("No data sharing practices identified")
                        
                        # Key Concerns
                        st.header("🚨 Key Concerns")
                        concerns = analysis.get("key_concerns", [])
                        if concerns:
                            for concern in concerns:
                                st.error(f"🚨 {concern}")
                        else:
                            st.success("No major concerns identified")
    
    # Security news section
    if check_security and software_name:
        st.markdown("---")
        st.header(f"🔍 Security News for {software_name}")
        
        with st.spinner("Searching for security information..."):
            security_results = search_security_news(software_name)
            
            if security_results:
                for result in security_results:
                    st.subheader(f"Search: {result['query']}")
                    st.write(result['result'])
                    if result['source']:
                        st.caption(f"Source: {result['source']}")
                    st.markdown("---")
            else:
                st.info("No specific security information found. This doesn't necessarily mean the software is safe - always verify from official sources.")
    
    # Footer
    st.markdown("---")
    st.markdown("**Disclaimer**: This tool provides AI-generated analysis for informational purposes. Always review official documentation and consult security experts for critical decisions.")

if __name__ == "__main__":
    main()