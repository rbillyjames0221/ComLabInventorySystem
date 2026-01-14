"""Network device scanner utility"""
import socket
import subprocess
import platform
import ipaddress
from typing import List, Dict, Optional


def get_local_network_info() -> Optional[Dict[str, str]]:
    """Get local network information (IP and subnet)"""
    try:
        # Get hostname
        hostname = socket.gethostname()
        
        # Get local IP address
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            # Connect to a remote address (doesn't actually send data)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
        except Exception:
            # Fallback: try to get IP from hostname
            local_ip = socket.gethostbyname(hostname)
        finally:
            s.close()
        
        # Calculate network range
        # Assume /24 subnet (255.255.255.0) for common home/office networks
        ip_obj = ipaddress.IPv4Address(local_ip)
        network = ipaddress.IPv4Network(f"{ip_obj}/{24}", strict=False)
        
        return {
            "hostname": hostname,
            "local_ip": local_ip,
            "network": str(network.network_address),
            "subnet_mask": str(network.netmask),
            "network_range": str(network)
        }
    except Exception as e:
        print(f"Error getting network info: {e}")
        return None


def ping_host(ip: str, timeout: float = 0.5) -> bool:
    """Ping a host to check if it's alive"""
    try:
        if platform.system().lower() == "windows":
            # Windows ping command
            result = subprocess.run(
                ["ping", "-n", "1", "-w", str(int(timeout * 1000)), ip],
                capture_output=True,
                timeout=2,
                text=True
            )
            return result.returncode == 0
        else:
            # Linux/Mac ping command
            result = subprocess.run(
                ["ping", "-c", "1", "-W", str(int(timeout * 1000)), ip],
                capture_output=True,
                timeout=2,
                text=True
            )
            return result.returncode == 0
    except Exception:
        return False


def get_hostname_from_ip(ip: str) -> Optional[str]:
    """Try to get hostname from IP address"""
    try:
        hostname, _, _ = socket.gethostbyaddr(ip)
        return hostname
    except Exception:
        return None


