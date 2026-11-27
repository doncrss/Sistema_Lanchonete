import os
import secrets
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Annotated

from fastapi import Depends, FastAPI, Header, HTTPException, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app import database
from app.database import Base, get_db
from app.models import pedido_models, produto_models, usuario_models
from app.models.pedido_models import Entrega, HistoricoStatus, ItemPedido, Pedido
from app.models.produto_models import Configuracao, Combo, ItemCombo, OpcaoVariacao, Produto, Fornecedor
from app.models.usuario_models import Cliente
from app.schemas.catalogo_schemas import (
    CatalogoProdutoResponse,
    ComboCreate,
    ComboResponse,
    ItemComboResponse,
    OpcaoVariacaoCreate,
    OpcaoVariacaoResponse,
)
from app.schemas.checkout_schemas import (
    ItemPedidoResponse,
    PedidoCheckout,
    PedidoResponse,
    StatusPedidoUpdate,
)
from app.schemas.produto_schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate
from app.schemas.fornecedor_schemas import FornecedorCreate, FornecedorResponse, FornecedorUpdate


_ = pedido_models, produto_models, usuario_models
STATUS_INICIAL = "recebido"
PRODUTOS_INICIAIS = [
    ("X-Burger da Casa", "Hambúrguer", 24.90),
    ("X-Bacon Crocante", "Hambúrguer", 29.90),
    ("Smash Duplo", "Hambúrguer", 32.90),
    ("Batata Frita", "Acompanhamento", 14.90),
    ("Onion Rings", "Acompanhamento", 16.90),
    ("Refrigerante Lata", "Bebida", 6.00),
    ("Milk-shake de Chocolate", "Bebida", 18.90),
]


def _initialize_database() -> None:
    Base.metadata.create_all(bind=database.engine)

    item_columns = {column["name"] for column in inspect(database.engine).get_columns("itens_pedido")}
    item_migrations = {
        "preco_unitario": "FLOAT NOT NULL DEFAULT 0",
        "variacao": "VARCHAR",
        "fk_combo": "INTEGER REFERENCES combos(id)",
    }
    for column, definition in item_migrations.items():
        if column not in item_columns:
            with database.engine.begin() as connection:
                connection.execute(
                    text(f"ALTER TABLE itens_pedido ADD COLUMN {column} {definition}")
                )

    combo_item_columns = {
        column["name"] for column in inspect(database.engine).get_columns("itens_combo")
    }
    if "fk_variacao" not in combo_item_columns:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE itens_combo ADD COLUMN "
                    "fk_variacao INTEGER REFERENCES produto_variacoes(id)"
                )
            )

    db = database.SessionLocal()
    try:
        if db.query(Produto).count() == 0:
            db.add_all(
                Produto(nome=nome, tipo=tipo, preco=preco)
                for nome, tipo, preco in PRODUTOS_INICIAIS
            )
            db.commit()

        if db.get(Configuracao, "catalogo_variacoes_iniciais_v1") is None:
            def add_missing_variations(product: Produto, group: str, values: list[tuple[str, float]]):
                existing_values = {
                    option.valor
                    for option in db.query(OpcaoVariacao)
                    .filter(
                        OpcaoVariacao.fk_produto == product.id,
                        OpcaoVariacao.nome == group,
                    )
                    .all()
                }
                for value, additional in values:
                    if value not in existing_values:
                        db.add(
                            OpcaoVariacao(
                                fk_produto=product.id,
                                nome=group,
                                valor=value,
                                adicional=additional,
                            )
                        )

            for burger in db.query(Produto).filter(Produto.tipo == "Hambúrguer").all():
                add_missing_variations(
                    burger,
                    "Tamanho",
                    [("Tradicional", 0), ("Grande", 5)],
                )
                add_missing_variations(
                    burger,
                    "Ponto da carne",
                    [("Ao ponto", 0), ("Bem passada", 0), ("Mal passada", 0)],
                )

            for product in db.query(Produto).filter(Produto.nome.ilike("%milk-shake%")).all():
                add_missing_variations(
                    product,
                    "Sabor",
                    [("Chocolate", 0), ("Morango", 0), ("Baunilha", 0), ("Ovomaltine", 0)],
                )

            for product in db.query(Produto).filter(Produto.nome.ilike("%refrigerante%")).all():
                add_missing_variations(
                    product,
                    "Volume",
                    [("Lata (350 ml)", 0), ("Garrafa (600 ml)", 4)],
                )

            db.add(Configuracao(chave="catalogo_variacoes_iniciais_v1"))
        db.commit()
    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    _initialize_database()
    yield


