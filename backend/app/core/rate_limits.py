import asyncio
from urllib.parse import quote
import redis.asyncio as redis
from app.core.config import settings
from app.core.errors import DomainError
s=settings()
redis_client=redis.from_url(s.redis_url or f"redis://:{quote(s.secret(s.redis_password_file),safe='')}@{s.redis_host}:6379/0",socket_connect_timeout=2,socket_timeout=2,decode_responses=True)
semaphore=asyncio.Semaphore(s.ai_max_concurrency)
async def reserve_ai(tokens):
    try:
        accepted=await redis_client.eval("""
        local r=tonumber(redis.call('GET',KEYS[1]) or '0')
        local t=tonumber(redis.call('GET',KEYS[2]) or '0')
        if r+1>tonumber(ARGV[1]) or t+tonumber(ARGV[3])>tonumber(ARGV[2]) then return 0 end
        redis.call('INCR',KEYS[1]); redis.call('INCRBY',KEYS[2],ARGV[3])
        if r==0 then redis.call('EXPIRE',KEYS[1],60) end
        if t==0 then redis.call('EXPIRE',KEYS[2],60) end
        return 1
        """,2,"ai:requests","ai:tokens",s.openai_rpm_limit,s.openai_tpm_limit,tokens)
    except redis.RedisError:raise DomainError("AI_UNAVAILABLE","AI coordination is temporarily unavailable",503)
    if not accepted:raise DomainError("AI_QUOTA","AI is busy. Use the booking controls or retry shortly.",429)
