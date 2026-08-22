# ===================================================================
# ETHIOPIAN ACADEMIC PORTAL - RESEARCH COLLABORATION SYSTEM
# WITH SUPABASE PERSISTENCE
# Berhanu Mekonen, PhD, Arba Minch University, June 25, 2026
# ===================================================================

import streamlit as st
import pandas as pd
import numpy as np 
from datetime import datetime, timedelta 
import json
import re
import hashlib
import os
import plotly.express as px
import plotly.graph_objects as go
from collections import Counter
import random
import time
from supabase import create_client, Client

st.set_page_config(
    page_title="Ethiopian Research Collaboration Portal",
    page_icon="🌿🇪🇹🎉",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ===================================================================
# SUPABASE CLIENT
# ===================================================================

def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["anon_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Supabase connection error: {e}. Please check your secrets.")
        st.stop()

def get_supabase():
    if "supabase" not in st.session_state:
        st.session_state.supabase = init_supabase()
    return st.session_state.supabase

def init_supabase_admin():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["service_role_key"]
        return create_client(url, key)
    except Exception as e:
        st.error(f"Admin Supabase connection error: {e}. Please check your service role key.")
        st.stop()

def get_supabase_admin():
    if "supabase_admin" not in st.session_state:
        st.session_state.supabase_admin = init_supabase_admin()
    return st.session_state.supabase_admin

# ===================================================================
# DATA LOAD & SYNC
# ===================================================================

def load_all_data():
    supabase = get_supabase()
    # Users
    res = supabase.table("users").select("*").execute()
    user_db = {}
    if res.data:
        for u in res.data:
            user_db[u["username"]] = u["password_hash"]
    st.session_state.user_db = user_db

    # User profiles
    res = supabase.table("user_profiles").select("*").execute()
    profiles = {}
    if res.data:
        for p in res.data:
            username = p.pop("username")
            profiles[username] = p
    st.session_state.user_profiles = profiles

    # Pending users
    res = supabase.table("pending_users").select("*").execute()
    st.session_state.pending_users = res.data if res.data else []

    # Notifications
    res = supabase.table("notifications").select("*").order("id", desc=True).execute()
    st.session_state.notifications = res.data if res.data else []

    # Forum posts
    res = supabase.table("forum_posts").select("*").order("id", desc=True).execute()
    st.session_state.forum_posts = res.data if res.data else []

    # Chat messages (column is 'sender')
    res = supabase.table("chat_messages").select("*").order("id").execute()
    st.session_state.chat_messages = res.data if res.data else []

    # Feedback (column is 'username')
    res = supabase.table("feedback").select("*").order("id", desc=True).execute()
    st.session_state.feedback = res.data if res.data else []

    # User points
    res = supabase.table("user_points").select("*").execute()
    points = {}
    if res.data:
        for p in res.data:
            points[p["username"]] = p["points"]
    st.session_state.user_points = points

    # User badges
    res = supabase.table("user_badges").select("*").execute()
    badges = {}
    if res.data:
        for b in res.data:
            username = b["username"]
            if username not in badges:
                badges[username] = []
            badges[username].append(b["badge_name"])
    st.session_state.user_badges = badges

    # Events
    res = supabase.table("events").select("*").order("id", desc=True).execute()
    st.session_state.events = res.data if res.data else []

    # Mentorships
    res = supabase.table("mentorships").select("*").order("id", desc=True).execute()
    st.session_state.mentorships = res.data if res.data else []

    # Grants
    res = supabase.table("grants").select("*").order("id").execute()
    st.session_state.grants = res.data if res.data else []

    # Papers
    res = supabase.table("papers").select("*").order("id", desc=True).execute()
    st.session_state.papers = res.data if res.data else []

    # Requests
    res = supabase.table("requests").select("*").order("id", desc=True).execute()
    st.session_state.requests = res.data if res.data else []

    # Ensure admin exists
    admin_exists = "admin" in st.session_state.user_db
    if not admin_exists:
        supabase_admin = get_supabase_admin()
        try:
            supabase_admin.table("users").insert({
                "username": "admin",
                "password_hash": hash_password("admin"),
                "role": "admin"
            }).execute()
            supabase_admin.table("user_profiles").insert({
                "username": "admin",
                "name": "Administrator"
            }).execute()
            load_all_data()  # reload
        except Exception as e:
            st.error(f"Could not create admin: {e}")

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password, hashed):
    return hash_password(password) == hashed

def init_user_db():
    if "user_db" not in st.session_state:
        load_all_data()
    if "logged_in" not in st.session_state:
        st.session_state.logged_in = False
    if "current_user" not in st.session_state:
        st.session_state.current_user = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "🏠 Home"
    if "show_about" not in st.session_state:
        st.session_state.show_about = False
    if "selected_professor" not in st.session_state:
        st.session_state.selected_professor = None
    if "show_letter" not in st.session_state:
        st.session_state.show_letter = False
    if "last_request" not in st.session_state:
        st.session_state.last_request = None
    if "onboarding_complete" not in st.session_state:
        st.session_state.onboarding_complete = False
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 1
    # Ensure admin exists
    if "admin" not in st.session_state.user_db:
        load_all_data()

def add_notification(message, notification_type="info", link=None):
    supabase_admin = get_supabase_admin()
    new_notif = {
        "message": message,
        "type": notification_type,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "read": False,
        "link": link
    }
    try:
        res = supabase_admin.table("notifications").insert(new_notif).execute()
        if res.data:
            st.session_state.notifications.insert(0, res.data[0])
    except Exception as e:
        st.error(f"Error adding notification: {e}")

def add_points(username, points, action):
    supabase_admin = get_supabase_admin()
    try:
        res = supabase_admin.table("user_points").select("points").eq("username", username).execute()
        if res.data:
            current = res.data[0]["points"]
            new_points = current + points
            supabase_admin.table("user_points").update({"points": new_points}).eq("username", username).execute()
        else:
            supabase_admin.table("user_points").insert({"username": username, "points": points}).execute()
            new_points = points
        st.session_state.user_points[username] = new_points
        add_notification(f"⭐ +{points} points for {action}!", "success")
    except Exception as e:
        st.error(f"Error updating points: {e}")

def add_badge(username, badge_name):
    supabase_admin = get_supabase_admin()
    try:
        res = supabase_admin.table("user_badges").select("*").eq("username", username).eq("badge_name", badge_name).execute()
        if not res.data:
            supabase_admin.table("user_badges").insert({"username": username, "badge_name": badge_name}).execute()
            if username not in st.session_state.user_badges:
                st.session_state.user_badges[username] = []
            st.session_state.user_badges[username].append(badge_name)
            add_notification(f"🏅 New badge earned: {badge_name}!", "success")
    except Exception as e:
        st.error(f"Error adding badge: {e}")

def login_user(username, password):
    init_user_db()
    if username not in st.session_state.user_db:
        return False, "❌ Username not found. Please register first."
    stored_hash = st.session_state.user_db[username]
    if verify_password(password, stored_hash):
        st.session_state.logged_in = True
        st.session_state.current_user = username
        profile = st.session_state.user_profiles.get(username, {})
        display_name = profile.get('name', username.split('@')[0].replace('.', ' ').title())
        add_notification(f"Welcome back, {display_name}!", "success")
        add_points(username, 5, "Daily login")
        st.balloons()
        time.sleep(0.5)
        return True, "✅ Login successful!"
    else:
        return False, "❌ Incorrect password. Please try again."

def logout_user():
    st.session_state.logged_in = False
    st.session_state.current_user = None

def request_registration(full_name, username, password, confirm_password, affiliation, status,
                         position, department, student_level, nationality, other_fields=""):
    init_user_db()
    if not full_name.strip():
        return False, "❌ Full name is required."
    if not username.endswith("@amu.edu.et"):
        return False, "❌ Username must end with @amu.edu.et"
    if username in st.session_state.user_db:
        return False, "❌ Username already exists."
    if password != confirm_password:
        return False, "❌ Passwords do not match."
    if len(password) < 6:
        return False, "❌ Password must be at least 6 characters long."
    if not affiliation.strip():
        return False, "❌ Affiliation is required."
    if not status:
        return False, "❌ Please select a status."
    if not department:
        return False, "❌ Please select a department."
    if not nationality:
        return False, "❌ Please select a nationality."
    supabase_admin = get_supabase_admin()
    res = supabase_admin.table("pending_users").select("*").eq("username", username).execute()
    if res.data:
        return False, "❌ Registration already pending. Please wait for admin approval."

    request = {
        "full_name": full_name.strip(),
        "username": username,
        "password_hash": hash_password(password),
        "affiliation": affiliation.strip(),
        "status": status,
        "position": position.strip() if position else "",
        "department": department,
        "student_level": student_level if student_level else "",
        "nationality": nationality,
        "other_fields": other_fields,
        "request_date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "approved": False,
        "rejected": False
    }
    try:
        supabase_admin.table("pending_users").insert(request).execute()
        st.session_state.pending_users.append(request)
        add_notification(f"📝 New registration request from {full_name} ({username})", "info")
        return True, "✅ Registration request submitted! Please wait for admin approval."
    except Exception as e:
        return False, f"❌ Database error: {e}"

def approve_user(request_index):
    if request_index >= len(st.session_state.pending_users):
        return False, "❌ Request not found."
    req = st.session_state.pending_users[request_index]
    if req['approved'] or req['rejected']:
        return False, "❌ Request already processed."
    username = req['username']
    supabase_admin = get_supabase_admin()
    try:
        # Add user
        supabase_admin.table("users").insert({
            "username": username,
            "password_hash": req['password_hash'],
            "role": "user"
        }).execute()
        # Add profile
        profile = {
            "username": username,
            "name": req['full_name'],
            "affiliation": req['affiliation'],
            "status": req['status'],
            "position": req['position'],
            "department": req['department'],
            "student_level": req['student_level'],
            "nationality": req['nationality'],
            "other_fields": req['other_fields']
        }
        supabase_admin.table("user_profiles").insert(profile).execute()
        # Mark pending as approved
        supabase_admin.table("pending_users").update({"approved": True}).eq("id", req["id"]).execute()
        # Update session
        st.session_state.user_db[username] = req['password_hash']
        st.session_state.user_profiles[username] = profile
        req['approved'] = True
        add_notification(f"✅ User {username} approved!", "success")
        return True, f"✅ User {username} approved successfully!"
    except Exception as e:
        return False, f"❌ Error approving: {e}"

def reject_user(request_index):
    if request_index >= len(st.session_state.pending_users):
        return False, "❌ Request not found."
    req = st.session_state.pending_users[request_index]
    if req['approved'] or req['rejected']:
        return False, "❌ Request already processed."
    supabase_admin = get_supabase_admin()
    try:
        supabase_admin.table("pending_users").update({"rejected": True}).eq("id", req["id"]).execute()
        req['rejected'] = True
        add_notification(f"❌ User {req['username']} registration rejected.", "warning")
        return True, f"❌ User {req['username']} rejected."
    except Exception as e:
        return False, f"❌ Error rejecting: {e}"

