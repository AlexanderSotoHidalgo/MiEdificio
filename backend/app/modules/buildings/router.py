from fastapi import APIRouter, HTTPException

from app.api.deps import AdminUser, DbSession
from app.models import Building
from app.modules.buildings.schemas import BuildingOut, BuildingUpdate

router = APIRouter(prefix="/buildings", tags=["Edificios"])


@router.get("/current", response_model=BuildingOut)
def current_building(admin: AdminUser, db: DbSession) -> Building:
    building = db.get(Building, admin.building_id)
    if building is None or not building.is_active:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")
    return building


@router.patch("/current", response_model=BuildingOut)
def update_building(payload: BuildingUpdate, admin: AdminUser, db: DbSession) -> Building:
    building = db.get(Building, admin.building_id)
    if building is None or not building.is_active:
        raise HTTPException(status_code=404, detail="Edificio no encontrado")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(building, field, value.strip() if isinstance(value, str) else value)
    db.commit()
    db.refresh(building)
    return building
