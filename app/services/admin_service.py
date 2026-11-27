from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.produto_models import Combo, ItemCombo, OpcaoVariacao, Produto, Fornecedor
from app.models.pedido_models import ItemPedido
from app.schemas.catalogo_schemas import ComboCreate, ComboResponse, ItemComboResponse, OpcaoVariacaoCreate
from app.schemas.produto_schemas import ProdutoCreate, ProdutoUpdate
from app.schemas.fornecedor_schemas import FornecedorCreate, FornecedorUpdate


def combo_response(db: Session, combo: Combo) -> ComboResponse:
    product = db.get(Produto, combo.fk_produto)
    rows = (db.query(ItemCombo, Produto, OpcaoVariacao)
            .join(Produto, Produto.id == ItemCombo.fk_produto)
            .outerjoin(OpcaoVariacao, OpcaoVariacao.id == ItemCombo.fk_variacao)
            .filter(ItemCombo.fk_combo == combo.id).all())
    return ComboResponse(id=combo.id, produto_id=combo.fk_produto, nome=product.nome,
        descricao=combo.descricao or "", preco=combo.preco,
        itens=[ItemComboResponse(produto_id=i.fk_produto, nome=p.nome, quantidade=i.quantidade,
            variacao=f"{o.nome}: {o.valor}" if o else None) for i, p, o in rows])


def create_variation(db: Session, product_id: int, payload: OpcaoVariacaoCreate):
    product = db.get(Produto, product_id)
    if not product: raise HTTPException(404, "Produto não encontrado.")
    if db.query(Combo).filter(Combo.fk_produto == product_id).first(): raise HTTPException(422, "Combos não possuem variações.")
    if db.query(OpcaoVariacao).filter(OpcaoVariacao.fk_produto == product_id, OpcaoVariacao.nome == payload.nome.strip(), OpcaoVariacao.valor == payload.valor.strip()).first():
        raise HTTPException(409, "Essa opção já existe para o produto.")
    option = OpcaoVariacao(fk_produto=product_id, nome=payload.nome.strip(), valor=payload.valor.strip(), adicional=payload.adicional)
    db.add(option); db.commit(); db.refresh(option)
    return option


def delete_variation(db: Session, variation_id: int):
    option = db.get(OpcaoVariacao, variation_id)
    if not option: raise HTTPException(404, "Variação não encontrada.")
    if db.query(ItemCombo).filter(ItemCombo.fk_variacao == variation_id).first(): raise HTTPException(409, "Variação usada em um combo não pode ser removida.")
    db.delete(option); db.commit()


def create_combo(db: Session, payload: ComboCreate):
    ids = [i.produto_id for i in payload.itens]
    if len(set(ids)) != len(ids): raise HTTPException(422, "Cada produto deve aparecer uma vez no combo.")
    products = {p.id: p for p in db.query(Produto).filter(Produto.id.in_(ids)).all()}
    if len(products) != len(ids): raise HTTPException(422, "Um ou mais produtos do combo não existem.")
    if any(p.tipo == "Combo" for p in products.values()):
        raise HTTPException(422, "Não é possível adicionar um combo dentro de outro.")

    variation_ids = [i.variacao_id for i in payload.itens if i.variacao_id]
    if len(set(variation_ids)) != len(variation_ids): raise HTTPException(422, "Variação duplicada na composição do combo.")
    variations = {o.id: o for o in db.query(OpcaoVariacao).filter(OpcaoVariacao.id.in_(variation_ids)).all()} if variation_ids else {}
    if len(variations) != len(variation_ids): raise HTTPException(422, "Uma ou mais variações do combo são inválidas.")
    for item in payload.itens:
        if item.variacao_id:
            option = variations[item.variacao_id]
            if option.fk_produto != item.produto_id or option.nome != "Volume": raise HTTPException(422, "Selecione um volume válido para o produto do combo.")

    combo_product = Produto(nome=payload.nome, tipo="Combo", preco=payload.preco)
    db.add(combo_product); db.flush()
    combo = Combo(nome=payload.nome, descricao=payload.descricao.strip(), preco=payload.preco, fk_produto=combo_product.id)
    db.add(combo); db.flush()
    db.add_all(ItemCombo(fk_combo=combo.id, fk_produto=i.produto_id, quantidade=i.quantidade, fk_variacao=i.variacao_id) for i in payload.itens)
    db.commit(); db.refresh(combo)
    return combo_response(db, combo)


def delete_combo(db: Session, combo_id: int):
    combo = db.get(Combo, combo_id)
    if not combo: raise HTTPException(404, "Combo não encontrado.")
    if db.query(ItemPedido).filter((ItemPedido.fk_combo == combo.id) | (ItemPedido.fk_produto == combo.fk_produto)).first(): raise HTTPException(409, "Combo vinculado a um pedido não pode ser excluído.")
    db.query(ItemCombo).filter(ItemCombo.fk_combo == combo.id).delete()
    product = db.get(Produto, combo.fk_produto)
    db.delete(combo)
    if product: db.delete(product)
    db.commit()


def create_product(db: Session, payload: ProdutoCreate):
    product = Produto(**payload.model_dump()); db.add(product); db.commit(); db.refresh(product); return product


def update_product(db: Session, product_id: int, payload: ProdutoUpdate):
    product = db.get(Produto, product_id)
    if not product: raise HTTPException(404, "Produto não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items(): setattr(product, field, value)
    db.commit(); db.refresh(product); return product


def delete_product(db: Session, product_id: int):
    product = db.get(Produto, product_id)
    if not product: raise HTTPException(404, "Produto não encontrado.")
    db.query(OpcaoVariacao).filter(OpcaoVariacao.fk_produto == product_id).delete(); db.delete(product)
    try: db.commit()
    except IntegrityError:
        db.rollback(); raise HTTPException(status.HTTP_409_CONFLICT, "Produto vinculado a pedidos não pode ser excluído.")


def create_supplier(db: Session, payload: FornecedorCreate):
    supplier = Fornecedor(**payload.model_dump())
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return supplier


def update_supplier(db: Session, supplier_id: int, payload: FornecedorUpdate):
    supplier = db.get(Fornecedor, supplier_id)
    if not supplier:
        raise HTTPException(404, "Fornecedor não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(supplier, field, value)
    db.commit()
    db.refresh(supplier)
    return supplier


def delete_supplier(db: Session, supplier_id: int):
    supplier = db.get(Fornecedor, supplier_id)
    if not supplier:
        raise HTTPException(404, "Fornecedor não encontrado.")
    db.delete(supplier)
    db.commit()
