"""
core/qr_generator.py - SMB and WiFi QR code payload generator and pixmap renderer.
"""
from io import BytesIO
from typing import Dict, Any, Optional
import json
import qrcode
from PySide6.QtGui import QPixmap, QImage
from core.session import ShareSession

def build_smb_payload(session: ShareSession) -> Dict[str, Any]:
    """
    Build structured JSON payload for SMB Share corresponding to PRD §8.1.
    Format:
    {
        "v": int,
        "host": str,
        "port": int,
        "share": str,
        "user": str,
        "pass": str,
        "ro": bool,
        "exp": int  # epoch timestamp or 0 for permanent
    }
    """
    return {
        "v": 1,
        "host": session.host_ip or "127.0.0.1",
        "port": session.port,
        "share": session.share_name,
        "user": session.username,
        "pass": session.password,
        "ro": session.read_only,
        "exp": session.expires_at,
    }

def escape_wifi_string(value: str) -> str:
    r"""
    Escape special characters for standard WiFi QR code format:
    Characters: \, ;, ,, :
    """
    res = []
    for char in value:
        if char in ("\\", ";", ",", ":"):
            res.append(f"\\{char}")
        else:
            res.append(char)
    return "".join(res)

def build_wifi_payload(ssid: str, security: str = "WPA", password: str = "", hidden: bool = False) -> str:
    r"""
    Build standard WiFi QR code string payload corresponding to PRD §8.2.
    Format: WIFI:T:<sec>;S:<ssid>;P:<password>;H:<hidden>;;
    Special characters (;, ,, :, \) are escaped.
    """
    esc_ssid = escape_wifi_string(ssid)
    sec_type = security.upper()
    if sec_type not in ("WPA", "WEP", "NOPASS"):
        sec_type = "WPA"

    parts = ["WIFI:"]
    parts.append(f"T:{sec_type};")
    parts.append(f"S:{esc_ssid};")
    if sec_type != "NOPASS" and password:
        esc_pass = escape_wifi_string(password)
        parts.append(f"P:{esc_pass};")
    if hidden:
        parts.append("H:true;")
    parts.append(";")
    return "".join(parts)

def render_to_pixmap(data_str: str, box_size: int = 10, border: int = 4) -> QPixmap:
    """
    Renders string data into a QPixmap QR code.
    Uses Pillow to create the QR image in memory and converts it to QPixmap.
    """
    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=box_size,
        border=border,
    )
    qr.add_data(data_str)
    qr.make(fit=True)

    pil_img = qr.make_image(fill_color="black", back_color="white").convert("RGBA")

    data = pil_img.tobytes("raw", "RGBA")
    qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qimg)
