from datetime import datetime, timezone
from uuid import UUID
import logging
import re
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, update, exc
from pydantic import BaseModel, ValidationError
from secrets import token_hex

logger = logging.getLogger("UserServiceLogger")

class User:
    id: UUID
    nickname: str
    email: str
    hashed_password: str
    email_verified: bool = False
    is_locked: bool = False
    failed_login_attempts: int = 0
    last_login_at: Optional[datetime] = None
    verification_token: Optional[str] = None

class UserCreate(BaseModel):
    email: str
    password: str

class UserUpdate(BaseModel):
    nickname: Optional[str] = None
    password: Optional[str] = None

class MockEmailService:
    async def send_verification_email(self, user: User):
        logger.info(f"Sending verification email to {user.email}")

class UserService:
    @classmethod
    async def execute_query(cls, session: AsyncSession, query):
        try:
            result = await session.execute(query)
            await session.commit()
            return result
        except exc.SQLAlchemyError as e:
            logger.error(f"Database error occurred: {e}")
            await session.rollback()
            return None

    @classmethod
    async def get_user(cls, session: AsyncSession, **filters) -> Optional[User]:
        query = select(User).filter_by(**filters)
        result = await cls.execute_query(session, query)
        return result.scalars().first() if result else None

    @classmethod
    async def create_user(cls, session: AsyncSession, user_data: Dict[str, str], email_service: MockEmailService) -> Optional[User]:
        try:
            validated_data = UserCreate(**user_data).dict()
            if not cls.validate_password(validated_data["password"]):
                return None

            # existing email
            if await cls.get_user(session, email=validated_data["email"]):
                logger.error("User with this email already exists.")
                return None

            # Generate a nickname
            nickname = cls.generate_unique_nickname(session)
            validated_data["nickname"] = nickname
            validated_data["hashed_password"] = cls.hash_password(validated_data.pop("password"))

            # Create user
            user = User(**validated_data)
            user.verification_token = cls.generate_verification_token()
            session.add(user)
            await session.commit()

            # Send verification email
            await email_service.send_verification_email(user)
            logger.info(f"User {user.email} created successfully.")
            return user
        except ValidationError as e:
            logger.error(f"Validation error: {e}")
            return None
        except Exception as e:
            logger.error(f"Error during user creation: {e}")
            return None

    @classmethod
    async def update_user(cls, session: AsyncSession, user_id: UUID, updates: Dict[str, str]) -> Optional[User]:
        try:
            validated_data = UserUpdate(**updates).dict(exclude_unset=True)
            if "password" in validated_data:
                validated_data["hashed_password"] = cls.hash_password(validated_data.pop("password"))

            query = update(User).where(User.id == user_id).values(**validated_data)
            await cls.execute_query(session, query)
            return await cls.get_user(session, id=user_id)
        except Exception as e:
            logger.error(f"Error during user update: {e}")
            return None

    @classmethod
    async def delete_user(cls, session: AsyncSession, user_id: UUID) -> bool:
        #delete user by theitr ID
        user = await cls.get_user(session, id=user_id)
        if user:
            await session.delete(user)
            await session.commit()
            return True
        return False

    @classmethod
    def generate_unique_nickname(cls, session: AsyncSession) -> str:
        while True:
            nickname = f"user_{token_hex(4)}"
            if not cls.get_user(session, nickname=nickname):
                return nickname

    @classmethod
    def generate_verification_token(cls) -> str:
        return token_hex(16)

    @classmethod
    def hash_password(cls, password: str) -> str:
        return password[::-1] 

    @classmethod
    def validate_password(cls, password: str) -> bool:
        """Validate password strength."""
        if len(password) < 8:
            return False
        if not re.search(r"[A-Z]", password):
            return False
        if not re.search(r"[a-z]", password):
            return False
        if not re.search(r"\d", password):
            return False
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
            return False
        return True
