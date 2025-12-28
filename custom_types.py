import pydantic

class RAGChunkAndSRC(pydantic.BaseModel):
    chunks: list[str]
    source_id: str = None


class RAGUpserResult(pydantic.BaseModel):
    ingested: int


class RAGSearchResult(pydantic.BaseModel):
    contexts: list[str]
    sources: list[str]

class RaGQueryResult(pydantic.BaseModel):
    answer: str
    sources: list[str]
    num_contexts: int
