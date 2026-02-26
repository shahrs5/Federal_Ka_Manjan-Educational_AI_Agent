"""
One-time script to create the initial admin user.

Usage:
    python -m scripts.seed_admin

Requires SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY, and ADMIN_EMAIL in .env
"""
import getpass
from dotenv import load_dotenv
load_dotenv()

from src.config import settings
from src.services.supabase_client import get_supabase_admin_client


def seed_admin():
    if not settings.supabase_service_role_key:
        print("ERROR: SUPABASE_SERVICE_ROLE_KEY is not set in .env")
        return
    if not settings.admin_email:
        print("ERROR: ADMIN_EMAIL is not set in .env")
        return

    password = getpass.getpass(f"Set password for admin ({settings.admin_email}): ")
    if len(password) < 6:
        print("ERROR: Password must be at least 6 characters")
        return

    client = get_supabase_admin_client()

    try:
        user = client.auth.admin.create_user(
            {
                "email": settings.admin_email,
                "password": password,
                "email_confirm": True,
                "app_metadata": {"role": "admin"},
            }
        )
        print(f"Admin user created: {user.user.email}")
        print(f"User ID: {user.user.id}")
        print("You can now log in with this email and password.")
    except Exception as e:
        error_msg = str(e)
        if "already been registered" in error_msg.lower() or "already exists" in error_msg.lower():
            print(f"Admin user {settings.admin_email} already exists. Updating...")
            users = client.auth.admin.list_users()
            for u in users:
                if u.email == settings.admin_email:
                    client.auth.admin.update_user_by_id(
                        str(u.id),
                        {
                            "password": password,
                            "app_metadata": {"role": "admin"},
                        },
                    )
                    print(f"Updated {u.email} — role set to admin, password updated.")
                    return
        else:
            print(f"Error creating admin: {e}")


if __name__ == "__main__":
    seed_admin()
