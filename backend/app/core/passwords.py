import asyncio
import bcrypt


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(lambda: bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode())


async def verify_password(plain: str, hashed: str) -> bool:
    return await asyncio.to_thread(lambda: bcrypt.checkpw(plain.encode(), hashed.encode()))