# ===================================================================
# CSS STYLES (full styling – same as original)
# ===================================================================
st.markdown("""
<style>
    :root {
        --primary: #1B5E20;
        --primary-light: #2E7D32;
        --primary-dark: #0D3B0D;
        --accent: #1A73E8;
        --accent-hover: #1557B0;
        --gold: #FFD700;
        --dark: #0a1a0a;
        --dark-card: #0f2a0f;
    }

    html, body, .stApp {
        font-size: 18px !important;
        line-height: 1.8 !important;
        background: #FFFFFF !important;
    }
    .stApp, .main, .block-container {
        background: #FFFFFF !important;
        color: #202124 !important;
    }
    h1, h2, h3, h4, h5, h6, p, li, span, div, .stMarkdown, .stTextInput, .stSelectbox, .stButton {
        color: #202124 !important;
        font-weight: 500 !important;
    }
    h1 {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #1A73E8, #4285F4, #34A853);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
    }
    h2 {
        font-size: 2.8rem !important;
        font-weight: 700 !important;
        color: #1A73E8 !important;
        border-bottom: 3px solid #E8F0FE;
        padding-bottom: 0.5rem;
    }
    h3 {
        font-size: 2.2rem !important;
        font-weight: 600 !important;
        color: #1A73E8 !important;
    }
    h4 {
        font-size: 1.8rem !important;
        font-weight: 600 !important;
        color: #202124 !important;
    }
    p, li, .stMarkdown {
        font-size: 1.2rem !important;
        font-weight: 400 !important;
        line-height: 2 !important;
        color: #202124 !important;
    }

    .login-container {
        max-width: 600px;
        margin: 2rem auto;
        padding: 2.5rem;
        background: #FFFFFF !important;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        box-shadow: 0 4px 24px rgba(0,0,0,0.08);
    }
    .login-container h1 {
        text-align: center;
        font-size: 2.5rem !important;
        margin-bottom: 0.5rem;
    }
    .login-container .login-subtitle {
        text-align: center;
        color: #5F6368 !important;
        font-size: 1.1rem !important;
        margin-bottom: 2rem;
    }
    .login-container .input-label {
        font-weight: 600 !important;
        color: #202124 !important;
        font-size: 1rem !important;
        display: block;
        margin-bottom: 0.3rem;
    }
    .login-container .input-hint {
        color: #5F6368 !important;
        font-size: 0.85rem !important;
        font-weight: 400 !important;
        display: block;
        margin-top: 0.2rem;
    }
    .login-btn {
        background: linear-gradient(135deg, #1A73E8, #4285F4) !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 0.9rem 2rem !important;
        border-radius: 30px !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        width: 100%;
        cursor: pointer !important;
        transition: all 0.3s !important;
        box-shadow: 0 2px 8px rgba(26,115,232,0.25) !important;
    }
    .login-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(26,115,232,0.35) !important;
    }
    .register-btn {
        background: linear-gradient(135deg, #34A853, #2D9249) !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 0.9rem 2rem !important;
        border-radius: 30px !important;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        width: 100%;
        cursor: pointer !important;
        transition: all 0.3s !important;
        box-shadow: 0 2px 8px rgba(52,168,83,0.25) !important;
    }
    .register-btn:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 16px rgba(52,168,83,0.35) !important;
    }

    .user-info {
        display: flex;
        align-items: center;
        gap: 15px;
        background: rgba(255, 255, 255, 0.9) !important;
        padding: 8px 20px;
        border-radius: 30px;
        border: 1px solid rgba(255, 255, 255, 0.3);
        backdrop-filter: blur(10px);
    }
    .user-info .user-avatar {
        width: 40px;
        height: 40px;
        border-radius: 50%;
        background: linear-gradient(135deg, #1A73E8, #4285F4);
        display: flex;
        align-items: center;
        justify-content: center;
        color: #FFFFFF;
        font-weight: 700;
        font-size: 1.2rem;
    }
    .user-info .user-name {
        color: #202124 !important;
        font-weight: 600 !important;
        font-size: 1rem !important;
    }

    .main-header {
        background: linear-gradient(rgba(27, 94, 32, 0.65), rgba(13, 59, 13, 0.75)),
                    url('https://images.unsplash.com/photo-1500382017468-9049fed747ef?w=1200&h=400&fit=crop') !important;
        background-size: cover !important;
        background-position: center !important;
        background-repeat: no-repeat !important;
        padding: 2rem 3rem 1.8rem 3rem !important;
        border-radius: 16px !important;
        border: 1px solid rgba(255, 215, 0, 0.3) !important;
        margin-bottom: 1.5rem !important;
        box-shadow: 0 4px 30px rgba(0,0,0,0.1) !important;
        position: relative !important;
        overflow: hidden !important;
    }
    .main-header::before {
        content: '' !important;
        position: absolute !important;
        top: 0 !important;
        left: 0 !important;
        right: 0 !important;
        bottom: 0 !important;
        background: linear-gradient(135deg, rgba(27, 94, 32, 0.3), rgba(13, 59, 13, 0.4)) !important;
        z-index: 0 !important;
    }
    .main-header .header-content {
        position: relative !important;
        z-index: 1 !important;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 20px;
    }
    .main-header .logo-section {
        display: flex;
        align-items: center;
        gap: 25px;
        flex: 1;
    }
    .main-header .logo-icon {
        width: 75px;
        height: 75px;
        background: rgba(255, 215, 0, 0.2) !important;
        border: 2px solid #FFD700 !important;
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 2.8rem;
        color: #FFFFFF;
        backdrop-filter: blur(10px);
        box-shadow: 0 4px 20px rgba(0,0,0,0.2);
        animation: pulse 3s infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    .main-header .logo-text h1 {
        font-size: 3.5rem !important;
        font-weight: 800 !important;
        color: #FFFFFF !important;
        background: none !important;
        -webkit-text-fill-color: #FFFFFF !important;
        margin: 0;
        text-shadow: 0 2px 30px rgba(0,0,0,0.3);
    }
    .main-header .logo-text .subtitle {
        color: rgba(255, 255, 255, 0.95) !important;
        font-size: 1.4rem !important;
        font-weight: 400 !important;
        margin: 5px 0 0 0;
        text-shadow: 0 1px 15px rgba(0,0,0,0.2);
    }
    .main-header .logo-text .subtitle .highlight {
        color: #FFD700 !important;
        font-weight: 600 !important;
    }
    .main-header .logo-text .developer-credit {
        color: rgba(255, 255, 255, 0.7) !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
        margin: 8px 0 0 0;
        font-style: italic;
        letter-spacing: 0.5px;
        text-shadow: 0 1px 10px rgba(0,0,0,0.2);
    }
    .main-header .logo-text .developer-credit .highlight-name {
        color: #FFD700 !important;
        font-weight: 600 !important;
    }
    .main-header .logo-text .developer-credit .highlight-institution {
        color: #90EE90 !important;
        font-weight: 600 !important;
    }
    .main-header .header-right {
        display: flex;
        align-items: center;
        gap: 30px;
        flex-wrap: wrap;
    }
    .main-header .header-stats {
        display: flex;
        gap: 25px;
        flex-wrap: wrap;
        align-items: center;
    }
    .main-header .stat-item {
        background: rgba(255, 255, 255, 0.12) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.15);
        padding: 12px 22px;
        border-radius: 14px;
        text-align: center;
        min-width: 100px;
        transition: all 0.3s;
    }
    .main-header .stat-item:hover {
        border-color: #FFD700;
        transform: translateY(-2px);
        background: rgba(255, 255, 255, 0.2) !important;
    }
    .main-header .stat-item .number {
        font-size: 2.5rem !important;
        font-weight: 800 !important;
        color: #FFD700 !important;
        display: block;
    }
    .main-header .stat-item .label {
        font-size: 0.95rem !important;
        font-weight: 500 !important;
        color: rgba(255, 255, 255, 0.8) !important;
        display: block;
        margin-top: 4px;
    }

    .research-dropdown {
        position: relative;
        display: inline-block;
        margin-left: 5px;
        z-index: 9999;
    }
    .research-btn {
        background: rgba(255, 215, 0, 0.2) !important;
        backdrop-filter: blur(10px);
        color: #FFFFFF !important;
        border: 1px solid rgba(255, 215, 0, 0.3) !important;
        padding: 12px 24px;
        border-radius: 30px;
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        cursor: pointer !important;
        transition: all 0.3s ease;
        display: inline-flex;
        align-items: center;
        gap: 10px;
        white-space: nowrap;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        letter-spacing: 0.3px;
        user-select: none;
    }
    .research-btn:hover {
        background: rgba(255, 215, 0, 0.35) !important;
        transform: translateY(-2px) scale(1.02);
        box-shadow: 0 4px 20px rgba(255, 215, 0, 0.2);
        color: #FFFFFF !important;
        border-color: #FFD700 !important;
    }
    .research-btn .arrow-down {
        display: inline-block;
        transition: transform 0.3s ease;
        font-size: 0.8rem;
        color: rgba(255,255,255,0.8);
    }
    .research-dropdown:hover .arrow-down {
        transform: rotate(180deg);
    }
    .research-dropdown-content {
        display: none;
        position: absolute;
        left: 0;
        bottom: 100%;
        background: #FFFFFF !important;
        min-width: 400px;
        max-width: 90vw;
        max-height: 350px;
        overflow-y: auto;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        padding: 1.2rem;
        box-shadow: 0 8px 32px rgba(0,0,0,0.12);
        z-index: 1000;
        margin-bottom: 10px;
    }
    .research-dropdown:hover .research-dropdown-content {
        display: block;
    }
    @media (max-width: 768px) {
        .research-dropdown-content {
            left: auto;
            right: 0;
            min-width: 280px;
            max-width: 85vw;
        }
    }
    .research-dropdown-content .dropdown-title {
        color: #1A73E8 !important;
        font-size: 1.2rem;
        font-weight: 600;
        margin-bottom: 12px;
        border-bottom: 1px solid #E8EAED;
        padding-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 10px;
        position: sticky;
        top: 0;
        background: #FFFFFF;
        z-index: 2;
    }
    .research-dropdown-content .link-item {
        display: flex;
        align-items: center;
        gap: 12px;
        padding: 10px 14px;
        border-radius: 10px;
        transition: all 0.3s ease;
        text-decoration: none;
        color: #202124 !important;
        font-size: 1rem;
        font-weight: 500 !important;
        cursor: pointer;
    }
    .research-dropdown-content .link-item:hover {
        background: #E8F0FE !important;
        transform: translateX(5px);
    }
    .research-dropdown-content .link-item .link-icon {
        font-size: 1.2rem;
        flex-shrink: 0;
    }
    .research-dropdown-content .link-item .link-text {
        flex: 1;
        color: #202124 !important;
    }
    .research-dropdown-content .link-item .link-url {
        color: #5F6368 !important;
        font-size: 0.7rem;
        font-family: monospace;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100px;
    }
    .research-dropdown-content .link-item .link-arrow {
        color: #1A73E8 !important;
        font-size: 0.9rem;
        transition: all 0.3s ease;
    }
    .research-dropdown-content .link-item:hover .link-arrow {
        transform: translateX(4px);
    }
    .research-dropdown-content .divider {
        border: none;
        border-top: 1px solid #E8EAED;
        margin: 4px 0;
    }
    .ethiopian-stripe {
        height: 5px;
        background: linear-gradient(to right, #078930, #FCDD09, #DA121A);
        border-radius: 3px;
        margin: 12px 0 0 0;
    }

    .status-bar {
        background: #F8F9FA !important;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        padding: 1.2rem 2.5rem;
        margin-bottom: 2rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 15px;
    }
    .status-bar .status-dot {
        width: 14px;
        height: 14px;
        border-radius: 50%;
        display: inline-block;
        animation: blink 2s infinite;
    }
    .status-bar .status-dot.online {
        background: #34A853;
        box-shadow: 0 0 20px rgba(52,168,83,0.3);
    }
    @keyframes blink {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.5; }
    }
    .status-bar .status-text {
        color: #202124 !important;
        font-size: 1.2rem !important;
        font-weight: 500 !important;
    }
    .status-bar .status-text .highlight-green {
        color: #34A853 !important;
        font-weight: 700 !important;
    }
    .status-bar .live-badge {
        background: linear-gradient(135deg, #1A73E8, #4285F4);
        color: #FFFFFF !important;
        padding: 6px 18px;
        border-radius: 25px;
        font-size: 1rem !important;
        font-weight: 600 !important;
        border: none;
    }

    .professor-card {
        background: #FFFFFF !important;
        border: 1px solid #E8EAED !important;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 1.5rem;
        transition: all 0.3s;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
    }
    .professor-card:hover {
        transform: translateY(-4px);
        border-color: #1A73E8 !important;
        box-shadow: 0 8px 32px rgba(0,0,0,0.08);
    }
    .badge-available {
        background: #E6F4EA !important;
        color: #34A853 !important;
        border: 1px solid #34A853;
        padding: 6px 18px;
        border-radius: 25px;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    .badge-full {
        background: #FCE8E6 !important;
        color: #EA4335 !important;
        border: 1px solid #EA4335;
        padding: 6px 18px;
        border-radius: 25px;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
    }
    .badge-verified {
        display: inline-block;
        padding: 3px 12px;
        border-radius: 20px;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        margin: 2px 4px 2px 0;
        background: #E8F0FE !important;
        color: #1A73E8 !important;
        border: 1px solid #1A73E8;
    }
    .badge-collab {
        background: #E8F0FE !important;
        color: #1A73E8 !important;
        border: 1px solid #1A73E8;
        padding: 4px 14px;
        border-radius: 25px;
        display: inline-block;
        margin: 2px 4px 2px 0;
        font-size: 0.85rem !important;
        font-weight: 500 !important;
    }
    .social-links {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;
        margin: 10px 0;
    }
    .social-link {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 16px;
        border-radius: 25px;
        font-size: 0.85rem !important;
        font-weight: 600 !important;
        text-decoration: none !important;
        transition: all 0.3s ease;
        border: 1px solid #E8EAED;
        color: #202124 !important;
    }
    .social-link-orcid {
        background: #E8F0FE !important;
        color: #1A73E8 !important;
        border-color: #1A73E8;
    }
    .social-link-researchgate {
        background: #E6F4EA !important;
        color: #34A853 !important;
        border-color: #34A853;
    }
    .social-link-scholar {
        background: #FCE8E6 !important;
        color: #EA4335 !important;
        border-color: #EA4335;
    }
    .social-link-scopus {
        background: #FFF3E0 !important;
        color: #FB8C00 !important;
        border-color: #FB8C00;
    }

    .notification-item {
        padding: 0.75rem;
        border-radius: 8px;
        margin-bottom: 0.5rem;
        border-left: 4px solid #1A73E8;
        background: #F8F9FA;
    }
    .notification-item.unread {
        background: #E8F0FE;
        border-left-color: #EA4335;
    }
    .notification-item .notification-time {
        color: #5F6368 !important;
        font-size: 0.8rem !important;
    }

    .chat-message {
        padding: 0.75rem 1rem;
        border-radius: 12px;
        margin-bottom: 0.5rem;
        max-width: 80%;
    }
    .chat-message.user {
        background: #E8F0FE !important;
        border: 1px solid #1A73E8;
        margin-left: auto;
    }
    .chat-message.other {
        background: #F8F9FA !important;
        border: 1px solid #E8EAED;
    }
    .chat-message .chat-author {
        font-weight: 600 !important;
        font-size: 0.9rem !important;
        color: #1A73E8 !important;
    }
    .chat-message .chat-time {
        color: #5F6368 !important;
        font-size: 0.7rem !important;
    }

    .badge-display {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        margin: 10px 0;
    }
    .badge-item {
        background: #E8F0FE !important;
        border: 1px solid #1A73E8;
        border-radius: 30px;
        padding: 4px 16px;
        font-size: 0.9rem !important;
        font-weight: 600 !important;
        color: #1A73E8 !important;
        display: inline-flex;
        align-items: center;
        gap: 6px;
    }
    .badge-item.gold {
        background: #FFF8E1 !important;
        border-color: #FFD700;
        color: #F9A825 !important;
    }

    .feedback-item {
        background: #FFFFFF !important;
        border: 1px solid #E8EAED;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1rem;
    }
    .feedback-item .feedback-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 0.5rem;
    }
    .feedback-item .feedback-rating {
        color: #FFD700;
        font-size: 1.2rem;
    }

    .dashboard-card {
        background: #FFFFFF !important;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s;
    }
    .dashboard-card:hover {
        transform: translateY(-4px);
        box-shadow: 0 8px 24px rgba(0,0,0,0.06);
        border-color: #1A73E8;
    }
    .dashboard-card .card-value {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        color: #1A73E8 !important;
    }
    .dashboard-card .card-label {
        color: #5F6368 !important;
        font-size: 1rem !important;
        font-weight: 500 !important;
    }

    .stButton > button {
        font-size: 1.2rem !important;
        font-weight: 600 !important;
        padding: 0.9rem 2.2rem !important;
        background: linear-gradient(135deg, #1A73E8, #4285F4) !important;
        color: white !important;
        border-radius: 30px !important;
        border: none !important;
        width: 100%;
        transition: all 0.3s !important;
        box-shadow: 0 2px 8px rgba(26,115,232,0.25) !important;
        min-height: 55px !important;
    }
    .stButton > button:hover {
        transform: translateY(-3px) !important;
        box-shadow: 0 4px 16px rgba(26,115,232,0.35) !important;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background: #F8F9FA !important;
        border-radius: 16px;
        padding: 8px;
        border: 1px solid #E8EAED;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 14px 30px;
        color: #5F6368 !important;
        font-weight: 500 !important;
        font-size: 1.1rem !important;
    }
    .stTabs [aria-selected="true"] {
        background: #FFFFFF !important;
        color: #1A73E8 !important;
        box-shadow: 0 2px 8px rgba(0,0,0,0.06) !important;
        border: 1px solid #E8EAED;
    }

    .stTextInput > div > div > input,
    .stTextArea > div > div > textarea,
    .stSelectbox > div > div > input {
        background: #FFFFFF !important;
        border: 1px solid #DADCE0 !important;
        border-radius: 12px !important;
        color: #202124 !important;
        padding: 14px 20px !important;
        font-size: 1.15rem !important;
        font-weight: 400 !important;
        min-height: 55px !important;
        transition: all 0.3s !important;
    }
    .stTextInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #1A73E8 !important;
        box-shadow: 0 0 0 3px rgba(26,115,232,0.15) !important;
    }

    .search-section {
        background: #F8F9FA !important;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        padding: 2rem;
        margin-bottom: 2rem;
    }

    .about-section {
        background: #FFFFFF !important;
        border: 1px solid #E8EAED;
        border-radius: 16px;
        padding: 2.5rem;
        margin: 2rem 0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06), 0 4px 24px rgba(0,0,0,0.04);
    }
    .about-section h2 {
        font-size: 2.5rem !important;
        color: #1A73E8 !important;
        margin-top: 2rem;
        border-bottom: 3px solid #E8F0FE;
        padding-bottom: 0.5rem;
        font-weight: 700 !important;
    }
    .about-section h3 {
        font-size: 1.8rem !important;
        color: #1A73E8 !important;
        margin-top: 1.5rem;
        font-weight: 600 !important;
    }
    .about-section .stat-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 20px;
        margin: 1.5rem 0;
    }
    .about-section .stat-card {
        background: #F8F9FA !important;
        border: 1px solid #E8EAED;
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        transition: all 0.3s;
    }
    .about-section .stat-card:hover {
        transform: translateY(-3px);
        box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        border-color: #1A73E8;
    }
    .about-section .stat-card .number {
        font-size: 3rem !important;
        font-weight: 800 !important;
        color: #1A73E8 !important;
        display: block;
    }
    .about-section .stat-card .label {
        font-size: 1.1rem !important;
        color: #5F6368 !important;
        font-weight: 500 !important;
    }
    .about-section .quote {
        font-style: italic;
        font-size: 1.4rem !important;
        font-weight: 500 !important;
        color: #1A73E8 !important;
        text-align: center;
        padding: 1.5rem;
        margin: 2rem 0;
        border-top: 1px solid #E8EAED;
        border-bottom: 1px solid #E8EAED;
    }
    .about-section .footer-credit {
        text-align: center;
        margin-top: 2.5rem;
        padding-top: 1.5rem;
        border-top: 1px solid #E8EAED;
        color: #5F6368 !important;
        font-size: 1rem !important;
        font-weight: 400 !important;
    }

    .letter-box {
        background: #FFFFFF !important;
        border: 2px solid #E8EAED;
        border-radius: 16px;
        padding: 3rem;
        font-family: 'Times New Roman', serif;
        line-height: 2;
        margin: 1.5rem 0;
        color: #202124 !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        font-size: 1.2rem !important;
    }
    .letter-box h2 {
        text-align: center;
        font-size: 2.2rem !important;
        font-weight: 700 !important;
        color: #1A73E8 !important;
        -webkit-text-fill-color: #1A73E8 !important;
    }
    .letter-box .date {
        text-align: right;
        font-size: 1.1rem !important;
        color: #5F6368 !important;
    }
    .letter-box .signature {
        margin-top: 3rem;
        border-top: 1px solid #E8EAED;
        padding-top: 2rem;
    }

    .css-1d391kg, .css-12w0qpk, [data-testid="stSidebar"] {
        background: #F8F9FA !important;
        border-right: 1px solid #E8EAED !important;
    }
</style>
""", unsafe_allow_html=True)

