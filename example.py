import sqlalchemy
from fastapi import FastAPI
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from FastApiSimpleCRUD import SimpleCrud

Base = declarative_base()
engine = create_engine('sqlite:///./test.db')
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
app = FastAPI()


# Crete Model
class Item(Base):
    __tablename__ = 'items'
    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, index=True)
    name = sqlalchemy.Column(sqlalchemy.String)
    description = sqlalchemy.Column(sqlalchemy.String)


simple_crud = SimpleCrud(SessionLocal, app, Base)
simple_crud.add(Item)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
