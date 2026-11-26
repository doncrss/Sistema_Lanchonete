from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ClienteCheckout(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    contato: str = Field(min_length=8, max_length=40)
    endereco: str = Field(default="", max_length=240)


class ItemPedidoInput(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0, le=50)
    observacao: str | None = Field(default=None, max_length=240)
    combo_id: int | None = Field(default=None, gt=0)
    variacao_ids: list[int] = Field(default_factory=list, max_length=10)


class PedidoCheckout(BaseModel):
    local: Literal["entrega", "retirada", "mesa"] = "entrega"
    cliente: ClienteCheckout
    itens: list[ItemPedidoInput] = Field(min_length=1, max_length=30)


class StatusPedidoUpdate(BaseModel):
    status: Literal[
        "recebido",
        "em_preparo",
        "pronto",
        "saiu_para_entrega",
        "concluido",
        "cancelado",
    ]


class ItemPedidoResponse(BaseModel):
    id: int
    produto_id: int
    nome: str
    quantidade: int
    preco_unitario: float
    subtotal: float
    observacao: str | None
    variacao: str | None
    is_combo: bool


class PedidoResponse(BaseModel):
    id: int
    local: str
    status: str
    data_hora: str
    cliente_nome: str
    cliente_contato: str
    endereco_entrega: str | None
    itens: list[ItemPedidoResponse]
    total: float

    model_config = ConfigDict(from_attributes=True)
