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
from app.models.produto_models import Produto
from app.models.usuario_models import Cliente
from app.schemas.checkout_schemas import (
    ItemPedidoResponse,
    PedidoCheckout,
    PedidoResponse,
    StatusPedidoUpdate,
)
from app.schemas.produto_schemas import ProdutoCreate, ProdutoResponse, ProdutoUpdate


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
    if "preco_unitario" not in item_columns:
        with database.engine.begin() as connection:
            connection.execute(
                text(
                    "ALTER TABLE itens_pedido "
                    "ADD COLUMN preco_unitario FLOAT NOT NULL DEFAULT 0"
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


@app.get("/api/produtos", response_model=list[ProdutoResponse])
def listar_produtos(db: Session = Depends(get_db)):
    return db.query(Produto).order_by(Produto.tipo, Produto.nome).all()


@app.get("/api/produtos/{produto_id}", response_model=ProdutoResponse)
def obter_produto(produto_id: int, db: Session = Depends(get_db)):
    produto = db.get(Produto, produto_id)
    if produto is None:
        raise HTTPException(status_code=404, detail="Produto não encontrado.")
    return produto


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
    db.add_all(
        ItemPedido(
            fk_pedido=pedido.id,
            fk_produto=item.produto_id,
            quantidade=item.quantidade,
            observacao=item.observacao.strip() if item.observacao else None,
            preco_unitario=produtos[item.produto_id].preco,
        )
        for item in payload.itens
    )
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
    return FileResponse(FRONTEND_DIR / "index.html")


app.mount("/", StaticFiles(directory=FRONTEND_DIR), name="frontend-assets")
