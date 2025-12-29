import os
import io
import logging
import random
import base64
import time
from typing import List, Dict, Any

import streamlit as st

# ---------- Configuration & Logging ----------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SIMO Logo Paths
LOGO_URL = os.path.join("utilities", "title.png")
S_LOGO_URL = os.path.join("utilities", "logo.png")

# Helper to convert local image to data URI
def get_image_data_uri(path: str) -> str:
    try:
        base_dir = os.path.dirname(__file__) if "__file__" in globals() else os.getcwd()
        full_path = path if os.path.isabs(path) else os.path.join(base_dir, path)
        if not os.path.exists(full_path):
            full_path = path
            if not os.path.exists(full_path):
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

LOGO_DATA_URI = get_image_data_uri(LOGO_URL)

# ---------- Mock Data Generators ----------
def get_demo_emails():
    return [
        {"id": 101, "sender": "alice@client.com", "subject": "Urgent: Project Timeline Update", "date": "10:30 AM", "body": "Hi Team,\n\nWe need to discuss the timeline for the Q3 deliverables. Can we schedule a call?\n\nBest,\nAlice"},
        {"id": 102, "sender": "bob@vendor.co", "subject": "Invoice #49202 Pending", "date": "Yesterday", "body": "Hello,\n\nJust following up on the invoice sent last week. Please confirm receipt.\n\nRegards,\nBob"},
        {"id": 103, "sender": "charlie@partner.net", "subject": "Integration Issues", "date": "Dec 26", "body": "Hi Support,\n\nWe are facing latency issues with the API integration. Please advise.\n\nCharlie"},
        {"id": 104, "sender": "diana@leads.io", "subject": "New Partnership Proposal", "date": "Dec 24", "body": "Hi,\n\nI'd like to propose a partnership opportunity. Let's connect.\n\nDiana"},
        {"id": 105, "sender": "eric@tech.com", "subject": "System Downtime Notice", "date": "Dec 20", "body": "Scheduled maintenance will occur this Sunday at 2 AM EST."}
    ]

def get_demo_generated():
    return [
        {"id": 201, "linked_email_id": 101, "recipient": "alice@client.com", "subject": "Re: Urgent: Project Timeline Update", "body": "Hi Alice,\n\nThanks for reaching out.\n\nWe are available tomorrow at 2 PM. Let us know if that works.\n\nBest,\nSIMO Team"}
    ]

def get_demo_approved():
    return [
        {"id": 301, "recipient": "hr@simo.co", "subject": "Re: Policy Updates", "body": "Received and noted. Thank you.\n\nBest,\nTeam"}
    ]

def get_demo_updated():
    return [
        {"id": 401, "recipient": "marketing@newsletter.com", "subject": "Re: Weekly Tech Trends", "body": "Thanks for sharing! We will share this with our engineering team internally.\n\nRegards,\nSIMO"}
    ]

def get_demo_sent():
    return [
        {"id": 501, "recipient": "old_client@test.com", "subject": "Re: Follow up", "body": "This issue has been resolved. Closing ticket #992."}
    ]

