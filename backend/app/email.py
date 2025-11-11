from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from pydantic import EmailStr

from .config import get_settings
from .logging_config import logger
from .models import User

# Get all our mail settings from the config
settings = get_settings()

# Create the ConnectionConfig object
conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_FROM_NAME=settings.MAIL_FROM_NAME,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
)


async def send_verification_email(email_to: EmailStr, user: User, token: str):
    """
    Sends the verification email to a new user.
    """

    # Simple HTML template for the email
    html_template = f"""
    <html>
        <body>
            <div style="font-family: Arial, sans-serif; line-height: 1.6;">
                <h2>Hello, {user.full_name or user.email}!</h2>
                <p>Welcome to our application! We're excited to have you.</p>
                <p>Please click the button below to verify your email address:</p>
                <a href="http://localhost:8000/auth/verify?token={token}" 
                   style="background-color: #007BFF; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; display: inline-block;">
                    Verify Your Email
                </a>
                <p>If the button doesn't work, copy and paste this link into your browser:</p>
                <p style="color: #666; font-size: 12px;">http://localhost:8000/auth/verify?token={token}</p>
                <p>If you did not create an account, please ignore this email.</p>
                <p>Thanks,<br>The Team</p>
            </div>
        </body>
    </html>
    """

    # Create the email message
    message = MessageSchema(
        subject="Verify Your Email Address",
        recipients=[email_to],
        body=html_template,
        subtype=MessageType.html,
    )

    # Initialize FastMail and send
    fm = FastMail(conf)
    try:
        logger.info(f"📧 Sending verification email to {email_to} ...")
        await fm.send_message(message)
        logger.success(f"✅ Verification email successfully sent to {email_to}")
    except Exception as e:
        logger.error(f"❌ Error sending verification email to {email_to}: {e}")
        pass
