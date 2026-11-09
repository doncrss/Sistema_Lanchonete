from pydantic import BaseModel, ConfigDict


class ProdutoCreate(BaseModel):
    nome: str
    tipo: str
    preco: float


class ProdutoUpdate(BaseModel):
    nome: str | None = None
    tipo: str | None = None
    preco: float | None = None


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    preco: float

    model_config = ConfigDict(from_attributes=True)