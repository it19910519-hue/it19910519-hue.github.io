from config import config

def is_admin(user_id: int) -> bool:
    return user_id == config.admin_id