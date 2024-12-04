"""
File: test_database_operations.py

Overview:
This Python test file utilizes pytest to manage database states and HTTP clients for testing a web application built with FastAPI and SQLAlchemy. It includes detailed fixtures to mock the testing environment, ensuring each test is run in isolation with a consistent setup.

Fixtures:
- `async_client`: Manages an asynchronous HTTP client for testing interactions with the FastAPI application.
- `db_session`: Handles database transactions to ensure a clean database state for each test.
- User fixtures (`user`, `locked_user`, `verified_user`, etc.): Set up various user states to test different behaviors under diverse conditions.
- `token`: Generates an authentication token for testing secured endpoints.
- `initialize_database`: Prepares the database at the session start.
- `setup_database`: Sets up and tears down the database before and after each test.
"""

# Standard library imports
import uuid
from datetime import datetime

# Third-party imports
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from faker import Faker

# Application-specific imports
from app.main import app
from app.database import Base, Database
from app.models.user_model import User, UserRole
from app.dependencies import get_db, get_settings
from app.utils.security import hash_password
from app.utils.template_manager import TemplateManager
from app.services.email_service import EmailService
from app.services.jwt_service import create_access_token

# Instantiate Faker for generating random data
fake = Faker()

# Configuration and setup
settings = get_settings()
TEST_DATABASE_URL = settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(TEST_DATABASE_URL, echo=settings.debug)
TestingSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Fixtures
@pytest.mark.email
@pytest.fixture
def email_service():
    """
    Provides an instance of the EmailService for testing.
    """
    return EmailService(template_manager=TemplateManager())

@pytest.fixture(scope="session", autouse=True)
def setup_database():
    """
    Initializes and cleans up the test database schema.
    """
    Database.initialize(TEST_DATABASE_URL)
    yield
    Database.shutdown()

@pytest.fixture(scope="function")
async def async_client(db_session):
    """
    Provides an async HTTP client for testing FastAPI endpoints.
    """
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        app.dependency_overrides[get_db] = lambda: db_session
        yield client
        app.dependency_overrides.clear()

@pytest.fixture(scope="function")
async def db_session():
    """
    Provides a scoped async database session for each test.
    """
    async with TestingSessionLocal() as session:
        yield session

@pytest.fixture(scope="function")
async def create_test_user(db_session, is_verified=False, is_locked=False, role=UserRole.AUTHENTICATED):
    """
    Helper to create a test user with customizable attributes.
    """
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=hash_password("SecurePass123!"),
        role=role,
        email_verified=is_verified,
        is_locked=is_locked,
    )
    db_session.add(user)
    await db_session.commit()
    return user

@pytest.fixture
async def regular_user(db_session):
    """
    Provides a regular test user.
    """
    return await create_test_user(db_session)

@pytest.fixture
async def admin_user(db_session):
    """
    Provides an admin test user.
    """
    return await create_test_user(db_session, role=UserRole.ADMIN)

@pytest.fixture
async def locked_user(db_session):
    """
    Provides a locked test user.
    """
    return await create_test_user(db_session, is_locked=True)

@pytest.fixture
async def verified_user(db_session):
    """
    Provides a verified test user.
    """
    return await create_test_user(db_session, is_verified=True)

@pytest.fixture(scope="function")
async def user_token(regular_user):
    """
    Generates a token for a regular test user.
    """
    return create_access_token(data={"sub": regular_user.email, "role": regular_user.role.name})

@pytest.fixture(scope="function")
async def admin_token(admin_user):
    """
    Generates a token for an admin test user.
    """
    return create_access_token(data={"sub": admin_user.email, "role": admin_user.role.name})

@pytest.fixture(scope="function")
async def generate_multiple_users(db_session, count=50):
    """
    Creates multiple users with the same role for testing.
    """
    users = []
    for _ in range(count):
        user = User(
            nickname=fake.user_name(),
            first_name=fake.first_name(),
            last_name=fake.last_name(),
            email=fake.email(),
            hashed_password=hash_password(fake.password()),
            role=UserRole.AUTHENTICATED,
            email_verified=False,
            is_locked=False,
        )
        db_session.add(user)
        users.append(user)
    await db_session.commit()
    return users

@pytest.fixture
async def manager_user(db_session):
    """
    Provides a manager test user.
    """
    return await create_te