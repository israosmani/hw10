import pytest
from pydantic import ValidationError
from uuid import UUID
from app.schemas.user_schemas import (
    UserBase,
    UserCreate,
    UserUpdate,
    UserResponse,
    LoginRequest,
)

# UserBase Tests
def test_user_base_initialization():
    data = {
        "email": "alice@example.com",
        "nickname": "alice123",
        "first_name": "Alice",
        "last_name": "Doe",
        "bio": "A passionate coder.",
        "profile_picture_url": "https://example.com/alice.jpg",
    }
    user = UserBase(**data)
    assert user.email == data["email"]
    assert user.nickname == data["nickname"]

def test_user_base_invalid_email_format():
    data = {"email": "invalid-email", "nickname": "nick123"}
    with pytest.raises(ValidationError) as exc:
        UserBase(**data)
    assert "value is not a valid email address" in str(exc.value)

# UserCreate Tests
def test_user_create_with_password():
    data = {
        "email": "bob@example.com",
        "nickname": "bob_the_builder",
        "password": "ComplexPassword1!",
        "first_name": "Bob",
        "last_name": "Builder",
    }
    user = UserCreate(**data)
    assert user.password == data["password"]

# UserUpdate Tests
def test_user_update_fields():
    data = {
        "email": "updated_bob@example.com",
        "nickname": "updated_bob",
        "bio": "Experienced in building.",
    }
    user_update = UserUpdate(**data)
    assert user_update.nickname == data["nickname"]
    assert user_update.email == data["email"]

# UserResponse Tests
def test_user_response_valid_data():
    data = {
        "id": UUID("f47ac10b-58cc-4372-a567-0e02b2c3d479"),
        "email": "charlie@example.com",
        "nickname": "charlie123",
        "role": "USER",
        "bio": "Explorer.",
        "profile_picture_url": "https://example.com/charlie.jpg",
    }
    user = UserResponse(**data)
    assert user.id == data["id"]
    assert user.email == data["email"]

# LoginRequest Tests
def test_login_request_validation():
    data = {"email": "user@example.com", "password": "Password123!"}
    login = LoginRequest(**data)
    assert login.email == data["email"]

# Parametrized Tests for Nickname Validation
@pytest.mark.parametrize("nickname", ["validNick", "valid_nick", "valid123"])
def test_valid_nickname(nickname):
    data = {"email": "user@example.com", "nickname": nickname}
    user = UserBase(**data)
    assert user.nickname == nickname

@pytest.mark.parametrize("nickname", ["inv@lid", "", "ab"])
def test_invalid_nickname(nickname):
    data = {"email": "user@example.com", "nickname": nickname}
    with pytest.raises(ValidationError):
        UserBase(**data)

# Parametrized Tests for URL Validation
@pytest.mark.parametrize(
    "url", ["https://example.com/image.jpg", "http://example.com/photo.png", None]
)
def test_valid_profile_picture_url(url):
    data = {"email": "test@example.com", "profile_picture_url": url}
    user = UserBase(**data)
    assert user.profile_picture_url == url

@pytest.mark.parametrize("url", ["invalid-url", "ftp://example.com/image.jpg"])
def test_invalid_profile_picture_url(url):
    data = {"email": "test@example.com", "profile_picture_url": url}
    with pytest.raises(ValidationError):
        UserBase(**data)
