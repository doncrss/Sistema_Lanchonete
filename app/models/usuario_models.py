from sqlalchemy import Column, Integer, String, Float, ForeignKey
from app.database import Base


class Cliente(Base):
    __tablename__ = "clientes"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    contato = Column(String, nullable=False)
    endereco = Column(String, nullable=False)

class Funcionario(Base):
    __tablename__ = "funcionarios"

    id = Column(Integer, primary_key=True, index=True)
    nome = Column(String, nullable=False)
    funcao_praticada = Column(String, nullable=False)
    cargo = Column(String, nullable=False)
    fk_pedido = Column(Integer, ForeignKey("pedidos.id"), nullable=True)
