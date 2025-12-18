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

"""
Streamlit App: Solis Client Communication Hub
Aesthetics: High-Fidelity SIMO/Solis Clone
Functionality: Auto-trigger pipeline, Edit Metadata/Body, Preview/Attach files, Submit.
"""

import os
import io
import logging
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
    logger.info("Fetched data from pipeline")
    return generated

def send_email_via_smtp(email_obj: GeneratedEmail, override_body: str = None) -> Tuple[bool, str]:
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        # Simulation for demo
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
        logger.info("Email sent successfully to %s", recipients)
        return True, f"Email sent to {', '.join(recipients)}"
    except Exception as e:
        logger.exception("Failed to send email")
        return False, f"Failed to send email: {e}"

# ---------- Branding & Styling ----------
def inject_custom_css():
    st.markdown("""
    <style>
        /* Import Montserrat font */
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700&display=swap');

        /* 1. Global Reset & Typography */
        html, body, [class*="css"] {
            font-family: 'Montserrat', sans-serif;
            color: #1A1A1A;
            background-color: #F8F9FA; /* Very light grey background */
        }
        
        /* 2. Container Width Restriction for readability */
        .block-container {
            max-width: 1000px; /* Optimal reading width */
            padding-top: 3rem;
            padding-bottom: 5rem;
        }

        /* 3. SIMO Cards */
        .sim-card {
            background-color: #FFFFFF;
            padding: 40px; /* Generous padding */
            border-radius: 16px;
            box-shadow: 0 8px 30px rgba(0,0,0,0.04); /* Soft, luxurious shadow */
            border: 1px solid #EAEAEA;
            margin-bottom: 30px;
        }

        /* 4. Headings */
        h1 {
            font-weight: 700;
            font-size: 32px;
            letter-spacing: -0.5px;
            margin-bottom: 10px;
        }
        h2, h3, h4 {
            font-weight: 600;
            color: #2D2D2D;
        }
        
        /* Custom Section Titles inside Cards */
        .card-header {
            font-size: 18px;
            font-weight: 700;
            color: #1A1A1A;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 20px;
            border-left: 4px solid #FF5F00; /* Orange accent line */
            padding-left: 12px;
        }

        /* 5. Input Fields (Text Input & Text Area) */
        /* Target the internal input elements */
        div[data-baseweb="input"] {
            background-color: #F9F9F9; /* Slight grey fill */
            border: 1px solid #E0E0E0;
            border-radius: 8px;
            padding: 5px;
        }
        /* Focus state */
        div[data-baseweb="input"]:focus-within {
            background-color: #FFFFFF;
            border-color: #FF5F00 !important;
            box-shadow: 0 0 0 2px rgba(255, 95, 0, 0.1) !important;
        }
        /* Text area specific */
        textarea {
            font-family: 'Montserrat', sans-serif !important;
            font-size: 14px !important;
            line-height: 1.6 !important;
        }

        /* 6. Buttons */
        /* Primary (Submit/Login) */
        button[kind="primary"] {
            background-color: #FF5F00 !important;
            color: white !important;
            border: none;
            border-radius: 50px; /* Pill shape */
            padding: 12px 36px;
            font-weight: 600;
            font-size: 15px;
            letter-spacing: 0.5px;
            transition: all 0.2s ease;
            box-shadow: 0 4px 10px rgba(255, 95, 0, 0.2);
            width: 100%; /* Full width for emphasis */
        }
        button[kind="primary"]:hover {
            background-color: #E04F00 !important;
            box-shadow: 0 6px 15px rgba(255, 95, 0, 0.3);
            transform: translateY(-1px);
        }

        /* Secondary (Small buttons like 'i' and 'x') */
        button[kind="secondary"] {
            border: 1px solid #EAEAEA;
            background-color: #FFFFFF;
            color: #555;
            border-radius: 8px;
            font-size: 14px;
            padding: 4px 12px;
            height: auto;
        }
        button[kind="secondary"]:hover {
            border-color: #FF5F00;
            color: #FF5F00;
            background-color: #FFF5F0;
        }

        /* 7. Sidebar Styling */
        [data-testid="stSidebar"] {
            background-color: #F4F4F4; /* Footer-like grey */
            border-right: 1px solid #E5E5E5;
        }
        [data-testid="stSidebar"] hr {
            border-color: #DDD;
        }

        /* 8. Utility Classes */
        .logo-container {
            display: flex;
            align-items: center;
            gap: 10px;
            padding-bottom: 20px;
            border-bottom: 1px solid #EAEAEA;
            margin-bottom: 30px;
        }
        .logo-text {
            font-size: 24px;
            font-weight: 800;
            color: #FF5F00;
            letter-spacing: 1px;
        }
        .logo-sub {
            color: #1A1A1A;
        }

    </style>
    """, unsafe_allow_html=True)

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Solis Hub", layout="wide", page_icon="🟠")

# Inject CSS
inject_custom_css()

# Session state initialization
if "page" not in st.session_state:
    st.session_state.page = "login"
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "generated_email" not in st.session_state:
    st.session_state.generated_email = None
