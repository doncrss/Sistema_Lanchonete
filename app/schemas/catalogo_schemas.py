from pydantic import BaseModel, Field


class OpcaoVariacaoCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=50)
    valor: str = Field(min_length=1, max_length=60)
    adicional: float = Field(default=0, ge=0, le=10000, allow_inf_nan=False)


class OpcaoVariacaoResponse(OpcaoVariacaoCreate):
    id: int


class ItemComboInput(BaseModel):
    produto_id: int = Field(gt=0)
    quantidade: int = Field(gt=0, le=50)


class ComboCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=120)
    descricao: str = Field(default="", max_length=300)
    preco: float = Field(ge=0, le=10000, allow_inf_nan=False)
    itens: list[ItemComboInput] = Field(min_length=2, max_length=10)


class ItemComboResponse(BaseModel):
    produto_id: int
    nome: str
    quantidade: int


class ComboResponse(BaseModel):
    id: int
    produto_id: int
    nome: str
    descricao: str
    preco: float
    itens: list[ItemComboResponse]


class CatalogoProdutoResponse(BaseModel):
    id: int
    nome: str
    tipo: str
    preco: float
    combo_id: int | None = None
    descricao: str | None = None
    itens_combo: list[ItemComboResponse] = Field(default_factory=list)
    variacoes: list[OpcaoVariacaoResponse] = Field(default_factory=list)
