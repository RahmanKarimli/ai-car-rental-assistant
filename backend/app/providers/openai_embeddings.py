import tiktoken
from openai import AsyncOpenAI, OpenAIError
from app.core.config import settings
from app.core.errors import DomainError
from app.core.rate_limits import reserve_ai,semaphore
s=settings()
class OpenAIEmbeddings:
    async def embed(self,inputs):
        if not s.api_key:raise DomainError("AI_NOT_CONFIGURED","Configure OpenAI before policy embedding",503)
        enc=tiktoken.get_encoding("cl100k_base")
        await reserve_ai(sum(len(enc.encode(x)) for x in inputs))
        try:
            async with AsyncOpenAI(api_key=s.api_key,base_url=s.openai_base_url,timeout=s.openai_timeout_seconds,max_retries=s.openai_max_retries) as client:
                async with semaphore:
                    response=await client.embeddings.create(model=s.openai_embedding_model,input=inputs,dimensions=1536)
            return [x.embedding for x in sorted(response.data,key=lambda x:x.index)]
        except OpenAIError:raise DomainError("EMBEDDINGS_UNAVAILABLE","Policy embeddings are temporarily unavailable",503)
embeddings=OpenAIEmbeddings()