app = FastAPI(
    title="Lanchotech",
    description="API de cardápio, pedidos e gestão da Lanchotech.",
    version="1.0.0",
    lifespan=lifespan,
)
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


def require_admin(
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    admin_token = os.getenv("ADMIN_TOKEN")
    if not admin_token:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Configure ADMIN_TOKEN para habilitar a gestão.",
        )
    if x_admin_token is None or not secrets.compare_digest(x_admin_token, admin_token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Chave administrativa inválida.",
        )


def _pedido_response(db: Session, pedido: Pedido) -> PedidoResponse:
    cliente = db.get(Cliente, pedido.fk_cliente)
    if cliente is None:
        raise HTTPException(status_code=500, detail="Cliente do pedido não encontrado.")

    historico = (
        db.query(HistoricoStatus)
        .filter(HistoricoStatus.fk_pedido == pedido.id)
        .order_by(HistoricoStatus.id.desc())
        .first()
    )
    entrega = (
        db.query(Entrega)
        .filter(Entrega.fk_pedido == pedido.id)
        .first()
    )
    linhas = (
        db.query(ItemPedido, Produto)
        .join(Produto, Produto.id == ItemPedido.fk_produto)
        .filter(ItemPedido.fk_pedido == pedido.id)
        .all()
    )
    itens = [
        ItemPedidoResponse(
            id=item.id,
            produto_id=produto.id,
            nome=produto.nome,
            quantidade=item.quantidade,
            preco_unitario=item.preco_unitario,
            subtotal=round(item.preco_unitario * item.quantidade, 2),
            observacao=item.observacao,
            variacao=item.variacao,
            is_combo=item.fk_combo is not None,
        )
        for item, produto in linhas
    ]
    return PedidoResponse(
        id=pedido.id,
        local=pedido.local,
        status=historico.status if historico else STATUS_INICIAL,
        data_hora=historico.data_hora if historico else "",
        cliente_nome=cliente.nome,
        cliente_contato=cliente.contato,
        endereco_entrega=entrega.endereco if entrega else None,
        itens=itens,
        total=round(sum(item.subtotal for item in itens), 2),
    )


@app.get("/api/health")
def health_check(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "servico": "lanchotech"}


def _catalog_product(db: Session, product: Produto) -> CatalogoProdutoResponse:
    combo = db.query(Combo).filter(Combo.fk_produto == product.id).first()
    combo_items = []
    if combo is not None:
        combo_items = [
            ItemComboResponse(
                produto_id=item_combo.fk_produto,
                nome=item.nome,
                quantidade=item_combo.quantidade,
                variacao=f"{option.nome}: {option.valor}" if option else None,
            )
            for item_combo, item, option in (
                db.query(ItemCombo, Produto, OpcaoVariacao)
                .join(Produto, Produto.id == ItemCombo.fk_produto)
                .outerjoin(OpcaoVariacao, OpcaoVariacao.id == ItemCombo.fk_variacao)
                .filter(ItemCombo.fk_combo == combo.id)
                .all()
            )
        ]
    variations = (
        db.query(OpcaoVariacao)
        .filter(OpcaoVariacao.fk_produto == product.id)
        .order_by(OpcaoVariacao.nome, OpcaoVariacao.id)
        .all()
    )
    return CatalogoProdutoResponse(
        id=product.id,
        nome=product.nome,
        tipo=product.tipo,
        preco=combo.preco if combo is not None else product.preco,
        combo_id=combo.id if combo is not None else None,
        descricao=combo.descricao if combo is not None else None,
        itens_combo=combo_items,
        variacoes=[
            OpcaoVariacaoResponse(
                id=option.id,
                nome=option.nome,
                valor=option.valor,
                adicional=option.adicional,
            )
            for option in variations
        ],
    )


