"""
Email notification service for sending download links to users.
"""
import smtplib
import os
from pathlib import Path
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables from .env file
# Get the directory where this file is located (backend/core/)
current_dir = Path(__file__).resolve().parent
# Go up one level to backend/ directory where .env file is located
backend_dir = current_dir.parent
env_path = backend_dir / '.env'

# Load .env file
load_dotenv(dotenv_path=env_path)


class EmailService:
    """Handles sending email notifications with download links."""
    
    def __init__(self):
        self.smtp_host = os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.smtp_email = os.getenv("SMTP_EMAIL", "")
        self.smtp_password = os.getenv("SMTP_PASSWORD", "")
        self.recipient_email = os.getenv("RECIPIENT_EMAIL", "numanarif.videos@gmail.com")
        self.base_url = os.getenv("BASE_URL", "http://localhost:3000")
        
    def is_configured(self) -> bool:
        """Check if email service is properly configured."""
        return bool(self.smtp_email and self.smtp_password)
    
    def send_clip_notification(self, project_id: str, clips: List[Dict[str, str]]) -> bool:
        """
        Send email notification with download links for generated clips.
        
        Args:
            project_id: Unique project identifier
            clips: List of clip info dicts with 'filename' and 'url' keys
            
        Returns:
            True if email sent successfully, False otherwise
        """
        if not self.is_configured():
            print("⚠️  Email service not configured. Skipping email notification.")
            print("   Set SMTP_EMAIL and SMTP_PASSWORD environment variables to enable.")
            return False
        
        try:
            # Create message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = f"🎬 Your Video Clips are Ready! (Project: {project_id})"
            msg["From"] = self.smtp_email
            msg["To"] = self.recipient_email
            
            # Create email body
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Plain text version
            text_content = f"""
Your Video Clips are Ready! 🎬

Project ID: {project_id}
Generated: {timestamp}
Number of Clips: {len(clips)}

Download Links:
"""
            for i, clip in enumerate(clips, 1):
                download_url = f"{self.base_url}{clip['url']}"
                text_content += f"\nClip {i}: {download_url}"
            
            text_content += f"""

These links will remain available for download.

Happy creating! 🎥

---
AI Video Shorts Generator
"""
            
            # HTML version
            html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px 20px;
            border-radius: 10px 10px 0 0;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 24px;
        }}
        .content {{
            background: #f8f9fa;
            padding: 30px 20px;
            border-radius: 0 0 10px 10px;
        }}
        .info-box {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            border-left: 4px solid #667eea;
        }}
        .info-row {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
        }}
        .label {{
            color: #666;
            font-weight: 500;
        }}
        .value {{
            color: #333;
            font-weight: 600;
        }}
        .clips-section {{
            margin-top: 20px;
        }}
        .clip-item {{
            background: white;
            padding: 15px;
            margin-bottom: 10px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .clip-header {{
            font-weight: 600;
            color: #667eea;
            margin-bottom: 8px;
        }}
        .download-btn {{
            display: inline-block;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 10px 20px;
            text-decoration: none;
            border-radius: 6px;
            font-weight: 600;
            transition: opacity 0.3s;
        }}
        .download-btn:hover {{
            opacity: 0.9;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #666;
            font-size: 14px;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🎬 Your Video Clips are Ready!</h1>
    </div>
    
    <div class="content">
        <div class="info-box">
            <div class="info-row">
                <span class="label">Project ID:</span>
                <span class="value">{project_id}</span>
            </div>
            <div class="info-row">
                <span class="label">Generated:</span>
                <span class="value">{timestamp}</span>
            </div>
            <div class="info-row">
                <span class="label">Number of Clips:</span>
                <span class="value">{len(clips)}</span>
            </div>
        </div>
        
        <div class="clips-section">
            <h2 style="color: #333; font-size: 18px; margin-bottom: 15px;">📥 Download Your Clips</h2>
"""
            
            for i, clip in enumerate(clips, 1):
                download_url = f"{self.base_url}{clip['url']}"
                html_content += f"""
            <div class="clip-item">
                <div class="clip-header">Clip {i}</div>
                <a href="{download_url}" class="download-btn">Download Clip {i}</a>
            </div>
"""
            
            html_content += """
        </div>
        
        <p style="margin-top: 20px; color: #666;">
            These links will remain available for download. You can access them anytime!
        </p>
    </div>
    
    <div class="footer">
        <p>Happy creating! 🎥</p>
        <p style="margin-top: 10px;">AI Video Shorts Generator</p>
    </div>
</body>
</html>
"""
            
            # Attach parts
            part1 = MIMEText(text_content, "plain")
            part2 = MIMEText(html_content, "html")
            msg.attach(part1)
            msg.attach(part2)
            
            # Send email
            with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
                server.starttls()
                server.login(self.smtp_email, self.smtp_password)
                server.send_message(msg)
            
            print(f"✅ Email notification sent successfully to {self.recipient_email}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to send email notification: {e}")
            return False


# Global instance
email_service = EmailService()
