from pydantic import BaseModel, ConfigDict, Field


class ProdutoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    tipo: str = Field(min_length=2, max_length=60)
    preco: float = Field(ge=0, le=10000, allow_inf_nan=False)


class ProdutoUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    tipo: str | None = Field(default=None, min_length=2, max_length=60)
    preco: float | None = Field(default=None, ge=0, le=10000, allow_inf_nan=False)


class ProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    preco: float

    model_config = ConfigDict(from_attributes=True)