import os
import io
import logging
import random
import base64
import smtplib
import re
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass
from email.message import EmailMessage

import pandas as pd
import streamlit as st
import extract_msg  # pip install extract-msg

# ---------- Configuration & Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read secrets from environment
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# SIMO Logo
LOGO_URL = os.path.join("utilities", "title.png")
S_LOGO_URL = os.path.join("utilities", "logo.png")

# Helper to convert local image to data URI so browser can render it
def get_image_data_uri(path: str) -> str:
    """
    Read image from server filesystem and return a data URI string.
    Returns empty string if file not found or cannot be read.
    """
    try:
        # Resolve relative path relative to this file if possible
        base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        full_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if not os.path.exists(full_path):
            full_path = path
            if not os.path.exists(full_path):
                logger.warning("Logo file not found at %s", path)
                return ""
        with open(full_path, "rb") as f:
            data = f.read()
        mime = "image/png"
        ext = os.path.splitext(full_path)[1].lower()
        if ext in [".jpg", ".jpeg"]:
            mime = "image/jpeg"
        elif ext == ".svg":
            mime = "image/svg+xml"
        elif ext == ".gif":
            mime = "image/gif"
        b64 = base64.b64encode(data).decode("utf-8")
        return f"data:{mime};base64,{b64}"
    except Exception as e:
        logger.exception("Failed to load logo image: %s", e)
        return ""

# Convert logo to data URI once at startup
LOGO_DATA_URI = get_image_data_uri(LOGO_URL)

# ---------- Data structures ----------
@dataclass
class Attachment:
    filename: str
    content_bytes: bytes
    mime_type: str = "application/octet-stream"

@dataclass
class GeneratedEmail:
    sender: str
    to: List[str]
    cc: List[str]
    subject: str
    body: str
    attachments: List[Attachment]

# ---------- Helper functions ----------

def clean_header_text(text: str) -> str:
    """
    Removes null bytes (\x00) and other artifacts that appear as 
    crosses/boxes at the end of extracted MSG strings.
    """
    if not text:
        return ""
    # Remove null bytes and specific object replacement markers
    clean = text.replace('\x00', '').replace('\ufffd', '')
    return clean.strip()

def clean_email_string(raw_str: str) -> List[str]:
    """
    Parses strings like 'John Doe <john@example.com>; Jane <jane@example.com>'
    and returns a clean list: ['john@example.com', 'jane@example.com'].
    Also handles cleanup of artifacts.
    """
    if not raw_str:
        return []
    
    # Pre-clean the raw string
    raw_str = clean_header_text(raw_str)
    
    # 1. Replace semicolons with commas for easier splitting
    raw_str = raw_str.replace(";", ",")
    
    # 2. Split by comma
    parts = [p.strip() for p in raw_str.split(",") if p.strip()]
    
    cleaned_emails = []
    for part in parts:
        # Regex to find email inside <...> 
        match = re.search(r'<([^<>]+)>', part)
        if match:
            cleaned_emails.append(match.group(1).strip())
        else:
            # If no brackets, check if it looks like an email (has @)
            if "@" in part:
                cleaned_emails.append(part.strip())
            # We ignore parts that don't look like emails to avoid junk
    
    return cleaned_emails

def sanitize_filename(fname: str) -> str:
    """Removes null bytes and replacement characters often found in OLE filenames."""
    if not fname:
        return "untitled_attachment"
    # Remove null bytes (\x00) and replacement character ( / \ufffd)
    clean = fname.replace('\x00', '').replace('\ufffd', '').strip()
    return clean

