from sqlalchemy import inspect, text

from app import database
from app.database import Base
from app.models.produto_models import Configuracao, OpcaoVariacao, Produto


PRODUTOS_INICIAIS = [
    ("X-Burger da Casa", "Hambúrguer", 24.90),
    ("X-Bacon Crocante", "Hambúrguer", 29.90),
    ("Smash Duplo", "Hambúrguer", 32.90),
    ("Batata Frita", "Acompanhamento", 14.90),
    ("Onion Rings", "Acompanhamento", 16.90),
    ("Refrigerante Lata", "Bebida", 6.00),
    ("Milk-shake de Chocolate", "Bebida", 18.90),
]


def initialize_database() -> None:
    Base.metadata.create_all(bind=database.engine)

    item_columns = {c["name"] for c in inspect(database.engine).get_columns("itens_pedido")}
    migrations = {
        "preco_unitario": "FLOAT NOT NULL DEFAULT 0",
        "variacao": "VARCHAR",
        "fk_combo": "INTEGER REFERENCES combos(id)",
    }
    for name, definition in migrations.items():
        if name not in item_columns:
            with database.engine.begin() as conn:
                conn.execute(text(f"ALTER TABLE itens_pedido ADD COLUMN {name} {definition}"))

    combo_columns = {c["name"] for c in inspect(database.engine).get_columns("itens_combo")}
    if "fk_variacao" not in combo_columns:
        with database.engine.begin() as conn:
            conn.execute(text("ALTER TABLE itens_combo ADD COLUMN fk_variacao INTEGER REFERENCES produto_variacoes(id)"))

    db = database.SessionLocal()
    try:
        if db.query(Produto).count() == 0:
            db.add_all(Produto(nome=n, tipo=t, preco=p) for n, t, p in PRODUTOS_INICIAIS)
            db.commit()

        if db.get(Configuracao, "catalogo_variacoes_iniciais_v1") is None:
            def add_options(product: Produto, group: str, values: list[tuple[str, float]]) -> None:
                existing = {o.valor for o in db.query(OpcaoVariacao).filter(
                    OpcaoVariacao.fk_produto == product.id,
                    OpcaoVariacao.nome == group,
                ).all()}
                for value, extra in values:
                    if value not in existing:
                        db.add(OpcaoVariacao(fk_produto=product.id, nome=group, valor=value, adicional=extra))

            for burger in db.query(Produto).filter(Produto.tipo == "Hambúrguer"):
                add_options(burger, "Tamanho", [("Tradicional", 0), ("Grande", 5)])
                add_options(burger, "Ponto da carne", [("Ao ponto", 0), ("Bem passada", 0), ("Mal passada", 0)])
            for product in db.query(Produto).filter(Produto.nome.ilike("%milk-shake%")):
                add_options(product, "Sabor", [("Chocolate", 0), ("Morango", 0), ("Baunilha", 0), ("Ovomaltine", 0)])
            for product in db.query(Produto).filter(Produto.nome.ilike("%refrigerante%")):
                add_options(product, "Volume", [("Lata (350 ml)", 0), ("Garrafa (600 ml)", 4)])
            db.add(Configuracao(chave="catalogo_variacoes_iniciais_v1"))
            db.commit()
    finally:
        db.close()
