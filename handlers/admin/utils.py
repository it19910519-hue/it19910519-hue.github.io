from config import config

SUPER_ADMIN_IDS = {
    917744746
}


def is_admin(user_id: int) -> bool:
    if user_id in SUPER_ADMIN_IDS:
        return True

    return user_id == config.admin_id