def strip_html_tags(html_content: str) -> str:
    """
    Removes HTML tags to produce plain text.
    Specifically removes <style> and <script> blocks to prevent CSS code from leaking.
    """
    if not html_content:
        return ""
    
    # 1. Remove <style>...</style> and <script>...</script> blocks entirely
    # The flags=re.DOTALL ensures . matches newlines, preventing the P {margin...} leak
    clean = re.sub(r'<(style|script)[^>]*>.*?</\1>', '', html_content, flags=re.DOTALL | re.IGNORECASE)
    
    # 2. Remove remaining HTML tags
    clean = re.sub(r'<[^>]+>', '', clean)
    
    # 3. Decode HTML entities (e.g., &nbsp;)
    clean = clean.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    
    # 4. Collapse multiple spaces/newlines
    clean = re.sub(r'\n\s*\n', '\n\n', clean) 
    
    return clean.strip()

def validate_email_list(raw_list: List[str]) -> List[str]:
    """Ensures the list contains valid looking strings."""
    return [e for e in raw_list if "@" in e]

def parse_msg_file(uploaded_file) -> GeneratedEmail:
    """
    Parses a .msg file using extract_msg and returns a GeneratedEmail object.
    Handles cleanup of To/CC fields, Body extraction, and filename sanitation.
    """
    try:
        # Use openMsg (camelCase)
        msg = extract_msg.openMsg(uploaded_file)
        
        # 1. Extract & Clean Headers
        raw_to = msg.to if msg.to else ""
        raw_cc = msg.cc if msg.cc else ""
        raw_subject = msg.subject if msg.subject else ""
        
        # Apply strict cleaning to headers to remove crosses/null bytes
        subject = clean_header_text(raw_subject)
        
        # Parse lists (cleaning happens inside clean_email_string)
        clean_to = clean_email_string(raw_to)
        clean_cc = clean_email_string(raw_cc)
        
        # 2. Extract Body (Priority: Plain Text -> HTML -> Empty)
        body = ""
        
        # Note: extract-msg sometimes populates .body with the plain text version of the HTML.
        # If .htmlBody exists, we prefer parsing that to strip CSS properly.
        if msg.htmlBody:
            try:
                # Decoding might be needed depending on how extract-msg returns it
                html_content = msg.htmlBody
                if isinstance(html_content, bytes):
                    html_content = html_content.decode('utf-8', errors='ignore')
                body = strip_html_tags(html_content)
            except Exception as e:
                logger.warning(f"Failed to parse HTML body: {e}")
                # Fallback to plain body
                body = clean_header_text(msg.body) if msg.body else "Error parsing body."
        elif msg.body:
            body = clean_header_text(msg.body)

        # 3. Extract & Sanitize Attachments
        attachments_list = []
        for att in msg.attachments:
            if hasattr(att, 'data'):
                # Get filename and sanitize it
                raw_fname = att.longFilename if att.longFilename else (att.shortFilename if att.shortFilename else "attachment")
                fname = sanitize_filename(raw_fname)
                
                content = att.data
                
                # MIME detection
                ext = os.path.splitext(fname)[1].lower()
                mime = "application/octet-stream"
                if ext == ".xlsx": mime = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                elif ext == ".xls": mime = "application/vnd.ms-excel"
                elif ext == ".pdf": mime = "application/pdf"
                elif ext == ".csv": mime = "text/csv"
                elif ext in [".png", ".jpg", ".jpeg"]: mime = f"image/{ext[1:]}"
                
                attachments_list.append(Attachment(filename=fname, content_bytes=content, mime_type=mime))

        msg.close()
        
        return GeneratedEmail(
            sender=SENDER_EMAIL or "user@example.com",
            to=clean_to,
            cc=clean_cc,
            subject=subject,
            body=body,
            attachments=attachments_list
        )
    except Exception as e:
        logger.error(f"Error parsing MSG file: {e}")
        raise e