# ===================================================================
# RESEARCHER PROFILES - ALL 8 RESEARCHERS
# ===================================================================

RESEARCHER_PROFILES = {
    "researcher_1": {
        "id": "A001",
        "name": "Dr. Berhanu Mekonen Alemu",
        "title": "Lecturer in Mathematics / Postdoctoral Researcher",
        "institution": "Arba Minch University",
        "department": "Department of Mathematics",
        "education": "Ph.D. in Operations Research, Arba Minch University (2026)",
        "profile_image": "🧮📊🤖",
        "research_interests": "Operations Research, Queuing Theory, Stochastic Modeling, Reinforcement Learning, Deep Q-Learning, Service Optimization, Queuing-Inventory Systems, Metaheuristics, Optimization Algorithms",
        "research_keywords": ["OR", "Queueing", "RL", "Service", "Optimization", "Inventory", "Metaheuristics"],
        "specializations": [
            {"area": "Operations Research", "level": 5},
            {"area": "Queuing Theory", "level": 5},
            {"area": "Stochastic Modeling", "level": 4},
            {"area": "Reinforcement Learning", "level": 4},
            {"area": "Deep Q-Learning", "level": 3},
            {"area": "Metaheuristics", "level": 3}
        ],
        "publications": [
            "Performance Analysis of Neutrosophic Multi-Server Queuing-Inventory System under Catastrophic Conditions (2026) - Neutrosophic Sets & Systems, 98, 267",
            "Queuing-Inventory System with Attraction-Retention Mechanisms Under a Partial Synchronous Vacation Policy: The Case of Ethio Telecom Service Center in Arba Minch, Ethiopia (2026) - Queueing Models and Service Management, 9(1)",
            "A Multi-Server Queuing-Inventory System with Attraction-Retention Mechanisms for Impatient Customers and Catastrophes in Warehouse (2025) - American Journal of Business & Operations Research, 12(2), 32",
            "Analyzing Queuing-Inventory Systems with Customer Attraction-Retention and Asynchronous Vacations: The Ethio Telecom Case (2024)"
        ],
        "supervisory_capacity": 4,
        "current_students": 3,
        "completed_phds": 0,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy"],
        "email": "berhanumekonen6@gmail.com",
        "phone": "+2519-05-52-74-81",
        "orcid_id": "0009-0001-4034-7944",
        "orcid_url": "https://orcid.org/0009-0001-4034-7944",
        "researchgate_url": "https://www.researchgate.net/profile/Berhanu-Mekonen-Alemu",
        "google_scholar_url": "https://scholar.google.com/citations?user=bZakMF_Vr7AC&hl=en",
        "scopus_url": "",
        "institutional_id": "AMU/SCI/MATH/001",
        "h_index": 1,
        "total_citations": 77,
        "trust_score": 88,
        "last_verified": "2026-08-06",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "PhD", "Publications"],
        "top_co_authors": [
            {"name": "Prof. Natesan Thillaigovindan", "institution": "Arba Minch University"},
            {"name": "Dr. Getinet Alemayehu Wole", "institution": "Haramaya University"}
        ],
        "collaborating_institutions": ["Arba Minch University", "Haramaya University"],
        "professional_memberships": ["Ethiopian Mathematical Society", "African Mathematical Union"],
        "biography": "Lecturer in Mathematics at Arba Minch University, Ethiopia, since 2022. Completed Ph.D. in Operations Research in 2026 under supervision of Prof. Natesan Thillaigovindan. Research focuses on queuing-inventory systems, attraction-retention mechanisms, and optimization.",
        "education_details": [
            {"degree": "Ph.D. in Operations Research", "institution": "Arba Minch University", "year": "2026"},
            {"degree": "M.Sc. in Operations Research", "institution": "Haramaya University", "year": "2019"},
            {"degree": "B.Sc. in Applied Mathematics", "institution": "Addis Ababa University", "year": "2016"}
        ]
    },
    "researcher_2": {
        "id": "A002",
        "name": "Prof. Natesan Thillaigovindan",
        "title": "Professor of Mathematics",
        "institution": "Arba Minch University",
        "department": "Department of Mathematics, College of Natural and Computational Sciences",
        "education": "Ph.D. in Mathematics, Annamalai University (2002)",
        "profile_image": "📊🧮📈",
        "research_interests": "Queuing Theory, Stochastic Processes, Fuzzy Set Theory, Fuzzy Functional Analysis, Fuzzy Algebra, Fuzzy Multi-Criteria Decision Analysis (MCDM), Neutrosophic Sets, Rough Sets, Soft Sets, Multi-Objective Optimization, Markov Processes",
        "research_keywords": ["Queuing Theory", "Stochastic Processes", "Fuzzy Sets", "MCDM", "Neutrosophic Sets", "Rough Sets", "Optimization", "Markov Processes"],
        "specializations": [
            {"area": "Queuing Theory", "level": 5},
            {"area": "Stochastic Processes", "level": 5},
            {"area": "Fuzzy Set Theory", "level": 5},
            {"area": "Fuzzy Functional Analysis", "level": 5},
            {"area": "Multi-Criteria Decision Making", "level": 5},
            {"area": "Neutrosophic Sets", "level": 4},
            {"area": "Rough Sets", "level": 4}
        ],
        "publications": [
            "Intuitionistic fuzzy n-normed linear space (2007) - Bulletin of Korean Mathematical Society - Cited by: 91",
            "Intuitionistic fuzzy bounded linear operators (2007) - Iranian Journal of Fuzzy Systems - Cited by: 32",
            "On interval valued fuzzy quasi-ideals of semigroups (2009) - East Asian Mathematical Journal - Cited by: 25",
            "Complete fuzzy n-normed linear space (2007) - Malaysian Journal of Fundamental and Applied Sciences - Cited by: 23",
            "Interval valued fuzzy ideals of near-rings (2015) - The Journal of Fuzzy Mathematics - Cited by: 22",
            "A better score function for multiple criteria decision making in fuzzy environment with criteria choice under risk (2016) - Expert Systems with Applications - Cited by: 19"
        ],
        "supervisory_capacity": 6,
        "current_students": 6,
        "completed_phds": 12,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy", "Peer Review"],
        "phd_students_completed": [
            {"name": "S. Vijayabalaji", "year": "2007"},
            {"name": "Berhanu Mekonen Alemu", "year": "2026"}
        ],
        "email": "thillaigovindan.natesan@gmail.com",
        "phone": "+251 947941300",
        "orcid_id": "0000-0002-3710-8918",
        "orcid_url": "https://orcid.org/0000-0002-3710-8918",
        "researchgate_url": "https://www.researchgate.net/profile/Natesan-Thillaigovindan",
        "google_scholar_url": "https://scholar.google.com/citations?user=7vV4eM8AAAAJ&hl=en",
        "scopus_url": "https://www.scopus.com/authid/detail.uri?authorId=16551299700",
        "institutional_id": "AMU/SCI/MATH/002",
        "h_index": 10,
        "total_citations": 452,
        "trust_score": 95,
        "last_verified": "2026-08-06",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "Scopus", "PhD", "50+ Publications", "Books"],
        "top_co_authors": [
            {"name": "Prof. Srinivasan Vijayabalaji", "institution": "University College of Engineering Panruti"},
            {"name": "Dr. Berhanu Mekonen Alemu", "institution": "Arba Minch University"}
        ],
        "collaborating_institutions": ["Arba Minch University", "Annamalai University", "Haramaya University"],
        "professional_memberships": ["Ethiopian Mathematical Society", "African Mathematical Union", "Indian Mathematical Society"],
        "biography": "Professor Natesan Thillaigovindan is a distinguished mathematician with over 40 years of academic experience. Currently serving as Professor at Arba Minch University, Ethiopia since October 2015. Has supervised 12 PhD candidates.",
        "education_details": [
            {"degree": "Ph.D. in Mathematics", "institution": "Annamalai University", "year": "2002"},
            {"degree": "M.Phil. in Mathematics", "institution": "Annamalai University", "year": "1994"},
            {"degree": "M.Sc. in Applied Mathematics", "institution": "NIT Tiruchirappalli", "year": "1977"}
        ]
    },
    "researcher_3": {
        "id": "A003",
        "name": "Dr. D.Sc. Abebe Geletu",
        "title": "German Research Chair / Full Professor of Mathematics",
        "institution": "AIMS Rwanda",
        "department": "Mathematics and Computer Science",
        "education": "D.Sc. (Habil.) in Systems Optimization, TU Ilmenau; Ph.D. in Numerical Optimization, TU Ilmenau; M.Sc. Applied Mathematics, AAU; B.Sc. Mathematics, AAU",
        "profile_image": "🧠🌍🔬",
        "research_interests": "Systems optimization for sustainable resources utilization in Africa; multidisciplinary research for engineering problems; AI and data-driven approaches for complex problems; mathematical optimization; intelligent and predictive control applications; big-data analytics; deep learning for image processing and computer vision; systems development and modernization of African agrifood supply-chain",
        "research_keywords": ["Optimization", "Stochastic Optimization", "Machine Learning", "AI", "Data-Driven Optimization", "Control Engineering", "Image Processing", "Computer Vision", "Big-Data Analytics", "Predictive Control", "Sustainability", "Smart Water Networks", "Microgrids", "Renewable Energy"],
        "specializations": [
            {"area": "Systems Optimization", "level": 5},
            {"area": "Stochastic Optimization", "level": 5},
            {"area": "Machine Learning", "level": 4},
            {"area": "Control Engineering", "level": 4},
            {"area": "Big-Data Analytics", "level": 4},
            {"area": "Image Processing", "level": 3}
        ],
        "publications": [
            "Chance constrained optimization of elliptic PDE systems with smoothing approximations. ESAIM: COCV, 26(2020)70.",
            "Analytic approximation and differentiability of joint chance constraints. Optimization, 68(10), 1985-2023, 2019.",
            "An inner-outer approximation approach to chance constrained optimization. SIAM Journal on Optimization, 27(3), 1834-1857, 2017.",
            "A tractable approximation of nonconvex chance constrained optimization with non-Gaussian uncertainties. Journal of Engineering Optimization, 47(4), pp. 495-520, 2015.",
            "Recent developments in computational approaches to optimization under uncertainty. ChemBioEng Reviews, 1(4), 170-190, 2014.",
            "On robustness of set-valued maps and marginal value functions. Discussiones Mathematicae, 25, 59-108, 2005.",
            "A Conceptual Method for Solving Generalized Semi-infinite Programming Problems. European Journal of Operations Research, 157(1), 3-15, 2004.",
            "Stochastische Optimierung parabolische PDE-Systeme. at-automatisierungstechnik, 66(11): 975-985, 2018.",
            "An approach to determining the number of time intervals for solving dynamic optimization problems. Industrial Engineering Chemical Research, 57, 4340-4350, 2018.",
            "An analytical Hessian and parallel computing approach for efficient dynamic optimization. Industrial Engineering Chemical Research, 54(48), 12086-12095, 2015."
        ],
        "supervisory_capacity": 8,
        "current_students": 7,
        "completed_phds": 3,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy", "Peer Review"],
        "phd_students_completed": [
            {"name": "Ines Mynttinen", "year": "2013", "topic": "Optimization of autonomously switching dynamic hybrid systems"},
            {"name": "Michael Klöppel", "year": "2014", "topic": "Efficient numerical solution of chance constrained optimization problems"},
            {"name": "Evgeny Lazutkin", "year": "2019", "topic": "Efficient solution of nonlinear optimal control problems"}
        ],
        "email": "abebe.geletu@aims.ac.rw",
        "phone": "+250 788 888 888",
        "orcid_id": "0000-0001-2345-6789",
        "orcid_url": "https://orcid.org/0000-0001-2345-6789",
        "researchgate_url": "https://www.researchgate.net/profile/Abebe-Geletu",
        "google_scholar_url": "https://scholar.google.com/citations?user=abebe_geletu",
        "scopus_url": "",
        "institutional_id": "AIMS/RW/CHAIR/001",
        "h_index": 15,
        "total_citations": 850,
        "trust_score": 92,
        "last_verified": "2026-08-09",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "D.Sc.", "Ph.D.", "50+ Publications", "German Research Chair", "Full Professor"],
        "top_co_authors": [
            {"name": "Prof. Pu Li", "institution": "TU Ilmenau, Germany"},
            {"name": "Prof. Armin Hoffmann", "institution": "TU Ilmenau, Germany"}
        ],
        "collaborating_institutions": ["TU Ilmenau (Germany)", "Addis Ababa University", "Haramaya University", "Hawassa University", "AIMS Rwanda"],
        "professional_memberships": ["Ethiopian Mathematical Society", "African Mathematical Union", "SIAM"],
        "biography": "Dr. D.Sc. Abebe Geletu is the German Research Chair and Full Professor of Mathematics at AIMS Rwanda. His research focuses on systems optimization for sustainable resources utilization in Africa, AI/data-driven approaches, and multidisciplinary engineering problems. He previously held academic positions at TU Ilmenau, Germany for over 20 years.",
        "education_details": [
            {"degree": "D.Sc. (Habil.) in Systems Optimization", "institution": "TU Ilmenau, Germany", "year": "2015"},
            {"degree": "Ph.D. in Numerical Optimization", "institution": "TU Ilmenau, Germany", "year": "2004"},
            {"degree": "M.Sc. in Applied Mathematics", "institution": "Addis Ababa University", "year": "1998"},
            {"degree": "B.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "1994"}
        ]
    },
    "researcher_4": {
        "id": "A004",
        "name": "Dr. Surafel Luleseged Tilahun",
        "title": "Associate Professor",
        "institution": "Addis Ababa Science and Technology University",
        "department": "Department of Mathematics",
        "education": "Ph.D. in Applied/Computational Mathematics",
        "profile_image": "📊🤖📈",
        "research_interests": "Applied and computational mathematics; data science and artificial intelligence theory and applications; metaheuristic algorithms; multiobjective optimization; operations research; machine learning; data analytics; optimization algorithms; evolutionary computation; global optimization",
        "research_keywords": ["Metaheuristic", "Genetic Algorithm", "Multiobjective Optimization", "Particle Swarm Optimization", "Operations Research", "Machine Learning", "Data Analytics", "Evolutionary Algorithms", "Heuristics", "Combinatorial Optimization", "Scheduling", "Global Optimization", "Simulated Annealing", "Differential Evolution", "Ant Colony Optimization"],
        "specializations": [
            {"area": "Metaheuristic Algorithms", "level": 5},
            {"area": "Multiobjective Optimization", "level": 5},
            {"area": "Machine Learning", "level": 4},
            {"area": "Operations Research", "level": 4},
            {"area": "Data Analytics", "level": 4},
            {"area": "Evolutionary Computation", "level": 4}
        ],
        "publications": [
            "A Convergent Particle Swarm Optimization Method with Repulsive Functional Constraints for Solving Unimodal and Multimodal Problems (SN Computer Science, June 2026)",
            "Chance-constrained reachability analysis for data-driven predictive control of unknown nonlinear systems (Kybernetika -Praha-, May 2026)",
            "Building Trustworthy and Ethical AI for Healthcare in Africa: Governance, Data Protection, and Interoperability Framework (Research, October 2025)",
            "Dynamic vehicle parking pricing: a bilevel optimization approach (Operational Research, January 2025)",
            "Rule based chatbot design methods: A review (Journal of Computational Science and Data Analytics, September 2024)"
        ],
        "supervisory_capacity": 5,
        "current_students": 4,
        "completed_phds": 2,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy"],
        "phd_students_completed": [
            {"name": "Student 1", "year": "2020", "topic": "Metaheuristic Optimization"},
            {"name": "Student 2", "year": "2022", "topic": "Machine Learning Applications"}
        ],
        "email": "surafel.luleseged@aastu.edu.et",
        "phone": "+251 911 234 567",
        "orcid_id": "0000-0002-3456-7890",
        "orcid_url": "https://orcid.org/0000-0002-3456-7890",
        "researchgate_url": "https://www.researchgate.net/profile/Surafel-Tilahun-2",
        "google_scholar_url": "https://scholar.google.com/citations?user=WKN0n8cAAAAJ&hl=en",
        "scopus_url": "",
        "institutional_id": "AASTU/MATH/001",
        "h_index": 18,
        "total_citations": 1265,
        "trust_score": 90,
        "last_verified": "2026-08-09",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "PhD", "Peer Review", "Editor-in-Chief"],
        "top_co_authors": [
            {"name": "Hong Choon Ong", "institution": "University of Science Malaysia"},
            {"name": "J.-M. T. Ngnotchouye", "institution": "University of KwaZulu-Natal"}
        ],
        "collaborating_institutions": ["University of Zululand", "University of KwaZulu-Natal", "University of Science Malaysia", "Saudi Electronic University", "Arba Minch University"],
        "professional_memberships": ["Ethiopian Mathematical Association", "Ethiopian Space Science Society", "SIAM", "CSSSA"],
        "biography": "Dr. Surafel Luleseged Tilahun is an Associate Professor at Addis Ababa Science and Technology University. He is currently working on applied and computational mathematics, data science, and AI theory and applications. He serves as Editor-in-Chief at the Journal of Computational Science and Data Analytics.",
        "education_details": [
            {"degree": "Ph.D. in Applied/Computational Mathematics", "institution": "University of Science Malaysia", "year": "2012"},
            {"degree": "M.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2008"},
            {"degree": "B.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2006"}
        ]
    },
    "researcher_5": {
        "id": "A005",
        "name": "Prof. Gemechis File Duressa",
        "title": "Professor (Full) of Mathematics",
        "institution": "Jimma University",
        "department": "Department of Mathematics",
        "education": "Ph.D. in Numerical Analysis/Applied Mathematics",
        "profile_image": "📐🧮⭐",
        "research_interests": "Numerical analysis of singularly perturbed differential equations; delay differential equations; differential difference equations; finite difference methods; finite element methods; B-spline collocation methods; computational neuroscience applications; singularly perturbed parabolic partial differential equations; boundary layer problems; uniform convergence methods",
        "research_keywords": ["Singular Perturbation", "Delay Differential Equations", "Parabolic PDEs", "Finite Difference Method", "B-Spline Collocation", "Boundary Layer Problems", "Uniform Convergence", "Reaction-Diffusion Equations", "Convection-Diffusion Problems", "Numerical Methods", "Stability Analysis", "Computational Neuroscience"],
        "specializations": [
            {"area": "Numerical Analysis", "level": 5},
            {"area": "Singular Perturbation", "level": 5},
            {"area": "Delay Differential Equations", "level": 5},
            {"area": "Finite Difference Methods", "level": 5},
            {"area": "Parabolic PDEs", "level": 4},
            {"area": "B-Spline Collocation", "level": 4}
        ],
        "publications": [
            "Modeling and optimal control analysis of transmission dynamics of COVID-19: The case of Ethiopia. Alexandria Engineering Journal 60 (1), 719-732 (2021).",
            "Novel Numerical Scheme for Singularly Perturbed Time Delay Convection-Diffusion Equation. Advances in Mathematical Physics 2021 (2021).",
            "Analysis of Atangana-Baleanu fractional-order SEAIR epidemic model with optimal control. Advances in Difference Equations 2021 (1), 174 (2021).",
            "Optimal control and sensitivity analysis for transmission dynamics of Coronavirus. Results in Physics 19, 103642 (2020).",
            "Uniformly Convergent Numerical Method for Singularly Perturbed Parabolic Differential Difference Equations. Kragujevac Journal of Mathematics 46 (1), 65-84 (2019).",
            "Robust finite difference method for singularly perturbed two-parameter parabolic convection-diffusion problems. International Journal of Computational Methods 18 (02), 2050034 (2021).",
            "Extended cubic B-spline collocation method for singularly perturbed parabolic differential-difference equation. International Journal for Numerical Methods in Biomedical Engineering 37 (2), e3423 (2021).",
            "A method of line with improved accuracy for singularly perturbed parabolic convection-diffusion problems with large temporal lag. Results in Applied Mathematics 11, 100174 (2021).",
            "Accelerated fitted operator finite difference method for singularly perturbed parabolic reaction-diffusion problems. Computational Methods for Differential Equations 9 (3), 886-898 (2021).",
            "Robust numerical method for singularly perturbed semilinear parabolic differential difference equations. Mathematics and Computers in Simulation 188, 537-547 (2021).",
            "A uniformly convergent collocation method for singularly perturbed delay parabolic reaction-diffusion problem. Abstract and Applied Analysis 2021 (2021)."
        ],
        "supervisory_capacity": 6,
        "current_students": 5,
        "completed_phds": 8,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy", "Peer Review"],
        "phd_students_completed": [
            {"name": "Student 1", "year": "2018", "topic": "Singular Perturbation Methods"},
            {"name": "Student 2", "year": "2020", "topic": "Numerical Analysis of PDEs"}
        ],
        "email": "gemechis.duressa@ju.edu.et",
        "phone": "+251 912 345 678",
        "orcid_id": "0000-0003-4567-8901",
        "orcid_url": "https://orcid.org/0000-0003-4567-8901",
        "researchgate_url": "https://www.researchgate.net/profile/Gemechis-Duressa",
        "google_scholar_url": "https://scholar.google.com/citations?user=gemechis_duressa",
        "scopus_url": "",
        "institutional_id": "JU/MATH/001",
        "h_index": 24,
        "total_citations": 2228,
        "trust_score": 94,
        "last_verified": "2026-08-09",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "PhD", "60+ Publications", "Full Professor"],
        "top_co_authors": [
            {"name": "Mesfin Mekuria", "institution": "Adama Science and Technology University"},
            {"name": "Tesfaye Aga Bullo", "institution": "Jimma University"}
        ],
        "collaborating_institutions": ["Jimma University", "Adama Science and Technology University", "Madda Walabu University", "NIT Warangal (India)"],
        "professional_memberships": ["Ethiopian Mathematical Association", "SIAM"],
        "biography": "Prof. Gemechis File Duressa is a Professor of Mathematics at Jimma University, Ethiopia. He is an instructor, researcher, and consultant specializing in numerical analysis of singularly perturbed differential equations. He has supervised numerous graduate students and published extensively in the field.",
        "education_details": [
            {"degree": "Ph.D. in Numerical Analysis/Applied Mathematics", "institution": "National Institute of Technology Warangal, India", "year": "2013"},
            {"degree": "M.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2007"},
            {"degree": "B.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2005"}
        ]
    },
    "researcher_6": {
        "id": "A006",
        "name": "Dr. Addisu Fekadu Andeta",
        "title": "Associate Professor of Biotechnology / Food Microbiology",
        "institution": "Arba Minch University",
        "department": "Biology/Biotechnology Program",
        "education": "Ph.D. in Bioscience Engineering, KU Leuven, Belgium",
        "profile_image": "🔬🧫🌾",
        "research_interests": "Fermented foods, Food microbiology, Microbial ecology, Genetic diversity studies, Starter culture technology, Food safety, Biotechnology, Probiotics, Agricultural microbiology, Food fermentation, Lactic acid bacteria, Enset fermentation, Soymilk, Water hyacinth utilization, Biotechnological applications",
        "research_keywords": ["Fermented Foods", "Food Microbiology", "Microbial Ecology", "Starter Cultures", "Probiotics", "Lactic Acid Bacteria", "Enset Fermentation", "Biotechnology", "Genetic Diversity", "Food Safety", "Agricultural Microbiology"],
        "specializations": [
            {"area": "Food Microbiology", "level": 5},
            {"area": "Fermentation Technology", "level": 5},
            {"area": "Microbial Ecology", "level": 4},
            {"area": "Biotechnology", "level": 4},
            {"area": "Probiotics", "level": 4},
            {"area": "Starter Culture Technology", "level": 4}
        ],
        "publications": [
            "Synergistic effects of antibiotics and heavy metals on antibiotic resistance gene formation and implications for public and environmental health (2026) - Discover Applied Sciences",
            "Native rhizobia nodulating soybean (Glycine max (L.) Merr.) performs better than commercial strain across locations in South Ethiopia Region (2026) - Scientific Reports",
            "Correction: Utilization of water hyacinth briquette as an alternative energy source to combat blooming in Abaya and Chamo Lakes, Ethiopia (2026) - BMC Environmental Science",
            "Soymilk as a sustainable nutritional alternative to cow's milk in South Ethiopia (2026) - Discover Food",
            "Probiotic potential of lactic acid bacteria isolated from Ethiopian traditional fermented Cheka beverage (2024) - Annals of Microbiology",
            "Ethno-pharmacological investigations of Moringa stenopetala Bak. Cuf. and its production challenges in southern Ethiopia (2022) - PLoS One",
            "Professionalism, stigma, and willingness to provide patient-centered safe abortion counseling and care (2022) - Reproductive Health",
            "Silage making of maize stover and banana pseudostem under South Ethiopian conditions (2020) - Microbial Biotechnology",
            "Effect of fermentation system on the physicochemical and microbial community dynamics during enset fermentation (2019) - Journal of Applied Microbiology",
            "Fermentation of enset (Ensete ventricosum) in the Gamo highlands of Ethiopia (2018) - Food Microbiology",
            "Variability, Heritability and Genetic Advance for Some Yield and Yield Related Traits in Barley Landraces (2015) - International Journal of Plant Breeding and Genetics",
            "Qualitative traits variation in barley (Hordeum vulgare L.) landraces from the Southern highlands of Ethiopia (2018) - International Journal of Biodiversity and Conservation"
        ],
        "supervisory_capacity": 5,
        "current_students": 4,
        "completed_phds": 2,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy"],
        "phd_students_completed": [
            {"name": "Student 1", "year": "2022", "topic": "Fermentation of Traditional Ethiopian Beverages"},
            {"name": "Student 2", "year": "2024", "topic": "Probiotic Potential of Lactic Acid Bacteria"}
        ],
        "email": "addisu.fekadu@amu.edu.et",
        "phone": "+251 917 890 124",
        "orcid_id": "Not Available",
        "orcid_url": "",
        "researchgate_url": "https://www.researchgate.net/profile/Addisu-Fekadu-Andeta",
        "google_scholar_url": "https://scholar.google.com/citations?user=Xs3MkUcAAAAJ&hl=en",
        "scopus_url": "",
        "institutional_id": "AMU/BIO/007",
        "h_index": 11,
        "total_citations": 379,
        "trust_score": 88,
        "last_verified": "2026-08-09",
        "verification_badges": ["ResearchGate", "Google Scholar", "PhD", "Associate Professor", "35+ Publications"],
        "top_co_authors": [
            {"name": "Dr. Berhanu Mekonen Alemu", "institution": "Arba Minch University"},
            {"name": "Prof. Natesan Thillaigovindan", "institution": "Arba Minch University"},
            {"name": "Leen Van Campenhout", "institution": "KU Leuven, Belgium"},
            {"name": "Dries Vandeweyer", "institution": "KU Leuven, Belgium"}
        ],
        "collaborating_institutions": ["KU Leuven (Belgium)", "Arba Minch University", "Addis Ababa University"],
        "professional_memberships": ["Ethiopian Biotechnology Society", "African Society for Microbiology", "Food Safety and Quality Association"],
        "biography": "Dr. Addisu Fekadu Andeta is an Associate Professor at Arba Minch University in the Biology/Biotechnology Program. He holds a Ph.D. in Bioscience Engineering from KU Leuven, Belgium. His research focuses on fermented foods, food microbiology, microbial ecology, and starter culture technology. He has published extensively on enset fermentation, probiotic potential of traditional Ethiopian beverages, and agricultural microbiology. He was awarded the Josef G Knoll European Science Award in September 2020.",
        "education_details": [
            {"degree": "Ph.D. in Bioscience Engineering", "institution": "KU Leuven, Belgium", "year": "2020"},
            {"degree": "M.Sc. in Biotechnology", "institution": "Addis Ababa University", "year": "2010"},
            {"degree": "B.Sc. in Biology", "institution": "Arba Minch University", "year": "2006"}
        ]
    },
    "researcher_7": {
        "id": "A007",
        "name": "Prof. Legesse Lemecha Obsu",
        "title": "Associate Professor of Mathematics / Dean for Postgraduate Studies",
        "institution": "Adama Science and Technology University",
        "department": "Department of Applied Mathematics",
        "education": "Ph.D. in Applied Mathematics",
        "profile_image": "📐🚦🧮",
        "research_interests": "Hyperbolic traffic flow modeling, Optimal control, Optimization, Mathematical Epidemiology, Hyperbolic conservation laws, Traffic flow, Mathematical modeling of infectious diseases, COVID-19 transmission dynamics, TB and COVID-19 co-infection, Pest control modeling, Fractional mathematical models, Malaria transmission dynamics, Cholera modeling, HIV/AIDS modeling, Coffee berry borer dynamics, Spatial modeling, Cost-effectiveness analysis",
        "research_keywords": ["Traffic Flow Modeling", "Optimal Control", "Optimization", "Mathematical Epidemiology", "Hyperbolic Conservation Laws", "Mathematical Modeling", "Infectious Diseases", "COVID-19", "TB", "Malaria", "Fractional Calculus", "Pest Control", "Cholera", "HIV/AIDS", "Spatial Modeling"],
        "specializations": [
            {"area": "Hyperbolic Traffic Flow Modeling", "level": 5},
            {"area": "Optimal Control", "level": 5},
            {"area": "Optimization", "level": 5},
            {"area": "Mathematical Epidemiology", "level": 5},
            {"area": "Mathematical Modeling", "level": 5},
            {"area": "Fractional Calculus", "level": 4}
        ],
        "publications": [
            "Optimal control strategies for the transmission risk of COVID-19 (2020) - Journal of Biological Dynamics",
            "Mathematical modeling for COVID-19 transmission dynamics: a case study in Ethiopia (2022) - Results in Physics",
            "Mathematical Modeling and Analysis of TB and COVID-19 Co-infection (2022) - Journal of Applied Mathematics",
            "Pest control using farming awareness: Impact of time delays and optimal use of biopesticides (2021) - Chaos, Solitons & Fractals",
            "Mathematical modeling and analysis for the co-infection of COVID-19 and tuberculosis (2022) - Heliyon",
            "A fractional mathematical model of malaria transmission dynamics with liver stage relapse (2026) - Discover Applied Sciences",
            "Spatial modeling and analysis of malaria transmission dynamics involving Anopheles stephensi with application to Ethiopia (2026) - Discover Public Health",
            "Optimal control and cost-effectiveness analysis of coffee berries invasion with Hypothenemus hampei dynamics (2026) - Mathematics in Applied Sciences and Engineering",
            "Optimal Control and Bifurcation Analysis of Cholera Model (2026) - Journal of Prime Research in Mathematics",
            "Fractional modeling of HIV/AIDS transmission dynamics considering pre-exposure prophylaxis and drug resistant strain (2026) - Journal of Applied Mathematics and Computing"
        ],
        "supervisory_capacity": 6,
        "current_students": 5,
        "completed_phds": 8,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy", "Peer Review"],
        "phd_students_completed": [
            {"name": "Student 1", "year": "2020", "topic": "Mathematical Epidemiology"},
            {"name": "Student 2", "year": "2022", "topic": "Optimal Control"},
            {"name": "Student 3", "year": "2024", "topic": "Traffic Flow Modeling"},
            {"name": "Student 4", "year": "2024", "topic": "Fractional Calculus"}
        ],
        "email": "legesse.obsu@astu.edu.et",
        "phone": "+251 911 234 568",
        "orcid_id": "Not Available",
        "orcid_url": "",
        "researchgate_url": "https://www.researchgate.net/profile/Legesse-Obsu",
        "google_scholar_url": "https://scholar.google.com/citations?hl=en&user=Go4xjW0AAAAJ",
        "scopus_url": "",
        "institutional_id": "ASTU/MATH/004",
        "h_index": 16,
        "total_citations": 789,
        "trust_score": 90,
        "last_verified": "2026-08-09",
        "verification_badges": ["ResearchGate", "Google Scholar", "PhD", "Professor", "Dean", "80+ Publications"],
        "top_co_authors": [
            {"name": "Abdisa Shiferaw Melese", "institution": "Adama Science and Technology University"},
            {"name": "Eshetu Dadi Gurmu", "institution": "Adama Science and Technology University"},
            {"name": "Prof. O. D. Makinde", "institution": "Stellenbosch University"},
            {"name": "Feyissa Kebede Bushu", "institution": "Adama Science and Technology University"},
            {"name": "Mohammed Dawed", "institution": "Hawassa University"},
            {"name": "Getachew Fetene", "institution": "Adama Science and Technology University"},
            {"name": "Abdurkadir Edeo Gemeda", "institution": "Adama Science and Technology University"}
        ],
        "collaborating_institutions": ["Adama Science and Technology University", "Stellenbosch University", "Hawassa University", "Addis Ababa University"],
        "professional_memberships": ["Ethiopian Mathematical Association", "African Mathematical Union", "SIAM"],
        "biography": "Prof. Legesse Lemecha Obsu is an Associate Professor of Mathematics and Dean for Postgraduate Studies at Adama Science and Technology University, Ethiopia. His research focuses on hyperbolic traffic flow modeling, optimal control, optimization, and mathematical epidemiology. He has published extensively on mathematical modeling of infectious diseases including COVID-19, TB, malaria, and HIV/AIDS. He has supervised numerous PhD and MSc students and serves as a reviewer for several international journals.",
        "education_details": [
            {"degree": "Ph.D. in Applied Mathematics", "institution": "Adama Science and Technology University", "year": "2015"},
            {"degree": "M.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2008"},
            {"degree": "B.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2005"}
        ]
    },
    "researcher_8": {
        "id": "A008",
        "name": "Dr. Simon Derkee Zawka",
        "title": "Associate Professor of Mathematics / Director for Publication, Documentation and Dissemination",
        "institution": "Arba Minch University",
        "department": "Department of Mathematics",
        "education": "Ph.D. in Mathematics, Andhra University, India (2018)",
        "profile_image": "🌿📊🧮",
        "research_interests": "Mathematical Bioeconomics, Mathematical Biology, Mathematical Modeling, Optimal Control, Dynamical Systems, Mathematical Ecology, Renewable Resource Management, Pollution Control, Harvesting Strategies, Prey-Predator Systems, Marine Protected Areas, Ecotourism, Fisheries Management",
        "research_keywords": ["Mathematical Bioeconomics", "Mathematical Biology", "Optimal Control", "Dynamical Systems", "Mathematical Modeling", "Renewable Resource Management", "Pollution Control", "Harvesting Strategies", "Prey-Predator Systems", "Marine Protected Areas", "Fisheries Management"],
        "specializations": [
            {"area": "Mathematical Bioeconomics", "level": 5},
            {"area": "Mathematical Biology", "level": 5},
            {"area": "Optimal Control", "level": 5},
            {"area": "Dynamical Systems", "level": 5},
            {"area": "Mathematical Modeling", "level": 5},
            {"area": "Mathematical Ecology", "level": 4}
        ],
        "publications": [
            "Optimal harvesting of a renewable resource in a polluted environment: An allocation problem of the sole owner (2019) - Natural Resource Modeling, 32(2), e12206",
            "Marine protected areas for resilience and economic development (2023) - Aquatic Living Resources, 36, 22",
            "Renewable resource management in a seasonally fluctuating environment with restricted harvesting effort (2018) - Mathematical Biosciences, 301, 1-9",
            "Existence and optimal harvesting of two competing species in a polluted environment with pollution reduction effect (2021) - Journal of Mathematical Modeling, 9(4), 517-536",
            "Optimal effort, fish farming, and marine reserve in fisheries management (2024) - Aquaculture and Fisheries, 9(6), 975-980",
            "Influence of investing in treating a polluted environment on the harvest: A problem of optimal allocation (2019) - Journal of Biological Systems, 27(02), 257-279",
            "Deep Koopman-based reachability analysis for data-driven predictive control of unknown nonlinear systems (2025) - IFAC Journal of Systems and Control",
            "Bio-Economics of a Renewable Resource in the Presence of Pollution: The Problem of Optimal Effort Allocation (2020) - Nonlinear Dyn. Syst. Theory, 20(5), 552-567",
            "Dynamics and optimal harvesting of prey–predator in a polluted environment in the presence of scavenger and pollution control (2023) - Mathematics Open, 2, 2350004",
            "The impact of pollution reduction on the optimal harvesting strategy in a seasonally changing and polluted environment (2024) - Mathematics in Applied Sciences and Engineering, 5(2), 165-184",
            "Optimal harvesting for a single-species population governed by Gompertz law: Influence of environmental fluctuation and limited harvesting capacity (2019) - International Journal of Biomathematics, 12(02), 1950018",
            "Optimizing shellfish aquaculture in nitrogen and fisheries management (2025) - Mathematical Modelling and Numerical Simulation with Applications, 5(1), 18-37",
            "Diversity and ecotourism on multipurpose marine protected areas (2024) - Mathematics in Applied Sciences and Engineering, 5(4), 329-342",
            "Optimal management of a prey-predator system in a polluted environment with effort shared between pollution reduction and harvesting (2024) - TWMS Journal of Applied and Engineering Mathematics",
            "Global behavior of solutions for periodic differential equations involving polynomial factors with applications to population dynamics (2017) - Functional Differential Equations, 23(3-4), 153-174"
        ],
        "supervisory_capacity": 5,
        "current_students": 4,
        "completed_phds": 2,
        "available_for_collaboration": True,
        "collaboration_types": ["Research Supervision", "Joint Research", "Consultancy", "Peer Review"],
        "phd_students_completed": [
            {"name": "Student 1", "year": "2022", "topic": "Mathematical Bioeconomics"},
            {"name": "Student 2", "year": "2024", "topic": "Optimal Control in Ecology"}
        ],
        "email": "simon.zawka@amu.edu.et",
        "phone": "+251 913 456 789",
        "orcid_id": "0000-0002-8814-5516",
        "orcid_url": "https://orcid.org/0000-0002-8814-5516",
        "researchgate_url": "https://www.researchgate.net/profile/Simon-Zawka",
        "google_scholar_url": "https://scholar.google.com/citations?user=4zYjiDQAAAAJ&hl=en",
        "scopus_url": "",
        "institutional_id": "AMU/MATH/008",
        "h_index": 4,
        "total_citations": 49,
        "trust_score": 85,
        "last_verified": "2026-08-09",
        "verification_badges": ["ORCID", "ResearchGate", "Google Scholar", "PhD", "Associate Professor", "Director", "20+ Publications"],
        "top_co_authors": [
            {"name": "Prof. P. D. N. Srinivasu", "institution": "Andhra University, India"},
            {"name": "Dr. Surafel Luleseged Tilahun", "institution": "Addis Ababa Science and Technology University"},
            {"name": "Dr. Abebe Geletu", "institution": "AIMS Rwanda"},
            {"name": "Dr. Teketel Ketema", "institution": "Mekdela Amba University"},
            {"name": "Worku T. Bitew", "institution": "State University of New York at Farmingdale"},
            {"name": "Prof. Seshadev Padhi", "institution": "Birla Institute of Technology"}
        ],
        "collaborating_institutions": ["Andhra University (India)", "Arba Minch University", "Addis Ababa Science and Technology University", "AIMS Rwanda", "State University of New York at Farmingdale", "Birla Institute of Technology"],
        "professional_memberships": ["Ethiopian Mathematical Association", "African Mathematical Union"],
        "biography": "Dr. Simon Derkee Zawka is an Associate Professor of Mathematics at Arba Minch University (AMU) in Ethiopia. He earned his BSc in Mathematics from Arba Minch University, his MSc in Mathematics from Addis Ababa University, and his PhD in Mathematics from Andhra University, India. His research interests lie in mathematical bioeconomics, mathematical biology, mathematical modeling, optimal control, and dynamical systems. He has served as Head of the Department of Mathematics and currently directs the Publication, Documentation, and Dissemination Directorate at AMU. He has published extensively in internationally reputable journals on renewable resource management, pollution control, harvesting strategies, and ecological modeling.",
        "education_details": [
            {"degree": "Ph.D. in Mathematics", "institution": "Andhra University, India", "year": "2018"},
            {"degree": "M.Sc. in Mathematics", "institution": "Addis Ababa University", "year": "2010"},
            {"degree": "B.Sc. in Applied Mathematics", "institution": "Arba Minch University", "year": "2007"}
        ]
    }
}

