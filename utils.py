"""
Shared utility functions for all pages
Include this in each page to show data freshness
"""

import streamlit as st
import sqlite3
from datetime import datetime

def show_data_freshness_warning(db_path="scan_results.db"):
    """
    Show data freshness indicator in sidebar
    
    Usage in any page:
        from utils import show_data_freshness_warning
        show_data_freshness_warning()
    """
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM scan_results")
        last_update = cursor.fetchone()[0]
        conn.close()
        
        if last_update:
            last_update_date = datetime.strptime(last_update, '%Y-%m-%d')
            days_ago = (datetime.now() - last_update_date).days
            
            st.sidebar.divider()
            st.sidebar.subheader("📊 Data Status")
            
            if days_ago == 0:
                st.sidebar.success(f"✅ Updated today")
                st.sidebar.caption(f"Last scan: {last_update}")
            elif days_ago == 1:
                st.sidebar.warning(f"⚠️ Updated yesterday")
                st.sidebar.caption(f"Last scan: {last_update}")
                st.sidebar.info("Run `python run_scan.py` to update")
            else:
                st.sidebar.error(f"🔴 {days_ago} days old")
                st.sidebar.caption(f"Last scan: {last_update}")
                st.sidebar.warning("**Prices outdated!**\n\nRun: `python run_scan.py`")
                
                if st.sidebar.button("📋 How to Update"):
                    st.sidebar.info("""
**Quick Update:**
                    
```bash
python run_scan.py
```

Then refresh this page!

See HOW_TO_UPDATE_PRICES.md for details.
                    """)
        else:
            st.sidebar.warning("No data found")
            
    except Exception as e:
        st.sidebar.error(f"Cannot check data status: {str(e)}")


def get_last_update_date(db_path="scan_results.db"):
    """
    Get last update date
    Returns: tuple (date_string, days_ago)
    """
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM scan_results")
        last_update = cursor.fetchone()[0]
        conn.close()
        
        if last_update:
            last_update_date = datetime.strptime(last_update, '%Y-%m-%d')
            days_ago = (datetime.now() - last_update_date).days
            return (last_update, days_ago)
        else:
            return (None, None)
    except:
        return (None, None)


def show_update_reminder_banner():
    """
    Show banner at top of page if data is old
    
    Usage:
        from utils import show_update_reminder_banner
        show_update_reminder_banner()
    """
    
    last_update, days_ago = get_last_update_date()
    
    if days_ago and days_ago >= 1:
        st.warning(f"""
⚠️ **Stock prices are {days_ago} day(s) old** (Last scan: {last_update})

Portfolio values may not reflect current market prices.

**To update:** Run `python run_scan.py` then refresh this page.
        """)


# Example usage in any page:
if __name__ == "__main__":
    st.title("Example Page")
    show_data_freshness_warning()
    show_update_reminder_banner()
    st.write("Your page content here...")
