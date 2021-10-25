from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Request
from dependencies import common_params, get_db, get_secret_random
from schemas import CreateEnvironment, CreateResource
from sqlalchemy.orm import Session
from typing import Optional
from models import Environment, Resource, ResourceType
from dependencies import get_token_header
import uuid
from datetime import datetime
from exceptions import username_already_exists
from sqlalchemy import over
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid
from sqlalchemy.dialects import postgresql

page_size = os.getenv('PAGE_SIZE')


router = APIRouter(
    prefix="/v1/resources",
    tags=["SoftwareEnvironmentRegistryAPIs"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

@router.post("")
def create(details: CreateResource, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #generate token
    id = details.id or uuid.uuid4().hex

    if details.active == True:
        active = 1
    else:
        active = 0
    
    env = db.query(Environment).get(details.environment)
    res_type = db.query(ResourceType).get(details.resource_type)
    
    #Set user entity
    resource = Resource(
        id=id,
        name=details.name,
        active=active,
        environment=env,
        resource_type=res_type,
        ipv4=details.ipv4,
        ipv6=details.ipv6,
        console_username=details.console_username,
        console_secret_id=details.password, #put the secret id here from the hashivault
        port=details.port,
        protocol=details.protocol
    )    

    #commiting data to db
    try:
        db.add(resource)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to create new environment")
    return {
        "success": True
    }

@router.get("")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, name: Optional[str] = None, environment: Optional[str] = None, status: Optional[bool] = None, ipv4: Optional[str] = None, ipv6: Optional[str] = None, resource_type: Optional[str] = None):
    filters = []

    if(name):
        filters.append(Resource.name.ilike(name+'%'))

    if(environment):
        filters.append(Resource.environment_id==environment)        

    if(ipv4):
        filters.append(Resource.ipv4.ilike(ipv4+'%')) 

    if(ipv6):
        filters.append(Resource.ipv6.ilike(ipv6+'%')) 

    if(resource_type):
        filters.append(Resource.resource_type_id==resource_type)

    if(status==True):
        filters.append(Resource.active == 1)
    

    query = db.query(
        over(func.row_number(), order_by=Resource.name).label('index'),
        Resource.id,
        Resource.name,
        case((Resource.active == 1, 'Yes'), (Resource.active == 0, 'No')).label('active'),
        Resource.ipv4,
        Resource.ipv6,
        Environment.name.label('environment'),
        ResourceType.name.label('resource_type')
    )

    query, pagination = apply_pagination(query.join(Resource.environment).join(Resource.resource_type).where(and_(*filters)).order_by(Resource.name.asc()), page_number = int(page), page_size = int(limit))
    # return str(query.statement)+

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

@router.get("/resource-types")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, name: Optional[str] = None, environment: Optional[str] = None, status: Optional[bool] = None):
    filters = []

    query = db.query(
        over(func.row_number(), order_by='name').label('index'),
        ResourceType.id,
        ResourceType.name,
        ResourceType.code        
    )

    query, pagination = apply_pagination(query.where(and_(*filters)).order_by(ResourceType.name.asc()), page_number = int(page), page_size = int(limit))

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
    resource = db.query(Resource).get(id.strip())
    db.delete(resource)
    db.commit()
    return Response(status_code=204)


@router.get("/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    resource = db.query(Resource).get(id.strip())
    if resource == None:
        raise HTTPException(status_code=404, detail="Item not found")
    response = {
        "data": resource
    }
    return response

@router.put("/{id}")
def update(id:str, details: CreateResource, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    #Set user entity
    resource = db.query(Resource).get(id)

    id = details.id or uuid.uuid4().hex

    if details.active == True:
        active = 1
    else:
        active = 0
    
    env = db.query(Environment).get(details.environment)
    res_type = db.query(ResourceType).get(details.resource_type)
    
    #Set user entity
    resource.id=id
    resource.name=details.name
    resource.active=active
    resource.environment=env
    resource.resource_type=res_type
    resource.ipv4=details.ipv4
    resource.ipv6=details.ipv6
    resource.console_username=details.console_username
    resource.console_secret_id=details.password
    resource.port=details.port
    resource.protocol=details.protocol


    #commiting data to db
    try:
        db.add(resource)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail=username_already_exists)
    return {
        "success": True
    }

