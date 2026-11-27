from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_admin
from app.schemas.catalogo_schemas import ComboCreate, ComboResponse, OpcaoVariacaoCreate, OpcaoVariacaoResponse
from app.schemas.produto_schemas import ProdutoCreate, ProdutoUpdate, ProdutoResponse
from app.schemas.fornecedor_schemas import FornecedorCreate, FornecedorResponse, FornecedorUpdate
from app.models.produto_models import Fornecedor
from app.services import admin_service

router = APIRouter(prefix="/api", tags=["Gestão"], dependencies=[Depends(require_admin)])

@router.post("/produtos", response_model=ProdutoResponse, status_code=201)
def criar_produto(payload: ProdutoCreate, db: Session = Depends(get_db)):
    return admin_service.create_product(db, payload)

@router.put("/produtos/{produto_id}", response_model=ProdutoResponse)
def atualizar_produto(produto_id: int, payload: ProdutoUpdate, db: Session = Depends(get_db)):
    return admin_service.update_product(db, produto_id, payload)

@router.delete("/produtos/{produto_id}", status_code=204)
def excluir_produto(produto_id: int, db: Session = Depends(get_db)):
    admin_service.delete_product(db, produto_id); return Response(status_code=204)

@router.post("/produtos/{produto_id}/variacoes", response_model=OpcaoVariacaoResponse, status_code=201)
def criar_variacao(produto_id: int, payload: OpcaoVariacaoCreate, db: Session = Depends(get_db)):
    return admin_service.create_variation(db, produto_id, payload)

@router.delete("/variacoes/{variacao_id}", status_code=204)
def excluir_variacao(variacao_id: int, db: Session = Depends(get_db)):
    admin_service.delete_variation(db, variacao_id); return Response(status_code=204)

@router.post("/combos", response_model=ComboResponse, status_code=201)
def criar_combo(payload: ComboCreate, db: Session = Depends(get_db)):
    return admin_service.create_combo(db, payload)

@router.delete("/combos/{combo_id}", status_code=204)
def excluir_combo(combo_id: int, db: Session = Depends(get_db)):
    admin_service.delete_combo(db, combo_id); return Response(status_code=204)

@router.get("/fornecedores", response_model=list[FornecedorResponse])
def listar_fornecedores(db: Session = Depends(get_db)):
    return db.query(Fornecedor).order_by(Fornecedor.nome).all()


@router.post("/fornecedores", response_model=FornecedorResponse, status_code=201)
def criar_fornecedor(payload: FornecedorCreate, db: Session = Depends(get_db)):
    return admin_service.create_supplier(db, payload)


@router.put("/fornecedores/{fornecedor_id}", response_model=FornecedorResponse)
def atualizar_fornecedor(fornecedor_id: int, payload: FornecedorUpdate, db: Session = Depends(get_db)):
    return admin_service.update_supplier(db, fornecedor_id, payload)


@router.delete("/fornecedores/{fornecedor_id}", status_code=204)
def excluir_fornecedor(fornecedor_id: int, db: Session = Depends(get_db)):
    admin_service.delete_supplier(db, fornecedor_id)
    return Response(status_code=204)
