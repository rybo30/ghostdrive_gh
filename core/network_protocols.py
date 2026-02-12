# =============================================================================
# network_protocols.py — Cross-Platform WiFi & Network Control
# Supports: Windows (netsh), Linux (nmcli/iwctl)
# =============================================================================
#
# SECURITY NOTE: These protocols are designed for AIRGAPPED operation.
# The blackout_mode() function is a critical security feature that isolates
# the system from all wireless networks, preventing remote exploitation.
#
# =============================================================================

import subprocess
import re
from typing import List, Tuple, Optional
from .platform_utils import get_os_type, OSType, get_network_manager

# =============================================================================
# Windows Network Functions
# =============================================================================

def _windows_disconnect_wifi() -> str:
    """Disconnect from WiFi on Windows using netsh."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "disconnect"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if "disconnected" in result.stdout.lower() or "completed successfully" in result.stdout.lower():
            return "📡 Disconnected from WiFi network."
        return f"⚠️ Disconnect attempted: {result.stdout.strip()}"
    except subprocess.TimeoutExpired:
        return "❌ WiFi disconnect timed out."
    except FileNotFoundError:
        return "❌ netsh not found. Is this Windows?"
    except Exception as e:
        return f"❌ Failed to disconnect: {e}"


def _windows_reconnect_wifi() -> str:
    """Reconnect to a known WiFi network on Windows."""
    try:
        # Get list of known profiles
        output = subprocess.check_output(
            ["netsh", "wlan", "show", "profiles"],
            text=True,
            stderr=subprocess.DEVNULL,
            timeout=10
        )
        
        profiles = []
        for line in output.splitlines():
            if "All User Profile" in line:
                ssid = line.split(":")[1].strip()
                profiles.append(ssid)
        
        if not profiles:
            return "⚠️ No saved WiFi networks found."
        
        # Try to connect to each known network
        for ssid in profiles:
            result = subprocess.run(
                ["netsh", "wlan", "connect", f"name={ssid}"],
                capture_output=True,
                text=True,
                timeout=15
            )
            if "completed successfully" in result.stdout.lower():
                return f"✅ Connected to: {ssid}"
        
        return "❌ Could not connect to any known network."
        
    except subprocess.TimeoutExpired:
        return "❌ WiFi reconnect timed out."
    except Exception as e:
        return f"❌ Reconnection failed: {e}"


def _windows_scan_networks() -> str:
    """Scan for available WiFi networks on Windows."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "networks", "mode=bssid"],
            capture_output=True,
            text=True,
            timeout=15
        )
        
        if result.returncode != 0:
            return f"❌ Scan failed: {result.stderr}"
        
        # Parse the output for cleaner display
        output = result.stdout
        if not output.strip():
            return "📡 No networks found (WiFi adapter may be disabled)."
        
        return f"📡 Available Networks:\n\n{output}"
        
    except subprocess.TimeoutExpired:
        return "❌ Network scan timed out."
    except Exception as e:
        return f"❌ Scan failed: {e}"


def _windows_get_connection_status() -> str:
    """Get current WiFi connection status on Windows."""
    try:
        result = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=10
        )
        return result.stdout if result.stdout else "No WiFi interface found."
    except Exception as e:
        return f"❌ Could not get status: {e}"


# =============================================================================
# Linux Network Functions (NetworkManager / nmcli)
# =============================================================================

def _linux_disconnect_wifi() -> str:
    """Disconnect from WiFi on Linux using nmcli."""
    nm = get_network_manager()
    
    if nm == "nmcli":
        try:
            # Get active WiFi connection
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show", "--active"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            wifi_connections = []
            for line in result.stdout.strip().split("\n"):
                if ":802-11-wireless" in line:
                    name = line.split(":")[0]
                    wifi_connections.append(name)
            
            if not wifi_connections:
                return "📡 No active WiFi connection to disconnect."
            
            # Disconnect each WiFi connection
            for conn in wifi_connections:
                subprocess.run(
                    ["nmcli", "connection", "down", conn],
                    capture_output=True,
                    timeout=10
                )
            
            return f"📡 Disconnected from WiFi: {', '.join(wifi_connections)}"
            
        except subprocess.TimeoutExpired:
            return "❌ WiFi disconnect timed out."
        except Exception as e:
            return f"❌ Failed to disconnect: {e}"
    
    elif nm == "iwctl":
        # For systems using iwd instead of NetworkManager
        try:
            # Get WiFi device name
            result = subprocess.run(
                ["iwctl", "device", "list"],
                capture_output=True,
                text=True,
                timeout=10
            )
            # This is a simplified approach - iwctl output parsing is more complex
            subprocess.run(["iwctl", "station", "wlan0", "disconnect"], timeout=10)
            return "📡 Disconnected from WiFi (iwctl)."
        except Exception as e:
            return f"❌ iwctl disconnect failed: {e}"
    
    else:
        return "❌ No supported network manager found (need nmcli or iwctl)."


