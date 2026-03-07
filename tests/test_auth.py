"""
Tests for authentication: hash_pin, verify_pin, create/decode token, login endpoint.
"""
import pytest
from fastapi import HTTPException

from backend.app.services.auth_service import hash_pin, verify_pin, create_token, decode_token


# --- Unit tests ---

def test_hash_pin_is_consistent():
    assert hash_pin("1234") == hash_pin("1234")


def test_hash_pin_different_pins_differ():
    assert hash_pin("1234") != hash_pin("5678")


def test_verify_pin_correct():
    h = hash_pin("9999")
    assert verify_pin("9999", h) is True


def test_verify_pin_wrong_pin():
    h = hash_pin("9999")
    assert verify_pin("0000", h) is False


def test_create_decode_token_roundtrip():
    token = create_token(user_id=42, name="Alice")
    data = decode_token(token)
    assert data.user_id == 42
    assert data.name == "Alice"


def test_decode_invalid_token_raises_401():
    with pytest.raises(HTTPException) as exc_info:
        decode_token("not.a.valid.token")
    assert exc_info.value.status_code == 401


# --- Login endpoint ---

async def test_login_success(client, user):
    resp = await client.post("/api/auth/login", json={"name": "TestUser", "pin": "1234"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "TestUser"
    assert data["user_id"] == user.id
    assert "token" in data


async def test_login_wrong_pin(client, user):
    resp = await client.post("/api/auth/login", json={"name": "TestUser", "pin": "wrong"})
    assert resp.status_code == 401


async def test_login_unknown_user(client):
    resp = await client.post("/api/auth/login", json={"name": "Nobody", "pin": "1234"})
    assert resp.status_code == 401
