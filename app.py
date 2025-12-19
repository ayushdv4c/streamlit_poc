"""
Streamlit two-page app:
- Page 1: collect user input and call Databricks pipeline (simulated)
- Page 2: preview generated email, optionally edit, and send with attachments

Best practices:
- Use environment variables / Streamlit secrets for credentials
- Validate inputs
- Keep attachments in memory (BytesIO)
- Use TLS for SMTP
- Clear logging and error handling
"""

import os
import io
import logging
import random
import base64
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

import pandas as pd
import streamlit as st
from email.message import EmailMessage
import smtplib

# ---------- Configuration & Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Read secrets from environment
SMTP_HOST = os.getenv("SMTP_HOST")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
SENDER_EMAIL = os.getenv("SENDER_EMAIL")

# Placeholder for SIMO Logo - Replace this URL or path with your actual image file
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
    mime_type: str = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

@dataclass
class GeneratedEmail:
    sender: str
    to: List[str]
    cc: List[str]
    subject: str
    body: str
    attachments: List[Attachment]

# ---------- Helper functions ----------
def validate_email_list(raw: str) -> List[str]:
    if not raw:
        return []
    return [e.strip() for e in raw.split(",") if e.strip()]

def create_sample_excel(name: str, rows: int = 5) -> bytes:
    df = pd.DataFrame({
        "Metric": [f"{name}_{i}" for i in range(rows)],
        "Value": [x * 12.5 for x in range(rows)],
        "Status": ["Active" if i % 2 == 0 else "Review" for i in range(rows)]
    })
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Sheet1")
    buffer.seek(0)
    return buffer.read()