# ===================================================================
# HELPER FUNCTIONS - ALL FULLY DEFINED
# ===================================================================

def create_forum_post(title, content, author, tags=[]):
    supabase_admin = get_supabase_admin()
    post = {
        "title": title,
        "content": content,
        "author": author,
        "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "tags": json.dumps([t.strip() for t in tags.split(",")]) if tags else "[]",
        "likes": 0,
        "views": 0,
        "comments": "[]"
    }
    try:
        res = supabase_admin.table("forum_posts").insert(post).execute()
        if res.data:
            new_post = res.data[0]
            st.session_state.forum_posts.insert(0, new_post)
            add_notification(f"📝 New forum post: '{title}' by {author}", "info")
            return new_post
    except Exception as e:
        st.error(f"Error creating post: {e}")

def add_comment_to_post(post_id, author, content):
    supabase_admin = get_supabase_admin()
    for post in st.session_state.forum_posts:
        if post["id"] == post_id:
            comments = json.loads(post["comments"]) if post.get("comments") else []
            new_comment = {"author": author, "content": content, "date": datetime.now().strftime("%Y-%m-%d %H:%M")}
            comments.append(new_comment)
            post["comments"] = json.dumps(comments)
            try:
                supabase_admin.table("forum_posts").update({"comments": json.dumps(comments)}).eq("id", post_id).execute()
                add_notification(f"💬 New comment on '{post['title']}' by {author}", "info")
            except Exception as e:
                st.error(f"Error adding comment: {e}")
            break

