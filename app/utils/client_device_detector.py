"""Client-side device detection utilities
This module provides functions to help generate unique device identifiers
from client-side information that can be sent to the server.
"""
import uuid


def generate_device_fingerprint(device_info: dict) -> str:
    """
    Generate a unique device fingerprint from client-side device information.
    
    This creates a deterministic unique ID based on various device characteristics
    that are available in the browser.
    
    Args:
        device_info: Dictionary containing device information from client:
            - user_agent: Browser user agent string
            - screen_resolution: Screen width x height
            - timezone: Timezone offset
            - language: Browser language
            - platform: Operating system platform
            - hardware_concurrency: CPU cores
            - device_memory: RAM (if available)
            - canvas_fingerprint: Canvas fingerprint hash (if available)
            - webgl_fingerprint: WebGL fingerprint hash (if available)
            - local_ip: Local IP address from WebRTC (if available)
    
    Returns:
        A unique device identifier (UUID5-based)
    """
    # Create a composite string from all available device characteristics
    fingerprint_parts = []
    
    # Add user agent (browser and OS info)
    fingerprint_parts.append(device_info.get('user_agent', ''))
    
    # Add screen resolution
    fingerprint_parts.append(str(device_info.get('screen_resolution', '')))
    
    # Add timezone
    fingerprint_parts.append(str(device_info.get('timezone', '')))
    
    # Add language
    fingerprint_parts.append(device_info.get('language', ''))
    
    # Add platform
    fingerprint_parts.append(device_info.get('platform', ''))
    
    # Add hardware info
    fingerprint_parts.append(str(device_info.get('hardware_concurrency', '')))
    fingerprint_parts.append(str(device_info.get('device_memory', '')))
    
    # Add canvas fingerprint if available (more unique)
    if device_info.get('canvas_fingerprint'):
        fingerprint_parts.append(device_info.get('canvas_fingerprint'))
    
    # Add WebGL fingerprint if available (more unique)
    if device_info.get('webgl_fingerprint'):
        fingerprint_parts.append(device_info.get('webgl_fingerprint'))
    
    # Add local IP if available (from WebRTC)
    if device_info.get('local_ip'):
        fingerprint_parts.append(device_info.get('local_ip'))
    
    # Combine all parts
    fingerprint_string = '|'.join(fingerprint_parts)
    
    # Generate UUID5 from the fingerprint string (deterministic)
    # Using DNS namespace for consistency
    unique_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, fingerprint_string))
    
    return unique_id


def detect_device_type_from_user_agent(user_agent: str) -> str:
    """
    Detect device type from user agent string.
    
    Args:
        user_agent: Browser user agent string
    
    Returns:
        Device type: "Desktop", "Laptop", "Mobile", "Tablet", or "Unknown"
    """
    if not user_agent:
        return "Unknown"
    
    user_agent_lower = user_agent.lower()
    
    # Mobile devices
    if any(keyword in user_agent_lower for keyword in ['mobile', 'android', 'iphone', 'ipod']):
        return "Mobile"
    
    # Tablets
    if any(keyword in user_agent_lower for keyword in ['ipad', 'tablet', 'playbook']):
        return "Tablet"
    
    # Laptops (common laptop identifiers in user agent)
    if any(keyword in user_agent_lower for keyword in ['laptop', 'notebook', 'thinkpad', 'macbook']):
        return "Laptop"
    
    # Desktop (default for non-mobile browsers)
    if any(keyword in user_agent_lower for keyword in ['windows', 'linux', 'macintosh', 'x11']):
        return "Desktop"
    
    return "Unknown"

