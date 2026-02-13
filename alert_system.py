"""
Portfolio Alert System - Email Only
Sends notifications for portfolio gain/loss via email
"""

import sqlite3
import pandas as pd
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

class PortfolioAlertSystem:
    """
    Email-based alert system for portfolio notifications
    
    Features:
    - Email alerts for gain/loss
    - Daily digest
    - Weekly summary
    """
    
    def __init__(self, db_path="scan_results.db"):
        self.db_path = db_path
        self.alert_config = self._load_alert_config()
    
    def _load_alert_config(self) -> Dict:
        """Load alert configuration from file"""
        try:
            with open('alert_config.json', 'r') as f:
                return json.load(f)
        except:
            return {
                'email_enabled': False,
                'email_from': '',
                'email_password': '',
                'email_to': '',
                'email_cc': '',  # Optional CC recipients
                'thresholds': {
                    'gain_alert': 5.0,      # Alert on 5%+ gain
                    'loss_alert': -3.0,     # Alert on -3% loss
                    'daily_digest': True,   # Send daily summary
                    'weekly_digest': True   # Send weekly summary
                }
            }
    
    def save_alert_config(self, config: Dict):
        """Save alert configuration"""
        with open('alert_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        self.alert_config = config
    
    def check_portfolio_alerts(self, portfolio_name: str) -> List[Dict]:
        """
        Check if portfolio has crossed alert thresholds
        
        Returns list of alerts to send
        """
        from portfolio_manager import calculate_portfolio_performance, PortfolioManager
        
        pm = PortfolioManager(self.db_path)
        
        # Get latest prices
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        # Calculate current performance
        performance = calculate_portfolio_performance(portfolio_name, latest_prices)
        
        if not performance:
            return []
        
        alerts = []
        thresholds = self.alert_config['thresholds']
        total_gain_pct = performance['total_gain_pct']
        
        # Check overall portfolio threshold
        if total_gain_pct >= thresholds['gain_alert']:
            alerts.append({
                'type': 'portfolio_gain',
                'portfolio': portfolio_name,
                'gain_pct': total_gain_pct,
                'gain_amount': performance['total_gain'],
                'current_value': performance['total_value'],
                'message': f"🎉 Portfolio '{portfolio_name}' is up {total_gain_pct:.2f}%! (+₹{performance['total_gain']:,.0f})"
            })
        
        elif total_gain_pct <= thresholds['loss_alert']:
            alerts.append({
                'type': 'portfolio_loss',
                'portfolio': portfolio_name,
                'loss_pct': total_gain_pct,
                'loss_amount': performance['total_gain'],
                'current_value': performance['total_value'],
                'message': f"⚠️ Portfolio '{portfolio_name}' is down {abs(total_gain_pct):.2f}% (-₹{abs(performance['total_gain']):,.0f})"
            })
        
        # Check individual position thresholds
        for position in performance['positions']:
            pos_gain_pct = position['gain_loss_pct']
            
            # Big gain alert
            if pos_gain_pct >= 10.0:
                alerts.append({
                    'type': 'position_gain',
                    'portfolio': portfolio_name,
                    'stock': position['ticker'],
                    'gain_pct': pos_gain_pct,
                    'gain_amount': position['gain_loss'],
                    'message': f"🚀 {position['ticker']} in '{portfolio_name}' is up {pos_gain_pct:.2f}%! Consider taking profits."
                })
            
            # Big loss alert
            elif pos_gain_pct <= -10.0:
                alerts.append({
                    'type': 'position_loss',
                    'portfolio': portfolio_name,
                    'stock': position['ticker'],
                    'loss_pct': pos_gain_pct,
                    'loss_amount': position['gain_loss'],
                    'message': f"📉 {position['ticker']} in '{portfolio_name}' is down {abs(pos_gain_pct):.2f}%. Review position."
                })
        
        return alerts
    
    def send_email_alert(self, subject: str, message: str, is_html: bool = True) -> bool:
        """Send alert via Email"""
        if not self.alert_config['email_enabled']:
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.alert_config['email_from']
            msg['To'] = self.alert_config['email_to']
            
            # Add CC if provided
            if self.alert_config.get('email_cc'):
                msg['Cc'] = self.alert_config['email_cc']
            
            # Create HTML version
            if is_html:
                html = f"""
                <html>
                  <head>
                    <style>
                      body {{
                        font-family: 'Segoe UI', Arial, sans-serif;
                        line-height: 1.6;
                        color: #333;
                      }}
                      .header {{
                        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                        color: white;
                        padding: 20px;
                        border-radius: 10px 10px 0 0;
                        margin-bottom: 20px;
                      }}
                      .content {{
                        background: #f7fafc;
                        padding: 30px;
                        border-radius: 0 0 10px 10px;
                      }}
                      .alert-box {{
                        background: white;
                        padding: 20px;
                        border-radius: 8px;
                        border-left: 4px solid #667eea;
                        margin: 20px 0;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                      }}
                      .gain {{
                        border-left-color: #48bb78;
                      }}
                      .loss {{
                        border-left-color: #f56565;
                      }}
                      .footer {{
                        color: #666;
                        font-size: 12px;
                        margin-top: 30px;
                        padding-top: 20px;
                        border-top: 1px solid #ddd;
                      }}
                      h2 {{
                        margin: 0 0 10px 0;
                      }}
                      .metric {{
                        font-size: 24px;
                        font-weight: bold;
                        color: #667eea;
                      }}
                      .gain-metric {{
                        color: #48bb78;
                      }}
                      .loss-metric {{
                        color: #f56565;
                      }}
                    </style>
                  </head>
                  <body>
                    <div class="header">
                      <h2>📊 Portfolio Alert</h2>
                    </div>
                    <div class="content">
                      {message}
                    </div>
                    <div class="footer">
                      <p>
                        Sent by Stock Research Platform<br>
                        {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                      </p>
                      <p style="font-size: 11px; color: #999;">
                        To manage alert settings, open your dashboard and go to Alert Settings.
                      </p>
                    </div>
                  </body>
                </html>
                """
                msg.attach(MIMEText(html, 'html'))
            else:
                # Plain text version
                msg.attach(MIMEText(message, 'plain'))
            
            # Send via Gmail SMTP
            recipients = [self.alert_config['email_to']]
            if self.alert_config.get('email_cc'):
                recipients.extend(self.alert_config['email_cc'].split(','))
            
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(
                    self.alert_config['email_from'],
                    self.alert_config['email_password']
                )
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False
    
    def generate_daily_digest(self) -> str:
        """Generate daily portfolio summary (HTML)"""
        from portfolio_manager import PortfolioManager, calculate_portfolio_performance
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        if portfolios.empty:
            return "<p>No portfolios to report.</p>"
        
        # Get latest prices
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        
        # Get scan date
        cursor = conn.cursor()
        cursor.execute("SELECT MAX(date) FROM scan_results")
        scan_date = cursor.fetchone()[0]
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        # Build digest HTML
        html = f"""
        <h3>📊 Daily Portfolio Summary</h3>
        <p style="color: #666;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
        <p style="font-size: 12px; color: #999;">Data as of: {scan_date}</p>
        """
        
        total_invested = 0
        total_current = 0
        
        for _, portfolio in portfolios.iterrows():
            performance = calculate_portfolio_performance(
                portfolio['name'],
                latest_prices
            )
            
            if performance:
                total_invested += performance['invested_value']
                total_current += performance['current_value']
                
                gain_pct = performance['total_gain_pct']
                is_gain = gain_pct >= 0
                
                html += f"""
                <div class="alert-box {'gain' if is_gain else 'loss'}">
                    <h4 style="margin: 0 0 10px 0;">{'🟢' if is_gain else '🔴'} {portfolio['name']}</h4>
                    <p style="margin: 5px 0;">
                        <strong>Current Value:</strong> <span class="metric">₹{performance['total_value']:,.0f}</span>
                    </p>
                    <p style="margin: 5px 0;">
                        <strong>Gain/Loss:</strong> 
                        <span class="{'gain-metric' if is_gain else 'loss-metric'}">
                            {gain_pct:+.2f}% (₹{performance['total_gain']:+,.0f})
                        </span>
                    </p>
                </div>
                """
        
        # Overall summary
        total_gain = total_current - total_invested
        total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0
        is_total_gain = total_gain >= 0
        
        html += f"""
        <div class="alert-box" style="border-left-color: #667eea; background: #f0f4ff;">
            <h3 style="margin: 0 0 15px 0; color: #667eea;">📈 Overall Summary</h3>
            <p style="margin: 8px 0;">
                <strong>Total Portfolio Value:</strong> 
                <span class="metric" style="font-size: 28px;">₹{total_current:,.0f}</span>
            </p>
            <p style="margin: 8px 0;">
                <strong>Total Gain/Loss:</strong> 
                <span class="{'gain-metric' if is_total_gain else 'loss-metric'}" style="font-size: 20px;">
                    {total_gain_pct:+.2f}% (₹{total_gain:+,.0f})
                </span>
            </p>
        </div>
        """
        
        return html
    
    def generate_weekly_digest(self) -> str:
        """Generate weekly portfolio summary with insights (HTML)"""
        daily_html = self.generate_daily_digest()
        
        # Replace title
        weekly_html = daily_html.replace("Daily Portfolio Summary", "Weekly Portfolio Summary")
        
        # Add weekly insights
        from portfolio_manager import PortfolioManager, calculate_portfolio_performance
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        best_portfolio = None
        worst_portfolio = None
        best_gain = float('-inf')
        worst_gain = float('inf')
        
        for _, portfolio in portfolios.iterrows():
            performance = calculate_portfolio_performance(
                portfolio['name'],
                latest_prices
            )
            
            if performance:
                gain_pct = performance['total_gain_pct']
                
                if gain_pct > best_gain:
                    best_gain = gain_pct
                    best_portfolio = portfolio['name']
                
                if gain_pct < worst_gain:
                    worst_gain = gain_pct
                    worst_portfolio = portfolio['name']
        
        insights = """
        <div class="alert-box" style="border-left-color: #ed8936;">
            <h4 style="margin: 0 0 10px 0; color: #ed8936;">📈 This Week's Highlights</h4>
        """
        
        if best_portfolio:
            insights += f"<p>🏆 <strong>Best Performer:</strong> {best_portfolio} ({best_gain:+.2f}%)</p>"
        
        if worst_portfolio and worst_portfolio != best_portfolio:
            insights += f"<p>📉 <strong>Needs Attention:</strong> {worst_portfolio} ({worst_gain:+.2f}%)</p>"
        
        insights += "</div>"
        
        # Insert insights before overall summary
        weekly_html = weekly_html.replace(
            '<div class="alert-box" style="border-left-color: #667eea;',
            insights + '<div class="alert-box" style="border-left-color: #667eea;'
        )
        
        return weekly_html
    
    def send_alert(self, alert: Dict):
        """Send alert via email"""
        message = alert['message']
        alert_type = alert['type'].replace('_', ' ').title()
        
        # Create HTML alert
        is_gain = 'gain' in alert['type']
        
        html_message = f"""
        <div class="alert-box {'gain' if is_gain else 'loss'}">
            <h3 style="margin: 0 0 15px 0;">{'🎉' if is_gain else '⚠️'} {alert_type}</h3>
            <p style="font-size: 18px; margin: 10px 0;">{message}</p>
        </div>
        """
        
        if 'current_value' in alert:
            html_message += f"""
            <div class="alert-box">
                <p><strong>Current Value:</strong> ₹{alert['current_value']:,.0f}</p>
            """
            
            if is_gain:
                html_message += f"<p><strong>Gain:</strong> <span class='gain-metric'>₹{alert.get('gain_amount', 0):,.0f}</span></p>"
            else:
                html_message += f"<p><strong>Loss:</strong> <span class='loss-metric'>₹{abs(alert.get('loss_amount', 0)):,.0f}</span></p>"
            
            html_message += "</div>"
        
        subject = f"Portfolio Alert: {alert_type}"
        self.send_email_alert(subject, html_message)
    
    def check_all_portfolios(self):
        """Check all portfolios and send alerts"""
        from portfolio_manager import PortfolioManager
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        all_alerts = []
        
        for _, portfolio in portfolios.iterrows():
            alerts = self.check_portfolio_alerts(portfolio['name'])
            all_alerts.extend(alerts)
        
        # Send alerts
        for alert in all_alerts:
            self.send_alert(alert)
        
        return all_alerts
    
    def send_daily_digest(self):
        """Send daily portfolio digest"""
        if not self.alert_config['thresholds']['daily_digest']:
            return
        
        digest = self.generate_daily_digest()
        
        subject = f"Daily Portfolio Summary - {datetime.now().strftime('%Y-%m-%d')}"
        self.send_email_alert(subject, digest)
    
    def send_weekly_digest(self):
        """Send weekly portfolio digest"""
        if not self.alert_config['thresholds']['weekly_digest']:
            return
        
        digest = self.generate_weekly_digest()
        
        subject = f"Weekly Portfolio Summary - {datetime.now().strftime('%Y-%m-%d')}"
        self.send_email_alert(subject, digest)


# CLI usage
if __name__ == "__main__":
    import sys
    
    alert_system = PortfolioAlertSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            # Check all portfolios
            alerts = alert_system.check_all_portfolios()
            print(f"Found {len(alerts)} alerts")
            for alert in alerts:
                print(f"  - {alert['message']}")
        
        elif command == "daily":
            # Send daily digest
            alert_system.send_daily_digest()
            print("Daily digest sent!")
        
        elif command == "weekly":
            # Send weekly digest
            alert_system.send_weekly_digest()
            print("Weekly digest sent!")
        
        else:
            print("Usage: python alert_system.py [check|daily|weekly]")
    else:
        print("Usage: python alert_system.py [check|daily|weekly]")
    
    def save_alert_config(self, config: Dict):
        """Save alert configuration"""
        with open('alert_config.json', 'w') as f:
            json.dump(config, f, indent=2)
        self.alert_config = config
    
    def check_portfolio_alerts(self, portfolio_name: str) -> List[Dict]:
        """
        Check if portfolio has crossed alert thresholds
        
        Returns list of alerts to send
        """
        from portfolio_manager import calculate_portfolio_performance, PortfolioManager
        
        pm = PortfolioManager(self.db_path)
        
        # Get latest prices
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        # Calculate current performance
        performance = calculate_portfolio_performance(portfolio_name, latest_prices)
        
        if not performance:
            return []
        
        alerts = []
        thresholds = self.alert_config['thresholds']
        total_gain_pct = performance['total_gain_pct']
        
        # Check overall portfolio threshold
        if total_gain_pct >= thresholds['gain_alert']:
            alerts.append({
                'type': 'portfolio_gain',
                'portfolio': portfolio_name,
                'gain_pct': total_gain_pct,
                'gain_amount': performance['total_gain'],
                'current_value': performance['total_value'],
                'message': f"🎉 Portfolio '{portfolio_name}' is up {total_gain_pct:.2f}%! (+₹{performance['total_gain']:,.0f})"
            })
        
        elif total_gain_pct <= thresholds['loss_alert']:
            alerts.append({
                'type': 'portfolio_loss',
                'portfolio': portfolio_name,
                'loss_pct': total_gain_pct,
                'loss_amount': performance['total_gain'],
                'current_value': performance['total_value'],
                'message': f"⚠️ Portfolio '{portfolio_name}' is down {abs(total_gain_pct):.2f}% (-₹{abs(performance['total_gain']):,.0f})"
            })
        
        # Check individual position thresholds
        for position in performance['positions']:
            pos_gain_pct = position['gain_loss_pct']
            
            # Big gain alert
            if pos_gain_pct >= 10.0:
                alerts.append({
                    'type': 'position_gain',
                    'portfolio': portfolio_name,
                    'stock': position['ticker'],
                    'gain_pct': pos_gain_pct,
                    'gain_amount': position['gain_loss'],
                    'message': f"🚀 {position['ticker']} in '{portfolio_name}' is up {pos_gain_pct:.2f}%! Consider taking profits."
                })
            
            # Big loss alert
            elif pos_gain_pct <= -10.0:
                alerts.append({
                    'type': 'position_loss',
                    'portfolio': portfolio_name,
                    'stock': position['ticker'],
                    'loss_pct': pos_gain_pct,
                    'loss_amount': position['gain_loss'],
                    'message': f"📉 {position['ticker']} in '{portfolio_name}' is down {abs(pos_gain_pct):.2f}%. Review position."
                })
        
        return alerts
    

    def send_email_alert(self, subject: str, message: str) -> bool:
        """Send alert via Email"""
        if not self.alert_config['email_enabled']:
            return False
        
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = self.alert_config['email_from']
            msg['To'] = self.alert_config['email_to']
            
            # HTML version
            html = f"""
            <html>
              <body style="font-family: Arial, sans-serif;">
                <h2 style="color: #667eea;">Portfolio Alert</h2>
                <div style="background: #f7fafc; padding: 20px; border-radius: 10px;">
                    {message.replace('\n', '<br>')}
                </div>
                <p style="color: #666; font-size: 12px; margin-top: 20px;">
                    Sent by Stock Research Platform<br>
                    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
              </body>
            </html>
            """
            
            msg.attach(MIMEText(html, 'html'))
            
            # Send via Gmail SMTP
            with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
                server.login(
                    self.alert_config['email_from'],
                    self.alert_config['email_password']
                )
                server.send_message(msg)
            
            return True
            
        except Exception as e:
            print(f"Email alert failed: {e}")
            return False
    
    def generate_daily_digest(self) -> str:
        """Generate daily portfolio summary"""
        from portfolio_manager import PortfolioManager, calculate_portfolio_performance
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        if portfolios.empty:
            return "No portfolios to report."
        
        # Get latest prices
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        # Build digest
        digest = f"📊 Daily Portfolio Summary - {datetime.now().strftime('%Y-%m-%d')}\n\n"
        
        total_invested = 0
        total_current = 0
        
        for _, portfolio in portfolios.iterrows():
            performance = calculate_portfolio_performance(
                portfolio['name'],
                latest_prices
            )
            
            if performance:
                total_invested += performance['invested_value']
                total_current += performance['current_value']
                
                emoji = "🟢" if performance['total_gain_pct'] >= 0 else "🔴"
                
                digest += f"{emoji} <b>{portfolio['name']}</b>\n"
                digest += f"   Value: ₹{performance['total_value']:,.0f}\n"
                digest += f"   Gain/Loss: {performance['total_gain_pct']:+.2f}% (₹{performance['total_gain']:+,.0f})\n\n"
        
        # Overall summary
        total_gain = total_current - total_invested
        total_gain_pct = (total_gain / total_invested * 100) if total_invested > 0 else 0
        
        digest += "─────────────────────\n"
        digest += f"<b>Total Portfolio Value: ₹{total_current:,.0f}</b>\n"
        digest += f"Total Gain/Loss: {total_gain_pct:+.2f}% (₹{total_gain:+,.0f})\n"
        
        return digest
    
    def generate_weekly_digest(self) -> str:
        """Generate weekly portfolio summary with insights"""
        daily = self.generate_daily_digest()
        
        # Add weekly insights
        weekly = daily.replace("Daily", "Weekly")
        weekly += "\n\n📈 <b>This Week's Highlights:</b>\n"
        
        # Get best/worst performers
        from portfolio_manager import PortfolioManager, calculate_portfolio_performance
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        conn = sqlite3.connect(self.db_path)
        query = """
        SELECT ticker, close_price 
        FROM scan_results 
        WHERE date = (SELECT MAX(date) FROM scan_results)
        """
        prices_df = pd.read_sql_query(query, conn)
        conn.close()
        
        latest_prices = dict(zip(prices_df['ticker'], prices_df['close_price']))
        
        best_portfolio = None
        worst_portfolio = None
        best_gain = float('-inf')
        worst_gain = float('inf')
        
        for _, portfolio in portfolios.iterrows():
            performance = calculate_portfolio_performance(
                portfolio['name'],
                latest_prices
            )
            
            if performance:
                gain_pct = performance['total_gain_pct']
                
                if gain_pct > best_gain:
                    best_gain = gain_pct
                    best_portfolio = portfolio['name']
                
                if gain_pct < worst_gain:
                    worst_gain = gain_pct
                    worst_portfolio = portfolio['name']
        
        if best_portfolio:
            weekly += f"🏆 Best: {best_portfolio} ({best_gain:+.2f}%)\n"
        
        if worst_portfolio and worst_portfolio != best_portfolio:
            weekly += f"📉 Needs attention: {worst_portfolio} ({worst_gain:+.2f}%)\n"
        
        return weekly
    
    def send_alert(self, alert: Dict):
        """Send alert via all enabled channels"""
        message = alert['message']
        
        # Telegram
        if self.alert_config['telegram_enabled']:
            self.send_telegram_alert(message)
        
        # Email
        if self.alert_config['email_enabled']:
            subject = f"Portfolio Alert: {alert['type'].replace('_', ' ').title()}"
            self.send_email_alert(subject, message)
    
    def check_all_portfolios(self):
        """Check all portfolios and send alerts"""
        from portfolio_manager import PortfolioManager
        
        pm = PortfolioManager(self.db_path)
        portfolios = pm.list_portfolios()
        
        all_alerts = []
        
        for _, portfolio in portfolios.iterrows():
            alerts = self.check_portfolio_alerts(portfolio['name'])
            all_alerts.extend(alerts)
        
        # Send alerts
        for alert in all_alerts:
            self.send_alert(alert)
        
        return all_alerts
    
    def send_daily_digest(self):
        """Send daily portfolio digest"""
        if not self.alert_config['thresholds']['daily_digest']:
            return
        
        digest = self.generate_daily_digest()
        
        # Send via enabled channels
        if self.alert_config['telegram_enabled']:
            self.send_telegram_alert(digest)
        
        if self.alert_config['email_enabled']:
            self.send_email_alert(
                f"Daily Portfolio Summary - {datetime.now().strftime('%Y-%m-%d')}",
                digest
            )
    
    def send_weekly_digest(self):
        """Send weekly portfolio digest"""
        if not self.alert_config['thresholds']['weekly_digest']:
            return
        
        digest = self.generate_weekly_digest()
        
        # Send via enabled channels
        if self.alert_config['telegram_enabled']:
            self.send_telegram_alert(digest)
        
        if self.alert_config['email_enabled']:
            self.send_email_alert(
                f"Weekly Portfolio Summary - {datetime.now().strftime('%Y-%m-%d')}",
                digest
            )


# CLI usage
if __name__ == "__main__":
    import sys
    
    alert_system = PortfolioAlertSystem()
    
    if len(sys.argv) > 1:
        command = sys.argv[1]
        
        if command == "check":
            # Check all portfolios
            alerts = alert_system.check_all_portfolios()
            print(f"Found {len(alerts)} alerts")
            for alert in alerts:
                print(f"  - {alert['message']}")
        
        elif command == "daily":
            # Send daily digest
            alert_system.send_daily_digest()
            print("Daily digest sent!")
        
        elif command == "weekly":
            # Send weekly digest
            alert_system.send_weekly_digest()
            print("Weekly digest sent!")
        
        else:
            print("Usage: python alert_system.py [check|daily|weekly]")
    else:
        print("Usage: python alert_system.py [check|daily|weekly]")