@app.get("/api/produtos", response_model=list[CatalogoProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    products = db.query(Produto).order_by(Produto.tipo, Produto.nome).all()
    return [_catalog_product(db, product) for product in products]


@app.get("/api/produtos/{produto_id}", response_model=ProdutoResponse)
def obter_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return produto


@app.post(
    "/api/produtos/{produto_id}/variacoes",
    response_model=OpcaoVariacaoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def criar_variacao(
    produto_id: int,
    payload: OpcaoVariacaoCreate,
    db: Session = Depends(get_db),
):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    if db.query(Combo).filter(Combo.fk_produto == produto_id).first():
        raise HTTPException(status_code=422, detail="Combos não possuem variações.")
    if db.query(OpcaoVariacao).filter(
        OpcaoVariacao.fk_produto == produto_id,
        OpcaoVariacao.nome == payload.nome.strip(),
        OpcaoVariacao.valor == payload.valor.strip(),
    ).first():
        raise HTTPException(status_code=409, detail="Essa opção já existe para o produto.")
    variacao = OpcaoVariacao(fk_produto=produto_id, **payload.model_dump())
    db.add(variacao)
    db.commit()
    db.refresh(variacao)
    return variacao


@app.delete(
    "/api/variacoes/{variacao_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def excluir_variacao(variacao_id: int, db: Session = Depends(get_db)):
    variacao = db.get(OpcaoVariacao, variacao_id)
    if variacao is None:
        raise HTTPException(status_code=404, detail="Variação não encontrada.")
    if db.query(ItemCombo).filter(ItemCombo.fk_variacao == variacao_id).first():
        raise HTTPException(
            status_code=409,
            detail="Variação usada em um combo não pode ser removida.",
        )
    db.delete(variacao)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _combo_response(db: Session, combo: Combo) -> ComboResponse:
    product = db.get(Produto, combo.fk_produto)
    items = (
        db.query(ItemCombo, Produto, OpcaoVariacao)
        .join(Produto, Produto.id == ItemCombo.fk_produto)
        .outerjoin(OpcaoVariacao, OpcaoVariacao.id == ItemCombo.fk_variacao)
        .filter(ItemCombo.fk_combo == combo.id)
        .all()
    )
    return ComboResponse(
        id=combo.id,
        produto_id=combo.fk_produto,
        nome=product.nome,
        descricao=combo.descricao or "",
        preco=combo.preco,
        itens=[
            ItemComboResponse(
                produto_id=item_combo.fk_produto,
                nome=item.nome,
                quantidade=item_combo.quantidade,
                variacao=f"{option.nome}: {option.valor}" if option else None,
            )
            for item_combo, item, option in items
        ],
    )


@app.post(
    "/api/combos",
    response_model=ComboResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def criar_combo(payload: ComboCreate, db: Session = Depends(get_db)):
    product_ids = [item.produto_id for item in payload.itens]
    if len(set(product_ids)) != len(product_ids):
        raise HTTPException(status_code=422, detail="Cada produto deve aparecer uma vez no combo.")
    products = {
        product.id: product
        for product in db.query(Produto).filter(Produto.id.in_(product_ids)).all()
    }
    if len(products) != len(product_ids):
        raise HTTPException(status_code=422, detail="Um ou mais produtos do combo não existem.")
    if any(product.tipo == "Combo" for product in products.values()):
        raise HTTPException(status_code=422, detail="Não é possível adicionar um combo dentro de outro.")

    variation_ids = [item.variacao_id for item in payload.itens if item.variacao_id is not None]
    if len(set(variation_ids)) != len(variation_ids):
        raise HTTPException(status_code=422, detail="Variação duplicada na composição do combo.")
    variations = {
        option.id: option
        for option in db.query(OpcaoVariacao).filter(OpcaoVariacao.id.in_(variation_ids)).all()
    } if variation_ids else {}
    if len(variations) != len(variation_ids):
        raise HTTPException(status_code=422, detail="Uma ou mais variações do combo são inválidas.")
    for item in payload.itens:
        if item.variacao_id is None:
            continue
        option = variations[item.variacao_id]
        if option.fk_produto != item.produto_id or option.nome != "Volume":
            raise HTTPException(
                status_code=422,
                detail="Selecione um volume válido para o produto do combo.",
            )

    combo_product = Produto(nome=payload.nome, tipo="Combo", preco=payload.preco)
    db.add(combo_product)
    db.flush()
    combo = Combo(
        nome=payload.nome,
        descricao=payload.descricao.strip(),
        preco=payload.preco,
        fk_produto=combo_product.id,
    )
    db.add(combo)
    db.flush()
    db.add_all(
        ItemCombo(
            fk_combo=combo.id,
            fk_produto=item.produto_id,
            quantidade=item.quantidade,
            fk_variacao=item.variacao_id,
        )
        for item in payload.itens
    )
    db.commit()
    db.refresh(combo)
    return _combo_response(db, combo)


@app.delete(
    "/api/combos/{combo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def excluir_combo(combo_id: int, db: Session = Depends(get_db)):
    combo = db.get(Combo, combo_id)
    if combo is None:
        raise HTTPException(status_code=404, detail="Combo não encontrado.")
    if db.query(ItemPedido).filter(
        (ItemPedido.fk_combo == combo.id) | (ItemPedido.fk_produto == combo.fk_produto)
    ).first():
        raise HTTPException(
            status_code=409,
            detail="Combo vinculado a um pedido não pode ser excluído.",
        )
    product = db.get(Produto, combo.fk_produto)
    db.query(ItemCombo).filter(ItemCombo.fk_combo == combo.id).delete()
    db.delete(combo)
    if product is not None:
        db.delete(product)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/produtos",
    response_model=ProdutoResponse,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_admin)],
)
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db)):
    produto = Produto(**payload.model_dump())
    db.add(produto)
    db.commit()
    db.refresh(produto)
    return produto


@app.put(
    "/api/produtos/{produto_id}",
    response_model=ProdutoResponse,
    dependencies=[Depends(require_admin)],
)
def atualizar_produto(
    produto_id: int,
    payload: ProdutoUpdate,
    db: Session = Depends(get_db),
):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    for campo, valor in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(produto, campo, valor)
    db.commit()
    db.refresh(produto)
    return produto


@app.delete(
    "/api/produtos/{produto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_admin)],
)
def excluir_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    db.query(OpcaoVariacao).filter(OpcaoVariacao.fk_produto == produto_id).delete()
    db.delete(produto)
    try:
        db.commit()
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Produto vinculado a pedidos não pode ser excluído.",
        ) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.post(
    "/api/pedidos",
    response_model=PedidoResponse,
    status_code=status.HTTP_201_CREATED,
)
def criar_pedido(payload: PedidoCheckout, db: Session = Depends(get_db)):
    if payload.local == "entrega" and not payload.cliente.endereco.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Informe o endereço para pedidos de entrega.",
        )

    produto_ids = {item.produto_id for item in payload.itens}
    produtos = {
        produto.id: produto
        for produto in db.query(Produto).filter(Produto.id.in_(produto_ids)).all()
    }
    if len(produtos) != len(produto_ids):
        raise HTTPException(status_code=422, detail="Um ou mais produtos não existem.")

    combo_ids = {item.combo_id for item in payload.itens if item.combo_id is not None}
    combos = {
        combo.id: combo
        for combo in db.query(Combo).filter(Combo.id.in_(combo_ids)).all()
    } if combo_ids else {}
    variations_by_item: dict[int, list[OpcaoVariacao]] = {}
    for index, item in enumerate(payload.itens):
        if item.combo_id is not None:
            combo = combos.get(item.combo_id)
            if combo is None or combo.fk_produto != item.produto_id:
                raise HTTPException(status_code=422, detail="Combo inválido.")
            if item.variacao_ids:
                raise HTTPException(status_code=422, detail="Combos não possuem variações.")
            continue
        if produtos[item.produto_id].tipo == "Combo":
            raise HTTPException(status_code=422, detail="Selecione um combo válido.")
        option_ids = set(item.variacao_ids)
        if len(option_ids) != len(item.variacao_ids):
            raise HTTPException(status_code=422, detail="Variação duplicada.")
        available_options = (
            db.query(OpcaoVariacao)
            .filter(OpcaoVariacao.fk_produto == item.produto_id)
            .all()
        )
        options = [option for option in available_options if option.id in option_ids]
        if len(options) != len(option_ids):
            raise HTTPException(status_code=422, detail="Uma ou mais variações são inválidas.")
        if len({option.nome for option in options}) != len(options):
            raise HTTPException(status_code=422, detail="Escolha apenas uma opção por variação.")
        expected_groups = {option.nome for option in available_options}
        selected_groups = {option.nome for option in options}
        if expected_groups != selected_groups:
            raise HTTPException(status_code=422, detail="Escolha uma opção para cada variação disponível.")
        variations_by_item[index] = options

    cliente = (
        db.query(Cliente)
        .filter(Cliente.contato == payload.cliente.contato.strip())
        .first()
    )
    if cliente is None:
        cliente = Cliente(
            nome=payload.cliente.nome.strip(),
            contato=payload.cliente.contato.strip(),
            endereco=payload.cliente.endereco.strip()
            or ("Retirada no balcão" if payload.local == "retirada" else "Consumo no local"),
        )
        db.add(cliente)
        db.flush()
    else:
        cliente.nome = payload.cliente.nome.strip()
        if payload.cliente.endereco.strip():
            cliente.endereco = payload.cliente.endereco.strip()

    pedido = Pedido(local=payload.local, fk_cliente=cliente.id)
    db.add(pedido)
    db.flush()
    order_items = []
    for index, item in enumerate(payload.itens):
        combo = combos.get(item.combo_id) if item.combo_id is not None else None
        options = variations_by_item.get(index, [])
        base_price = combo.preco if combo is not None else produtos[item.produto_id].preco
        option_label = ", ".join(f"{option.nome}: {option.valor}" for option in options) or None
        order_items.append(
            ItemPedido(
                fk_pedido=pedido.id,
                fk_produto=item.produto_id,
                fk_combo=combo.id if combo else None,
                quantidade=item.quantidade,
                observacao=item.observacao.strip() if item.observacao else None,
                variacao=option_label,
                preco_unitario=round(base_price + sum(option.adicional for option in options), 2),
            )
        )
    db.add_all(order_items)
    db.add(
        HistoricoStatus(
            fk_pedido=pedido.id,
            status=STATUS_INICIAL,
            data_hora=datetime.now(timezone.utc).isoformat(),
        )
    )
    if payload.local == "entrega":
        db.add(
            Entrega(
                fk_pedido=pedido.id,
                endereco=payload.cliente.endereco.strip(),
                status="pendente",
            )
        )
    db.commit()
    db.refresh(pedido)
    return _pedido_response(db, pedido)


