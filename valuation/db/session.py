from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from valuation.config import settings

# Engine dùng cho ghi dữ liệu (cần quyền write)
engine_write = create_engine(
    settings.database_url_write, 
    pool_pre_ping=True, 
    pool_size=5, 
    max_overflow=10
)
SessionLocalWrite = sessionmaker(autocommit=False, autoflush=False, bind=engine_write)

# Engine dùng cho đọc dữ liệu (readonly).
# AUTOCOMMIT: luồng phân tích chỉ đọc, không cần transaction. Tránh trường hợp
# một query lỗi để lại transaction "aborted" → connection trả về pool ở trạng
# thái hỏng → poison query sau (gây flaky test ngẫu nhiên khi dùng pytest-randomly).
engine_read = create_engine(
    settings.database_url_readonly,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
    isolation_level="AUTOCOMMIT",
)
SessionLocalRead = sessionmaker(autocommit=False, autoflush=False, bind=engine_read)

Base = declarative_base()

def get_write_db():
    db = SessionLocalWrite()
    try:
        yield db
    finally:
        db.close()

def get_read_db():
    db = SessionLocalRead()
    try:
        yield db
    finally:
        db.close()
