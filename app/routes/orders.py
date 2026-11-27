from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.security import require_admin
from app.schemas.checkout_schemas import PedidoCheckout, PedidoResponse, StatusPedidoUpdate
from app.services.order_service import create_order, list_orders, update_order_status

router = APIRouter(prefix="/api/pedidos", tags=["Pedidos"])

@router.post("", response_model=PedidoResponse, status_code=201)
def criar(payload: PedidoCheckout, db: Session = Depends(get_db)):
    return create_order(db, payload)

@router.get("", response_model=list[PedidoResponse], dependencies=[Depends(require_admin)])
def listar(db: Session = Depends(get_db)):
    return list_orders(db)

@router.patch("/{pedido_id}/status", response_model=PedidoResponse, dependencies=[Depends(require_admin)])
def atualizar(pedido_id: int, payload: StatusPedidoUpdate, db: Session = Depends(get_db)):
    return update_order_status(db, pedido_id, payload)
