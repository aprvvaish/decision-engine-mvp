"""
Alert Configuration Page - Email Only
Configure portfolio gain/loss notifications via email
"""

import streamlit as st
import json
from alert_system import PortfolioAlertSystem
from datetime import datetime

st.set_page_config(page_title="Alert Settings", page_icon="🔔", layout="wide")

st.title("🔔 Portfolio Alerts & Notifications")
st.markdown("**Get email notifications when your portfolios hit gain/loss thresholds**")

st.divider()

# Initialize alert system
alert_system = PortfolioAlertSystem()
config = alert_system.alert_config

# Tabs for different sections
tab1, tab2, tab3 = st.tabs([
    "⚙️ Configuration",
    "📧 Email Setup",
    "🧪 Test & Preview"
])

# ============================================================================
# TAB 1: CONFIGURATION
# ============================================================================

with tab1:
    st.header("Alert Configuration")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📊 Thresholds")
        
        gain_threshold = st.slider(
            "Gain Alert (%)",
            min_value=1.0,
            max_value=20.0,
            value=config['thresholds'].get('gain_alert', 5.0),
            step=0.5,
            help="Get notified when portfolio gains exceed this %",
            key="gain_threshold_slider"
        )
        
        loss_threshold = st.slider(
            "Loss Alert (%)",
            min_value=-20.0,
            max_value=-1.0,
            value=config['thresholds'].get('loss_alert', -3.0),
            step=0.5,
            help="Get notified when portfolio loses more than this %",
            key="loss_threshold_slider"
        )
        
        st.info(f"""
**Current Settings:**
- Alert on gains ≥ **{gain_threshold}%**
- Alert on losses ≤ **{loss_threshold}%**
        """)
    
    with col2:
        st.subheader("📅 Digest Reports")
        
        daily_digest = st.checkbox(
            "Daily Summary",
            value=config['thresholds'].get('daily_digest', True),
            help="Receive daily portfolio summary every evening",
            key="daily_digest_checkbox"
        )
        
        if daily_digest:
            st.caption("📧 Sent at 6:00 PM (after market close)")
        
        weekly_digest = st.checkbox(
            "Weekly Summary",
            value=config['thresholds'].get('weekly_digest', True),
            help="Receive weekly portfolio summary every Sunday",
            key="weekly_digest_checkbox"
        )
        
        if weekly_digest:
            st.caption("📧 Sent on Sunday at 9:00 AM")
    
    if st.button("💾 Save Configuration", type="primary"):
        config['thresholds']['gain_alert'] = gain_threshold
        config['thresholds']['loss_alert'] = loss_threshold
        config['thresholds']['daily_digest'] = daily_digest
        config['thresholds']['weekly_digest'] = weekly_digest
        
        alert_system.save_alert_config(config)
        st.success("✅ Configuration saved!")

# ============================================================================
# TAB 2: EMAIL SETUP
# ============================================================================

