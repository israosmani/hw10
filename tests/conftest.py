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
import datetime
import uuid

# Third-party imports
import pytest
from faker import Faker
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from passlib.hash import bcrypt

# Application-specific imports
from app.main import app
from app.database import Base
from app.models.user_model import User, UserRole
from app.dependencies import get_db
from app.utils.template_manager import TemplateManager
from app.services.email_service import EmailService
from app.services.jwt_service import create_access_token

fake = Faker()

# Configure database for tests
TEST_DB_URL = app.state.settings.database_url.replace("postgresql://", "postgresql+asyncpg://")
engine = create_async_engine(TEST_DB_URL, echo=app.state.settings.debug)
SessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

# Utility function for password hashing
def generate_hashed_password(password: str) -> str:
    return bcrypt.hash(password)

# Fixtures for email services
@pytest.fixture
def email_service_fixture():
    return EmailService(template_manager=TemplateManager())

# Database setup and teardown
@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

# Database session for each test
@pytest.fixture(scope="function")
async def db_session_fixture():
    async with SessionLocal() as session:
        yield session

# HTTP client for testing FastAPI routes
@pytest.fixture(scope="function")
async def test_client(db_session_fixture):
    app.dependency_overrides[get_db] = lambda: db_session_fixture
    async with AsyncClient(app=app, base_url="http://testserver") as client:
        yield client
    app.dependency_overrides.clear()

# Generate test users
@pytest.fixture(scope="function")
async def create_user(db_session_fixture, email_verified=False, is_locked=False, role=UserRole.AUTHENTICATED):
    user = User(
        nickname=fake.user_name(),
        first_name=fake.first_name(),
        last_name=fake.last_name(),
        email=fake.email(),
        hashed_password=generate_hashed_password("Password$123"),
        email_verified=email_verified,
        is_locked=is_locked,
        role=role
    )
    db_session_fixture.add(user)
    await db_session_fixture.commit()
    return user

# Specific user types
@pytest.fixture(scope="function")
async def locked_user_fixture(db_session_fixture):
    return await create_user(db_session_fixture, is_locked=True)

@pytest.fixture(scope="function")
async def regular_user_fixture(db_session_fixture):
    return await create_user(db_session_fixture)

@pytest.fixture(scope="function")
async def admin_user_fixture(db_session_fixture):
    return await create_user(db_session_fixture, role=UserRole.ADMIN)

@pytest.fixture(scope="function")
async def verified_user_fixture(db_session_fixture):
    return await create_user(db_session_fixture, email_verified=True)

@pytest.fixture(scope="function")
async def manager_user_fixture(db_session_fixture):
    return await create_user(db_session_fixture, role=UserRole.MANAGER, email_verified=True)

# Generate JWT tokens
@pytest.fixture(scope="function")
async def generate_token(db_session_fixture, create_user):
    async def _generate_token(user_role=UserRole.AUTHENTICATED):
        user = await create_user(db_session_fixture, role=user_role)
        token = create_access_token(data={"sub": user.email, "role": user.role.name})
        return token
    return _generate_token

# Generate multiple users of the same role
@pytest.fixture(scope="function")
async def create_multiple_users(db_session_fixture):
    async def _create_multiple_users(role, count=50):
        users = []
        for _ in range(count):
            user = User(
                nickname=fake.user_name(),
                first_name=fake.first_name(),
                last_name=fake.last_name(),
                email=fake.email(),
                hashed_password=generate_hashed_password("Password123"),
                role=role
            )
            db_session_fixture.add(user)
            users.append(user)
        await db_session_fixture.commit()
        return users
    return _create_multiple_users

# Static test data
@pytest.fixture
def user_creation_data():
    return {"username": "john_doe", "password": "SecurePassword123!"}

@pytest.fixture
def user_update_data_fixture():
    return {
        "email": "john.doe.updated@example.com",
        "bio": "Experienced software developer with a knack for APIs.",
    }

@pytest.fixture
def login_data_fixture():
    return {"username": "john_doe", "password": "SecurePassword123!"}