# ---------- Branding & Styling ----------
def inject_custom_css():
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Montserrat:wght@300;400;500;600;700;800&display=swap');

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

        /* Hide Streamlit Header/Footer */
        header[data-testid="stHeader"] { background-color: transparent !important; }
        header[data-testid="stHeader"] > div[data-testid="stDecoration"] { display: none; }
        footer { display: none; }
        
        /* HIDE "Press Enter to submit" INSTRUCTIONS */
        div[data-testid="InputInstructions"] { display: none !important; }

        /* Main Background */
        div[data-testid="stAppViewContainer"] {
            background-color: var(--bg-light);
        }

        /* --- CARD STYLING --- */
        div[data-testid="block-container"] {
            background-color: var(--card-white);
            border-radius: 16px;
            border: 2px solid #D1D5DB; 
            box-shadow: 0 10px 40px rgba(0,0,0,0.1);
            padding: 2rem 3rem !important;
            max-width: 1300px; 
            margin-top: 2rem;
        }

        /* Inputs */
        div[data-baseweb="input"] {
            background-color: #F3F4F6 !important;
            border-radius: 50px !important;
            border: 1px solid transparent;
        }
        div[data-baseweb="input"]:focus-within {
            background-color: #FFFFFF !important;
            border-color: var(--primary-orange) !important;
            box-shadow: 0 0 0 3px rgba(255, 95, 0, 0.15) !important;
        }
        div[data-baseweb="text-area"] {
             background-color: #F3F4F6 !important;
             border-radius: 12px !important;
        }

        /* Buttons */
        button[kind="primary"] {
            background-color: var(--primary-orange) !important;
            color: white !important;
            border: none;
            border-radius: 50px;
            text-transform: uppercase;
            font-weight: 700;
            transition: all 0.3s ease;
        }
        button[kind="primary"]:hover {
            background-color: var(--primary-orange-hover) !important;
            box-shadow: 0 6px 16px rgba(255, 95, 0, 0.35);
            transform: translateY(-2px);
        }
        button[kind="secondary"] {
            background-color: transparent !important;
            color: var(--text-gray) !important;
            border: 1px solid #E5E7EB !important;
            border-radius: 50px;
        }
        button[kind="secondary"]:hover {
            border-color: var(--primary-orange) !important;
            color: var(--primary-orange) !important;
        }

        /* --- FIXED TAB NAVIGATION STYLING --- */
        div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            justify-content: space-between; 
            align-items: center;
            gap: 10px; 
            width: 100%;
            margin-bottom: 20px;
            overflow: visible; 
        }
        
        div[role="radiogroup"] > label {
            flex: 1 1 auto; 
            min-width: 0;
            background-color: transparent;
            border: none;
            margin: 0;
            padding: 0;
        }
        
        div[role="radiogroup"] > label > div:first-child {
            display: none; /* Hide Radio Circle */
        }
        
        /* The Tab Box itself */
        div[role="radiogroup"] > label > div:last-child {
            text-align: center;
            padding: 12px 10px; 
            font-weight: 600;
            font-size: 13px;
            color: var(--text-gray);
            border: 1px solid #E5E7EB;
            border-radius: 8px;
            background-color: #FAFAFA;
            transition: all 0.2s;
            display: block;
            width: auto;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        /* Selected Tab Style */
        div[role="radiogroup"] > label[data-checked="true"] > div:last-child {
            color: #FFFFFF;
            background-color: var(--primary-orange);
            border-color: var(--primary-orange);
            box-shadow: 0 4px 6px rgba(255, 95, 0, 0.2);
        }

        div[role="radiogroup"] > label:hover > div:last-child {
            border-color: var(--primary-orange);
            color: var(--primary-orange);
        }
        
        div[role="radiogroup"] > label[data-checked="true"]:hover > div:last-child {
            color: #FFFFFF;
        }

        /* Email List Item Styling */
        div.row-widget.stButton > button {
            text-align: left;
            border: 1px solid #eee;
            background-color: #fff;
            color: #333;
            border-radius: 8px;
            padding: 15px;
            width: 100%;
        }
        div.row-widget.stButton > button:hover {
            border-color: var(--primary-orange);
            color: var(--primary-orange);
            background-color: #FFF5F0;
        }
        div.row-widget.stButton > button:focus {
            box-shadow: none;
            border-color: var(--primary-orange);
            background-color: #FFF5F0;
        }

        /* Login Specific */
        .login-header {
            font-size: 28px;
            font-weight: 800;
            color: #334355;
            text-align: center;
            margin-bottom: 25px;
        }
        .forgot-pass {
            text-align: right;
            margin-top: 8px;
            color: var(--primary-orange);
            font-size: 15px;
            font-weight: 600;
            cursor: pointer;
        }
        
        /* Content Box Style */
        .content-box {
            background-color: #F9FAFB; 
            border: 1px solid #E5E7EB; 
            border-radius: 12px; 
            padding: 25px; 
            margin-bottom: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

# ---------- State Management ----------
def init_state(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

init_state("page", "login")
init_state("authenticated", False)
init_state("username", "Guest")
init_state("active_tab_index", 0)

# Data Lists
init_state("emails", get_demo_emails())                   
init_state("responses_generated", get_demo_generated())   
init_state("responses_approved", get_demo_approved())     
init_state("responses_updated", get_demo_updated())       
init_state("responses_sent", get_demo_sent())             

# Selection States 
init_state("sel_email_id", None)          
init_state("sel_gen_id", None)            
init_state("sel_appr_id", None)           
init_state("sel_upd_id", None)            
init_state("sel_sent_id", None)           

# Logic Flags
init_state("response_generated_flag", False)
init_state("edit_mode_response", False)
init_state("temp_response_body", "")

def go_to(page: str):
    st.session_state.page = page

# ---------- Page 1: Login ----------
def page_login():
    st.markdown("<br>", unsafe_allow_html=True)
    col_l, col_center, col_r = st.columns([1, 2, 1])
    
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
            with c1: st.checkbox("Remember me")
            with c2: st.markdown('<div class="forgot-pass">Forgot Password?</div>', unsafe_allow_html=True)
            
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
        
        st.markdown('<div style="text-align:center; margin-top:25px; font-size:14px; color:#555;">New to SIMO? <a href="#" style="color:#FF5F00;font-weight:700;text-decoration:none;">Sign up</a></div>', unsafe_allow_html=True)

# ---------- Page 2: Dashboard ----------
def page_dashboard():
    if not st.session_state.authenticated:
        go_to("login")
        st.rerun()
        return

    # Sidebar
    with st.sidebar:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown(f"### Hi, {st.session_state.username}")
        st.markdown("_Have a productive day!_")
        st.markdown("<br>" * 15, unsafe_allow_html=True)
        if st.button("Log Out", type="primary"):
            st.session_state.authenticated = False
            init_state("active_tab_index", 0)
            go_to("login")
            st.rerun()

    # Header Logo
    logo_img_tag = f'<img src="{LOGO_DATA_URI}" alt="SIMO Logo" style="height: 40px; object-fit: contain;">' if LOGO_DATA_URI else ''
    st.markdown(f"""<div style="display:flex; justify-content:flex-end; align-items:center; padding-bottom:15px; margin-bottom:10px;">{logo_img_tag}</div>""", unsafe_allow_html=True)

    # 1. COUNTS
    c1 = len(st.session_state.emails)
    c2 = len(st.session_state.responses_generated)
    c3 = len(st.session_state.responses_approved)
    c4 = len(st.session_state.responses_updated)
    c5 = len(st.session_state.responses_sent)

    # 2. NAVIGATION (Flexible sizing)
    tab_options = [
        f"New Emails ({c1})", 
        f"Generated Responses ({c2})", 
        f"Approved Responses ({c3})", 
        f"Responses Updated ({c4})",
        f"Responses Sent ({c5})"
    ]

    selected_tab_label = st.radio(
        "Navigation", 
        options=tab_options, 
        index=st.session_state.active_tab_index, 
        horizontal=True, 
        label_visibility="collapsed",
        key="nav_radio"
    )

    st.session_state.active_tab_index = tab_options.index(selected_tab_label)

    # --------------------------------------------------------------------------------
    # TAB 1: NEW EMAILS
    # --------------------------------------------------------------------------------
    if st.session_state.active_tab_index == 0:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if c1 == 0:
            st.info("No new emails pending.")
        else:
            for email in st.session_state.emails:
                lbl = f"✉️ {email['sender']} | {email['subject']}"
                if st.button(lbl, key=f"t1_btn_{email['id']}", use_container_width=True):
                    st.session_state.sel_email_id = email['id']
                    st.session_state.response_generated_flag = False

            st.markdown("<hr style='border-top: 1px solid #E5E7EB; margin: 25px 0;'>", unsafe_allow_html=True)

            if st.session_state.sel_email_id:
                sel_email = next((e for e in st.session_state.emails if e['id'] == st.session_state.sel_email_id), None)
                if sel_email:
                    st.markdown(f"### Reading: {sel_email['subject']}")
                    st.markdown(f"""
                    <div class="content-box">
                        <div style="font-size: 14px; color: #666; margin-bottom: 10px;">
                            <strong>From:</strong> {sel_email['sender']}<br>
                            <strong>Date:</strong> {sel_email['date']}
                        </div>
                        <div style="white-space: pre-wrap;">{sel_email['body']}</div>
                    </div>""", unsafe_allow_html=True)

                    col_btn_l, col_btn_r = st.columns([1, 2])
                    with col_btn_l:
                        if st.button("✨ Generate Response", type="primary", key="t1_gen_btn"):
                            new_resp = {
                                "id": random.randint(1000, 9999),
                                "linked_email_id": sel_email['id'],
                                "recipient": sel_email['sender'],
                                "subject": f"Re: {sel_email['subject']}",
                                "body": f"Hi {sel_email['sender'].split('@')[0]},\n\nThank you for your email regarding '{sel_email['subject']}'.\n\nWe are looking into it and will get back to you shortly.\n\nBest,\nSIMO Team"
                            }
                            st.session_state.responses_generated.insert(0, new_resp)
                            st.session_state.response_generated_flag = True
                            st.rerun()

                    if st.session_state.response_generated_flag:
                        st.success("Response Generated! Check 'Generated Responses' tab.")
                else:
                    st.info("Select an email above.")

    # --------------------------------------------------------------------------------
    # TAB 2: RESPONSES GENERATED
    # --------------------------------------------------------------------------------
    elif st.session_state.active_tab_index == 1:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if c2 == 0:
            st.info("No generated responses pending review.")
        else:
            for resp in st.session_state.responses_generated:
                lbl = f"📝 To: {resp['recipient']} | {resp['subject']}"
                if st.button(lbl, key=f"t2_btn_{resp['id']}", use_container_width=True):
                    st.session_state.sel_gen_id = resp['id']
                    st.session_state.edit_mode_response = False
                    st.session_state.temp_response_body = resp['body']

            st.markdown("<hr style='border-top: 1px solid #E5E7EB; margin: 25px 0;'>", unsafe_allow_html=True)

            if st.session_state.sel_gen_id:
                idx = next((i for i, r in enumerate(st.session_state.responses_generated) if r['id'] == st.session_state.sel_gen_id), None)
                if idx is not None:
                    curr = st.session_state.responses_generated[idx]
                    
                    c_h1, c_h2 = st.columns([4, 1])
                    with c_h1: st.markdown(f"### Reviewing: {curr['subject']}")
                    with c_h2: 
                        is_editing = st.checkbox("Edit Response", value=st.session_state.edit_mode_response, key="t2_edit_chk")
                        st.session_state.edit_mode_response = is_editing

                    if st.session_state.edit_mode_response:
                        st.session_state.temp_response_body = st.text_area("Body", value=curr['body'], height=250, label_visibility="collapsed")
                    else:
                        st.markdown(f"""
                        <div class="content-box">
                            <div style="font-size: 14px; color: #666; margin-bottom: 10px;"><strong>To:</strong> {curr['recipient']}</div>
                            <div style="white-space: pre-wrap;">{curr['body']}</div>
                        </div>""", unsafe_allow_html=True)
                        st.session_state.temp_response_body = curr['body']

                    c_act1, c_act2, spacer = st.columns([1, 1, 2])
                    with c_act1:
                        if st.button("Accept", type="primary", key="t2_accept"):
                            st.session_state.responses_approved.insert(0, curr)
                            st.session_state.responses_generated.pop(idx)
                            st.session_state.sel_gen_id = None
                            st.rerun()
                    with c_act2:
                        if st.button("Update", type="secondary", key="t2_update"):
                            curr['body'] = st.session_state.temp_response_body
                            st.session_state.responses_updated.insert(0, curr)
                            st.session_state.responses_generated.pop(idx)
                            st.session_state.sel_gen_id = None
                            st.rerun()

    # --------------------------------------------------------------------------------
    # TAB 3: RESPONSES APPROVED
    # --------------------------------------------------------------------------------
    elif st.session_state.active_tab_index == 2:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if c3 == 0:
            st.info("No approved responses pending send.")
        else:
            for resp in st.session_state.responses_approved:
                lbl = f"✅ To: {resp['recipient']} | {resp['subject']}"
                if st.button(lbl, key=f"t3_btn_{resp['id']}", use_container_width=True):
                    st.session_state.sel_appr_id = resp['id']

            st.markdown("<hr style='border-top: 1px solid #E5E7EB; margin: 25px 0;'>", unsafe_allow_html=True)

            if st.session_state.sel_appr_id:
                idx = next((i for i, r in enumerate(st.session_state.responses_approved) if r['id'] == st.session_state.sel_appr_id), None)
                if idx is not None:
                    curr = st.session_state.responses_approved[idx]
                    st.markdown(f"### Ready to Send: {curr['subject']}")
                    st.markdown(f"""
                    <div class="content-box">
                        <div style="font-size: 14px; color: #666; margin-bottom: 10px;"><strong>To:</strong> {curr['recipient']}</div>
                        <div style="white-space: pre-wrap;">{curr['body']}</div>
                    </div>""", unsafe_allow_html=True)

                    c_send_l, c_send_r = st.columns([1, 2])
                    with c_send_l:
                        if st.button("Send Email", type="primary", key="t3_send"):
                            with st.spinner("Sending..."): time.sleep(0.5)
                            st.session_state.responses_sent.insert(0, curr)
                            st.session_state.responses_approved.pop(idx)
                            st.session_state.sel_appr_id = None
                            st.balloons()
                            st.rerun()

    # --------------------------------------------------------------------------------
    # TAB 4: RESPONSES UPDATED
    # --------------------------------------------------------------------------------
    elif st.session_state.active_tab_index == 3:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if c4 == 0:
            st.info("No updated responses pending send.")
        else:
            for resp in st.session_state.responses_updated:
                lbl = f"✏️ To: {resp['recipient']} | {resp['subject']}"
                if st.button(lbl, key=f"t4_btn_{resp['id']}", use_container_width=True):
                    st.session_state.sel_upd_id = resp['id']

            st.markdown("<hr style='border-top: 1px solid #E5E7EB; margin: 25px 0;'>", unsafe_allow_html=True)

            if st.session_state.sel_upd_id:
                idx = next((i for i, r in enumerate(st.session_state.responses_updated) if r['id'] == st.session_state.sel_upd_id), None)
                if idx is not None:
                    curr = st.session_state.responses_updated[idx]
                    st.markdown(f"### Ready to Send (Updated): {curr['subject']}")
                    st.markdown(f"""
                    <div class="content-box">
                        <div style="font-size: 14px; color: #666; margin-bottom: 10px;"><strong>To:</strong> {curr['recipient']}</div>
                        <div style="white-space: pre-wrap;">{curr['body']}</div>
                    </div>""", unsafe_allow_html=True)

                    c_s1, c_s2, c_s3 = st.columns([1, 1, 1])
                    with c_s2:
                        if st.button("Send Email", type="primary", key="t4_send", use_container_width=True):
                            with st.spinner("Sending..."): time.sleep(0.5)
                            st.session_state.responses_sent.insert(0, curr)
                            st.session_state.responses_updated.pop(idx)
                            st.session_state.sel_upd_id = None
                            st.balloons()
                            st.rerun()

    # --------------------------------------------------------------------------------
    # TAB 5: RESPONSES SENT
    # --------------------------------------------------------------------------------
    elif st.session_state.active_tab_index == 4:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if c5 == 0:
            st.info("No sent history found.")
        else:
            for resp in st.session_state.responses_sent:
                lbl = f"✈️ To: {resp['recipient']} | {resp['subject']}"
                if st.button(lbl, key=f"t5_btn_{resp['id']}", use_container_width=True):
                    st.session_state.sel_sent_id = resp['id']

            st.markdown("<hr style='border-top: 1px solid #E5E7EB; margin: 25px 0;'>", unsafe_allow_html=True)

            if st.session_state.sel_sent_id:
                curr = next((r for r in st.session_state.responses_sent if r['id'] == st.session_state.sel_sent_id), None)
                if curr:
                    st.markdown(f"### Sent: {curr['subject']}")
                    st.markdown(f"""
                    <div class="content-box" style="background-color: #f0fdf4; border-color: #bbf7d0;">
                        <div style="font-size: 14px; color: #166534; margin-bottom: 10px;">
                            <strong>Status:</strong> Sent<br>
                            <strong>To:</strong> {curr['recipient']}
                        </div>
                        <div style="white-space: pre-wrap;">{curr['body']}</div>
                    </div>""", unsafe_allow_html=True)

# ---------- Main App Entry ----------
st.set_page_config(page_title="SIMO", layout="centered", page_icon=S_LOGO_URL, initial_sidebar_state="expanded")
inject_custom_css()

if st.session_state.page == "login":
    page_login()
else:
    page_dashboard()