if "editable_body" not in st.session_state:
    st.session_state.editable_body = None
if "editable_subject" not in st.session_state:
    st.session_state.editable_subject = None
if "editable_to" not in st.session_state:
    st.session_state.editable_to = None
if "editable_cc" not in st.session_state:
    st.session_state.editable_cc = None
if "attachments" not in st.session_state:
    st.session_state.attachments = []
if "preview_file_idx" not in st.session_state:
    st.session_state.preview_file_idx = None 

def go_to(page: str):
    st.session_state.page = page

# ---------- Page 1: Login ----------
def page_login():
    # Centering Layout using Columns
    # We use empty columns on sides to center the content effectively on wide screens
    col_l, col_center, col_r = st.columns([1, 1, 1])
    
    with col_center:
        st.markdown("<br><br>", unsafe_allow_html=True)
        # Logo
        st.markdown(
            """<div style="text-align: center; margin-bottom: 40px;">
                <span style="font-size: 36px; font-weight: 800; color: #FF5F00; letter-spacing: 1px;">SOLIS</span>
                <span style="font-size: 36px; font-weight: 800; color: #1A1A1A; letter-spacing: 1px;"> | SIMO</span>
               </div>""", 
            unsafe_allow_html=True
        )
        
        # Login Card
        st.markdown('<div class="sim-card">', unsafe_allow_html=True)
        st.markdown('<div class="card-header">Partner Login</div>', unsafe_allow_html=True)
        st.markdown("<p style='color: #666; margin-bottom: 25px;'>Secure access to client communication pipeline.</p>", unsafe_allow_html=True)

        with st.form("login_form"):
            username = st.text_input("Username", placeholder="e.g. demo")
            password = st.text_input("Password", type="password", placeholder="•••••••")
            st.markdown("<br>", unsafe_allow_html=True)
            # This button will pick up the 'primary' css styles
            submitted = st.form_submit_button("Sign In", type="primary")

        if submitted:
            # Dummy auth logic
            DUMMY_USER = "demo"
            DUMMY_PASS = "demo123"
            if username == DUMMY_USER and password == DUMMY_PASS:
                st.session_state.authenticated = True
                go_to("dashboard")
                st.rerun()
            else:
                st.error("Invalid credentials. Try: demo / demo123")
        
        st.markdown('</div>', unsafe_allow_html=True)
        st.markdown("<div style='text-align:center; color:#AAA; font-size:12px;'>© 2025 Solis. All rights reserved.</div>", unsafe_allow_html=True)

