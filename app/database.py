from sqlalchemy import create_engine


from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = "sqlite:///./banco.db"

Base = declarative_base()


def get_engine():
    return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())