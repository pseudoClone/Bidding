from sqlmodel import create_engine, SQLModel
from dotenv import load_dotenv
import os

load_dotenv()
DATABASE_URL = str(os.getenv("DATABASE_URL"))
engine = create_engine(DATABASE_URL, echo=True)


def init_db():
    SQLModel.metadata.create_all(engine)


init_db()
