"""
Automated Alert Scheduler
Runs in background and sends alerts at scheduled times
"""

import schedule
import time
from datetime import datetime
from alert_system import PortfolioAlertSystem
import subprocess
import sys

class AlertScheduler:
    """
    Background service that:
    - Checks portfolios periodically
    - Sends daily digest at specified time
    - Sends weekly digest on specified day
    """
    
    def __init__(self):
        self.alert_system = PortfolioAlertSystem()
        print("🤖 Alert Scheduler Started!")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 50)
        self._show_config()
    
    def _show_config(self):
        """Show current configuration"""
        config = self.alert_system.alert_config
        
        print("\n📊 Configuration:")
        print(f"  Gain Alert: ≥{config['thresholds']['gain_alert']}%")
        print(f"  Loss Alert: ≤{config['thresholds']['loss_alert']}%")
        print(f"  Daily Digest: {'✅ Enabled' if config['thresholds']['daily_digest'] else '❌ Disabled'}")
        print(f"  Weekly Digest: {'✅ Enabled' if config['thresholds']['weekly_digest'] else '❌ Disabled'}")
        
        print("\n📧 Email Alerts:")
        print(f"  Status: {'✅ Enabled' if config['email_enabled'] else '❌ Disabled'}")
        if config['email_enabled']:
            print(f"  From: {config['email_from']}")
            print(f"  To: {config['email_to']}")
            if config.get('email_cc'):
                print(f"  CC: {config['email_cc']}")
        
        if not config['email_enabled']:
            print("\n⚠️  WARNING: Email alerts not enabled!")
            print("   Configure in: streamlit run dashboard.py → Alert Settings")
        
        print("-" * 50)
    
    def update_prices_and_check(self):
        """Update stock prices then check for alerts"""
        print(f"\n🔄 [{datetime.now().strftime('%H:%M:%S')}] Updating prices...")
        
        try:
            # Run scanner to update prices
            result = subprocess.run(
                [sys.executable, 'run_scan.py'],
                capture_output=True,
                timeout=1800  # 30 minute timeout
            )
            
            if result.returncode == 0:
                print("✅ Prices updated successfully")
                
                # Now check for alerts
                print("🔍 Checking portfolios for alerts...")
                alerts = self.alert_system.check_all_portfolios()
                
                if alerts:
                    print(f"📬 Sent {len(alerts)} alerts")
                    for alert in alerts:
                        print(f"  - {alert['type']}: {alert['message'][:50]}...")
                else:
                    print("✅ No alerts (all portfolios within thresholds)")
            else:
                print(f"❌ Price update failed: {result.stderr.decode()}")
                
        except subprocess.TimeoutExpired:
            print("⚠️ Price update timed out (>30 min)")
        except Exception as e:
            print(f"❌ Error: {e}")
    
    def send_daily_digest(self):
        """Send daily portfolio summary"""
        print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] Sending daily digest...")
        
        try:
            self.alert_system.send_daily_digest()
            print("✅ Daily digest sent")
        except Exception as e:
            print(f"❌ Failed to send daily digest: {e}")
    
    def send_weekly_digest(self):
        """Send weekly portfolio summary"""
        print(f"\n📊 [{datetime.now().strftime('%H:%M:%S')}] Sending weekly digest...")
        
        try:
            self.alert_system.send_weekly_digest()
            print("✅ Weekly digest sent")
        except Exception as e:
            print(f"❌ Failed to send weekly digest: {e}")
    
    def schedule_jobs(self):
        """Set up all scheduled jobs"""
        config = self.alert_system.alert_config
        
        # Real-time checks (every 4 hours during market hours)
        schedule.every().day.at("10:00").do(self.update_prices_and_check)
        schedule.every().day.at("14:00").do(self.update_prices_and_check)
        schedule.every().day.at("16:00").do(self.update_prices_and_check)
        
        print("\n⏰ Scheduled Jobs:")
        print("  🔄 Price check: 10:00 AM, 2:00 PM, 4:00 PM")
        
        # Daily digest (if enabled)
        if config['thresholds']['daily_digest']:
            schedule.every().day.at("18:00").do(self.send_daily_digest)
            print("  📊 Daily digest: 6:00 PM")
        
        # Weekly digest (if enabled)
        if config['thresholds']['weekly_digest']:
            schedule.every().sunday.at("09:00").do(self.send_weekly_digest)
            print("  📊 Weekly digest: Sunday 9:00 AM")
        
        print("\n✅ Scheduler ready! Press Ctrl+C to stop.\n")
    
    def run(self):
        """Start the scheduler"""
        self.schedule_jobs()
        
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute


# Run the scheduler
if __name__ == "__main__":
    try:
        scheduler = AlertScheduler()
        scheduler.run()
    except KeyboardInterrupt:
        print("\n\n👋 Scheduler stopped by user")
    except Exception as e:
        print(f"\n❌ Scheduler error: {e}")
        print("Check your configuration and try again")