with tab2:
    st.header("📧 Email Alerts Setup")
    
    st.info("""
**Email alerts using Gmail (FREE)**
- ✅ Works with any Gmail account
- ✅ Professional HTML reports
- ✅ Can forward to multiple people
- ✅ Keeps history in inbox
- ✅ Works everywhere
    """)
    
    with st.expander("🔐 Step 1: Enable Gmail App Password (3 minutes)", expanded=True):
        st.markdown("""
**You need an "App Password" (not your regular Gmail password):**

1. Go to: [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
2. Sign in to your Gmail account
3. Select app: **Mail**
4. Select device: **Other (Custom name)**
5. Name it: `Portfolio Alerts`
6. Click **Generate**
7. **Copy the 16-character password** (like: `abcd efgh ijkl mnop`)

**Note:** If you don't see "App passwords" option:
- You need to enable **2-Step Verification** first
- Go to: [https://myaccount.google.com/security](https://myaccount.google.com/security)
- Enable 2-Step Verification
- Then App passwords will appear

**Why App Password?**
- More secure than regular password
- Can be revoked anytime
- Dedicated for this app only
        """)
    
    st.divider()
    
    with st.expander("⚙️ Step 2: Configure Email Settings", expanded=True):
        email_enabled = st.checkbox(
            "Enable Email Alerts",
            value=config.get('email_enabled', False),
            help="Turn on email notifications"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            email_from = st.text_input(
                "Your Gmail Address",
                value=config.get('email_from', ''),
                placeholder="your.email@gmail.com",
                help="Gmail account to send from"
            )
            
            email_password = st.text_input(
                "Gmail App Password",
                value=config.get('email_password', ''),
                type="password",
                placeholder="abcd efgh ijkl mnop",
                help="16-character app password from Google (NOT your regular password)"
            )
        
        with col2:
            email_to = st.text_input(
                "Send Alerts To",
                value=config.get('email_to', ''),
                placeholder="your.email@gmail.com",
                help="Email address to receive alerts (can be same as 'From')"
            )
            
            email_cc = st.text_input(
                "CC (Optional)",
                value=config.get('email_cc', ''),
                placeholder="spouse@gmail.com, advisor@gmail.com",
                help="Additional recipients (comma-separated)"
            )
        
        if st.button("💾 Save Email Settings", type="primary", key="save_email"):
            config['email_enabled'] = email_enabled
            config['email_from'] = email_from
            config['email_password'] = email_password
            config['email_to'] = email_to
            config['email_cc'] = email_cc
            
            alert_system.save_alert_config(config)
            st.success("✅ Email configured!")
            
            if email_enabled and email_from and email_password and email_to:
                st.info("👉 Go to 'Test & Preview' tab to send a test email!")
            elif email_enabled:
                st.warning("⚠️ Please fill in all required fields (Gmail address, App Password, and recipient)")

# ============================================================================
# TAB 3: TEST & PREVIEW
# ============================================================================

with tab3:
    st.header("🧪 Test & Preview Alerts")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📨 Send Test Email")
        
        if config.get('email_enabled'):
            if st.button("📧 Send Test Email", type="primary", use_container_width=True):
                with st.spinner("Sending test email..."):
                    message = """
                    <div class="alert-box">
                        <h3>🧪 Test Alert</h3>
                        <p>This is a test email from your Portfolio Alert System!</p>
                        <p>If you received this, email alerts are working correctly. ✅</p>
                        <p><strong>You'll receive emails when:</strong></p>
                        <ul>
                            <li>Portfolio gains/losses exceed your thresholds</li>
                            <li>Individual stocks move ±10%</li>
                            <li>Daily summary (if enabled)</li>
                            <li>Weekly summary (if enabled)</li>
                        </ul>
                        <p style="color: #667eea; font-weight: bold;">
                            Your alerts are properly configured! 🎉
                        </p>
                    </div>
                    """
                    
                    success = alert_system.send_email_alert(
                        "✅ Test Alert - Portfolio Notification System",
                        message
                    )
                    
                    if success:
                        st.success("✅ Test email sent successfully! Check your inbox.")
                        st.info("💡 If you don't see it, check your spam/junk folder")
                    else:
                        st.error("""
❌ Failed to send email. Common issues:

1. **Wrong App Password** - Make sure you're using the 16-character App Password (NOT your regular Gmail password)
2. **2-Step Verification not enabled** - Enable it first in Google Account settings
3. **Typo in email address** - Double-check your Gmail address
4. **App Password expired** - Generate a new one

**How to fix:**
- Go to [https://myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords)
- Delete old password (if exists)
- Generate new App Password
- Copy it exactly and paste in Email Setup tab
                        """)
        else:
            st.info("⚠️ Enable Email in the 'Email Setup' tab first")
            if st.button("Go to Email Setup →"):
                st.rerun()
    
    with col2:
        st.subheader("📊 Preview Digests")
        
        if st.button("👀 Preview Daily Digest", use_container_width=True):
            with st.spinner("Generating preview..."):
                try:
                    digest = alert_system.generate_daily_digest()
                    st.markdown("**Daily digest will look like this:**")
                    st.markdown(digest, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error generating preview: {e}")
                    st.info("Make sure you have created at least one portfolio and run a scan")
        
        if st.button("👀 Preview Weekly Digest", use_container_width=True):
            with st.spinner("Generating preview..."):
                try:
                    digest = alert_system.generate_weekly_digest()
                    st.markdown("**Weekly digest will look like this:**")
                    st.markdown(digest, unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Error generating preview: {e}")
                    st.info("Make sure you have created at least one portfolio and run a scan")
    
    st.divider()
    
    st.subheader("🔍 Check Current Portfolios")
    
    if st.button("🔔 Check for Alerts Now", use_container_width=True):
        if not config.get('email_enabled'):
            st.warning("⚠️ Email alerts are not enabled. Enable them in the 'Email Setup' tab to receive notifications.")
        else:
            with st.spinner("Checking portfolios..."):
                try:
                    alerts = alert_system.check_all_portfolios()
                    
                    if alerts:
                        st.success(f"📬 Found {len(alerts)} alerts and sent emails!")
                        
                        for alert in alerts:
                            alert_type = alert['type']
                            
                            if 'gain' in alert_type:
                                st.success(f"🟢 {alert['message']}")
                            else:
                                st.warning(f"🔴 {alert['message']}")
                    else:
                        st.info("✅ No alerts at this time. All portfolios within thresholds.")
                except Exception as e:
                    st.error(f"Error checking portfolios: {e}")

# Footer
st.divider()

st.markdown("### 📚 Quick Setup Guide")

col1, col2 = st.columns(2)

with col1:
    st.markdown("""
**5-Minute Setup:**
1. ✅ Get Gmail App Password (3 min)
2. ✅ Enter credentials in Email Setup tab
3. ✅ Set thresholds (Configuration tab)
4. ✅ Send test email
5. ✅ Done!
    """)

with col2:
    st.markdown("""
**You'll Receive Emails For:**
- 🎉 Portfolio gains ≥5% (customizable)
- ⚠️ Portfolio losses ≥-3% (customizable)
- 🚀 Individual stock moves ±10%
- 📊 Daily summary at 6 PM
- 📊 Weekly summary on Sunday
    """)

st.caption("💡 **Pro Tip:** Check spam folder after sending test email - you may need to mark as 'Not Spam'")