def _linux_reconnect_wifi() -> str:
    """Reconnect to a known WiFi network on Linux."""
    nm = get_network_manager()
    
    if nm == "nmcli":
        try:
            # Get list of known connections
            result = subprocess.run(
                ["nmcli", "-t", "-f", "NAME,TYPE", "connection", "show"],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            wifi_connections = []
            for line in result.stdout.strip().split("\n"):
                if ":802-11-wireless" in line:
                    name = line.split(":")[0]
                    wifi_connections.append(name)
            
            if not wifi_connections:
                return "⚠️ No saved WiFi networks found."
            
            # Try to connect to each known network
            for conn in wifi_connections:
                result = subprocess.run(
                    ["nmcli", "connection", "up", conn],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return f"✅ Connected to: {conn}"
            
            return "❌ Could not connect to any known network."
            
        except subprocess.TimeoutExpired:
            return "❌ WiFi reconnect timed out."
        except Exception as e:
            return f"❌ Reconnection failed: {e}"
    
    else:
        return "❌ No supported network manager found for reconnection."


def _linux_scan_networks() -> str:
    """Scan for available WiFi networks on Linux."""
    nm = get_network_manager()
    
    if nm == "nmcli":
        try:
            # Force a rescan
            subprocess.run(
                ["nmcli", "device", "wifi", "rescan"],
                capture_output=True,
                timeout=10
            )
            
            # Get list of networks
            result = subprocess.run(
                ["nmcli", "-f", "SSID,SIGNAL,SECURITY", "device", "wifi", "list"],
                capture_output=True,
                text=True,
                timeout=15
            )
            
            if result.returncode != 0:
                return f"❌ Scan failed: {result.stderr}"
            
            return f"📡 Available Networks:\n\n{result.stdout}"
            
        except subprocess.TimeoutExpired:
            return "❌ Network scan timed out."
        except Exception as e:
            return f"❌ Scan failed: {e}"
    
    else:
        return "❌ No supported network manager found for scanning."


def _linux_get_connection_status() -> str:
    """Get current WiFi connection status on Linux."""
    nm = get_network_manager()
    
    if nm == "nmcli":
        try:
            result = subprocess.run(
                ["nmcli", "device", "status"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.stdout if result.stdout else "No network devices found."
        except Exception as e:
            return f"❌ Could not get status: {e}"
    
    return "❌ No supported network manager found."


# =============================================================================
# Cross-Platform Public API
# =============================================================================

def disconnect_wifi() -> str:
    """
    Disconnect from the current WiFi network.
    Works on Windows and Linux.
    """
    os_type = get_os_type()
    
    if os_type == OSType.WINDOWS:
        return _windows_disconnect_wifi()
    elif os_type == OSType.LINUX:
        return _linux_disconnect_wifi()
    else:
        return f"❌ Unsupported OS: {os_type.value}"


def reconnect_wifi() -> str:
    """
    Attempt to reconnect to a known WiFi network.
    Works on Windows and Linux.
    """
    os_type = get_os_type()
    
    if os_type == OSType.WINDOWS:
        return _windows_reconnect_wifi()
    elif os_type == OSType.LINUX:
        return _linux_reconnect_wifi()
    else:
        return f"❌ Unsupported OS: {os_type.value}"


def scan_networks() -> str:
    """
    Scan for available WiFi networks.
    Works on Windows and Linux.
    """
    os_type = get_os_type()
    
    if os_type == OSType.WINDOWS:
        return _windows_scan_networks()
    elif os_type == OSType.LINUX:
        return _linux_scan_networks()
    else:
        return f"❌ Unsupported OS: {os_type.value}"


def get_connection_status() -> str:
    """
    Get current network connection status.
    Works on Windows and Linux.
    """
    os_type = get_os_type()
    
    if os_type == OSType.WINDOWS:
        return _windows_get_connection_status()
    elif os_type == OSType.LINUX:
        return _linux_get_connection_status()
    else:
        return f"❌ Unsupported OS: {os_type.value}"


# =============================================================================
# Security Protocols
# =============================================================================

def blackout_mode() -> str:
    """
    🔒 BLACKOUT PROTOCOL
    
    Immediately disconnects all wireless connections for security purposes.
    This is a critical security feature for airgapped operation.
    
    Use cases:
    - Preventing remote access during sensitive operations
    - Isolating compromised systems
    - Preparing for secure local-only robot communication
    """
    result = disconnect_wifi()
    
    if "Disconnected" in result or "📡" in result:
        return f"🔒 BLACKOUT PROTOCOL ACTIVATED\n\n{result}\n\nSystem is now isolated from wireless networks."
    else:
        return f"⚠️ BLACKOUT PROTOCOL WARNING\n\n{result}\n\nManual verification recommended."


def secure_reconnect() -> str:
    """
    🔓 SECURE RECONNECT PROTOCOL
    
    Attempts to restore network connectivity to a known, trusted network.
    Should only be used when the operator confirms it's safe to reconnect.
    """
    result = reconnect_wifi()
    
    if "✅" in result:
        return f"🔓 SECURE RECONNECT COMPLETE\n\n{result}"
    else:
        return f"⚠️ RECONNECT STATUS\n\n{result}"


# =============================================================================
# Testing
# =============================================================================

if __name__ == "__main__":
    from .platform_utils import print_system_summary
    
    print_system_summary()
    print("\n")
    print("Testing network status...")
    print(get_connection_status())
