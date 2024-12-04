import pytest
from unittest.mock import AsyncMock
from app.dependencies import get_settings
from app.models.user_model import User
from app.services.user_service import UserService

pytestmark = pytest.mark.asyncio

# Test: Creating a user with valid data
@pytest.mark.email
async def test_create_user_valid_data(db_session, email_service):
    user_data = {
        "email": "valid_user@example.com",
        "password": "ValidPassword123!"
    }
    user = await UserService.create(db_session, user_data, email_service)
    assert user and user.email == user_data["email"]

# Alternative: Mocking email service in user creation
async def test_create_user_with_mocked_email_service(db_session):
    user_data = {
        "email": "valid_user@example.com",
        "password": "ValidPassword123!"
    }

    # Mock email service to prevent actual email sending
    mock_email_service = AsyncMock()
    mock_email_service.send_verification_email.return_value = None

    user = await UserService.create(db_session, user_data, mock_email_service)
    assert user and user.email == user_data["email"]

# Test: Creating a user with invalid data
async def test_create_user_invalid_data(db_session, email_service):
    user_data = {
        "nickname": "",  # Invalid nickname
        "email": "invalidemail",  # Invalid email format
        "password": "short"  # Short password
    }
    user = await UserService.create(db_session, user_data, email_service)
    assert user is None

# Test: Fetching user by ID
async def test_get_user_by_id_exists(db_session, user):
    result = await UserService.get_by_id(db_session, user.id)
    assert result.id == user.id

# Test: Handling user not found by ID
async def test_get_user_by_id_not_found(db_session):
    result = await UserService.get_by_id(db_session, "nonexistent-id")
    assert result is None

# Test: Fetching user by nickname
async def test_get_user_by_nickname_exists(db_session, user):
    result = await UserService.get_by_nickname(db_session, user.nickname)
    assert result.nickname == user.nickname

# Test: Handling user not found by nickname
async def test_get_user_by_nickname_not_found(db_session):
    result = await UserService.get_by_nickname(db_session, "non_existent_nickname")
    assert result is None

# Test: Fetching user by email
async def test_get_user_by_email_exists(db_session, user):
    result = await UserService.get_by_email(db_session, user.email)
    assert result.email == user.email

# Test: Handling user not found by email
async def test_get_user_by_email_not_found(db_session):
    result = await UserService.get_by_email(db_session, "non_existent_email@example.com")
    assert result is None

# Test: Validating user update
async def test_update_user_with_valid_data(db_session, user):
    new_email = "new_email@example.com"
    updated_user = await UserService.update(db_session, user.id, {"email": new_email})
    assert updated_user and updated_user.email == new_email

# Test: Invalid user update
async def test_update_user_with_invalid_data(db_session, user):
    updated_user = await UserService.update(db_session, user.id, {"email": "invalidemail"})
    assert updated_user is None

# Test: User deletion when user exists
async def test_delete_user_when_exists(db_session, user):
    deletion_status = await UserService.delete(db_session, user.id)
    assert deletion_status

# Test: Attempting to delete non-existent user
async def test_delete_user_when_not_exists(db_session):
    deletion_status = await UserService.delete(db_session, "non-existent-id")
    assert not deletion_status

# Test: Listing users with pagination
async def test_pagination_for_user_listing(db_session, users_with_same_role_50_users):
    page_1 = await UserService.list_users(db_session, skip=0, limit=10)
    page_2 = await UserService.list_users(db_session, skip=10, limit=10)
    assert len(page_1) == len(page_2) == 10
    assert page_1[0].id != page_2[0].id

# Test: Registering a user with valid data
@pytest.mark.email
async def test_register_user_valid_data(db_session, email_service):
    user_data = {
        "email": "register_valid_user@example.com",
        "password": "RegisterValid123!"
    }
    user = await UserService.register_user(db_session, user_data, email_service)
    assert user and user.email == user_data["email"]

# Test: Registering a user with invalid data
async def test_register_user_invalid_data(db_session, email_service):
    user_data = {
        "email": "invalidemail",  # Invalid email
        "password": "short"  # Invalid password
    }
    user = await UserService.register_user(db_session, user_data, email_service)
    assert user is None

# Test: Successful user login
async def test_login_user_valid(db_session, verified_user):
    credentials = {
        "email": verified_user.email,
        "password": "ValidPassword$1234"
    }
    logged_in_user = await UserService.login_user(db_session, credentials["email"], credentials["password"])
    assert logged_in_user is not None

# Test: Invalid email during login
async def test_login_user_invalid_email(db_session):
    user = await UserService.login_user(db_session, "nonexistent@noway.com", "Password123!")
    assert user is None

# Test: Invalid password during login
async def test_login_user_invalid_password(db_session, user):
    user = await UserService.login_user(db_session, user.email, "WrongPassword!")
    assert user is None

# Test: Account lock after max failed login attempts
async def test_lock_account_after_failed_attempts(db_session, verified_user):
    max_attempts = get_settings().max_login_attempts
    for _ in range(max_attempts):
        await UserService.login_user(db_session, verified_user.email, "wrongpassword")
    
    is_locked = await UserService.is_account_locked(db_session, verified_user.email)
    assert is_locked, "Account should be locked after reaching max failed attempts"

# Test: Resetting user password
async def test_password_reset(db_session, user):
    new_password = "NewSecurePassword123!"
    success = await UserService.reset_password(db_session, user.id, new_password)
    assert success

# Test: Verifying email with a token
async def test_email_verification(db_session, user):
    token = "valid_token_example"
    user.verification_token = token
    await db_session.commit()
    success = await UserService.verify_email_with_token(db_session, user.id, token)
    assert success

# Test: Unlocking a locked user account
async def test_unlock_account(db_session, locked_user):
    success = await UserService.unlock_user_account(db_session, locked_user.id)
    assert success
    refreshed_user = await UserService.get_by_id(db_session, locked_user.id)
    assert not refreshed_user.is_locked