def fetch_from_databricks(user_inputs: Dict[str, Any]) -> GeneratedEmail:
    """Simulated Databricks pipeline call."""
    recipient = user_inputs.get("recipient_email", "client@example.com")
    cc = user_inputs.get("cc_email", "")
    name = user_inputs.get("name", "Valued Partner")
    product = user_inputs.get("product", "Global Connectivity")

    subject = f"Monthly Performance Review: {product}"
    body = (
        f"Hello {name},\n\n"
        f"Please find attached the latest performance metrics for your {product} deployment.\n\n"
        f"Key Highlights:\n"
        f"• Uptime: 99.99%\n"
        f"• Data Usage: Increased by 15% WoW\n"
        f"• Active Devices: 142\n\n"
        f"The detailed breakdown is included in the attached spreadsheets. "
        f"Let us know if you have questions regarding the usage trends.\n\n"
        f"Best regards,\n"
        f"Solis Client Success Team\n"
    )

    attachments = [
        Attachment(filename="usage_summary.xlsx", content_bytes=create_sample_excel("usage", 8)),
        Attachment(filename="device_metrics.xlsx", content_bytes=create_sample_excel("metrics", 12)),
    ]

    generated = GeneratedEmail(
        sender=SENDER_EMAIL or "success@solis.co",
        to=[recipient],
        cc=validate_email_list(cc),
        subject=subject,
        body=body,
        attachments=attachments
    )
    return generated

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
        maintype, subtype = att.mime_type.split("/", 1) if "/" in att.mime_type else ("application", "octet-stream")
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
        /* Import Montserrat Font (matches SIMO/Solis typography) */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');

        /* --- GLOBAL VARIABLES & RESET --- */
        :root {
            --primary-orange: #FF5F00;
            --primary-orange-hover: #E04F00;
            --text-dark: #1C1C1E;
            --text-gray: #555555;
            --bg-light: #F9FAFB;
            --card-white: #FFFFFF;
            --border-color: #E5E7EB;
        }

        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif;
            color: var(--text-dark);
        }
        
        /* 1. HIDING STREAMLIT DEFAULT UI ELEMENTS */
        header[data-testid="stHeader"] { 
            background-color: transparent !important; 
        }
        header[data-testid="stHeader"] > div:first-child {
            display: none;
        }
        footer { display: none; }
        div[data-testid="InputInstructions"] { display: none !important; }

        /* 2. MAIN CARD STYLING */
        div[data-testid="stAppViewContainer"] {
            background-color: var(--bg-light);
        }

        /* The main Card */
        div[data-testid="block-container"] {
            background-color: var(--card-white);
            border-radius: 16px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.08); /* Soft, premium shadow */
            border: 1px solid var(--border-color);
            padding: 3rem !important;
            max-width: 750px;
            margin-top: 2rem;
        }

        /* 3. INPUT FIELDS */
        /* Rounded, clean inputs matching the website aesthetic */
        div[data-baseweb="input"] {
            background-color: #F3F4F6 !important; /* Slight gray bg for inputs */
            border: 1px solid transparent;
            border-radius: 50px !important; /* Pill shape inputs */
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

        /* 4. BUTTONS */
        /* Primary Action Buttons (Orange Pill) */
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
        
        /* Secondary / Icon Buttons (Ghost style) */
        button[kind="secondary"] {
            border: 1px solid transparent;
            background: transparent;
            color: var(--text-gray);
            border-radius: 8px;
            transition: color 0.2s;
        }
        button[kind="secondary"]:hover {
            color: var(--primary-orange);
            background: #FFF5F0; /* Very light orange tint */
            border-color: #FED7AA;
        }

        /* 5. SIDEBAR */
        [data-testid="stSidebar"] {
            background-color: #FFFFFF;
            border-right: 1px solid var(--border-color);
        }
        [data-testid="stSidebar"] h3 {
            font-weight: 700;
            color: var(--primary-orange);
        }
        
        /* 6. TYPOGRAPHY & HEADERS */
        h1, h2, h3 {
            font-weight: 800 !important;
            letter-spacing: -0.5px;
        }
        
        /* LOGIN PAGE SPECIFIC */
        .login-header {
            font-size: 28px;
            font-weight: 800;
            color: var(--text-dark);
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
        
        /* Checkbox Styling */
        div[data-baseweb="checkbox"] span {
            font-size: 13px;
            font-weight: 500;
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

def go_to(page: str):
    st.session_state.page = page

# ---------- Page 1: Login ----------
def page_login():
    # Vertical spacer
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Layout columns: [Spacer, Login Box, Spacer]
    # Ratio [1, 2.5, 1] ensures the login box is wide enough for inline elements
    col_l, col_center, col_r = st.columns([1, 2.5, 1])
    
    with col_center:
        # LOGO above the login form
        if LOGO_DATA_URI:
            st.markdown(f"<div style='display:flex; justify-content:center; margin-bottom:15px;'><img src='{LOGO_DATA_URI}' style='height:45px; object-fit: contain;'></div>", unsafe_allow_html=True)

        st.markdown('<div class="login-header">Log in to SIMO</div>', unsafe_allow_html=True)
        
        with st.form("login_form"):
            username_input = st.text_input("Email", placeholder="UserID", label_visibility="collapsed")
            st.markdown("<div style='margin-bottom: 15px;'></div>", unsafe_allow_html=True)
            
            password_input = st.text_input("Password", type="password", placeholder="Password", label_visibility="collapsed")
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True)
            
            # Row for "Remember me" and "Forgot Password"
            c1, c2 = st.columns([1, 1])
            with c1:
                st.checkbox("Remember me")
            with c2:
                st.markdown('<div class="forgot-pass">Forgot Password?</div>', unsafe_allow_html=True)
            
            st.markdown("<br>", unsafe_allow_html=True)

            # Centering the Login Button
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

    # Sidebar with Greetings
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        
        # Greeting Logic (Persistent)
        if "greeting" not in st.session_state or not st.session_state.greeting:
            greetings = [
                "Have a great day!",
                "Hope you're having a good one!",
                "Keep up the great work!",
                "Happy to see you again!",
                "Make today amazing!"
            ]
            st.session_state.greeting = random.choice(greetings)
        
        st.markdown(f"### Hi, {st.session_state.username}")
        st.markdown(f"_{st.session_state.greeting}_")
        
        st.markdown("<br>" * 15, unsafe_allow_html=True)
        if st.button("Log Out", type="primary"):
            st.session_state.authenticated = False
            st.session_state.generated_email = None
            st.session_state.greeting = None
            go_to("login")
            st.rerun()

    # Auto-Generate Logic
    if not st.session_state.generated_email:
        user_inputs = {
            "name": "Acme Corp",
            "recipient_email": "client@acme.com",
            "cc_email": "manager@solis.co",
            "product": "Solis Enterprise"
        }
        with st.spinner("Fetching client metrics..."):
            generated = fetch_from_databricks(user_inputs)
            st.session_state.generated_email = generated
            st.session_state.editable_body = generated.body
            st.session_state.editable_subject = generated.subject
            st.session_state.editable_to = ", ".join(generated.to)
            st.session_state.editable_cc = ", ".join(generated.cc)
            st.session_state.attachments = generated.attachments.copy()
        st.rerun()

    gen = st.session_state.generated_email
    
    # --- DASHBOARD CONTENT ---
    
    # 1. Header (Inside the main card area)
    logo_img_tag = f'<img src="{LOGO_DATA_URI}" alt="SIMO Logo" style="height: 40px; object-fit: contain;">' if LOGO_DATA_URI else ''
    
    st.markdown(f"""
    <div style="display:flex; justify-content:flex-end; align-items:center; padding-bottom:15px; margin-bottom:20px; border-bottom:1px solid #E5E7EB;">
        {logo_img_tag}
    </div>
    """, unsafe_allow_html=True)
    
    # 2. Metadata Section
    col_h1, col_h2 = st.columns([4, 1])
    with col_h1:
        st.markdown('<h3 style="margin:0; padding:0; font-size:18px; color:#1C1C1E;">Details</h3>', unsafe_allow_html=True)
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

    # 3. Message Content
    st.markdown("<strong style='color:#1C1C1E;'>Response</strong>", unsafe_allow_html=True)
    
    if is_editing:
        st.session_state.editable_body = st.text_area("Body", value=st.session_state.editable_body, height=500, label_visibility="collapsed")
    else:
        st.text_area("Body", value=st.session_state.editable_body, height=500, disabled=True, label_visibility="collapsed")
        
    st.markdown("<br><hr style='margin: 30px 0; border-top: 1px solid #E5E7EB;'><br>", unsafe_allow_html=True)

    # 4. Attachments Section
    st.markdown("<h3 style='margin:0; padding:0; font-size:18px; color:#1C1C1E;'>Attachments</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    current_attachments = st.session_state.attachments
    to_remove = []
    
    if not current_attachments:
         st.markdown("<span style='color:#666;'>No attachments.</span>", unsafe_allow_html=True)
    else:
        for idx, att in enumerate(current_attachments):
            # Layout: Icon | Name | Preview | Download | Delete
            c1, c2, c3, c4, c5 = st.columns([0.5, 5, 1, 1, 1])
            c1.markdown("📄") 
            c2.markdown(f"<span style='font-weight:600; color:#333;'>{att.filename}</span>", unsafe_allow_html=True)
            
            # Preview Button
            if c3.button("👁️", key=f"preview_{idx}", help="Preview"):
                st.session_state.preview_file_idx = None if st.session_state.preview_file_idx == idx else idx

            # Download Button
            c4.download_button(
                label="📥",
                data=att.content_bytes,
                file_name=att.filename,
                mime=att.mime_type,
                key=f"dl_{idx}",
                help="Download"
            )

            # Delete Button
            if c5.button("❌", key=f"del_{idx}", help="Remove"):
                to_remove.append(idx)
            
            # Preview Panel
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

    uploaded_files = st.file_uploader("Add files", accept_multiple_files=True)
    if uploaded_files:
        for uf in uploaded_files:
            st.session_state.attachments.append(Attachment(filename=uf.name, content_bytes=uf.read()))
        st.rerun()

    st.markdown("<br><br>", unsafe_allow_html=True)

    # 5. Submit Button
    col_submit_l, col_submit_action, col_submit_r = st.columns([1, 2, 1])
    with col_submit_action:
        if st.button("Submit", type="primary", use_container_width=True):
            final_to = validate_email_list(st.session_state.editable_to)
            final_cc = validate_email_list(st.session_state.editable_cc)
            
            if not final_to:
                st.error("Recipient required.")
            else:
                email_to_send = GeneratedEmail(
                    sender=gen.sender,
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
    
    st.markdown("<br><br>", unsafe_allow_html=True)


# ---------- Router ----------
if st.session_state.page == "login":
    page_login()
else:
    page_dashboard()
