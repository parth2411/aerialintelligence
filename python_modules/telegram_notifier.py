import requests
import time
from pathlib import Path
from .config import Config

class TelegramNotifier:
    # Class variable to track last alert time (persists across instances)
    _last_alert_time = {}
    _alert_cooldown_seconds = Config.ALERT_COOLDOWN_SECONDS  # Don't send same alert within 30 seconds
    
    def __init__(self):
        self.enabled = Config.TELEGRAM_ENABLED
        self.bot_token = Config.TELEGRAM_BOT_TOKEN
        self.chat_id = Config.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.bot_token}"
    
    def send_alert(self, threat_analysis, image_path=None):
        """
        Send security alert to Telegram with debouncing
        
        Args:
            threat_analysis: Threat analysis dict
            image_path: Optional path to image file
        """
        if not self.enabled:
            print("📱 Telegram notifications disabled")
            return False
        
        level = threat_analysis['threat_level']
        
        # Check if we should debounce this alert
        if self._should_debounce(level):
            print(f"⏭️  Alert debounced: {level} alert sent recently (cooldown: {self._alert_cooldown_seconds}s)")
            return False
        
        print(f"\n🚨 Sending {level} priority alert to Telegram")
        
        # Format message
        message = self._format_alert_message(threat_analysis)
        
        # Send with image if available
        success = False
        if image_path and Path(image_path).exists():
            success = self._send_photo(image_path, message)
        else:
            success = self._send_message(message)
        
        # Update last alert time if successful
        if success:
            self._update_last_alert_time(level)
        
        return success
    
    def _should_debounce(self, threat_level):
        """Check if alert should be debounced (too soon since last alert)"""
        current_time = time.time()
        
        # Check last alert time for this threat level
        if threat_level in self._last_alert_time:
            time_since_last = current_time - self._last_alert_time[threat_level]
            return time_since_last < self._alert_cooldown_seconds
        
        return False
    
    def _update_last_alert_time(self, threat_level):
        """Update last alert time for this threat level"""
        self._last_alert_time[threat_level] = time.time()
    
    @classmethod
    def set_cooldown(cls, seconds):
        """Set alert cooldown period in seconds"""
        cls._alert_cooldown_seconds = seconds
    
    @classmethod
    def reset_cooldown(cls):
        """Reset all alert cooldowns (useful for testing)"""
        cls._last_alert_time.clear()
    
    def _format_alert_message(self, analysis):
        """Format alert message for Telegram"""
        emoji_map = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': '🔔',
            'NONE': '✅'
        }
        
        level = analysis['threat_level']
        emoji = emoji_map.get(level, '📢')
        
        message = f"{emoji} SAFETY ALERT - {level} PRIORITY {emoji}\n\n"
        message += f"⏰ Time: {analysis['timestamp']}\n\n"
        message += f"🔍 DETECTED SITUATION:\n{analysis['classification']}\n\n"
        
        if analysis['threat_reasons']:
            message += "⚠️ THREAT INDICATORS:\n"
            for reason in analysis['threat_reasons'][:5]:
                # Extract just the keyword
                if ':' in reason:
                    keyword = reason.split(':')[-1].strip()
                    message += f"• {keyword}\n"
            message += "\n"
        
        message += "📱 This is an automated safety monitoring alert.\n"
        
        if level in ['HIGH', 'CRITICAL']:
            message += f"{emoji} IMMEDIATE ATTENTION REQUIRED {emoji}"
        
        return message
    
    def _send_message(self, text):
        """Send text message to Telegram"""
        try:
            url = f"{self.api_url}/sendMessage"
            data = {
                'chat_id': self.chat_id,
                'text': text,
                'parse_mode': 'HTML'
            }
            
            response = requests.post(url, json=data, timeout=10)
            
            if response.status_code == 200:
                print("✅ Alert sent successfully")
                return True
            else:
                print(f"❌ Failed to send alert: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error sending alert: {e}")
            return False
    
    def _send_photo(self, image_path, caption):
        """Send photo with caption to Telegram"""
        try:
            url = f"{self.api_url}/sendPhoto"
            
            with open(image_path, 'rb') as photo:
                files = {'photo': photo}
                data = {
                    'chat_id': self.chat_id,
                    'caption': caption
                }
                
                response = requests.post(url, files=files, data=data, timeout=30)
            
            if response.status_code == 200:
                print("✅ Alert with image sent successfully")
                return True
            else:
                print(f"❌ Failed to send photo: {response.text}")
                # Fallback to text only
                return self._send_message(caption)
                
        except Exception as e:
            print(f"❌ Error sending photo: {e}")
            # Fallback to text only
            return self._send_message(caption)
    
    def test_connection(self):
        """Test Telegram bot connection"""
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=10)
            
            if response.status_code == 200:
                bot_info = response.json()['result']
                print(f"✅ Telegram bot connected: @{bot_info['username']}")
                return True
            else:
                print(f"❌ Telegram connection failed: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Telegram test failed: {e}")
            return False