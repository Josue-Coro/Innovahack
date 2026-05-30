import bcrypt

def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Truncate plain password to 72 bytes to match creation logic
    password_bytes = plain_password.encode('utf-8')[:72]
    hashed_password_bytes = hashed_password.encode('utf-8')
    return bcrypt.checkpw(password_bytes, hashed_password_bytes)

def get_password_hash(password: str) -> str:
    # bcrypt has a 72-byte limit, so we truncate it just in case
    password_bytes = password.encode('utf-8')[:72]
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password_bytes, salt).decode('utf-8')
