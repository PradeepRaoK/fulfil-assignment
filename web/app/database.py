from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.exc import OperationalError
import os
import time

DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///./test.db')

# Create engine without connecting yet
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=0)

# Wait for the database to be ready (up to 30s)
for i in range(15):
    try:
        # Try connecting
        conn = engine.connect()
        conn.close()
        print("Database is ready!")
        break
    except OperationalError:
        print("Database not ready, waiting 2s...")
        time.sleep(2)
else:
    raise RuntimeError("Database not ready after 30s")

# Session and Base
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()