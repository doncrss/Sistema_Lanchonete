from sqlalchemy.orm import Session

from app.models.produto_models import Combo, ItemCombo, OpcaoVariacao, Produto
from app.schemas.catalogo_schemas import CatalogoProdutoResponse, ItemComboResponse, OpcaoVariacaoResponse


def catalog_product(db: Session, product: Produto) -> CatalogoProdutoResponse:
    combo = db.query(Combo).filter(Combo.fk_produto == product.id).first()
    combo_items = []
    if combo:
        rows = (
            db.query(ItemCombo, Produto, OpcaoVariacao)
            .join(Produto, Produto.id == ItemCombo.fk_produto)
            .outerjoin(OpcaoVariacao, OpcaoVariacao.id == ItemCombo.fk_variacao)
            .filter(ItemCombo.fk_combo == combo.id).all()
        )
        combo_items = [ItemComboResponse(
            produto_id=i.fk_produto,
            nome=p.nome,
            quantidade=i.quantidade,
            variacao=f"{o.nome}: {o.valor}" if o else None,
        ) for i, p, o in rows]

    variations = db.query(OpcaoVariacao).filter(OpcaoVariacao.fk_produto == product.id).order_by(OpcaoVariacao.nome, OpcaoVariacao.id).all()
    return CatalogoProdutoResponse(
        id=product.id,
        nome=product.nome,
        tipo=product.tipo,
        preco=combo.preco if combo else product.preco,
        combo_id=combo.id if combo else None,
        descricao=combo.descricao if combo else None,
        itens_combo=combo_items,
        variacoes=[OpcaoVariacaoResponse(id=o.id, nome=o.nome, valor=o.valor, adicional=o.adicional) for o in variations],
    )


def list_catalog(db: Session) -> list[CatalogoProdutoResponse]:
    products = db.query(Produto).order_by(Produto.tipo, Produto.nome).all()
    return [catalog_product(db, p) for p in products]
