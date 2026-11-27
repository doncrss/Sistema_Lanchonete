from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_admin
from app.schemas.catalogo_schemas import ComboCreate, ComboResponse, OpcaoVariacaoCreate, OpcaoVariacaoResponse
from app.schemas.produto_schemas import ProdutoCreate, ProdutoUpdate, ProdutoResponse
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