def get_mac_address(ip: str) -> Optional[str]:
    """Get MAC address from IP using ARP table"""
    try:
        if platform.system().lower() == "windows":
            # Windows ARP command
            result = subprocess.run(
                ["arp", "-a", ip],
                capture_output=True,
                timeout=2,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                # Parse ARP output to extract MAC address
                # Format: "192.168.1.1          00-11-22-33-44-55     dynamic"
                for line in output.split('\n'):
                    if ip in line:
                        parts = line.split()
                        if len(parts) >= 2:
                            mac = parts[1].replace('-', ':')
                            return mac.upper()
        else:
            # Linux ARP command
            result = subprocess.run(
                ["arp", "-n", ip],
                capture_output=True,
                timeout=2,
                text=True
            )
            if result.returncode == 0:
                output = result.stdout
                # Parse ARP output
                for line in output.split('\n'):
                    if ip in line:
                        parts = line.split()
                        if len(parts) >= 3:
                            return parts[2].upper()
    except Exception:
        pass
    return None


def detect_device_type(hostname: Optional[str], mac: Optional[str]) -> str:
    """Try to detect device type from hostname or MAC address"""
    if not hostname:
        return "Unknown"
    
    hostname_lower = hostname.lower()
    
    # Check for common device patterns
    if any(keyword in hostname_lower for keyword in ['laptop', 'notebook', 'thinkpad', 'macbook']):
        return "Laptop"
    elif any(keyword in hostname_lower for keyword in ['desktop', 'pc', 'computer']):
        return "Desktop"
    elif any(keyword in hostname_lower for keyword in ['mobile', 'phone', 'android', 'iphone', 'ipad']):
        return "Mobile"
    elif any(keyword in hostname_lower for keyword in ['server', 'srv']):
        return "Server"
    elif any(keyword in hostname_lower for keyword in ['router', 'gateway', 'ap']):
        return "Network Device"
    else:
        return "Unknown"


def scan_network_devices(max_hosts: int = 50, timeout: float = 0.5) -> List[Dict[str, str]]:
    """
    Scan local network for active devices using ping
    
    Args:
        max_hosts: Maximum number of hosts to scan (to avoid long waits)
        timeout: Timeout for each ping in seconds
    
    Returns:
        List of detected devices with IP, hostname, MAC, and device type
    """
    detected_devices = []
    
    # Get network information
    network_info = get_local_network_info()
    if not network_info:
        return detected_devices
    
    local_ip = network_info["local_ip"]
    network = ipaddress.IPv4Network(network_info["network_range"], strict=False)
    
    print(f"Scanning network {network_info['network_range']} for devices...")
    
    # Scan network (limit to max_hosts to avoid long waits)
    hosts_scanned = 0
    for ip_obj in network.hosts():
        if hosts_scanned >= max_hosts:
            break
        
        ip_str = str(ip_obj)
        
        # Skip our own IP
        if ip_str == local_ip:
            continue
        
        hosts_scanned += 1
        
        # Ping the host
        if ping_host(ip_str, timeout):
            # Get additional information
            hostname = None
            try:
                hostname = get_hostname_from_ip(ip_str)
            except:
                pass
            
            mac = get_mac_address(ip_str)
            device_type = detect_device_type(hostname, mac)
            
            device_info = {
                "ip": ip_str,
                "hostname": hostname or ip_str,
                "mac_address": mac or "Unknown",
                "device_type": device_type,
                "status": "Online"
            }
            
            detected_devices.append(device_info)
            print(f"Found device: {ip_str} - {hostname or 'Unknown'} ({device_type})")
    
    return detected_devices


def scan_network_devices_fast() -> List[Dict[str, str]]:
    """
    Fast network scan using ARP table (Windows/Linux)
    This is faster than ping scanning as it uses the system's ARP cache
    """
    detected_devices = []
    
    try:
        if platform.system().lower() == "windows":
            # Windows ARP -a command
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                network_info = get_local_network_info()
                local_ip = network_info["local_ip"] if network_info else None
                
                for line in output.split('\n'):
                    line = line.strip()
                    if not line or 'Interface' in line or '---' in line or 'Internet Address' in line:
                        continue
                    
                    # Parse ARP table line
                    # Windows format: "192.168.1.1          00-11-22-33-44-55     dynamic"
                    # Or: "  192.168.1.1          00-11-22-33-44-55     dynamic"
                    parts = [p for p in line.split() if p]
                    if len(parts) >= 2:
                        ip_str = parts[0].strip('()')
                        
                        # Skip our own IP
                        if local_ip and ip_str == local_ip:
                            continue
                        
                        # Validate IP address
                        try:
                            ipaddress.IPv4Address(ip_str)
                        except:
                            continue
                        
                        # Extract MAC address (second part, handle both formats)
                        mac_raw = parts[1]
                        # Handle MAC formats: 00-11-22-33-44-55 or 00:11:22:33:44:55
                        mac = mac_raw.replace('-', ':').upper()
                        
                        # Skip invalid MAC addresses (like "ff-ff-ff-ff-ff-ff")
                        if mac == "FF:FF:FF:FF:FF:FF" or not mac or len(mac) < 17:
                            continue
                        
                        # Get hostname (try reverse DNS lookup)
                        hostname = None
                        try:
                            hostname = get_hostname_from_ip(ip_str)
                        except:
                            pass
                        
                        device_type = detect_device_type(hostname, mac)
                        
                        device_info = {
                            "ip": ip_str,
                            "hostname": hostname or ip_str,
                            "mac_address": mac,
                            "device_type": device_type,
                            "status": "Online"
                        }
                        
                        detected_devices.append(device_info)
        
        else:
            # Linux ARP -a command
            result = subprocess.run(
                ["arp", "-a"],
                capture_output=True,
                timeout=5,
                text=True
            )
            
            if result.returncode == 0:
                output = result.stdout
                network_info = get_local_network_info()
                local_ip = network_info["local_ip"] if network_info else None
                
                for line in output.split('\n'):
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Parse ARP table line
                    # Linux format: "hostname (192.168.1.1) at 00:11:22:33:44:55 [ether] on eth0"
                    # Or: "? (192.168.1.1) at 00:11:22:33:44:55 [ether] on eth0"
                    parts = line.split()
                    if len(parts) >= 4:
                        # Extract IP from parentheses
                        ip_part = parts[1].strip('()')
                        mac = parts[3].upper()
                        
                        # Skip our own IP
                        if local_ip and ip_part == local_ip:
                            continue
                        
                        # Validate IP address
                        try:
                            ipaddress.IPv4Address(ip_part)
                        except:
                            continue
                        
                        # Skip invalid MAC addresses
                        if mac == "FF:FF:FF:FF:FF:FF" or not mac or len(mac) < 17:
                            continue
                        
                        # Extract hostname (first part)
                        hostname = parts[0] if parts[0] != '?' else None
                        if not hostname or hostname == '?':
                            try:
                                hostname = get_hostname_from_ip(ip_part)
                            except:
                                hostname = None
                        
                        device_type = detect_device_type(hostname, mac)
                        
                        device_info = {
                            "ip": ip_part,
                            "hostname": hostname or ip_part,
                            "mac_address": mac,
                            "device_type": device_type,
                            "status": "Online"
                        }
                        
                        detected_devices.append(device_info)
    
    except Exception as e:
        print(f"Error scanning ARP table: {e}")
    
    return detected_devices

