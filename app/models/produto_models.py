from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class Produto(Base):
    __tablename__ = "produtos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    tipo = Column(String, nullable=False)
    preco = Column(Float, default=0)


class Categoria(Base):
    __tablename__ = "categorias"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)


class ProdutoCategoria(Base):
    __tablename__ = "produtos_categorias"

    id = Column(Integer, primary_key=True, index=True)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    fk_categoria = Column(Integer, ForeignKey("categorias.id"), nullable=False)


class Combo(Base):
    __tablename__ = "combos"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    descricao = Column(String, nullable=True)
    preco = Column(Float, default=0)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)


class ItemCombo(Base):
    __tablename__ = "itens_combo"

    id = Column(Integer, primary_key=True, index=True)
    quantidade = Column(Integer, nullable=False, default=1)
    fk_combo = Column(Integer, ForeignKey("combos.id"), nullable=False)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)


class Promocao(Base):
    __tablename__ = "promocoes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    data_inicio = Column(String, nullable=False)
    data_termino = Column(String, nullable=False)
    preco_promo = Column(Float, default=0)


class ProdutoPromocao(Base):
    __tablename__ = "produtos_promocoes"

    id = Column(Integer, primary_key=True, index=True)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)
    fk_promocao = Column(Integer, ForeignKey("promocoes.id"), nullable=False)


class Ingrediente(Base):
    __tablename__ = "ingredientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    quantidade = Column(String, nullable=True)
    unidade = Column(String, nullable=True)
    fk_produto = Column(Integer, ForeignKey("produtos.id"), nullable=False)

class Fornecedor(Base):
    __tablename__ = "fornecedores"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    contato = Column(String, nullable=False)