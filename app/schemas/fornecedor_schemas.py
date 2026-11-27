from pydantic import BaseModel, ConfigDict, Field


class FornecedorCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    contato: str = Field(min_length=2, max_length=120)


class FornecedorUpdate(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    contato: str | None = Field(default=None, min_length=2, max_length=120)


class FornecedorResponse(BaseModel):
    id: int
    nome: str
    contato: str

    model_config = ConfigDict(from_attributes=True)
