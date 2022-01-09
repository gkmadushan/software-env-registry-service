from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from routers import environments, resources
from fastapi.security import OAuth2PasswordBearer

from fastapi_route_logger_middleware import RouteLoggerMiddleware
import logging
from datetime import date

logging.basicConfig(filename='../logs/{}_app.log'.format(date.today().strftime("%Y-%m-%d")), level=logging.INFO)
app = FastAPI(debug=True)
app.add_middleware(RouteLoggerMiddleware)


origins = [
    "http://localhost",
    "http://localhost:8080",
    "http://localhost:3000",
]

# middlewares
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# user routes
app.include_router(environments.router)
app.include_router(resources.router)
