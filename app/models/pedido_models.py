from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base



class Pedido(Base):
    __tablename__ = "pedidos"

    id = Column(Integer, primary_key=True, index=True)
    local = Column(String, nullable=False)

    fk_cliente = Column(
        Integer,
        ForeignKey("clientes.id"),
        nullable=False
    )

    fk_cupom = Column(
        Integer,
        ForeignKey("cupons.id"),
        nullable=True
    )

    fk_mesa = Column(
        Integer,
        ForeignKey("mesas.id"),
        nullable=True
    )


class Cupom(Base):
    __tablename__ = "cupons"

    id = Column(Integer, primary_key=True, index=True)
    codigo = Column(String, nullable=False, unique=True)
    desconto = Column(Float, default=0)
    validade = Column(String, nullable=True)


class ItemPedido(Base):
    __tablename__ = "itens_pedido"

    id = Column(Integer, primary_key=True, index=True)
    quantidade = Column(Integer, nullable=False)
    observacao = Column(String, nullable=True)

    fk_pedido = Column(
        Integer,
        ForeignKey("pedidos.id"),
        nullable=False
    )

    fk_produto = Column(
        Integer,
        ForeignKey("produtos.id"),
        nullable=False
    )


class HistoricoStatus(Base):
    __tablename__ = "historico_status"

    id = Column(Integer, primary_key=True, index=True)
    status = Column(String, nullable=False)
    data_hora = Column(String, nullable=False)

    fk_pedido = Column(
        Integer,
        ForeignKey("pedidos.id"),
        nullable=False
    )


class Pagamento(Base):
    __tablename__ = "pagamentos"

    id = Column(Integer, primary_key=True, index=True)
    tipo = Column(String, nullable=False)
    valor = Column(Float, default=0)
    status = Column(String, nullable=False, default="pendente")

    fk_pedido = Column(
        Integer,
        ForeignKey("pedidos.id"),
        nullable=False
    )


class Avaliacao(Base):
    __tablename__ = "avaliacoes"

    id = Column(Integer, primary_key=True, index=True)
    nota = Column(Integer, nullable=False)
    comentario = Column(String, nullable=True)

    fk_pedido = Column(
        Integer,
        ForeignKey("pedidos.id"),
        nullable=False
    )


class Entrega(Base):
    __tablename__ = "entregas"

    id = Column(Integer, primary_key=True, index=True)
    endereco = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pendente")

    fk_pedido = Column(
        Integer,
        ForeignKey("pedidos.id"),
        nullable=False
    )

class Variacao(Base):
    __tablename__ = "variacoes"

    ponto_carne = Column(String, primary_key=True, index=True)
    tamanho = Column(String, nullable=False)
    preco_novo = Column(Float, default=0)

    fk_produto = Column(
        Integer,
        ForeignKey("produtos.id"),
        nullable=False
    )

