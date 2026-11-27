from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.produto_models import Produto
from app.services.catalog_service import list_catalog, catalog_product
from app.schemas.catalogo_schemas import CatalogoProdutoResponse

router = APIRouter(prefix="/api/produtos", tags=["Cardápio"])

@router.get("", response_model=list[CatalogoProdutoResponse])
def listar(db: Session = Depends(get_db)):
    return list_catalog(db)

@router.get("/{produto_id}")
def obter(produto_id: int, db: Session = Depends(get_db)):
    product = db.get(Produto, produto_id)
    if not product: raise HTTPException(404, "Produto não encontrado.")
    return catalog_product(db, product)
