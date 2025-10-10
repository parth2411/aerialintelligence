import re
from datetime import datetime
from .config import Config

class ThreatDetector:
    def __init__(self):
        self.threshold = Config.THREAT_THRESHOLD
        self.threat_patterns = self._initialize_patterns()
    
    def _initialize_patterns(self):
        """Initialize threat detection patterns"""
        return {
            'critical': [
                # Violence and weapons
                r'\b(gun|weapon|knife|pistol|rifle|firearm|armed|shooting|scissor)\b',
                r'\b(violence|fight|attack|assault|blood)\b',
                r'\b(breaking|smashing|destroying|vandal|damage)\b',
                r'\b(fire|smoke|explosion|flames|burning)\b',
                # Break-ins
                r'\b(breaking.{0,10}(in|into|through)|forced.{0,10}entry)\b',
                r'\b(intruder|burglar|break-in)\b',
            ],
            'high': [
                # Suspicious activity
                r'\b(unauthorized|suspicious.{0,10}person|unknown.{0,10}individual)\b',
                r'\b(lurking|hiding|sneaking|prowling)\b',
                r'\b(mask|hood|face.{0,10}covered|disguise)\b',
                r'\b(climbing.{0,10}(fence|wall)|jumping.{0,10}fence)\b',
            ],
            'medium': [
                # Unusual situations
                r'\b(abandoned.{0,10}(bag|package)|unattended.{0,10}item)\b',
                r'\b(loitering|lingering|watching)\b',
                r'\b(at.{0,10}night|after.{0,10}hours|dark)\b',
                r'\b(unusual.{0,10}activity|strange.{0,10}behavior)\b',
            ],
            'normal': [
                # Normal indicators (reduce threat)
                r'\b(employee|worker|staff|security|guard)\b',
                r'\b(uniform|badge|identification)\b',
                r'\b(delivery|service|repair|maintenance)\b',
            ]
        }
    
    def analyze_threat(self, classification_text, image_file="unknown"):
        """
        Analyze classification for threats
        
        Returns:
            dict: Threat analysis results
        """
        print(f"\n🔍 Analyzing threat for: {image_file}")
        
        text = classification_text.lower()
        threat_score = 1
        threat_reasons = []
        detected_patterns = []
        
        # Check critical threats
        for pattern in self.threat_patterns['critical']:
            if re.search(pattern, text, re.IGNORECASE):
                threat_score = max(threat_score, 5)
                match = re.search(pattern, text, re.IGNORECASE)
                threat_reasons.append(f"Critical threat: {match.group(0)}")
                detected_patterns.append('CRITICAL')
        
        # Check high threats
        for pattern in self.threat_patterns['high']:
            if re.search(pattern, text, re.IGNORECASE):
                threat_score = max(threat_score, 4)
                match = re.search(pattern, text, re.IGNORECASE)
                threat_reasons.append(f"High threat: {match.group(0)}")
                detected_patterns.append('HIGH')
        
        # Check medium threats
        for pattern in self.threat_patterns['medium']:
            if re.search(pattern, text, re.IGNORECASE):
                threat_score = max(threat_score, 3)
                match = re.search(pattern, text, re.IGNORECASE)
                threat_reasons.append(f"Medium threat: {match.group(0)}")
                detected_patterns.append('MEDIUM')
        
        # Check for normal indicators (reduce score)
        normal_count = 0
        for pattern in self.threat_patterns['normal']:
            if re.search(pattern, text, re.IGNORECASE):
                normal_count += 1
        
        if normal_count > 0:
            threat_score = max(1, threat_score - normal_count)
            threat_reasons.append(f"Normal activity indicators: {normal_count}")
        
        # Determine threat level
        threat_level = self._get_threat_level(threat_score)
        
        # Calculate confidence
        confidence = self._calculate_confidence(len(threat_reasons), normal_count)
        
        # Create analysis result
        analysis = {
            'timestamp': datetime.now().isoformat(),
            'image_file': image_file,
            'classification': classification_text,
            'threat_detected': threat_score >= self.threshold,
            'threat_level': threat_level,
            'threat_score': threat_score,
            'threat_reasons': threat_reasons,
            'confidence': confidence,
            'recommended_action': self._get_recommended_action(threat_level)
        }
        
        # Print analysis
        print(f"📊 Threat Analysis:")
        print(f"   Level: {threat_level}")
        print(f"   Score: {threat_score}/5")
        print(f"   Alert: {'YES' if analysis['threat_detected'] else 'NO'}")
        print(f"   Confidence: {confidence}%")
        
        if threat_reasons:
            print(f"   Reasons:")
            for reason in threat_reasons[:3]:
                print(f"      • {reason}")
        
        return analysis
    
    def _get_threat_level(self, score):
        """Convert score to threat level"""
        if score >= 5:
            return 'CRITICAL'
        elif score >= 4:
            return 'HIGH'
        elif score >= 3:
            return 'MEDIUM'
        elif score >= 2:
            return 'LOW'
        else:
            return 'NONE'
    
    def _calculate_confidence(self, threat_indicators, normal_indicators):
        """Calculate confidence percentage"""
        confidence = 50  # Base confidence
        
        if threat_indicators > 0:
            confidence += min(threat_indicators * 15, 40)
        
        if normal_indicators > 0:
            confidence -= min(normal_indicators * 10, 30)
        
        return max(10, min(confidence, 95))
    
    def _get_recommended_action(self, threat_level):
        """Get recommended action for threat level"""
        actions = {
            'CRITICAL': 'immediate_response',
            'HIGH': 'investigate_immediately',
            'MEDIUM': 'monitor_closely',
            'LOW': 'log_for_review',
            'NONE': 'none'
        }
        return actions.get(threat_level, 'none')
    
    def generate_summary(self, analysis):
        """Generate human-readable threat summary"""
        emoji = {
            'CRITICAL': '🚨',
            'HIGH': '⚠️',
            'MEDIUM': '⚡',
            'LOW': '👁️',
            'NONE': '✅'
        }
        
        level = analysis['threat_level']
        summary = [
            f"{emoji[level]} THREAT LEVEL: {level}",
            f"🎯 Confidence: {analysis['confidence']}%",
            f"📊 Score: {analysis['threat_score']}/5",
            f"📷 Image: {analysis['image_file']}",
            f"⏰ Time: {datetime.fromisoformat(analysis['timestamp']).strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        if analysis['threat_reasons']:
            summary.append("\n📝 Threat Indicators:")
            for reason in analysis['threat_reasons'][:5]:
                summary.append(f"   • {reason}")
        
        return "\n".join(summary)