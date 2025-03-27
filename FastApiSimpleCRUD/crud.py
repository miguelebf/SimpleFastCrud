from typing import List, Optional, Type

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, create_model
from sqlalchemy.orm import Session


class SimpleCrud:

    def __init__(self, get_db, api_router, Base):
        self.models = []
        self.get_db = get_db
        self.api_router = api_router
        self.Base = Base

    def add(
        self,
        model,
        schema: Optional[Type[BaseModel]] = None,
        dependencies: Optional[List] = None,
        relationship: bool = True
        ):
        if schema is None:
            schema = self._generate_schema(model, relationship)

        self.models.append((model, schema, dependencies or []))

        self._generate_endpoints(model, schema, dependencies)

    def _generate_schema(self, model, relationship: bool) -> Type[BaseModel]:
        fields = {}
        for column in model.__table__.columns:
            field_type = self._get_pydantic_type(column.type)
            fields[column.name
                  ] = (field_type, ... if column.primary_key else None)

        if relationship:
            for rel in model.__mapper__.relationships:
                related_model = rel.mapper.class_
                related_schema = self._generate_schema(
                    related_model, relationship=False
                    )
                fields[rel.key] = (Optional[List[related_schema]], None)

        schema_name = f"{model.__name__}Schema"
        return create_model(schema_name, **fields)

    def _get_pydantic_type(self, column_type):
        # Mapear tipos de SQLAlchemy a tipos de Pydantic
        from sqlalchemy import Boolean, Float, Integer, String
        if isinstance(column_type, Integer):
            return int
        elif isinstance(column_type, String):
            return str
        elif isinstance(column_type, Float):
            return float
        elif isinstance(column_type, Boolean):
            return bool
        else:
            return str

    def _generate_endpoints(
        self, model, schema: Type[BaseModel], dependencies: List
        ):
        router = APIRouter()
        tag = model.__tablename__.capitalize()

        # Endpoint para obtener todos los registros
        @router.get(
            f"/{model.__tablename__}",
            response_model=List[schema],
            dependencies=dependencies,
            tags=[tag]
            )
        def get_all(db: Session = Depends(self.get_db)):
            return db.query(model).all()

        # Endpoint para obtener un registro por ID
        @router.get(
            f"/{model.__tablename__}/{{id}}",
            response_model=schema,
            dependencies=dependencies,
            tags=[tag]
            )
        def get_one(id: int, db: Session = Depends(self.get_db)):
            db_model = db.query(model).filter(model.id == id).first()
            if db_model is None:
                raise HTTPException(status_code=404, detail="Item not found")
            return db_model

        @router.post(
            f"/{model.__tablename__}",
            response_model=schema,
            dependencies=dependencies,
            tags=[tag]
            )
        def create(item: schema, db: Session = Depends(self.get_db)):
            db_model = model(**item.dict())
            db.add(db_model)
            db.commit()
            db.refresh(db_model)
            return db_model

        @router.patch(
            f"/{model.__tablename__}/{{id}}",
            response_model=schema,
            dependencies=dependencies,
            tags=[tag]
            )
        def update(id: int, item: schema, db: Session = Depends(self.get_db)):
            db_model = db.query(model).filter(model.id == id).first()
            if db_model is None:
                raise HTTPException(status_code=404, detail="Item not found")
            for key, value in item.dict().items():
                setattr(db_model, key, value)
            db.commit()
            db.refresh(db_model)
            return db_model

        @router.delete(
            f"/{model.__tablename__}/{{id}}",
            dependencies=dependencies,
            tags=[tag]
            )
        def delete(id: int, db: Session = Depends(self.get_db)):
            db_model = db.query(model).filter(model.id == id).first()
            if db_model is None:
                raise HTTPException(status_code=404, detail="Item not found")
            db.delete(db_model)
            db.commit()
            return {"message": "Item deleted"}

        self.api_router.include_router(router)