def like_post(post_id):
    supabase_admin = get_supabase_admin()
    for post in st.session_state.forum_posts:
        if post["id"] == post_id:
            post["likes"] += 1
            try:
                supabase_admin.table("forum_posts").update({"likes": post["likes"]}).eq("id", post_id).execute()
            except Exception as e:
                st.error(f"Error liking post: {e}")
            break

def show_notification_center():
    unread = len([n for n in st.session_state.notifications if not n.get('read', False)])
    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown("### 🔔 Notifications")
        if unread > 0:
            st.warning(f"📌 {unread} new notification(s)")
    with col2:
        if st.button("Mark All Read"):
            supabase_admin = get_supabase_admin()
            for n in st.session_state.notifications:
                n['read'] = True
                try:
                    supabase_admin.table("notifications").update({"read": True}).eq("id", n["id"]).execute()
                except:
                    pass
            st.rerun()
    if st.session_state.notifications:
        for note in reversed(st.session_state.notifications[-10:]):
            unread_class = "unread" if not note.get('read', False) else ""
            st.markdown(f"""
            <div class="notification-item {unread_class}">
                <strong>{note['message']}</strong>
                <div class="notification-time">⏱ {note['time']}</div>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No notifications")

def show_onboarding():
    if st.session_state.onboarding_complete:
        return
    profile = st.session_state.user_profiles.get(st.session_state.current_user, {})
    if profile.get('name') and profile.get('institution') and st.session_state.onboarding_step == 1:
        st.session_state.onboarding_step = 2
    st.markdown("### 🚀 Welcome! Let's set up your profile")
    step = st.session_state.onboarding_step
    if step == 1:
        st.markdown("#### Step 1: Tell us about yourself")
        name = st.text_input("Full Name", value=profile.get('name', ''))
        institution = st.selectbox("Your Institution", ["Arba Minch University", "Addis Ababa University", "Bahir Dar University", "Jimma University", "Hawassa University", "Other"], index=0)
        department = st.text_input("Department", value=profile.get('department', ''))
        if st.button("Next →"):
            supabase_admin = get_supabase_admin()
            try:
                supabase_admin.table("user_profiles").update({
                    "name": name,
                    "institution": institution,
                    "department": department
                }).eq("username", st.session_state.current_user).execute()
                st.session_state.user_profiles[st.session_state.current_user].update({"name": name, "institution": institution, "department": department})
                st.session_state.onboarding_step = 2
                st.rerun()
            except Exception as e:
                st.error(f"Error updating profile: {e}")
    elif step == 2:
        st.markdown("#### Step 2: Your research interests")
        interests = st.multiselect("Select your research interests", ["Agriculture", "Medicine", "Engineering", "Environmental Science", "Physics", "Mathematics", "Computer Science", "Biology", "Chemistry", "Social Sciences"])
        if st.button("Next →"):
            supabase_admin = get_supabase_admin()
            try:
                supabase_admin.table("user_profiles").update({
                    "interests": json.dumps(interests)
                }).eq("username", st.session_state.current_user).execute()
                st.session_state.user_profiles[st.session_state.current_user]["interests"] = interests
                st.session_state.onboarding_step = 3
                st.rerun()
            except Exception as e:
                st.error(f"Error updating interests: {e}")
    elif step == 3:
        st.markdown("#### Step 3: What are you looking for?")
        collab_type = st.radio("I am looking to:", ["Find Collaborators", "Join a Project", "Find a Supervisor", "Offer Mentorship"])
        if st.button("🚀 Start Exploring!"):
            supabase_admin = get_supabase_admin()
            try:
                supabase_admin.table("user_profiles").update({
                    "collab_type": collab_type,
                    "onboarding_complete": True
                }).eq("username", st.session_state.current_user).execute()
                st.session_state.user_profiles[st.session_state.current_user]["collab_type"] = collab_type
                st.session_state.onboarding_complete = True
                add_points(st.session_state.current_user, 10, "Completed onboarding")
                add_badge(st.session_state.current_user, "🌟 Explorer")
                st.success("✅ Profile complete! Welcome to the research community.")
                st.rerun()
            except Exception as e:
                st.error(f"Error updating: {e}")

def show_event_calendar():
    st.markdown("### 📅 Event Calendar")
    with st.expander("➕ Add New Event", expanded=False):
        with st.form("add_event"):
            event_title = st.text_input("Event Title")
            event_date = st.date_input("Date", datetime.now())
            event_desc = st.text_area("Description")
            event_type = st.selectbox("Type", ["Conference", "Workshop", "Seminar", "Webinar", "Defense", "Deadline"])
            if st.form_submit_button("Add Event"):
                supabase_admin = get_supabase_admin()
                new_event = {
                    "title": event_title,
                    "date": event_date.strftime("%Y-%m-%d"),
                    "description": event_desc,
                    "type": event_type,
                    "added_by": st.session_state.current_user
                }
                try:
                    res = supabase_admin.table("events").insert(new_event).execute()
                    if res.data:
                        st.session_state.events.insert(0, res.data[0])
                        add_notification(f"📅 New event added: {event_title}", "info")
                        st.success("Event added!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error adding event: {e}")
    if st.session_state.events:
        for ev in sorted(st.session_state.events, key=lambda x: x['date']):
            st.markdown(f"""
            <div style="background:#F8F9FA;padding:1rem;border-radius:12px;margin-bottom:0.5rem;border-left:4px solid #1A73E8;">
                <strong>{ev['title']}</strong> <span style="color:#5F6368;">({ev['type']})</span><br>
                📅 {ev['date']} · Added by {ev['added_by']}<br>
                {ev['description']}
            </div>
            """, unsafe_allow_html=True)
    else:
        st.info("No events yet. Add one to share with the community!")

def show_grants():
    st.markdown("### 💰 Grant & Funding Opportunities")
    if not st.session_state.grants:
        supabase_admin = get_supabase_admin()
        default_grants = [
            {"title": "National Science Foundation - Research Grants", "deadline": "2026-12-15", "amount": "$50,000 - $200,000", "link": "https://nsf.gov"},
            {"title": "African Union Research Innovation Fund", "deadline": "2026-11-30", "amount": "€100,000", "link": "https://au.int"},
            {"title": "Wellcome Trust - Public Health Research", "deadline": "2026-10-01", "amount": "£150,000", "link": "https://wellcome.org"}
        ]
        for g in default_grants:
            try:
                res = supabase_admin.table("grants").insert(g).execute()
                if res.data:
                    st.session_state.grants.append(res.data[0])
            except:
                pass
    for grant in st.session_state.grants:
        st.markdown(f"""
        <div style="background:#E8F0FE;padding:1rem;border-radius:12px;margin-bottom:0.5rem;">
            <strong>{grant['title']}</strong><br>
            📅 Deadline: {grant['deadline']} · 💵 {grant['amount']}<br>
            <a href="{grant['link']}" target="_blank">Apply Now →</a>
        </div>
        """, unsafe_allow_html=True)

def show_researcher_of_month():
    researchers = list(RESEARCHER_PROFILES.keys())
    month = datetime.now().month
    idx = month % len(researchers)
    prof = RESEARCHER_PROFILES[researchers[idx]]
    st.markdown(f"""
    <div style="background:linear-gradient(135deg,#E8F0FE,#FFFFFF);border:2px solid #FFD700;border-radius:16px;padding:2rem;margin:1rem 0;">
        <div style="display:flex;align-items:center;gap:20px;flex-wrap:wrap;">
            <div style="font-size:4rem;">{prof['profile_image']}</div>
            <div>
                <h3 style="margin:0;">🏆 Researcher of the Month</h3>
                <h2 style="margin:0;color:#1A73E8;">{prof['name']}</h2>
                <p style="margin:0;">{prof['title']} · {prof['institution']}</p>
                <p>⭐ Trust Score: {prof['trust_score']}% · 📊 h-index: {prof['h_index']} · 📄 {len(prof['publications'])} publications</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

def show_chat():
    st.markdown("### 💬 Live Chat Room")
    if not st.session_state.chat_messages:
        st.info("No messages yet. Start the conversation!")
    for msg in st.session_state.chat_messages[-20:]:
        cls = "user" if msg['sender'] == st.session_state.current_user else "other"
        st.markdown(f"""
        <div class="chat-message {cls}">
            <span class="chat-author">{msg['sender']}</span>
            <span class="chat-time">({msg['time']})</span>
            <p style="margin:0.2rem 0 0 0;">{msg['content']}</p>
        </div>
        """, unsafe_allow_html=True)
    with st.form("chat_form"):
        msg = st.text_input("Type your message...", key="chat_input", placeholder="Share a quick thought...")
        if st.form_submit_button("Send"):
            if msg:
                supabase_admin = get_supabase_admin()
                new_msg = {
                    "sender": st.session_state.current_user,
                    "content": msg,
                    "time": datetime.now().strftime("%H:%M")
                }
                try:
                    res = supabase_admin.table("chat_messages").insert(new_msg).execute()
                    if res.data:
                        st.session_state.chat_messages.append(res.data[0])
                        add_points(st.session_state.current_user, 2, "Chat message")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error sending message: {e}")

def show_about_page():
    st.markdown("### About the Ethiopian Research Collaboration Portal")
    st.markdown("""
    <div class="about-section">
        <h2>🌿🇪🇹🎉 About This Portal</h2>
        <p>The <b>Ethiopian Research Collaboration Portal</b> is a digital platform designed to bridge the gap between Ethiopian researchers, academic professionals, and students by facilitating meaningful academic collaborations.</p>
        <div class="stat-grid">
            <div class="stat-card"><span class="number">8</span><span class="label">👨‍🏫 Verified Professionals</span></div>
            <div class="stat-card"><span class="number">10</span><span class="label">🎓 Student Researchers</span></div>
            <div class="stat-card"><span class="number">100+</span><span class="label">📄 Publications</span></div>
            <div class="stat-card"><span class="number">30+</span><span class="label">🎯 PhDs Completed</span></div>
        </div>
        <h3>📌 Key Importance</h3>
        <ul><li>Connects Ethiopian researchers across institutions</li><li>Enhances research supervision and mentorship</li><li>Promotes joint research and publications</li><li>Creates consultancy opportunities</li></ul>
        <div class="quote">"The Research Collaboration Portal is not just a tool—it's a movement to transform Ethiopian research from isolated silos into a connected, collaborative, and globally competitive academic ecosystem."</div>
        <div class="footer-credit">🌿🇪🇹🎉 Berhanu Mekonen, PhD · Arba Minch University · June 25, 2026</div>
    </div>
    """, unsafe_allow_html=True)
    if st.button("🔙 Back to Main Portal", use_container_width=True):
        st.session_state.show_about = False
        st.rerun()

# ===================================================================
# LOAD DATA, SEARCH, LETTER GENERATION
# ===================================================================

@st.cache_data
def load_data():
    academicians_data = []
    for key, prof in RESEARCHER_PROFILES.items():
        academician = {
            "id": prof["id"],
            "name": prof["name"],
            "title": prof["title"],
            "institution": prof["institution"],
            "department": prof["department"],
            "education": prof["education"],
            "specializations": prof["specializations"],
            "publications": prof["publications"],
            "supervisory_capacity": prof["supervisory_capacity"],
            "current_students": prof["current_students"],
            "completed_phds": prof.get("completed_phds", 0),
            "email": prof["email"],
            "phone": prof.get("phone", "Not publicly available"),
            "research_interests": prof["research_interests"],
            "available_for_collaboration": prof.get("available_for_collaboration", True),
            "collaboration_types": prof.get("collaboration_types", ["Research Supervision", "Joint Research"]),
            "profile_image": prof["profile_image"],
            "research_keywords": prof["research_keywords"],
            "orcid_id": prof.get("orcid_id", ""),
            "orcid_url": prof.get("orcid_url", ""),
            "researchgate_url": prof.get("researchgate_url", ""),
            "google_scholar_url": prof.get("google_scholar_url", ""),
            "scopus_url": prof.get("scopus_url", ""),
            "h_index": prof.get("h_index", 0),
            "total_citations": prof.get("total_citations", 0),
            "trust_score": prof.get("trust_score", 0),
            "last_verified": prof.get("last_verified", "2026-08-06"),
            "verification_badges": prof.get("verification_badges", []),
            "biography": prof.get("biography", "")
        }
        academicians_data.append(academician)

    students_data = [
        {"id": "S001", "name": "Abebe Kebede", "research_proposal": "Mathematical modeling of infectious disease spread", "field_of_interest": "Applied Mathematics", "degree_background": "MSc in Mathematics", "email": "abebe.kebede@amu.edu.et", "institution": "Arba Minch University"},
        {"id": "S002", "name": "Tigist Worku", "research_proposal": "Solar energy optimization for rural electrification", "field_of_interest": "Electrical Engineering", "degree_background": "MSc in Electrical Engineering", "email": "tigist.worku@aau.edu.et", "institution": "Addis Ababa University"},
        {"id": "S003", "name": "Fasil Hailu", "research_proposal": "Water resource management for drought-prone regions", "field_of_interest": "Civil Engineering", "degree_background": "MSc in Hydraulic Engineering", "email": "fasil.hailu@bdu.edu.et", "institution": "Bahir Dar University"},
        {"id": "S004", "name": "Meron Tekle", "research_proposal": "Machine learning for crop yield prediction", "field_of_interest": "Computer Science", "degree_background": "MSc in Computer Science", "email": "meron.tekle@ju.edu.et", "institution": "Jimma University"},
        {"id": "S005", "name": "Yonas Desta", "research_proposal": "Climate-smart agricultural practices", "field_of_interest": "Agricultural Science", "degree_background": "MSc in Agriculture", "email": "yonas.desta@hu.edu.et", "institution": "Hawassa University"},
        {"id": "S006", "name": "Hiwot Getachew", "research_proposal": "Epidemiological modeling of non-communicable diseases", "field_of_interest": "Public Health", "degree_background": "MPH in Epidemiology", "email": "hiwot.getachew@aau.edu.et", "institution": "Addis Ababa University"},
        {"id": "S007", "name": "Dawit Eshetu", "research_proposal": "Control system design for automated irrigation", "field_of_interest": "Electrical Engineering", "degree_background": "MSc in Control Engineering", "email": "dawit.eshetu@bdu.edu.et", "institution": "Bahir Dar University"},
        {"id": "S008", "name": "Sara Mohammed", "research_proposal": "Natural language processing for Amharic language", "field_of_interest": "Computer Science", "degree_background": "MSc in Computer Science", "email": "sara.mohammed@ju.edu.et", "institution": "Jimma University"},
        {"id": "S009", "name": "Henok Amanuel", "research_proposal": "Industrial engineering optimization of manufacturing processes", "field_of_interest": "Mechanical Engineering", "degree_background": "MSc in Industrial Engineering", "email": "henok.amanuel@aau.edu.et", "institution": "Addis Ababa University"},
        {"id": "S010", "name": "Beza Tadesse", "research_proposal": "Computational modeling of renewable energy materials", "field_of_interest": "Physics", "degree_background": "MSc in Physics", "email": "beza.tadesse@bdu.edu.et", "institution": "Bahir Dar University"}
    ]
    return pd.DataFrame(academicians_data), pd.DataFrame(students_data)

def search_academicians(academicians_df, search_query, search_type):
    if not search_query:
        return academicians_df
    search_query = search_query.lower()
    if search_type == "Name":
        return academicians_df[academicians_df['name'].str.lower().str.contains(search_query, na=False)]
    elif search_type == "Research Area":
        return academicians_df[academicians_df['research_interests'].str.lower().str.contains(search_query, na=False)]
    elif search_type == "Institution":
        return academicians_df[academicians_df['institution'].str.lower().str.contains(search_query, na=False)]
    elif search_type == "Keyword":
        mask = academicians_df['research_keywords'].apply(lambda x: any(search_query in kw.lower() for kw in x) if isinstance(x, list) else False)
        return academicians_df[mask]
    else:
        mask = (academicians_df['name'].str.lower().str.contains(search_query, na=False) |
                academicians_df['institution'].str.lower().str.contains(search_query, na=False) |
                academicians_df['research_interests'].str.lower().str.contains(search_query, na=False))
        return academicians_df[mask]

def generate_request_letter(student_name, student_institution, professor_name, professor_title,
                           professor_institution, research_topic, request_type,
                           student_email, student_phone):
    date = datetime.now().strftime("%B %d, %Y")
    if request_type == "Research Supervision":
        subject = f"Request for PhD Supervision - {student_name}"
        body = f"I am writing to formally request your consideration to serve as my PhD supervisor. I am currently pursuing my doctoral studies at {student_institution}. My research focuses on: {research_topic}"
    else:
        subject = f"Request for Collaboration - {student_name}"
        body = f"I am writing to propose a collaboration between {student_institution} and {professor_institution}. My research involves: {research_topic}"
    return {
        'date': date,
        'from_address': f"{student_name}\\n{student_institution}\\n{student_email}",
        'to_address': f"{professor_name}\\n{professor_title}\\n{professor_institution}",
        'subject': subject,
        'body': body
    }

# ===================================================================
# LOGIN PAGE
# ===================================================================

def show_login_page():
    init_user_db()
    st.markdown("""
    <div style="text-align:center; padding:1rem 0;">
        <div style="font-size:4rem; margin-bottom:0.5rem;">🌿🇪🇹🎉</div>
        <h1 style="font-size:3rem; margin:0;">Research Collaboration Portal</h1>
        <p style="color:#5F6368; font-size:1.2rem; margin-top:0.5rem;">Sign in to access the Ethiopian Research Network</p>
        <p style="color:#5F6368; font-size:1rem; margin-top:0.3rem;">Please register first if you don't have an account</p>
    </div>
    """, unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Request Registration"])
    with tab1:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            with st.form("login_form"):
                username = st.text_input("📧 Email Address", placeholder="your.name@amu.edu.et")
                password = st.text_input("🔒 Password", type="password", placeholder="Enter your password")
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    submitted = st.form_submit_button("Sign In", use_container_width=True)
                if submitted:
                    if not username or not password:
                        st.error("❌ Please enter both username and password.")
                    else:
                        if username in st.session_state.user_db:
                            success, message = login_user(username, password)
                            if success:
                                st.success(message)
                                time.sleep(1)
                                st.rerun()
                            else:
                                st.error(message)
                        else:
                            pending = [p for p in st.session_state.pending_users if p['username'] == username]
                            if pending:
                                if pending[0]['rejected']:
                                    st.error("❌ Your registration request was rejected by the admin.")
                                elif pending[0]['approved']:
                                    st.success("✅ Your request was approved! Please login.")
                                else:
                                    st.warning("⏳ Your registration request is pending admin approval. Please wait.")
                            else:
                                st.error("❌ Username not found. Please register first.")
            st.markdown("""
            <div style="text-align:center; margin-top:1.5rem; padding-top:1rem; border-top:1px solid #E8EAED;">
                <p style="color:#5F6368; font-size:0.9rem; margin:0;">
                    📧 For support, contact: <b style="color:#1A73E8;">berhanu.mekonen@amu.edu.et</b>
                </p>
                <p style="color:#5F6368; font-size:0.9rem; margin:0;">
                    📞 Phone: <b style="color:#1A73E8;">+251 905 527 481</b>
                </p>
                <p style="color:#5F6368; font-size:0.85rem; margin-top:0.5rem;">
                    ⚠️ Admin: username <b>admin</b> password <b>admin</b>
                </p>
            </div>
            """, unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
    with tab2:
        with st.container():
            st.markdown('<div class="login-container">', unsafe_allow_html=True)
            st.markdown("""
            <div style="text-align:center; margin-bottom:1.5rem;">
                <h3 style="margin:0; color:#1A73E8;">Request Account</h3>
                <p style="color:#5F6368; font-size:0.95rem;">Fill in the details below. Admin will review and approve.</p>
            </div>
            """, unsafe_allow_html=True)
            with st.form("registration_request_form"):
                full_name = st.text_input("👤 Full Name *", placeholder="e.g., Berhanu Mekonen")
                username = st.text_input("📧 Email Address (username) *", placeholder="your.name@amu.edu.et")
                password = st.text_input("🔒 Create Password *", type="password", placeholder="Minimum 6 characters")
                confirm_password = st.text_input("✅ Confirm Password *", type="password", placeholder="Re-enter your password")
                affiliation = st.text_input("🏛️ Affiliation / Institution *", placeholder="e.g., Arba Minch University")
                status = st.selectbox("📌 Current Status *", STATUS_OPTIONS)
                position = st.text_input("💼 Position (if any)", placeholder="e.g., Head of Department")
                department = st.selectbox("📚 Department *", DEPARTMENT_OPTIONS)
                student_level = st.selectbox("🎓 Student Level (if student)", [""] + STUDENT_LEVEL_OPTIONS)
                nationality = st.selectbox("🌍 Nationality *", COUNTRIES_WITH_FLAGS)
                other_fields = st.text_area("📝 Additional Information (optional)", placeholder="Any other details...")
                if st.form_submit_button("Submit Request", use_container_width=True):
                    success, message = request_registration(
                        full_name, username, password, confirm_password,
                        affiliation, status, position, department, student_level, nationality, other_fields
                    )
                    if success:
                        st.success(message)
                        st.balloons()
                        time.sleep(0.5)
                    else:
                        st.error(message)
            st.markdown('</div>', unsafe_allow_html=True)

# ===================================================================
# ADMIN PANEL
# ===================================================================

def show_admin_panel():
    st.markdown("### 👨‍💼 Admin Dashboard")
    st.markdown("Welcome, Administrator! Here you can manage user registrations and view system stats.")

    pending = [p for p in st.session_state.pending_users if not p['approved'] and not p['rejected']]
    if pending:
        st.markdown(f"#### 📌 Pending Registration Requests ({len(pending)})")
        for i, req in enumerate(pending):
            with st.expander(f"Request from {req['full_name']} ({req['username']}) - {req['request_date']}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"""
                    **Full Name:** {req['full_name']}  
                    **Username:** {req['username']}  
                    **Affiliation:** {req['affiliation']}  
                    **Status:** {req['status']}  
                    **Position:** {req.get('position', 'N/A')}  
                    **Department:** {req['department']}  
                    """)
                with col2:
                    st.markdown(f"""
                    **Student Level:** {req.get('student_level', 'N/A')}  
                    **Nationality:** {req['nationality']}  
                    **Request Date:** {req['request_date']}  
                    **Additional Info:** {req.get('other_fields', 'None')}  
                    """)
                col_a, col_b = st.columns(2)
                with col_a:
                    if st.button(f"✅ Approve", key=f"approve_{i}"):
                        success, msg = approve_user(i)
                        if success:
                            st.success(msg)
                            st.balloons()
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(msg)
                with col_b:
                    if st.button(f"❌ Reject", key=f"reject_{i}"):
                        success, msg = reject_user(i)
                        if success:
                            st.warning(msg)
                            st.rerun()
                        else:
                            st.error(msg)
    else:
        st.info("No pending registration requests.")

    approved = [p for p in st.session_state.pending_users if p.get('approved')]
    rejected = [p for p in st.session_state.pending_users if p.get('rejected')]
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Registered Users", len(st.session_state.user_db) - 1)
    col2.metric("Pending Requests", len(pending))
    col3.metric("Approved", len(approved))
    col4.metric("Rejected", len(rejected))

    st.markdown("#### 👥 All Approved Users")
    users = [u for u in st.session_state.user_db.keys() if u != 'admin']
    if users:
        df_users = pd.DataFrame({
            "Username": users,
            "Name": [st.session_state.user_profiles.get(u, {}).get('name', 'N/A') for u in users],
            "Affiliation": [st.session_state.user_profiles.get(u, {}).get('affiliation', 'N/A') for u in users],
            "Status": [st.session_state.user_profiles.get(u, {}).get('status', 'N/A') for u in users]
        })
        st.dataframe(df_users, use_container_width=True)
    else:
        st.info("No approved users yet.")

# ===================================================================
# MAIN APPLICATION
# ===================================================================

def main():
    init_user_db()
    if not st.session_state.logged_in:
        show_login_page()
        return

    academicians_df, students_df = load_data()
    if 'requests' not in st.session_state:
        st.session_state.requests = []
    if 'selected_professor' not in st.session_state:
        st.session_state.selected_professor = None
    if 'show_letter' not in st.session_state:
        st.session_state.show_letter = False
    if 'last_request' not in st.session_state:
        st.session_state.last_request = None
    if 'show_about' not in st.session_state:
        st.session_state.show_about = False

    current_user = st.session_state.current_user
    profile = st.session_state.user_profiles.get(current_user, {})
    user_display_name = profile.get('name', current_user.split('@')[0].replace('.', ' ').title())
    is_admin = (current_user == 'admin')

    with st.sidebar:
        st.markdown("### Research Portal")
        st.markdown("---")
        st.markdown(f"""
        <div style="background:#E8F0FE;padding:1rem;border-radius:12px;margin-bottom:1rem;">
            <p style="margin:0;font-weight:600;color:#1A73E8;">👤 {user_display_name}</p>
            <p style="margin:0;font-size:0.85rem;color:#5F6368;">{current_user}</p>
            <p style="margin:0;font-size:0.85rem;color:#5F6368;">⭐ Points: {st.session_state.user_points.get(current_user, 0)}</p>
            <div class="badge-display">
                {''.join(f'<span class="badge-item">🏅 {b}</span>' for b in st.session_state.user_badges.get(current_user, []))}
            </div>
        </div>
        """, unsafe_allow_html=True)

        unread = len([n for n in st.session_state.notifications if not n.get('read', False)])
        if is_admin:
            nav_options = ["👑 Admin Dashboard", "🏠 Home", "🔍 Find Researchers", "💬 Forum", "📊 Analytics", "📋 My Requests", "💬 Chat", "📅 Events", "💰 Grants", "👥 Mentorship", "📄 Papers", "📝 Feedback", "👤 Profile"]
        else:
            nav_options = ["🏠 Home", "🔍 Find Researchers", "💬 Forum", "📊 Analytics", "📋 My Requests", "💬 Chat", "📅 Events", "💰 Grants", "👥 Mentorship", "📄 Papers", "📝 Feedback", "👤 Profile"]
        if unread > 0:
            nav_options.append(f"📨 Notifications <span class='notification-badge'>{unread}</span>")
        else:
            nav_options.append("📨 Notifications")
        selected_page = st.radio("Navigation", nav_options, index=0)
        st.session_state.current_page = selected_page

        if st.button("🚪 Logout", use_container_width=True):
            logout_user()
            st.rerun()
        st.markdown("---")
        if st.button("About This Portal", use_container_width=True):
            st.session_state.show_about = True
            st.rerun()
        st.markdown("---")
        st.markdown("Connecting Ethiopian Researchers")
        st.markdown("*Berhanu Mekonen, PhD, Arba Minch University, June 25, 2026*")

    if st.session_state.show_about:
        show_about_page()
        return

    current_page = getattr(st.session_state, 'current_page', "🏠 Home")

    # HEADER
    available_profs = len(academicians_df[academicians_df['available_for_collaboration'] == True])
    total_publications = sum([len(p.get('publications', [])) for _, p in academicians_df.iterrows()])
    total_completed_phds = sum([p.get('completed_phds', 0) for _, p in academicians_df.iterrows()])

    st.markdown(f"""
    <div class="main-header">
        <div class="header-content">
            <div class="logo-section">
                <div class="logo-icon">🌿🇪🇹🎉</div>
                <div class="logo-text">
                    <h1>Ethiopian Research Collaboration Portal</h1>
                    <div class="subtitle">Connecting <span class="highlight">Ethiopian</span> Researchers & Academic Professionals</div>
                    <div class="developer-credit">🌿🇪🇹🎉 <span class="highlight-name">Berhanu Mekonen, PhD</span> · <span class="highlight-institution">Arba Minch University</span> · June 25, 2026</div>
                </div>
            </div>
            <div class="header-right">
                <div class="user-info"><div class="user-avatar">{user_display_name[0]}</div><span class="user-name">{user_display_name}</span></div>
                <div class="header-stats">
                    <div class="stat-item"><span class="number">{len(academicians_df)}</span><span class="label">Verified Professionals</span></div>
                    <div class="stat-item"><span class="number">{available_profs}</span><span class="label">Available</span></div>
                    <div class="stat-item"><span class="number">{len(students_df)}</span><span class="label">Student Researchers</span></div>
                    <div class="stat-item"><span class="number">{total_publications}</span><span class="label">Publications</span></div>
                    <div class="stat-item"><span class="number">{total_completed_phds}</span><span class="label">PhDs Completed</span></div>
                </div>
                <div class="research-dropdown">
                    <button class="research-btn">🌍 Researches in the world 🎉<span class="arrow-down">▼</span></button>
                    <div class="research-dropdown-content">
                        <div class="dropdown-title">📚 Research Resources</div>
                        <a href="https://scholar.google.com/" target="_blank" class="link-item"><span class="link-icon">🔬</span><span class="link-text">Google Scholar</span><span class="link-url">scholar.google.com</span><span class="link-arrow">→</span></a>
                        <hr class="divider">
                        <a href="https://www.scimagojr.com/" target="_blank" class="link-item"><span class="link-icon">📊</span><span class="link-text">Check Scopus Indexed or not</span><span class="link-url">scimagojr.com</span><span class="link-arrow">→</span></a>
                        <hr class="divider">
                        <a href="https://mjl.clarivate.com/home" target="_blank" class="link-item"><span class="link-icon">📋</span><span class="link-text">Check Web of Science Indexed or not</span><span class="link-url">mjl.clarivate.com</span><span class="link-arrow">→</span></a>
                    </div>
                </div>
            </div>
        </div>
        <div class="ethiopian-stripe"></div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown(f"""
    <div class="status-bar">
        <div><span class="status-dot online"></span><span class="status-text">System Online · <span class="highlight-green">{len(academicians_df)}</span> verified professionals ready for collaboration</span></div>
        <div><span class="live-badge">LIVE · {datetime.now().strftime('%H:%M:%S')}</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ===================================================================
    # PAGE ROUTING
    # ===================================================================

    if current_page == "👑 Admin Dashboard" and is_admin:
        show_admin_panel()
        return

    if current_page == "🏠 Home" or current_page == "🔍 Find Researchers":
        if current_page == "🏠 Home":
            show_researcher_of_month()
            st.markdown("---")
        st.markdown("### Find Academic Professionals")
        with st.container():
            st.markdown('<div class="search-section">', unsafe_allow_html=True)
            col1, col2, col3 = st.columns([1, 1.5, 0.8])
            with col1:
                prof_search_type = st.selectbox("Search by:", ["All Fields", "Name", "Research Area", "Institution", "Keyword"])
            with col2:
                prof_search_query = st.text_input("Enter search term:", placeholder="e.g., mathematics, queuing...")
            with col3:
                show_available_only = st.checkbox("Available Only", value=True)
            st.markdown('</div>', unsafe_allow_html=True)

        filtered_profs = search_academicians(academicians_df, prof_search_query, prof_search_type)
        if show_available_only:
            filtered_profs = filtered_profs[filtered_profs['available_for_collaboration'] == True]
        st.caption(f"Found {len(filtered_profs)} verified professional(s)")

        for _, prof in filtered_profs.iterrows():
            slots = prof['supervisory_capacity'] - prof['current_students']
            status_class = "badge-available" if slots > 0 else "badge-full"
            status_text = f"{slots} slots available" if slots > 0 else "Fully booked"
            with st.expander(f"{prof['profile_image']} {prof['name']} - {prof['title']}", expanded=False):
                col1, col2 = st.columns([2, 1])
                with col1:
                    verification_html = "".join(f'<span class="badge-verified">{b}</span>' for b in prof.get('verification_badges', []))
                    social_links_html = ""
                    if prof.get('orcid_url'):
                        social_links_html += f'<a href="{prof["orcid_url"]}" target="_blank" class="social-link social-link-orcid">ORCID</a>'
                    if prof.get('researchgate_url'):
                        social_links_html += f'<a href="{prof["researchgate_url"]}" target="_blank" class="social-link social-link-researchgate">ResearchGate</a>'
                    if prof.get('google_scholar_url'):
                        social_links_html += f'<a href="{prof["google_scholar_url"]}" target="_blank" class="social-link social-link-scholar">Google Scholar</a>'
                    if prof.get('scopus_url'):
                        social_links_html += f'<a href="{prof["scopus_url"]}" target="_blank" class="social-link social-link-scopus">Scopus</a>'
                    if social_links_html:
                        social_links_html = f'<div class="social-links">{social_links_html}</div>'
                    st.markdown(f"""
                    <div class="professor-card">
                        <div class="card-header">
                            <div>
                                <h3>{prof['profile_image']} {prof['name']}</h3>
                                <span class="title-badge">{prof['title']}</span>
                                <div style="margin-top:8px;">{verification_html}</div>
                                {social_links_html}
                            </div>
                            <div>
                                <span class="{status_class}">{status_text}</span>
                                <br>
                                <span style="color:#FBBC04;">⭐ Trust Score: {prof['trust_score']}%</span>
                            </div>
                        </div>
                        <div>
                            <p><b>🏛️ Institution:</b> {prof['institution']}</p>
                            <p><b>📚 Department:</b> {prof['department']}</p>
                            <p><b>🎓 Education:</b> {prof['education']}</p>
                            <p><b>🔬 Research Interests:</b> {prof['research_interests']}</p>
                            <div>
                                {''.join(f'<span class="badge-collab">{t}</span>' for t in prof.get('collaboration_types', []))}
                            </div>
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if prof.get('publications'):
                        with st.expander("📄 Publications"):
                            for pub in prof['publications']:
                                st.write(f"• {pub}")
                with col2:
                    st.markdown(f"""
                    <div style="background:#F8F9FA;border:1px solid #E8EAED;border-radius:12px;padding:1.5rem;">
                        <h4 style="color:#202124;">📬 Contact</h4>
                        <p style="color:#202124;">✉️ {prof['email']}</p>
                        <p style="color:#202124;">📞 {prof['phone']}</p>
                        <p style="color:#202124;">📊 Completed PhDs: <span style="color:#1A73E8;font-weight:700;">{prof['completed_phds']}</span></p>
                        <p style="color:#202124;">📋 Available Slots: <span style="color:#1A73E8;font-weight:700;">{slots}</span></p>
                        <p style="color:#202124;">📈 h-index: <span style="color:#1A73E8;font-weight:700;">{prof['h_index']}</span> | 📑 Citations: <span style="color:#1A73E8;font-weight:700;">{prof['total_citations']}</span></p>
                    </div>
                    """, unsafe_allow_html=True)
                    if slots > 0:
                        if st.button(f"Request Collaboration with {prof['name'].split()[0]}", key=f"req_{prof['id']}"):
                            st.session_state.selected_professor = prof.to_dict()
                            st.success(f"Ready to request collaboration with {prof['name']}")
                            st.rerun()
                    else:
                        st.warning("No available slots")

    elif current_page == "📋 My Requests" or st.session_state.selected_professor:
        st.markdown("### Request Collaboration")
        if st.session_state.selected_professor:
            prof = st.session_state.selected_professor
            st.markdown(f"""
            <div style="background:#E8F0FE;border:1px solid #1A73E8;border-radius:12px;padding:1.5rem;margin-bottom:1.5rem;border-left:5px solid #1A73E8;">
                <h4 style="color:#202124;">Requesting: {prof['name']} - {prof['title']}</h4>
                <p style="color:#5F6368;">🏛️ {prof['institution']} • 📚 {prof['department']}</p>
            </div>
            """, unsafe_allow_html=True)
            with st.form("collaboration_request"):
                request_type = st.selectbox("Type of Collaboration", prof.get('collaboration_types', ['Research Supervision', 'Joint Research', 'Consultancy']))
                col1, col2 = st.columns(2)
                with col1:
                    requester_name = st.text_input("Full Name *", value=user_display_name)
                    requester_email = st.text_input("Email Address *", value=current_user)
                with col2:
                    requester_institution = st.text_input("Institution *", value=profile.get('institution', 'Arba Minch University'))
                    requester_phone = st.text_input("Phone Number", value="")
                research_topic = st.text_area("Research Topic/Proposal *", height=150)
                submitted = st.form_submit_button("Submit Request", use_container_width=True)
                if submitted:
                    if not requester_name or not requester_email or not requester_institution or not research_topic:
                        st.error("Please fill in all required fields")
                    else:
                        letter_data = generate_request_letter(
                            requester_name, requester_institution,
                            prof['name'], prof['title'], prof['institution'],
                            research_topic, request_type,
                            requester_email, requester_phone
                        )
                        supabase_admin = get_supabase_admin()
                        request = {
                            "requester": requester_name,
                            "requester_institution": requester_institution,
                            "professor": prof['name'],
                            "professor_institution": prof['institution'],
                            "request_type": request_type,
                            "research_topic": research_topic,
                            "status": "Pending",
                            "letter": letter_data,
                            "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                        }
                        try:
                            res = supabase_admin.table("requests").insert(request).execute()
                            if res.data:
                                st.session_state.requests.insert(0, res.data[0])
                                st.session_state.last_request = res.data[0]
                                st.session_state.show_letter = True
                                add_notification(f"📩 Collaboration request submitted to {prof['name']}", "success")
                                st.success(f"✅ Request submitted successfully to {prof['name']}!")
                                st.balloons()
                                st.markdown(f"""
                                <div class="letter-box">
                                    <h2>REQUEST FOR {request_type.upper()}</h2>
                                    <p class="date"><b>Date:</b> {letter_data['date']}</p>
                                    <p><b>From:</b><br>{letter_data['from_address']}</p>
                                    <p><b>To:</b><br>{letter_data['to_address']}</p>
                                    <p><b>Subject:</b> {letter_data['subject']}</p>
                                    <p>Dear {prof['name'].split()[0]},</p>
                                    <p>{letter_data['body']}</p>
                                    <div class="signature">
                                        <p>Yours sincerely,</p>
                                        <p><b>{requester_name}</b><br>{requester_institution}</p>
                                    </div>
                                </div>
                                """, unsafe_allow_html=True)
                        except Exception as e:
                            st.error(f"Error saving request: {e}")
        else:
            st.info("👈 Please go to 'Find Professionals' and click 'Request Collaboration'")
        st.markdown("### My Collaboration Requests")
        if not st.session_state.requests:
            st.info("You haven't submitted any collaboration requests yet.")
        else:
            for req in reversed(st.session_state.requests):
                with st.expander(f"📩 {req['request_type']} - {req['professor']} ({req['status']})"):
                    st.markdown(f"""
                    <div style="background:#F8F9FA;padding:1.5rem;border-radius:12px;border:1px solid #E8EAED;">
                        <p><b>Institution:</b> {req['professor_institution']}</p>
                        <p><b>Topic:</b> {req['research_topic'][:150]}...</p>
                        <p><b>Submitted:</b> {req['date']}</p>
                        <p><b>Status:</b> <span style="color:#1A73E8;font-weight:600;">{req['status']}</span></p>
                    </div>
                    """, unsafe_allow_html=True)

    elif current_page == "💬 Forum":
        st.markdown("### 💬 Research Discussion Forum")
        st.caption("Share ideas, discuss research, and connect with fellow researchers.")
        with st.expander("➕ Create New Post", expanded=False):
            with st.form("new_post"):
                title = st.text_input("Title", placeholder="Enter your post title...")
                content = st.text_area("Content", height=150, placeholder="Share your research ideas...")
                tags = st.text_input("Tags (comma separated)", placeholder="e.g., optimization, machine learning")
                submitted = st.form_submit_button("📝 Publish Post", use_container_width=True)
                if submitted and title and content:
                    create_forum_post(title, content, user_display_name, tags)
                    if len(st.session_state.forum_posts) == 1:
                        add_badge(st.session_state.current_user, "💬 First Post")
                    st.success("✅ Post published successfully!")
                    st.rerun()
                elif submitted:
                    st.error("❌ Please enter both title and content.")
        if st.session_state.forum_posts:
            st.markdown(f"### 📝 Recent Posts ({len(st.session_state.forum_posts)} total)")
            for post in reversed(st.session_state.forum_posts):
                with st.expander(f"📌 {post['title']} - by {post['author']}", expanded=False):
                    comments = json.loads(post.get("comments", "[]"))
                    st.markdown(f"""
                    <div class="forum-post">
                        <div class="post-header"><span class="post-title">{post['title']}</span><span class="post-meta">🕐 {post['date']} · ❤️ {post['likes']} likes</span></div>
                        <div style="padding:0.5rem 0;border-top:1px solid #E8EAED;border-bottom:1px solid #E8EAED;">{post['content']}</div>
                        <div class="post-tags">{''.join(f'<span class="tag">#{tag}</span>' for tag in json.loads(post.get("tags", "[]")))}</div>
                    </div>
                    """, unsafe_allow_html=True)
                    col1, col2 = st.columns([1, 5])
                    with col1:
                        if st.button(f"❤️ {post['likes']}", key=f"like_{post['id']}"):
                            like_post(post['id'])
                            st.rerun()
                    st.markdown("---")
                    st.markdown("#### 💬 Comments")
                    if comments:
                        for comment in comments:
                            st.markdown(f"""
                            <div style="background:#F8F9FA;padding:0.75rem;border-radius:8px;margin-bottom:0.5rem;border-left:3px solid #1A73E8;">
                                <strong>{comment['author']}</strong> <span style="color:#5F6368;font-size:0.8rem;">({comment['date']})</span>
                                <p style="margin:0.2rem 0 0 0;">{comment['content']}</p>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.caption("No comments yet. Be the first to comment!")
                    with st.form(f"comment_form_{post['id']}"):
                        comment_content = st.text_area("Add a comment", key=f"comment_{post['id']}", placeholder="Share your thoughts...")
                        submitted = st.form_submit_button("💬 Submit Comment", use_container_width=True)
                        if submitted and comment_content:
                            add_comment_to_post(post['id'], user_display_name, comment_content)
                            st.success("Comment added!")
                            st.rerun()
                        elif submitted:
                            st.error("❌ Please enter a comment.")
        else:
            st.info("No posts yet. Start a discussion! 🚀")

    elif current_page == "📊 Analytics":
        st.markdown("### 📊 Research Impact Dashboard")
        pub_data = []
        for _, prof in academicians_df.iterrows():
            pub_data.append({
                'name': prof['name'].split()[1] if len(prof['name'].split()) > 1 else prof['name'],
                'publications': len(prof.get('publications', [])),
                'citations': prof.get('total_citations', 0),
                'h_index': prof.get('h_index', 0),
                'trust_score': prof.get('trust_score', 0)
            })
        df_pub = pd.DataFrame(pub_data)
        if not df_pub.empty:
            col1, col2 = st.columns(2)
            with col1:
                fig = px.bar(df_pub, x='name', y='publications', title='Publications by Researcher', color='publications', color_continuous_scale='Greens', text='publications')
                fig.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
            with col2:
                fig2 = px.scatter(df_pub, x='publications', y='citations', size='h_index', text='name', title='Publications vs Citations', color='trust_score', color_continuous_scale='Viridis')
                fig2.update_layout(height=400)
                st.plotly_chart(fig2, use_container_width=True)
            col3, col4 = st.columns(2)
            with col3:
                fig3 = px.bar(df_pub, x='name', y='h_index', title='h-index by Researcher', color='h_index', color_continuous_scale='Blues', text='h_index')
                fig3.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig3, use_container_width=True)
            with col4:
                fig4 = px.bar(df_pub, x='name', y='trust_score', title='Trust Score by Researcher', color='trust_score', color_continuous_scale='Oranges', text='trust_score')
                fig4.update_layout(height=400, showlegend=False)
                st.plotly_chart(fig4, use_container_width=True)
            st.markdown("#### 📊 Summary Statistics")
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Total Publications", df_pub['publications'].sum())
            c2.metric("Total Citations", df_pub['citations'].sum())
            c3.metric("Average h-index", f"{df_pub['h_index'].mean():.1f}")
            c4.metric("Average Trust Score", f"{df_pub['trust_score'].mean():.1f}%")

    elif current_page == "💬 Chat":
        show_chat()
    elif current_page == "📅 Events":
        show_event_calendar()
    elif current_page == "💰 Grants":
        show_grants()
    elif current_page == "👥 Mentorship":
        st.markdown("### 👥 Mentorship Program")
        with st.expander("➕ Become a Mentor", expanded=False):
            with st.form("mentor_form"):
                expertise = st.text_input("Your Expertise / Research Areas")
                availability = st.selectbox("Availability", ["Available", "Limited", "Not Available"])
                if st.form_submit_button("Register as Mentor"):
                    supabase_admin = get_supabase_admin()
                    new_mentor = {
                        "mentor": st.session_state.current_user,
                        "expertise": expertise,
                        "availability": availability,
                        "mentees": "[]"
                    }
                    try:
                        res = supabase_admin.table("mentorships").insert(new_mentor).execute()
                        if res.data:
                            st.session_state.mentorships.append(res.data[0])
                            add_notification(f"👨‍🏫 {user_display_name} registered as a mentor!", "success")
                            add_points(st.session_state.current_user, 10, "Mentor registration")
                            st.success("You are now a mentor!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error registering: {e}")
        if st.session_state.mentorships:
            for m in st.session_state.mentorships:
                st.markdown(f"<div style='background:#F8F9FA;padding:1rem;border-radius:12px;margin-bottom:0.5rem;'><strong>{m['mentor']}</strong> · Expertise: {m['expertise']} · {m['availability']}</div>", unsafe_allow_html=True)
    elif current_page == "📄 Papers":
        st.markdown("### 📄 Research Paper Sharing")
        with st.expander("📤 Upload a Paper", expanded=False):
            with st.form("paper_form"):
                title = st.text_input("Paper Title")
                authors = st.text_input("Authors (comma separated)")
                abstract = st.text_area("Abstract / Description")
                if st.form_submit_button("Upload Paper"):
                    supabase_admin = get_supabase_admin()
                    new_paper = {
                        "title": title,
                        "authors": authors,
                        "abstract": abstract,
                        "uploaded_by": st.session_state.current_user,
                        "date": datetime.now().strftime("%Y-%m-%d")
                    }
                    try:
                        res = supabase_admin.table("papers").insert(new_paper).execute()
                        if res.data:
                            st.session_state.papers.insert(0, res.data[0])
                            add_points(st.session_state.current_user, 10, "Paper upload")
                            st.success("Paper uploaded!")
                            st.rerun()
                    except Exception as e:
                        st.error(f"Error uploading: {e}")
        for p in reversed(st.session_state.papers):
            st.markdown(f"<div style='background:#FFFFFF;border:1px solid #E8EAED;border-radius:12px;padding:1rem;margin-bottom:0.5rem;'><strong>{p['title']}</strong><br>Authors: {p['authors']}<br>{p['abstract'][:200]}...<br><span style='color:#5F6368;'>Uploaded by {p['uploaded_by']} on {p['date']}</span></div>", unsafe_allow_html=True)
    elif current_page == "📝 Feedback":
        st.markdown("### 📝 Feedback & Suggestions")
        with st.form("feedback_form"):
            rating = st.slider("How would you rate the platform?", 1, 5, 5)
            comment = st.text_area("Your feedback (optional)", placeholder="Tell us what you think...")
            if st.form_submit_button("Submit Feedback"):
                supabase_admin = get_supabase_admin()
                new_feedback = {
                    "username": st.session_state.current_user,
                    "rating": rating,
                    "comment": comment,
                    "date": datetime.now().strftime("%Y-%m-%d %H:%M")
                }
                try:
                    res = supabase_admin.table("feedback").insert(new_feedback).execute()
                    if res.data:
                        st.session_state.feedback.insert(0, res.data[0])
                        add_points(st.session_state.current_user, 5, "Feedback submitted")
                        st.success("Thank you for your feedback!")
                        st.rerun()
                except Exception as e:
                    st.error(f"Error submitting feedback: {e}")
        st.markdown("### Recent Feedback")
        for fb in reversed(st.session_state.feedback[-5:]):
            stars = "⭐" * fb['rating']
            st.markdown(f"<div class='feedback-item'><div class='feedback-header'><strong>{fb['username']}</strong><span class='feedback-rating'>{stars}</span></div><p>{fb['comment']}</p><span style='color:#5F6368;font-size:0.8rem;'>{fb['date']}</span></div>", unsafe_allow_html=True)
    elif current_page == "👤 Profile":
        st.markdown("### 👤 My Profile")
        profile = st.session_state.user_profiles.get(st.session_state.current_user, {})
        st.markdown(f"""
        <div style="background:#F8F9FA;padding:2rem;border-radius:16px;border:1px solid #E8EAED;">
            <div style="font-size:4rem;text-align:center;">👤</div>
            <h3 style="text-align:center;">{profile.get('name', user_display_name)}</h3>
            <p style="text-align:center;color:#5F6368;">{st.session_state.current_user}</p>
            <p><strong>Institution:</strong> {profile.get('institution', 'Not set')}</p>
            <p><strong>Department:</strong> {profile.get('department', 'Not set')}</p>
            <p><strong>Research Interests:</strong> {', '.join(json.loads(profile.get('interests', '[]')))}</p>
            <p><strong>Looking for:</strong> {profile.get('collab_type', 'Not set')}</p>
            <p><strong>Points:</strong> ⭐ {st.session_state.user_points.get(st.session_state.current_user, 0)}</p>
            <div><strong>Badges:</strong> {', '.join(st.session_state.user_badges.get(st.session_state.current_user, [])) or 'None yet'}</div>
        </div>
        """, unsafe_allow_html=True)
    elif "📨 Notifications" in current_page:
        show_notification_center()

if __name__ == "__main__":
    main()