# ---------- Page 2: Dashboard (Auto-Load) ----------
def page_dashboard():
    # Security check
    if not st.session_state.authenticated:
        go_to("login")
        st.rerun()
        return

    # Sidebar: Simple Actions
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### User Profile")
        st.caption("Logged in as")
        st.markdown("**Demo Agent**")
        st.markdown("---")
        
        # Spacer
        st.markdown("<br>" * 15, unsafe_allow_html=True)
        
        if st.button("Log Out"):
            st.session_state.authenticated = False
            st.session_state.generated_email = None
            # Reset all session states
            for key in ["editable_body", "editable_subject", "editable_to", "editable_cc", "attachments"]:
                if key in st.session_state:
                    del st.session_state[key]
            go_to("login")
            st.rerun()

    # --- Header / Navbar ---
    st.markdown("""
    <div class="logo-container">
        <span class="logo-text">SOLIS</span>
        <span class="logo-text logo-sub">HUB</span>
    </div>
    """, unsafe_allow_html=True)

    # --- Auto-Generate Logic (Simulated Pipeline) ---
    if not st.session_state.generated_email:
        user_inputs = {
            "name": "Acme Corp",
            "recipient_email": "client@acme.com",
            "cc_email": "manager@solis.co",
            "product": "Solis Enterprise"
        }
        with st.spinner("Fetching client metrics from Databricks..."):
            generated = fetch_from_databricks(user_inputs)
            st.session_state.generated_email = generated
            # Init edit states
            st.session_state.editable_body = generated.body
            st.session_state.editable_subject = generated.subject
            st.session_state.editable_to = ", ".join(generated.to)
            st.session_state.editable_cc = ", ".join(generated.cc)
            st.session_state.attachments = generated.attachments.copy()
        st.rerun()

    gen: GeneratedEmail = st.session_state.generated_email
    
    # --- Main Content Area ---
    # 1. Main Card: Metadata & Body
    st.markdown('<div class="sim-card">', unsafe_allow_html=True)
    
    # Header Row with Edit Toggle
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown('<div class="card-header">Communication Details</div>', unsafe_allow_html=True)
    with col_h2:
        is_editing = st.checkbox("Enable Editing", value=False)
    
    # --- Metadata Section ---
    # Using columns for To/CC to look like a proper email header
    col_meta1, col_meta2 = st.columns(2)
    with col_meta1:
        if is_editing:
            new_to = st.text_input("To", value=st.session_state.editable_to)
            st.session_state.editable_to = new_to
        else:
            st.text_input("To", value=st.session_state.editable_to, disabled=True)
            
    with col_meta2:
        if is_editing:
            new_cc = st.text_input("CC", value=st.session_state.editable_cc)
            st.session_state.editable_cc = new_cc
        else:
            st.text_input("CC", value=st.session_state.editable_cc, disabled=True)

    # Subject Line
    if is_editing:
        new_subj = st.text_input("Subject Line", value=st.session_state.editable_subject)
        st.session_state.editable_subject = new_subj
    else:
        st.text_input("Subject Line", value=st.session_state.editable_subject, disabled=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # --- Body Section ---
    st.markdown("<strong>Message Content</strong>", unsafe_allow_html=True)
    if is_editing:
        # Height 600px as requested
        new_body = st.text_area("Body", value=st.session_state.editable_body, height=600, label_visibility="collapsed")
        st.session_state.editable_body = new_body
    else:
        st.text_area("Body", value=st.session_state.editable_body, height=600, disabled=True, label_visibility="collapsed")
        
    st.markdown('</div>', unsafe_allow_html=True)

    # 2. Attachments Card
    st.markdown('<div class="sim-card">', unsafe_allow_html=True)
    st.markdown('<div class="card-header">Attachments</div>', unsafe_allow_html=True)
    
    current_attachments = st.session_state.attachments
    to_remove = []
    
    if not current_attachments:
         st.markdown("<em style='color:#999'>No attachments included.</em>", unsafe_allow_html=True)
    else:
        # Table Header
        h1, h2, h3, h4 = st.columns([0.5, 8, 1, 1])
        h2.caption("FILENAME")
        h3.caption("PREVIEW")
        h4.caption("ACTION")
        st.divider()

        for idx, att in enumerate(current_attachments):
            c1, c2, c3, c4 = st.columns([0.5, 8, 1, 1])
            c1.markdown("📄") 
            c2.markdown(f"**{att.filename}**")
            
            # Info / Preview Button
            # Using 'secondary' styling implicitly via Streamlit default, styled by CSS
            if c3.button("ℹ️", key=f"info_{idx}", help="Preview Data"):
                if st.session_state.preview_file_idx == idx:
                     st.session_state.preview_file_idx = None
                else:
                     st.session_state.preview_file_idx = idx

            # Remove Button
            if c4.button("❌", key=f"del_{idx}", help="Remove attachment"):
                to_remove.append(idx)
            
            # Expanded Preview Area
            if st.session_state.preview_file_idx == idx:
                st.markdown("<div style='background-color:#F8F9FA; padding:15px; border-radius:8px; margin-top:10px;'>", unsafe_allow_html=True)
                try:
                    with io.BytesIO(att.content_bytes) as f:
                        df_preview = pd.read_excel(f)
                    st.dataframe(df_preview, use_container_width=True)
                except Exception as e:
                    st.error(f"Cannot preview file: {e}")
                st.markdown("</div>", unsafe_allow_html=True)
            
            st.markdown("<div style='margin-bottom: 12px;'></div>", unsafe_allow_html=True) # Spacer
    
    if to_remove:
        st.session_state.attachments = [a for i, a in enumerate(current_attachments) if i not in to_remove]
        if st.session_state.preview_file_idx in to_remove:
             st.session_state.preview_file_idx = None
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    
    # File Uploader
    uploaded_files = st.file_uploader("Attach additional files", accept_multiple_files=True, type=["xlsx", "pdf", "csv"])
    if uploaded_files:
        for uf in uploaded_files:
            st.session_state.attachments.append(Attachment(filename=uf.name, content_bytes=uf.read()))
        st.success(f"Attached {len(uploaded_files)} files.")
        st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    # 3. Final Submit Action
    # Centered or right aligned? User asked for "submit button... at the end".
    # Making it full-width or large in a column
    col_submit_l, col_submit_action, col_submit_r = st.columns([1, 2, 1])
    with col_submit_action:
        # Using type='primary' to trigger the orange pill style
        if st.button("Submit Communication", type="primary", use_container_width=True):
            # Final Validation
            final_to = validate_email_list(st.session_state.editable_to)
            final_cc = validate_email_list(st.session_state.editable_cc)
            
            if not final_to:
                st.error("Recipient 'To' field cannot be empty.")
            else:
                email_to_send = GeneratedEmail(
                    sender=gen.sender,
                    to=final_to,
                    cc=final_cc,
                    subject=st.session_state.editable_subject,
                    body=st.session_state.editable_body,
                    attachments=st.session_state.attachments.copy()
                )
                with st.spinner("Dispatching via secure SMTP..."):
                    success, msg = send_email_via_smtp(email_to_send)
                
                if success:
                    st.success("✅ Communication dispatched successfully.")
                    st.balloons()
                else:
                    st.error(f"❌ {msg}")
    
    st.markdown("<br><br>", unsafe_allow_html=True)

# ---------- Router ----------
if st.session_state.page == "login":
    page_login()
else:
    page_dashboard()
