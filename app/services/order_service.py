from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.pedido_models import Entrega, HistoricoStatus, ItemPedido, Pedido
from app.models.produto_models import Combo, OpcaoVariacao, Produto
from app.models.usuario_models import Cliente
from app.schemas.checkout_schemas import ItemPedidoResponse, PedidoCheckout, PedidoResponse, StatusPedidoUpdate

STATUS_INICIAL = "recebido"


def pedido_response(db: Session, pedido: Pedido) -> PedidoResponse:
    cliente = db.get(Cliente, pedido.fk_cliente)
    if not cliente: raise HTTPException(500, "Cliente do pedido não encontrado.")
    history = db.query(HistoricoStatus).filter(HistoricoStatus.fk_pedido == pedido.id).order_by(HistoricoStatus.id.desc()).first()
    delivery = db.query(Entrega).filter(Entrega.fk_pedido == pedido.id).first()
    rows = db.query(ItemPedido, Produto).join(Produto, Produto.id == ItemPedido.fk_produto).filter(ItemPedido.fk_pedido == pedido.id).all()
    items = [ItemPedidoResponse(id=i.id, produto_id=p.id, nome=p.nome, quantidade=i.quantidade,
        preco_unitario=i.preco_unitario, subtotal=round(i.preco_unitario * i.quantidade, 2),
        observacao=i.observacao, variacao=i.variacao, is_combo=i.fk_combo is not None) for i, p in rows]
    return PedidoResponse(id=pedido.id, local=pedido.local, status=history.status if history else STATUS_INICIAL,
        data_hora=history.data_hora if history else "", cliente_nome=cliente.nome, cliente_contato=cliente.contato,
        endereco_entrega=delivery.endereco if delivery else None, itens=items,
        total=round(sum(i.subtotal for i in items), 2))


def create_order(db: Session, payload: PedidoCheckout) -> PedidoResponse:
    if payload.local == "entrega" and not payload.cliente.endereco.strip(): raise HTTPException(422, "Informe o endereço para pedidos de entrega.")
    product_ids = {i.produto_id for i in payload.itens}
    products = {p.id: p for p in db.query(Produto).filter(Produto.id.in_(product_ids)).all()}
    if len(products) != len(product_ids): raise HTTPException(422, "Um ou mais produtos não existem.")

    combo_ids = {i.combo_id for i in payload.itens if i.combo_id}
    combos = {c.id: c for c in db.query(Combo).filter(Combo.id.in_(combo_ids)).all()} if combo_ids else {}
    options_by_item = {}
    for index, item in enumerate(payload.itens):
        if item.combo_id:
            combo = combos.get(item.combo_id)
            if not combo or combo.fk_produto != item.produto_id: raise HTTPException(422, "Combo inválido.")
            if item.variacao_ids: raise HTTPException(422, "Combos não possuem variações.")
            continue
        if products[item.produto_id].tipo == "Combo": raise HTTPException(422, "Selecione um combo válido.")
        if len(set(item.variacao_ids)) != len(item.variacao_ids): raise HTTPException(422, "Variação duplicada.")
        available = db.query(OpcaoVariacao).filter(OpcaoVariacao.fk_produto == item.produto_id).all()
        options = [o for o in available if o.id in set(item.variacao_ids)]
        if len(options) != len(set(item.variacao_ids)): raise HTTPException(422, "Uma ou mais variações são inválidas.")
        if len({o.nome for o in options}) != len(options): raise HTTPException(422, "Escolha apenas uma opção por variação.")
        if {o.nome for o in available} != {o.nome for o in options}: raise HTTPException(422, "Escolha uma opção para cada variação disponível.")
        options_by_item[index] = options

    cliente = db.query(Cliente).filter(Cliente.contato == payload.cliente.contato.strip()).first()
    if not cliente:
        cliente = Cliente(nome=payload.cliente.nome.strip(), contato=payload.cliente.contato.strip(),
            endereco=payload.cliente.endereco.strip() or ("Retirada no balcão" if payload.local == "retirada" else "Consumo no local"))
        db.add(cliente); db.flush()
    else:
        cliente.nome = payload.cliente.nome.strip()
        if payload.cliente.endereco.strip(): cliente.endereco = payload.cliente.endereco.strip()

    pedido = Pedido(local=payload.local, fk_cliente=cliente.id)
    db.add(pedido); db.flush()
    order_items = []
    for index, item in enumerate(payload.itens):
        combo = combos.get(item.combo_id) if item.combo_id else None
        options = options_by_item.get(index, [])
        base = combo.preco if combo else products[item.produto_id].preco
        label = ", ".join(f"{o.nome}: {o.valor}" for o in options) or None
        order_items.append(ItemPedido(fk_pedido=pedido.id, fk_produto=item.produto_id, fk_combo=combo.id if combo else None,
            quantidade=item.quantidade, observacao=item.observacao.strip() if item.observacao else None,
            variacao=label, preco_unitario=round(base + sum(o.adicional for o in options), 2)))
    db.add_all(order_items)
    db.add(HistoricoStatus(fk_pedido=pedido.id, status=STATUS_INICIAL, data_hora=datetime.now(timezone.utc).isoformat()))
    if payload.local == "entrega": db.add(Entrega(fk_pedido=pedido.id, endereco=payload.cliente.endereco.strip(), status="pendente"))
    db.commit(); db.refresh(pedido)
    return pedido_response(db, pedido)


def list_orders(db: Session) -> list[PedidoResponse]:
    pedidos = db.query(Pedido).order_by(Pedido.id.desc()).limit(100).all()
    return [pedido_response(db, p) for p in pedidos]


def update_order_status(db: Session, pedido_id: int, payload: StatusPedidoUpdate) -> PedidoResponse:
    pedido = db.get(Pedido, pedido_id)
    if not pedido: raise HTTPException(404, "Pedido não encontrado.")
    db.add(HistoricoStatus(fk_pedido=pedido.id, status=payload.status, data_hora=datetime.now(timezone.utc).isoformat()))
    db.commit()
    return pedido_response(db, pedido)
