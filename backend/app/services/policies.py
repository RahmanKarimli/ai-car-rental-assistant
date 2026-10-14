from uuid import uuid4
import tiktoken
from sqlalchemy import select,or_,func
from app.models import PolicyDocument,PolicyChunk
from app.providers.openai_embeddings import embeddings
from app.services.audit import now
from app.core.security import digest
from app.core.config import settings

async def ingest(db,document):
    existing=await db.scalar(select(PolicyChunk.id).where(PolicyChunk.document_id==document.id).limit(1))
    if existing:return
    enc=tiktoken.get_encoding("cl100k_base")
    segments=[]
    current_section=document.topic
    for part in document.full_text.split("\n#"):
        heading=part.splitlines()[0] if part.splitlines() else current_section
        tokens=enc.encode(part)
        for start in range(0,len(tokens),520):segments.append((heading,enc.decode(tokens[start:start+600])))
    for start in range(0,len(segments),16):
        group=segments[start:start+16]
        vectors=await embeddings.embed([body for _,body in group])
        for offset,((section,content),vector) in enumerate(zip(group,vectors)):
            db.add(PolicyChunk(document_id=document.id,chunk_index=start+offset,content=content,section_reference=section,
                search_vector=func.to_tsvector("english" if document.language=="en" else "simple",content),embedding=vector,
                embedding_model=settings().openai_embedding_model,content_hash=digest(content)))
    await db.flush()
async def retrieve(db,query,language,branch_id=None):
    vector=(await embeddings.embed([query]))[0]
    conditions=[PolicyDocument.status=="PUBLISHED",PolicyDocument.language==language,PolicyDocument.effective_from<=now(),or_(PolicyDocument.effective_until.is_(None),PolicyDocument.effective_until>now())]
    if branch_id:conditions.append(or_(PolicyDocument.branch_id.is_(None),PolicyDocument.branch_id==branch_id))
    else:conditions.append(PolicyDocument.branch_id.is_(None))
    base=select(PolicyChunk,PolicyDocument).join(PolicyDocument).where(*conditions)
    dense=(await db.execute(base.order_by(PolicyChunk.embedding.cosine_distance(vector)).limit(12))).all()
    tsquery=func.plainto_tsquery("english" if language=="en" else "simple",query)
    sparse=(await db.execute(base.where(PolicyChunk.search_vector.op("@@")(tsquery)).order_by(func.ts_rank_cd(PolicyChunk.search_vector,tsquery).desc()).limit(12))).all()
    scores={};items={}
    for result in [dense,sparse]:
        for rank,(chunk,document) in enumerate(result):
            scores[chunk.id]=scores.get(chunk.id,0)+1/(60+rank+1);items[chunk.id]=(chunk,document)
    return [{"source_id":str(chunk.id),"document":doc.document_key,"version":doc.version,"section":chunk.section_reference,"content":chunk.content} for chunk,doc in [items[id] for id in sorted(scores,key=scores.get,reverse=True)[:5]]]
