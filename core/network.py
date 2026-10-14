"""
core/network.py - Local IP and WiFi SSID network detection.
"""
import socket
import subprocess
import re
import logging
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)

def get_local_ips() -> List[Tuple[str, str]]:
    """
    Get available local IPv4 addresses.
    Returns list of tuples: (interface_label, ip_address).
    Filters out 127.0.0.1 loopback unless no other interfaces exist.
    """
    results: List[Tuple[str, str]] = []
    seen = set()

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
            s.settimeout(0.5)

            s.connect(("8.8.8.8", 80))
            primary_ip = s.getsockname()[0]
            if primary_ip and primary_ip not in seen and not primary_ip.startswith("127."):
                results.append(("Primary / Default Route", primary_ip))
                seen.add(primary_ip)
    except Exception:
        pass

    try:
        hostname = socket.gethostname()
        _, _, ip_list = socket.gethostbyname_ex(hostname)
        for ip in ip_list:
            if ip not in seen and not ip.startswith("127."):
                results.append((f"Interface ({ip})", ip))
                seen.add(ip)
    except Exception as e:
        logger.debug(f"Error querying host IPs: {e}")

    if not results:
        results.append(("Localhost", "127.0.0.1"))

    return results

def get_wifi_ssid() -> Optional[str]:
    """
    Query currently connected WiFi SSID on Windows via `netsh wlan show interfaces`.
    Returns SSID string if connected, or None if disconnected/unsupported.
    """
    try:

        proc = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False
        )
        if proc.returncode != 0:
            return None

        for line in proc.stdout.splitlines():
            line_strip = line.strip()

            if line_strip.startswith("SSID") and not line_strip.startswith("BSSID"):
                parts = line_strip.split(":", 1)
                if len(parts) == 2:
                    ssid = parts[1].strip()
                    if ssid:
                        return ssid
    except Exception as e:
        logger.debug(f"Unable to query WiFi SSID: {e}")
    return None
