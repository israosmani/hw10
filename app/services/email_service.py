import os  
from unittest.mock import AsyncMock  
from settings.config import settings  
from app.utils.smtp_connection import SMTPClient  
from app.utils.template_manager import TemplateManager  
from app.models.user_model import User  

class EmailService:
    def __init__(self, template_manager: TemplateManager):
        mock_email = os.getenv("MOCK_EMAIL", "false").lower() == "true"
        if mock_email:
            print("Email service is operating in mock mode for testing.")
            self.smtp_client = AsyncMock()  
        elif all([settings.smtp_server, settings.smtp_port, 
                  settings.smtp_username, settings.smtp_password]):
            self.smtp_client = SMTPClient(
                server=settings.smtp_server,
                port=settings.smtp_port,
                username=settings.smtp_username,
                password=settings.smtp_password
            )
        else:
            print("SMTP configuration is incomplete. Email functionality disabled.")
            self.smtp_client = None

        self.template_manager = template_manager

    async def send_email_to_user(self, user_info: dict, email_category: str):
        if not self.smtp_client:
            return
        
        email_subjects = {
            'email_verification': "Verify Your Account",
            'password_reset': "Password Reset Instructions",
            'account_locked': "Account Locked Notification"
        }

        if email_category not in email_subjects:
            raise ValueError(f"Invalid email category: {email_category}")

        html_body = self.template_manager.render_template(email_category, **user_info)
        recipient_email = user_info.get("email")
        
        await self.smtp_client.send_email(
            subject=email_subjects[email_category],
            content=html_body,
            recipient=recipient_email
        )

    async def send_verification_email(self, user: User):
        if not self.smtp_client:
            return

        verification_link = (
            f"{settings.server_base_url}verify-email/{user.id}/{user.verification_token}"
        )
        await self.send_email_to_user({
            "name": user.first_name,
            "verification_url": verification_link,
            "email": user.email
        }, 'email_verification')