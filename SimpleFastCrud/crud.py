from typing import Any, Dict, List, Optional, Type

from fastapi import Depends, HTTPException, Query
from pydantic import BaseModel, create_model
from sqlalchemy.orm import Session


class SimpleFastCrud:

    def __init__(self):
        self.models = []

    def add(
        self,
        model: Type[BaseModel],
        api_router,
        get_db,
        auth_dep: Optional[Depends] = None,
        filter_param: Optional[str] = None,
        schema: Optional[Type[BaseModel]] = None,
        dependencies: Optional[List] = None,
        relationship: bool = True,
        pagination: bool = False,
        steps: int = 10,
        filter_query_search: Optional[str] = None,
        filter_fields: Optional[dict] = None
        ):
        if schema is None:
            input_schema, output_schema = self._generate_schemas(
                model, relationship
                )
        else:
            input_schema = output_schema = schema

        self.models.append((
            model, input_schema, output_schema, dependencies or [], auth_dep,
            filter_param, pagination, steps, filter_query_search, filter_fields
            ))

        self._generate_endpoints(
            model, input_schema, output_schema, dependencies or [], auth_dep,
            filter_param, pagination, steps, filter_query_search,
            filter_fields, api_router, get_db
            )

    def _generate_schemas(
        self, model: Type[BaseModel], relationship: bool
        ) -> (Type[BaseModel], Type[BaseModel]):
        input_fields = {}
        output_fields = {}
        for column in model.__table__.columns:
            field_type = self._get_pydantic_type(column.type)
            if not column.primary_key:
                input_fields[column.name] = (field_type, ...)
            output_fields[column.name
                         ] = (field_type, ... if column.primary_key else None)

        if relationship:
            for rel in model.__mapper__.relationships:
                related_model = rel.mapper.class_
                related_input_schema, related_output_schema = self._generate_schemas(
                    related_model, relationship=False
                    )
                if rel.uselist:
                    input_fields[
                        rel.key
                        ] = (Optional[List[related_input_schema]], None)
                    output_fields[
                        rel.key
                        ] = (Optional[List[related_output_schema]], None)
                else:
                    input_fields[rel.key
                                ] = (Optional[related_input_schema], None)
                    output_fields[rel.key
                                 ] = (Optional[related_output_schema], None)

        input_schema = create_model(
            f"{model.__name__}InputSchema", **input_fields
            )
        output_schema = create_model(
            f"{model.__name__}OutputSchema", **output_fields
            )
        return input_schema, output_schema

    def _get_pydantic_type(self, column_type):
        from sqlalchemy import Boolean, Float, Integer, String
        if isinstance(column_type, Integer):
            return int
        elif isinstance(column_type, String):
            return str
        elif isinstance(column_type, Float):
            return float
        elif isinstance(column_type, Boolean):
            return bool
        return str

    def _generate_endpoints(
        self, model: Type[BaseModel], input_schema: Type[BaseModel],
        output_schema: Type[BaseModel], dependencies: List[Depends],
        auth_dep: Optional[Depends], filter_param: Optional[str],
        pagination: bool, steps: int, filter_query_search: Optional[str],
        filter_fields: Optional[dict], api_router, get_db
        ):
        from fastapi import APIRouter
        router = APIRouter()
        tag = model.__tablename__.capitalize()
        endpoint_dependencies = []

        if dependencies:
            endpoint_dependencies.extend(dependencies)
        if auth_dep:
            endpoint_dependencies.append(auth_dep)

        # Generar función get_all dinámicamente
        get_all_func = self._create_get_all_function(
            model, filter_param, filter_query_search, filter_fields,
            pagination, steps, endpoint_dependencies, auth_dep, get_db
            )

        # Registrar endpoint GET all
        router.add_api_route(
            f"/{model.__tablename__}",
            endpoint=get_all_func,
            methods=["GET"],
            dependencies=endpoint_dependencies,
            tags=[tag]
            )

        # Endpoint GET one (Obtener un elemento por ID)
        @router.get(
            f"/{model.__tablename__}/{{id}}",
            dependencies=endpoint_dependencies,
            tags=[tag],
            )
        async def get_one(
            id: int,
            db: Session = Depends(get_db),
            authorized_user: dict = auth_dep
            ):
            if auth_dep and not authorized_user:
                raise HTTPException(
                    status_code=401, detail="Authentication required"
                    )

            query = db.query(model)

            if filter_param and authorized_user:
                tenant_id = authorized_user.get(filter_param)
                if not tenant_id:
                    raise HTTPException(
                        status_code=403, detail="No tenant ID found in user"
                        )
                query = query.filter(getattr(model, filter_param) == tenant_id)

            db_model = query.filter(model.id == id).first()

            if not db_model:
                raise HTTPException(status_code=404, detail="Item not found")
            return {"data": db_model, "message": "", "metadata": {}}

        # Endpoint POST create (Crear nuevo elemento)
        @router.post(
            f"/{model.__tablename__}",
            dependencies=endpoint_dependencies,
            tags=[tag],
            )
        async def create(
            item: input_schema,
            db: Session = Depends(get_db),
            authorized_user: dict = auth_dep
            ):
            if auth_dep and not authorized_user:
                raise HTTPException(
                    status_code=401, detail="Authentication required"
                    )

            item_data = item.dict()

            if filter_param and authorized_user:
                tenant_id = authorized_user.get(filter_param)
                if not tenant_id:
                    raise HTTPException(
                        status_code=403, detail="No tenant ID found in user"
                        )
                item_data[filter_param] = tenant_id

            try:
                db_model = model(**item_data)
                db.add(db_model)
                db.commit()
                db.refresh(db_model)
                return {
                    "data": db_model,
                    "message": "Item created successfully",
                    "metadata": {}
                    }
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=422, detail=str(e))

        # Endpoint PUT update (Actualizar elemento existente)
        @router.put(
            f"/{model.__tablename__}/{{id}}",
            dependencies=endpoint_dependencies,
            tags=[tag],
            response_model=output_schema
            )
        async def update(
            id: int,
            item: input_schema,
            db: Session = Depends(get_db),
            authorized_user: dict = auth_dep
            ):
            query = db.query(model)

            if filter_param and authorized_user:
                filter_param_ = authorized_user.get(filter_param)
                if not filter_param_:
                    raise HTTPException(
                        status_code=403,
                        detail=f'No {filter_param} found in user'
                        )
                query = query.filter(
                    getattr(model, filter_param_) == filter_param_
                    )

            db_model = query.filter(model.id == id).first()

            if not db_model:
                raise HTTPException(status_code=404, detail="Item not found")

            try:
                update_data = item.dict(exclude_unset=True)
                for key, value in update_data.items():
                    setattr(db_model, key, value)
                db.commit()
                db.refresh(db_model)
                return db_model
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=422, detail=str(e))

        # Endpoint DELETE (Eliminar elemento)
        @router.delete(
            f"/{model.__tablename__}/{{id}}",
            dependencies=endpoint_dependencies,
            tags=[tag]
            )
        async def delete(
            id: int,
            db: Session = Depends(get_db),
            authorized_user: dict = auth_dep
            ):
            if auth_dep and not authorized_user:
                raise HTTPException(
                    status_code=401, detail="Authentication required"
                    )

            query = db.query(model)

            if filter_param and authorized_user:
                tenant_id = authorized_user.get(filter_param)
                if not tenant_id:
                    raise HTTPException(
                        status_code=403, detail="No tenant ID found in user"
                        )
                query = query.filter(getattr(model, filter_param) == tenant_id)

            db_model = query.filter(model.id == id).first()

            if not db_model:
                raise HTTPException(status_code=404, detail="Item not found")

            try:
                db.delete(db_model)
                db.commit()
                return {"message": "Item deleted successfully"}
            except Exception as e:
                db.rollback()
                raise HTTPException(status_code=422, detail=str(e))

        api_router.include_router(router)

    def _create_get_all_function(
        self, model: Type[BaseModel], filter_param: Optional[str],
        filter_query_search: Optional[str], filter_fields: Optional[dict],
        pagination: bool, steps: int, endpoint_dependencies: List[Depends],
        auth_dep: Optional[Depends], get_db
        ):
        from datetime import datetime
        from typing import Optional

        from fastapi import Query
        from sqlalchemy.orm import Session

        # Obtener el nombre de la dependencia de autenticación si existe
        auth_dep_name = auth_dep.dependency.__name__ if auth_dep else None

        # Parámetros base
        params = [
            'db: Session = Depends(get_db)',
            f'authorized_user: dict = Depends({auth_dep_name})'
            if auth_dep else 'authorized_user: dict = None',
            'page: int = Query(1, ge=1, description="Page number")',
            f'per_page: int = Query({steps}, ge=1, le=100, description="Items per page")',
            f'pagination: bool = Query({pagination}, description="Enable pagination")',
            'search: Optional[str] = Query(None, description="Search query")'
            ]

        # Agregar parámetros de filtro
        if filter_fields:
            for field, options in filter_fields.items():
                comparison = options.get("comparison", "eq")
                description = options.get("description", f"Filter by {field}")

                if comparison == "between":
                    params.append(
                        f'{field}_from: Optional[str] = Query(None, description="From value for {field}")'
                        )
                    params.append(
                        f'{field}_to: Optional[str] = Query(None, description="To value for {field}")'
                        )
                else:
                    params.append(
                        f'{field}: Optional[str] = Query(None, description="{description}")'
                        )

        # Construir el código de la función
        func_code = f"async def get_all({', '.join(params)}):\n"
        func_code += "    query = db.query(model)\n"

        # Filtro de tenant
        if filter_param and auth_dep:
            func_code += (
                "    if authorized_user:\n"
                f"        filter_param_ = authorized_user.get('{filter_param}')\n"
                "        if filter_param_ is not None:\n"
                f"            query = query.filter(model.{filter_param} == filter_param_)\n"
                "        else:\n"
                "            raise HTTPException(status_code=400, detail='Missing tenant ID')\n"
                )

        # Filtro de búsqueda
        if filter_query_search:
            func_code += (
                "    if search is not None:\n"
                f"        query = query.filter(model.{filter_query_search}.ilike(f'%{{search}}%'))\n"
                "    else:\n"
                "        search = ''  # Default empty search\n"
                )

        # Filtros adicionales
        if filter_fields:
            for field, options in filter_fields.items():
                comparison = options.get("comparison", "eq")
                field_type = options.get(
                    "type", "string"
                    )  # Obtener el tipo del campo

                if comparison == "between":
                    func_code += (
                        f"    if {field}_from is not None and {field}_to is not None:\n"
                        f"        if '{field_type}' == 'date':\n"
                        f"            try:\n"
                        f"                {field}_from = datetime.strptime({field}_from, '%d-%m-%Y').strftime('%Y-%m-%d')\n"
                        f"                {field}_to = datetime.strptime({field}_to, '%d-%m-%Y').strftime('%Y-%m-%d')\n"
                        f"            except ValueError:\n"
                        f"                raise HTTPException(status_code=400, detail='Invalid date format. Use DD-MM-YYYY.')\n"
                        f"        query = query.filter(model.{field}.between({field}_from, {field}_to))\n"
                        "    else:\n"
                        f"        {field}_from, {field}_to = None, None  # Default values\n"
                        )
                else:
                    operator = {
                        "eq": "==",
                        "ne": "!=",
                        "lt": "<",
                        "le": "<=",
                        "gt": ">",
                        "ge": ">="
                        }.get(comparison, "==")

                    func_code += (
                        f"    if {field} is not None:\n"
                        f"        query = query.filter(model.{field} {operator} {field})\n"
                        "    else:\n"
                        f"        {field} = None  # Default value\n"
                        )

        # Paginación
        func_code += (
            "    query = query.order_by(model.id.desc())\n"  # Ordenar por id descendente
            "    if pagination:\n"
            "        offset = (page - 1) * per_page\n"
            "        query = query.offset(offset).limit(per_page)\n"
            "\n"
            "    items = query.all()\n"
            "    return {\n"
            "        \"data\": items,\n"
            "        \"message\": \"\",\n"
            "        \"metadata\": {\n"
            "            \"page\": page,\n"
            "            \"per_page\": per_page,\n"
            "            \"total\": len(items)\n"
            "        }\n"
            "    }\n"
            )

        # Preparar el contexto para exec
        local_vars = {}
        global_vars = {
            'model': model,
            'Depends': Depends,
            'Query': Query,
            'Session': Session,
            'Optional': Optional,
            'get_db': get_db,
            'List': List,
            'datetime': datetime  # Agregar datetime al contexto global
            }

        if auth_dep:
            global_vars[auth_dep_name] = auth_dep.dependency

        # Ejecutar el código para crear la función
        exec(func_code, global_vars, local_vars)
        return local_vars['get_all']
