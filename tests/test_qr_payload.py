"""
tests/test_qr_payload.py - Tests for QR payload generation and WiFi string formatting.
"""
import json
import pytest
from core.session import ShareSession
from core.qr_generator import build_smb_payload, build_wifi_payload, escape_wifi_string

def test_build_smb_payload_permanent():
    session = ShareSession(
        folder_path="C:\\Shared",
        username="usr12345",
        password="Pwd1234567890123",
        port=4455,
        read_only=True,
        timeout_minutes=0,
        host_ip="192.168.1.100"
    )
    payload = build_smb_payload(session)
    assert payload["v"] == 1
    assert payload["host"] == "192.168.1.100"
    assert payload["port"] == 4455
    assert payload["share"] == "SHARE"
    assert payload["user"] == "usr12345"
    assert payload["pass"] == "Pwd1234567890123"
    assert payload["ro"] is True
    assert payload["exp"] == 0

def test_build_smb_payload_with_timeout():
    session = ShareSession(
        folder_path="C:\\Shared",
        username="usr12345",
        password="Pwd1234567890123",
        port=4455,
        read_only=False,
        timeout_minutes=15,
        host_ip="192.168.1.50"
    )
    payload = build_smb_payload(session)
    assert payload["ro"] is False
    assert payload["v"] == 1
    assert payload["host"] == "192.168.1.50"
    assert isinstance(payload["exp"], int)
    assert payload["exp"] > 0
    assert payload["exp"] == session.expires_at

def test_escape_wifi_string():
    raw = r"My\Home:WiFi;Net,5G"
    escaped = escape_wifi_string(raw)
    assert escaped == r"My\\Home\:WiFi\;Net\,5G"

def test_build_wifi_payload_wpa():
    res = build_wifi_payload("Home;WiFi", "WPA", "secret;123")
    assert res == r"WIFI:T:WPA;S:Home\;WiFi;P:secret\;123;;"

def test_build_wifi_payload_nopass():
    res = build_wifi_payload("FreeCafe", "NOPASS", "")
    assert res == "WIFI:T:NOPASS;S:FreeCafe;;"

def test_build_wifi_payload_hidden():
    res = build_wifi_payload("SecretNet", "WPA", "password", hidden=True)
    assert res == "WIFI:T:WPA;S:SecretNet;P:password;H:true;;"