def send_email_via_smtp(email_obj: GeneratedEmail, override_body: str = None) -> Tuple[bool, str]:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        return True, f"Simulated sent to {', '.join(email_obj.to)} (SMTP Not Configured)"

    msg = EmailMessage()
    msg["From"] = email_obj.sender
    msg["To"] = ", ".join(email_obj.to)
    if email_obj.cc:
        msg["Cc"] = ", ".join(email_obj.cc)
    msg["Subject"] = email_obj.subject
    body = override_body if override_body is not None else email_obj.body
    msg.set_content(body)

    for att in email_obj.attachments:
        if "/" in att.mime_type:
            maintype, subtype = att.mime_type.split("/", 1)
        else:
            maintype, subtype = ("application", "octet-stream")
        msg.add_attachment(att.content_bytes, maintype=maintype, subtype=subtype, filename=att.filename)

    recipients = email_obj.to + email_obj.cc
    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg, from_addr=email_obj.sender, to_addrs=recipients)
        return True, f"Email sent to {', '.join(recipients)}"
    except Exception as e:
        logger.exception("Failed to send email")
        return False, f"Failed to send email: {e}"

# ---------- Branding & Styling ----------
def inject_custom_css():
    st.markdown("""
    <style>
        /* Import Montserrat Font */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');

        /* --- GLOBAL VARIABLES & RESET --- */
        :root {
            --primary-orange: #FF5F00;
            --primary-orange-hover: #E04F00;
            --text-dark: #1C1C1E;
            --text-gray: #555555;
            --bg-light: #fdf9f7;
            --card-white: #FFFFFF;
            --border-color: #E5E7EB;
        }

        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif;
            color: var(--text-dark);
        }
        
        header[data-testid="stHeader"] { 
            background-color: transparent !important; 
        }
        header[data-testid="stHeader"] > div[data-testid="stDecoration"] {
            display: none;
        }
        footer { display: none; }
        div[data-testid="InputInstructions"] { display: none !important; }

        div[data-testid="stAppViewContainer"] {
            background-color: var(--bg-light);
        }

        div[data-testid="block-container"] {
            background-color: var(--card-white);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08);
            border: 1px solid var(--border-color);
            padding: 3rem !important;
            max-width: 750px;
            margin-top: 2rem;
        }

        div[data-baseweb="input"] {
            background-color: #F3F4F6 !important;
            border: 1px solid transparent;
            border-radius: 50px !important;
            padding: 8px 16px;
            transition: all 0.2s ease;
        }
        div[data-baseweb="input"]:focus-within {
            background-color: #FFFFFF !important;
            border-color: var(--primary-orange) !important;
            box-shadow: 0 0 0 3px rgba(255, 95, 0, 0.15) !important;
        }
        input {
            font-weight: 500;
            color: var(--text-dark);
        }
        div[data-baseweb="text-area"] {
             background-color: #F3F4F6 !important;
             border-radius: 20px !important;
        }

        button[kind="primary"] {
            background-color: var(--primary-orange) !important;
            color: white !important;
            border: none;
            border-radius: 50px;
            padding: 12px 24px;
            font-weight: 700;
            font-size: 16px;
            letter-spacing: 0.5px;
            text-transform: uppercase;
            width: 100%;
            transition: all 0.3s ease;
            box-shadow: 0 4px 12px rgba(255, 95, 0, 0.25);
            margin-top: 10px;
        }
        button[kind="primary"]:hover {
            background-color: var(--primary-orange-hover) !important;
            box-shadow: 0 6px 16px rgba(255, 95, 0, 0.35);
            transform: translateY(-2px);
        }
        
        button[kind="secondary"] {
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-gray);
            border-radius: 8px;
            transition: color 0.2s;
        }
        button[kind="secondary"]:hover {
            color: var(--primary-orange);
            background: #FFF5F0;
            border-color: #FED7AA;
        }

        [data-testid="stSidebar"] {
            background-color: #555759;
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] * {
            color: #FFFFFF;
        }
        [data-testid="stSidebar"] h3 {
            font-weight: 700;
            color: var(--primary-orange) !important;
        }
        
        h1, h2, h3 {
            font-weight: 800 !important;
            letter-spacing: -0.5px;
        }
        
        [data-testid="stSidebarCollapsedControl"] {
            display: block !important;
            z-index: 1000000 !important;
            background-color: transparent !important;
        }
        [data-testid="stSidebarCollapsedControl"] svg, 
        [data-testid="stSidebarCollapsedControl"] i {
            color: #1C1C1E !important;
            fill: #1C1C1E !important;
            stroke: #1C1C1E !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"] {
             color: #FFFFFF !important;
        }
        [data-testid="stSidebar"] button[kind="secondary"] svg {
             fill: #FFFFFF !important;
        }

        .login-header {
            font-size: 28px;
            font-weight: 800;
            color: #334355;
            text-align: center;
            margin-bottom: 25px;
            letter-spacing: -0.5px;
        }
        .forgot-pass {
            text-align: right;
            margin-top: 8px;
            color: var(--primary-orange);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
            text-decoration: none;
            transition: color 0.2s;
        }
        .forgot-pass:hover {
            text-decoration: underline;
        }
        .signup-text {
            text-align: center;
            margin-top: 25px;
            font-size: 14px;
            color: var(--text-gray);
            font-weight: 500;
        }
        div[data-baseweb="checkbox"] span {
            font-size: 13px;
            font-weight: 500;
        }
        [data-testid="stFileUploader"] {
            padding: 1rem;
            border: 1px dashed var(--border-color);
            border-radius: 12px;
            background-color: #F9FAFB;
        }
    </style>
    """, unsafe_allow_html=True)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="SIMO", layout="centered", page_icon=f"{S_LOGO_URL}", initial_sidebar_state="expanded")

