from io import StringIO
from sys import version
from sqlalchemy.sql.sqltypes import DateTime
from sqlalchemy.exc import IntegrityError
from starlette.responses import Response
from fastapi import APIRouter, Depends, HTTPException, Request
from dependencies import common_params, get_db, get_secret_random
from schemas import CreateEnvironment, CreateResource, TestResource
from sqlalchemy.orm import Session
from typing import Optional
from models import Environment, Resource, ResourceType, O
from dependencies import get_token_header
import uuid
from datetime import datetime, timedelta
from exceptions import username_already_exists
from sqlalchemy import over
from sqlalchemy import engine_from_config, and_, func, literal_column, case
from sqlalchemy_filters import apply_pagination
import time
import os
import uuid
from sqlalchemy.dialects import postgresql
import paramiko
from io import StringIO
import socket
import requests
import base64
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import subprocess
import re


page_size = os.getenv('PAGE_SIZE')
CREDENTIAL_SERVICE_URL = os.getenv('CREDENTIAL_SERVICE_URL')


router = APIRouter(
    prefix="/v1/resources",
    tags=["SoftwareEnvironmentRegistryAPIs"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.post("/connection-test")
def test(details: TestResource, db: Session = Depends(get_db)):
    client = paramiko.SSHClient()
    response = {}
    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(details.ipv4, username=details.console_username, password=details.password, port=details.port)
        stdin, stdout, stderr = client.exec_command('cat /etc/*-release')
        distro_info = str(stdout.read())
        oslist = db.query(O).all()
        osname = 'unknown'
        for os in oslist:
            if re.search(os.os, distro_info, re.IGNORECASE):
                osname = os.os
                break

        return {'osname': osname}
    except (socket.error, paramiko.BadHostKeyException, paramiko.AuthenticationException, paramiko.SSHException) as e:
        raise HTTPException(status_code=422, detail=str(e))

    return Response(status_code=204)


@router.post("")
def create(details: CreateResource, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    supported_protocols = {'ssh': 'SSH', 'SSH': 'SSH'}

    protocol = supported_protocols.get(details.protocol, 'SSH')

    id = details.id or uuid.uuid4().hex
    key_iostring = StringIO()
    client = paramiko.SSHClient()

    try:
        client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        client.connect(details.ipv4, username=details.console_username, password=details.password, port=details.port)

    except (socket.error, paramiko.BadHostKeyException, paramiko.AuthenticationException, paramiko.SSHException) as e:
        raise HTTPException(status_code=422, detail=str(e))

    try:
        key = paramiko.RSAKey.generate(2048)
        key.write_private_key(key_iostring)

        data = {
            "resource": id,
            "encrypted_key": key_iostring.getvalue(),
            "public_key": "ssh-rsa "+key.get_base64(),
            "expire_at": str(datetime.now()+timedelta(90)),
            "active": True
        }

        stdin, stdout, stderr = client.exec_command(f"echo 'ssh-rsa {key.get_base64()}' >> ~/.ssh/authorized_keys")

        response = requests.post(CREDENTIAL_SERVICE_URL+'/v1/credentials',
                                 data=json.dumps(data), headers={"Content-Type": "application/json"})
        secret_id = json.loads(response.text)['id']

    except BaseException as e:
        raise HTTPException(status_code=422, detail=str(e))

    if details.active == True:
        active = 1
    else:
        active = 0

    env = db.query(Environment).get(details.environment)
    res_type = db.query(ResourceType).get(details.resource_type)

    # Set user entity
    resource = Resource(
        id=id,
        name=details.name,
        active=active,
        environment=env,
        resource_type=res_type,
        ipv4=details.ipv4,
        ipv6=details.ipv6,
        console_username=details.console_username,
        console_secret_id=secret_id,
        port=details.port,
        protocol=protocol,
        os=details.os

    )

    # commiting data to db
    try:
        db.add(resource)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail="Unable to create new environment")
    return Response(status_code=204)


@router.get("")
def get_by_filter(page: Optional[str] = 1, limit: Optional[int] = page_size, commons: dict = Depends(common_params), db: Session = Depends(get_db), id: Optional[str] = None, name: Optional[str] = None, environment: Optional[str] = None, status: Optional[bool] = None, ipv4: Optional[str] = None, ipv6: Optional[str] = None, resource_type: Optional[str] = None):
    filters = []

    if(name):
        filters.append(Resource.name.ilike(name+'%'))
    else:
        filters.append(Resource.name.ilike('%'))

    if(environment):
        filters.append(Resource.environment_id == environment)

    if(ipv4):
        filters.append(Resource.ipv4.ilike(ipv4+'%'))

    if(ipv6):
        filters.append(Resource.ipv6.ilike(ipv6+'%'))

    if(resource_type):
        filters.append(Resource.resource_type_id == resource_type)

    if(status == True):
        filters.append(Resource.active == 1)

    query = db.query(
        over(func.row_number(), order_by=Resource.name).label('index'),
        Resource.id,
        func.concat(Resource.name, ' (', Resource.ipv4, ')').label('name'),
        case((Resource.active == 1, 'Yes'), (Resource.active == 0, 'No')).label('active'),
        Resource.ipv4,
        Resource.ipv6,
        Environment.name.label('environment'),
        ResourceType.name.label('resource_type'),
        Resource.console_username,
        Resource.console_secret_id,
        Resource.port,
        Resource.os,
        Environment.group_id.label('access_group')
    )

    query, pagination = apply_pagination(query.join(Resource.environment).join(Resource.resource_type).where(
        and_(*filters)).order_by(Resource.name.asc()), page_number=int(page), page_size=int(limit))
    # return str(query.statement)+

    response = {
        "data": query.all(),
        "meta": {
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

    query, pagination = apply_pagination(query.where(
        and_(*filters)).order_by(ResourceType.name.asc()), page_number=int(page), page_size=int(limit))

    response = {
        "data": query.all(),
        "meta": {
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


@router.get("/os")
def get_by_filter(db: Session = Depends(get_db)):
    os = db.query(O).all()

    response = {
        "data": os
    }

    return response


@router.get("/{id}")
def get_by_id(id: str, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    query = db.query(
        Resource.id, Resource.environment_id, Resource.ipv4, Resource.ipv6, Resource.name,
        Resource.console_secret_id, Resource.port, Resource.active, Resource.resource_type_id,
        Resource.console_username, Resource.protocol, Resource.os,
        Environment.group_id.label('access_group')).join(Resource.environment).filter(Resource.id == id.strip())
    if query.count() == 0:
        raise HTTPException(status_code=404, detail="Item not found")
    response = {
        "data": query.first()
    }
    return response


@router.put("/{id}")
def update(id: str, details: CreateResource, commons: dict = Depends(common_params), db: Session = Depends(get_db)):
    # Set user entity
    resource = db.query(Resource).get(id)

    id = details.id or uuid.uuid4().hex

    if details.active == True:
        active = 1
    else:
        active = 0

    env = db.query(Environment).get(details.environment)
    res_type = db.query(ResourceType).get(details.resource_type)

    # Set user entity
    resource.id = id
    resource.name = details.name
    resource.active = active
    resource.environment = env
    resource.resource_type = res_type
    resource.ipv4 = details.ipv4
    resource.ipv6 = details.ipv6
    resource.console_username = details.console_username
    resource.console_secret_id = details.password
    resource.port = details.port
    resource.protocol = details.protocol
    resource.os = details.os

    # commiting data to db
    try:
        db.add(resource)
        db.commit()
    except IntegrityError as err:
        db.rollback()
        raise HTTPException(status_code=422, detail=username_already_exists)
    return {
        "success": True
    }
