from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from {{package_name}}.api.deps import db_session
from {{package_name}}.modules.{{module_name}}.schemas import {{class_name}}Create, {{class_name}}Read
from {{package_name}}.modules.{{module_name}}.services import {{class_name}}Service


router = APIRouter()


@router.get("/", response_model=list[{{class_name}}Read])
def list_{{module_name}}(db: Session = Depends(db_session)) -> list[{{class_name}}Read]:
    return {{class_name}}Service(db).list_{{module_name}}()


@router.post("/", response_model={{class_name}}Read, status_code=status.HTTP_201_CREATED)
def create_{{module_name}}(payload: {{class_name}}Create, db: Session = Depends(db_session)) -> {{class_name}}Read:
    return {{class_name}}Service(db).create_{{module_name}}(payload)
