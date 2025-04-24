# SimpleFastCrud

SimpleFastCrud is a tool that simplifies the creation of dynamic CRUD endpoints in FastAPI using SQLAlchemy and Pydantic. This package automatically generates schemas and endpoints for SQLAlchemy models.

## Installation

```bash
pip install SimpleFastCrud
```

## Basic Usage

### Initial Setup

```python
from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy.orm import Session
from SimpleFastCrud.crud import SimpleFastCrud
from your_project.database import get_db  # Function to get the database session
from your_project.models import YourModel  # SQLAlchemy model

app = FastAPI()
api_router = APIRouter()
crud = SimpleCrud()

crud.add(
    model=YourModel,
    api_router=api_router,
    get_db=get_db
)

app.include_router(api_router)
```

### Complete Example

#### SQLAlchemy Model

```python
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
```

#### FastAPI Configuration

```python
from fastapi import FastAPI, Depends, APIRouter
from sqlalchemy.orm import Session
from SimpleFastCrud.crud import SimpleFastCrud
from your_project.database import get_db
from your_project.models import User

app = FastAPI()
api_router = APIRouter()
crud = SimpleCrud()

crud.add(
    model=User,
    api_router=api_router,
    get_db=get_db
)

app.include_router(api_router)
```

### Generated Endpoints

1. **GET /users**: Retrieve all users.
2. **GET /users/{id}**: Retrieve a user by ID.
3. **POST /users**: Create a new user.
4. **PUT /users/{id}**: Update an existing user.
5. **DELETE /users/{id}**: Delete a user.

### Customization

#### Adding Authentication Dependencies

```python
from fastapi import Depends
from your_project.auth import get_current_user

crud.add(
    model=User,
    api_router=api_router,
    get_db=get_db,
    auth_dep=Depends(get_current_user)
)
```

#### Filters and Pagination

```python
crud.add(
    model=User,
    api_router=api_router,
    get_db=get_db,
    filter_param='tenant_id',
    pagination=True,
    steps=20
)
```

## Contributions

Contributions are welcome! Please open an issue or a pull request in the project repository.

## License

This project is licensed under the MIT License.