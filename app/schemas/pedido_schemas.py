from pydantic import BaseModel, ConfigDict

class PedidoCreate(BaseModel):
    local: str
    fk_cliente: int
    fk_cupom: int | None = None
    fk_mesa: int | None = None

class PedidoUpdate(BaseModel):
    local: str | None = None
    fk_cliente: int | None = None
    fk_cupom: int | None = None
    fk_mesa: int | None = None

class PedidoResponse(BaseModel):
    id: int
    local: str
    fk_cliente: int
    fk_cupom: int | None = None
    fk_mesa: int | None = None


    model_config = ConfigDict(from_attributes=True)

class CupomCreate(BaseModel):
    codigo: str
    desconto: float
    validade: str | None = None

class CupomUpdate(BaseModel):
    codigo: str | None = None
    desconto: float | None = None
    validade: str | None = None

class CupomResponse(BaseModel):
    id: int
    codigo: str
    desconto: float
    validade: str | None = None

    model_config = ConfigDict(from_attributes=True)