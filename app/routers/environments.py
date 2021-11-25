from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Request
from dependencies import common_params, get_db, get_secret_random
from schemas import CreateEnvironment
from sqlalchemy.orm import Session
from typing import Optional
from models import Environment, Resource, ResourceType
from dependencies import get_token_header
from datetime import datetime
from exceptions import username_already_exists
from sqlalchemy import over
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid

page_size = os.getenv('PAGE_SIZE')


router = APIRouter(
    prefix="/v1/environments",
    tags=["SoftwareEnvironmentRegistryAPIs"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

@router.post("")
def create(details: CreateEnvironment, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #generate token
    id = details.id or uuid.uuid4().hex
    if details.deleted==True:
        deleted = 1
    else:
        deleted = 0

    if details.active == True:
        active = 1
    else:
        active = 0
    #Set user entity
    env = Environment(
        id=id,
        name=details.name,
        description=details.description,
        deleted=deleted,
        group_id=details.group,
        active=active
    )    

    #commiting data to db
    try:
        db.add(env)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to create new environment")
    return {
        "success": True
    }

@router.get("")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, name: Optional[str] = None, group: Optional[str] = None, status: Optional[bool] = None):
    filters = []

    filters.append(Environment.deleted==0)

    if(name):
        filters.append(Environment.name.ilike(name+'%'))

    if(group):
        filters.append(Environment.group_id==group)

    if(status==True):
        filters.append(Environment.active==1)
    
    # if(status==False):
    #     filters.append(Environment.active==0)

    query = db.query(
        over(func.row_number(), order_by='name').label('index'),
        Environment.id,
        Environment.name,
        case((Environment.active == 1, 'Yes'), (Environment.active == 0, 'No')).label('active')
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(Environment.name.asc()), page_number = int(page), page_size = int(limit))

    response = {
        "data": query.all(),
        "meta":{
            "total_records": pagination.total_results,
            "limit": pagination.page_size,
            "num_pages": pagination.num_pages,
            "current_page": pagination.page_number
        }
    }

    return response

@router.delete("/{id}")
def delete_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    env = db.query(Environment).get(id.strip())
    env.deleted = 1
    # db.delete(env)
    db.add(env)
    db.commit()
    return Response(status_code=204)


@router.get("/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    env = db.query(Environment).get(id.strip())
    if env == None:
        raise HTTPException(status_code=404, detail="Item not found")
    response = {
        "data": env
    }
    return response

@router.put("/{id}")
def update(id:str, details: CreateEnvironment, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #Set user entity
    env = db.query(Environment).get(id)

    if details.deleted==True:
        deleted = 1
    else:
        deleted = 0

    if details.active == True:
        active = 1
    else:
        active = 0

    env.name = details.name
    env.description = details.description
    env.deleted=deleted
    env.group_id=details.group
    env.active=active

    #commiting data to db
    try:
        db.add(env)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail=username_already_exists)
    return {
        "success": True
    }