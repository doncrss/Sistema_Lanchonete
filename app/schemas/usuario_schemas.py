from pydantic import BaseModel, ConfigDict


class ClienteCreate(BaseModel):
    nome: str
    contato: str
    endereco: str


class ClienteUpdate(BaseModel):
    nome: str | None = None
    contato: str | None = None
    endereco: str | None = None


class ClienteResponse(BaseModel):
    id: int
    nome: str
    contato: str
    endereco: str

    model_config = ConfigDict(from_attributes=True)


class FuncionarioCreate(BaseModel):
    nome: str
    funcao_praticada: str
    cargo: str
    fk_pedido: int | None = None


class FuncionarioUpdate(BaseModel):
    nome: str | None = None
    funcao_praticada: str | None = None
    cargo: str | None = None
    fk_pedido: int | None = None


class FuncionarioResponse(BaseModel):
    id: int
    nome: str
    funcao_praticada: str
    cargo: str
    fk_pedido: int | None = None

    model_config = ConfigDict(from_attributes=True)