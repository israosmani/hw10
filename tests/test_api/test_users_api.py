from builtins import range, str
import pytest
from sqlalchemy import select
from httpx import AsyncClient
from urllib.parse import urlencode

from app.dependencies import get_settings
from app.models.user_model import User
from app.services.user_service import UserService
from app.utils.nickname_gen import generate_nickname
from app.services.jwt_service import decode_token

pytestmark = pytest.mark.asyncio

# User Service Tests
async def test_create_valid_user(db_session, email_service):
    payload = {
        "email": "valid_user@example.com",
        "password": "StrongPassword123!",
    }
    created_user = await UserService.create(db_session, payload, email_service)
    assert created_user is not None
    assert created_user.email == payload["email"]


async def test_create_user_invalid_payload(db_session, email_service):
    payload = {
        "nickname": "",
        "email": "invalidemail",
        "password": "short",
    }
    created_user = await UserService.create(db_session, payload, email_service)
    assert created_user is None


async def test_fetch_user_by_id_exists(db_session, user):
    fetched_user = await UserService.get_by_id(db_session, user.id)
    assert fetched_user is not None
    assert fetched_user.id == user.id


async def test_fetch_user_by_id_nonexistent(db_session):
    invalid_user_id = "non-existent-id"
    fetched_user = await UserService.get_by_id(db_session, invalid_user_id)
    assert fetched_user is None


async def test_fetch_user_by_nickname(db_session, user):
    fetched_user = await UserService.get_by_nickname(db_session, user.nickname)
    assert fetched_user.nickname == user.nickname


async def test_fetch_user_by_email(db_session, user):
    fetched_user = await UserService.get_by_email(db_session, user.email)
    assert fetched_user.email == user.email


async def test_update_user_email(db_session, user):
    new_email = "updated_email@example.com"
    updated_user = await UserService.update(db_session, user.id, {"email": new_email})
    assert updated_user is not None
    assert updated_user.email == new_email


async def test_delete_existing_user(db_session, user):
    result = await UserService.delete(db_session, user.id)
    assert result is True


async def test_paginated_user_list(db_session, users_with_same_role_50_users):
    first_batch = await UserService.list_users(db_session, skip=0, limit=10)
    second_batch = await UserService.list_users(db_session, skip=10, limit=10)
    assert len(first_batch) == 10
    assert len(second_batch) == 10
    assert first_batch[0].id != second_batch[0].id


# API Tests
@pytest.mark.asyncio
async def test_create_user_unauthorized(async_client, user_token):
    headers = {"Authorization": f"Bearer {user_token}"}
    payload = {
        "nickname": generate_nickname(),
        "email": "new_user@example.com",
        "password": "Secure$123Password!",
    }
    response = await async_client.post("/users/", json=payload, headers=headers)
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_retrieve_user_authorized(async_client, admin_user, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.get(f"/users/{admin_user.id}", headers=headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(admin_user.id)


@pytest.mark.asyncio
async def test_modify_user_email_authorized(async_client, admin_user, admin_token):
    updated_data = {"email": f"new_email_{admin_user.id}@example.com"}
    headers = {"Authorization": f"Bearer {admin_token}"}
    response = await async_client.put(f"/users/{admin_user.id}", json=updated_data, headers=headers)
    assert response.status_code == 200
    assert response.json()["email"] == updated_data["email"]


@pytest.mark.asyncio
async def test_successful_login(async_client, verified_user):
    credentials = {
        "username": verified_user.email,
        "password": "StrongPassword#1234",
    }
    response = await async_client.post(
        "/login/",
        data=urlencode(credentials),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"
    token_data = decode_token(response_data["access_token"])
    assert token_data is not None
    assert token_data["role"] == "AUTHENTICATED"


@pytest.mark.asyncio
async def test_failed_login_invalid_credentials(async_client):
    credentials = {
        "username": "nonexistentuser@domain.com",
        "password": "InvalidPassword123!",
    }
    response = await async_client.post(
        "/login/",
        data=urlencode(credentials),
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    assert response.status_code == 401
    assert "The email or password is incorrect" in response.json().get("detail", "")