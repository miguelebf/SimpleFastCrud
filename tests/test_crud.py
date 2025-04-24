import unittest
from typing import List, Optional, Type
from unittest.mock import MagicMock, patch

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from SimpleFastCrud.crud import SimpleFastCrud


class TestSimpleCrud(unittest.TestCase):

    def setUp(self):
        self.crud = SimpleCrud()
        self.mock_model = MagicMock(__tablename__='test_model')
        self.mock_router = MagicMock(spec=APIRouter)
        self.mock_get_db = MagicMock()
        self.mock_auth_dep = MagicMock(spec=Depends)

    def test_generate_schemas(self):
        with patch('FastApiSimpleCRUD.crud.create_model') as mock_create_model:
            mock_model = MagicMock()
            mock_model.__table__.columns = []
            mock_model.__mapper__.relationships = []

            input_schema, output_schema = self.crud._generate_schemas(
                mock_model, relationship=True
                )

            self.assertTrue(mock_create_model.called)
            self.assertIsNotNone(input_schema)
            self.assertIsNotNone(output_schema)

    def test_get_pydantic_type(self):
        from sqlalchemy import Boolean, Float, Integer, String

        self.assertEqual(self.crud._get_pydantic_type(Integer()), int)
        self.assertEqual(self.crud._get_pydantic_type(String()), str)
        self.assertEqual(self.crud._get_pydantic_type(Float()), float)
        self.assertEqual(self.crud._get_pydantic_type(Boolean()), bool)

    def test_generate_endpoints(self):
        with patch.object(
            self.crud, '_create_get_all_function', return_value=MagicMock()
            ) as mock_get_all_func:
            self.crud._generate_endpoints(
                model=self.mock_model,
                input_schema=MagicMock(),
                output_schema=MagicMock(),
                dependencies=[],
                auth_dep=self.mock_auth_dep,
                filter_param=None,
                pagination=False,
                steps=10,
                filter_query_search=None,
                filter_fields=None,
                api_router=self.mock_router,
                get_db=self.mock_get_db
                )

            self.assertTrue(mock_get_all_func.called)
            self.assertTrue(self.mock_router.add_api_route.called)

    def test_create_get_all_function(self):
        with patch('FastApiSimpleCRUD.crud.exec') as mock_exec:
            func = self.crud._create_get_all_function(
                model=self.mock_model,
                filter_param=None,
                filter_query_search=None,
                filter_fields=None,
                pagination=False,
                steps=10,
                endpoint_dependencies=[],
                auth_dep=self.mock_auth_dep,
                get_db=self.mock_get_db
                )

            self.assertTrue(mock_exec.called)
            self.assertIsNotNone(func)


if __name__ == '__main__':
    unittest.main()