@app.get(
    "/api/pedidos",
    response_model=list[PedidoResponse],
    dependencies=[Depends(require_admin)],
)
def listar_pedidos(db: Session = Depends(get_db)):
    pedidos = db.query(Pedido).order_by(Pedido.id.desc()).limit(100).all()
    return [_pedido_response(db, pedido) for pedido in pedidos]


@app.patch(
    "/api/pedidos/{pedido_id}/status",
    response_model=PedidoResponse,
    dependencies=[Depends(require_admin)],
)
def atualizar_status_pedido(
    pedido_id: int,
    payload: StatusPedidoUpdate,
    db: Session = Depends(get_db),
):
    pedido = db.get(Pedido, pedido_id)
    if pedido is None:
        raise HTTPException(status_code=404, detail="Pedido não encontrado.")
    db.add(
        HistoricoStatus(
            fk_pedido=pedido.id,
            status=payload.status,
            data_hora=datetime.now(timezone.utc).isoformat(),
        )
    )
    db.commit()
    return _pedido_response(db, pedido)


@app.get("/", include_in_schema=False)
def frontend():
    return FileResponse(FRONTEND_DIR / "minimal.html")


@app.get("/api/fornecedores", response_model=list[FornecedorResponse], dependencies=[Depends(require_admin)])
def listar_fornecedores(db: Session = Depends(get_db)):
    return db.query(Fornecedor).order_by(Fornecedor.nome).all()


@app.post("/api/fornecedores", response_model=FornecedorResponse, status_code=status.HTTP_201_CREATED, dependencies=[Depends(require_admin)])
def criar_fornecedor(payload: FornecedorCreate, db: Session = Depends(get_db)):
    fornecedor = Fornecedor(**payload.model_dump())
    db.add(fornecedor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@app.put("/api/fornecedores/{fornecedor_id}", response_model=FornecedorResponse, dependencies=[Depends(require_admin)])
def atualizar_fornecedor(fornecedor_id: int, payload: FornecedorUpdate, db: Session = Depends(get_db)):
    fornecedor = db.get(Fornecedor, fornecedor_id)
    if fornecedor is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    for campo, valor in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(fornecedor, campo, valor)
    db.commit()
    db.refresh(fornecedor)
    return fornecedor


@app.delete("/api/fornecedores/{fornecedor_id}", status_code=status.HTTP_204_NO_CONTENT, dependencies=[Depends(require_admin)])
def excluir_fornecedor(fornecedor_id: int, db: Session = Depends(get_db)):
    fornecedor = db.get(Fornecedor, fornecedor_id)
    if fornecedor is None:
        raise HTTPException(status_code=404, detail="Fornecedor não encontrado.")
    db.delete(fornecedor)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")
