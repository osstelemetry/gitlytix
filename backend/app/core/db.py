from sqlmodel import Session, create_engine
from sqlalchemy.orm import sessionmaker

from app.core.config import settings

# Use ClickHouse's HTTP interface with SQLModel
engine = create_engine(str(settings.SQLALCHEMY_DATABASE_URI), echo=True)

# Use SQLModel's session maker
SessionLocal = sessionmaker(bind=engine)

def get_db():
    with Session(engine) as session:
        yield session