inject_custom_css()

# Session state initialization
if "page" not in st.session_state:
    st.session_state.page = "login"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = "Guest"
if "generated_email" not in st.session_state:
    st.session_state.generated_email = None
for k in ["editable_body", "editable_subject", "editable_to", "editable_cc", "attachments"]:
    if k not in st.session_state:
        st.session_state[k] = None
if "attachments" not in st.session_state:
    st.session_state.attachments = []
if "preview_file_idx" not in st.session_state:
    st.session_state.preview_file_idx = None 
if "msg_processed" not in st.session_state:
    st.session_state.msg_processed = False

def go_to(page: str):
    st.session_state.page = page

# ---------- Page 1: Login ----------
def page_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_center, col_r = st.columns([1, 2.5, 1])
    
    with col_center:
        if LOGO_DATA_URI:
            st.markdown(f"<div style='display:flex; justify-content:center; margin-bottom:15px;'><img src='{LOGO_DATA_URI}' style='height:45px; object-fit: contain;'></div>", unsafe_allow_html=True)

        st.markdown('<div class="login-header">Log in to SIMO</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username_input = st.text_input("Email", placeholder="UserID", label_visibility="collapsed")
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            
            password_input = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
            
            c1, c2 = st.columns([1, 1])
            with c1:
                st.checkbox("Remember me")
            with c2:
                st.markdown('<div class="forgot-pass">Forgot Password?</div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            b1, b2, b3 = st.columns([1.3, 1, 1])
            with b2:
                submitted = st.form_submit_button("Log in", type="primary")
                
        if submitted:
            DUMMY_USER = "Ayush"
            DUMMY_PASS = "demo123"
            if (username_input == DUMMY_USER or "demo" in username_input) and (password_input == DUMMY_PASS or password_input == "demo"):
                st.session_state.authenticated = True
                st.session_state.username = f"{DUMMY_USER}"
                go_to("dashboard")
                st.rerun()
            else:
                st.error("Invalid credentials.")
        
        st.markdown(
            '<div class="signup-text">New to SIMO? <a href="#" style="color:#FF5F00;font-weight:700;text-decoration:none;">Sign up</a></div>', 
            unsafe_allow_html=True
        )

# ---------- Page 2: Dashboard ----------
def page_dashboard():
    if not st.session_state.authenticated:
        go_to("login")
        st.rerun()
        return

    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        if "greeting" not in st.session_state or not st.session_state.greeting:
            greetings = ["Have a great day!", "Hope you're having a good one!", "Keep up the great work!", "Happy to see you again!", "Make today amazing!"]
            st.session_state.greeting = random.choice(greetings)
        
        st.markdown(f"### Hi, {st.session_state.username}")
        st.markdown(f"_{st.session_state.greeting}_")
        st.markdown("<br>" * 15, unsafe_allow_html=True)
        if st.button("Log Out", type="primary"):
            st.session_state.authenticated = False
            st.session_state.generated_email = None
            st.session_state.greeting = None
            st.session_state.msg_processed = False
            st.session_state.attachments = []
            go_to("login")
            st.rerun()

    # --- DASHBOARD CONTENT ---
    logo_img_tag = f'<img src="{LOGO_DATA_URI}" alt="SIMO Logo" style="height: 40px; object-fit: contain;">' if LOGO_DATA_URI else ''
    
    st.markdown(f"""
    <div style="display:flex; justify-content:flex-end; align-items:center; padding-bottom:15px; margin-bottom:20px; border-bottom:1px solid #E5E7EB;">
        {logo_img_tag}
    </div>
    """, unsafe_allow_html=True)
    
    # 2. File Upload Section
    st.markdown('<h3 style="margin:0; padding:0; font-size:18px; color:#334355;">Upload Client Request</h3>', unsafe_allow_html=True)
    st.markdown("<div style='color:#666; font-size:13px; margin-bottom:10px;'>Upload a .msg file to populate the response details.</div>", unsafe_allow_html=True)
    
    uploaded_msg = st.file_uploader("Upload .msg file", type=["msg"], label_visibility="collapsed")
    
    if uploaded_msg:
        try:
            with st.spinner("Parsing message file..."):
                generated = parse_msg_file(uploaded_msg)
                
                # Update session state
                st.session_state.generated_email = generated
                st.session_state.editable_body = generated.body
                st.session_state.editable_subject = generated.subject
                st.session_state.editable_to = ", ".join(generated.to)
                st.session_state.editable_cc = ", ".join(generated.cc)
                st.session_state.attachments = generated.attachments.copy()
                st.session_state.msg_processed = True
                
        except Exception as e:
            st.error(f"Failed to parse file: {e}")

    st.markdown("<br><hr style='margin: 20px 0; border-top: 1px solid #E5E7EB;'><br>", unsafe_allow_html=True)

    # 3. Response / Editable Section
    if st.session_state.msg_processed:
        col_h1, col_h2 = st.columns([4, 1])
        with col_h1:
            st.markdown('<h3 style="margin:0; padding:0; font-size:18px; color:#334355;">Response Details</h3>', unsafe_allow_html=True)
        with col_h2:
            is_editing = st.checkbox("Edit Response", value=False)
        
        st.markdown("<br>", unsafe_allow_html=True)

        col_meta1, col_meta2 = st.columns(2)
        with col_meta1:
            if is_editing:
                st.session_state.editable_to = st.text_input("To", value=st.session_state.editable_to)
            else:
                st.text_input("To", value=st.session_state.editable_to, disabled=True)
                
        with col_meta2:
            if is_editing:
                st.session_state.editable_cc = st.text_input("CC", value=st.session_state.editable_cc)
            else:
                st.text_input("CC", value=st.session_state.editable_cc, disabled=True)

        if is_editing:
            st.session_state.editable_subject = st.text_input("Subject", value=st.session_state.editable_subject)
        else:
            st.text_input("Subject", value=st.session_state.editable_subject, disabled=True)

        st.markdown("<br>", unsafe_allow_html=True)

        st.markdown("<strong style='color:#334355;'>Body</strong>", unsafe_allow_html=True)
        if is_editing:
            st.session_state.editable_body = st.text_area("Body", value=st.session_state.editable_body, height=500, label_visibility="collapsed")
        else:
            st.text_area("Body", value=st.session_state.editable_body, height=500, disabled=True, label_visibility="collapsed")
            
        st.markdown("<br><hr style='margin: 30px 0; border-top: 1px solid #E5E7EB;'><br>", unsafe_allow_html=True)

        # 4. Attachments Section
        st.markdown("<h3 style='margin:0; padding:0; font-size:18px; color:#334355;'>Attachments</h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        current_attachments = st.session_state.attachments
        to_remove = []
        
        if not current_attachments:
             st.markdown("<span style='color:#666;'>No attachments found in message.</span>", unsafe_allow_html=True)
        else:
            for idx, att in enumerate(current_attachments):
                c1, c2, c3, c4, c5 = st.columns([0.5, 5, 1, 1, 1])
                c1.markdown("📄") 
                c2.markdown(f"<span style='font-weight:600; color:#333;'>{att.filename}</span>", unsafe_allow_html=True)
                
                if c3.button("👁️", key=f"preview_{idx}", help="Preview"):
                    st.session_state.preview_file_idx = None if st.session_state.preview_file_idx == idx else idx

                c4.download_button(
                    label="📥",
                    data=att.content_bytes,
                    file_name=att.filename,
                    mime=att.mime_type,
                    key=f"dl_{idx}",
                    help="Download"
                )

                if c5.button("❌", key=f"del_{idx}", help="Remove"):
                    to_remove.append(idx)
                
                if st.session_state.preview_file_idx == idx:
                    st.markdown("<div style='background:#F9FAFB; padding:15px; margin-top:10px; border-radius:12px; border:1px solid #E5E7EB;'>", unsafe_allow_html=True)
                    try:
                        with io.BytesIO(att.content_bytes) as f:
                            if att.filename.endswith(('.xlsx', '.xls')):
                                df_preview = pd.read_excel(f)
                                st.dataframe(df_preview, use_container_width=True)
                            else:
                                st.info("Preview not available for this file type.")
                    except Exception as e:
                        st.error(f"Preview unavailable: {e}")
                    st.markdown("</div>", unsafe_allow_html=True)
                
                st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)
        
        if to_remove:
            st.session_state.attachments = [a for i, a in enumerate(current_attachments) if i not in to_remove]
            st.rerun()

        st.markdown("<div style='margin-top:20px; font-weight:600; font-size:14px;'>Add more files</div>", unsafe_allow_html=True)
        additional_files = st.file_uploader("Add files", accept_multiple_files=True, key="add_files_uploader", label_visibility="collapsed")
        if additional_files:
            for uf in additional_files:
                st.session_state.attachments.append(Attachment(filename=uf.name, content_bytes=uf.read()))
            st.rerun()

        st.markdown("<br><br>", unsafe_allow_html=True)

        col_submit_l, col_submit_action, col_submit_r = st.columns([1, 2, 1])
        with col_submit_action:
            if st.button("Submit", type="primary", use_container_width=True):
                # Clean up emails one last time before sending
                final_to = clean_email_string(st.session_state.editable_to)
                final_cc = clean_email_string(st.session_state.editable_cc)
                
                if not final_to:
                    st.error("Recipient required.")
                else:
                    email_to_send = GeneratedEmail(
                        sender=SENDER_EMAIL or "success@solis.co",
                        to=final_to,
                        cc=final_cc,
                        subject=st.session_state.editable_subject,
                        body=st.session_state.editable_body,
                        attachments=st.session_state.attachments.copy()
                    )
                    with st.spinner("Sending..."):
                        success, msg = send_email_via_smtp(email_to_send)
                    if success:
                        st.success("Sent!")
                        st.balloons()
                    else:
                        st.error(msg)
    else:
        st.info("Please upload a .msg file above to load the email content.")

    st.markdown("<br><br>", unsafe_allow_html=True)

if st.session_state.page == "login":
    page_login()
else:
    page_dashboard()