from sqlalchemy import create_engine, Column, String, Numeric, Date, Time
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy import text

# ✅ DATABASE URL
DATABASE_URL = "postgresql://postgres:asmit.2singh@db.ucxotdzdzhfneiuqzaxg.supabase.co:5432/postgres"

# Fix old postgres:// format
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# ✅ Engine
engine = create_engine(DATABASE_URL)

# ✅ Session
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Base
Base = declarative_base()

# ✅ Model
class Tender(Base):
    __tablename__ = "tenders"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        server_default=text("gen_random_uuid()")
    )

    tender_id = Column(String, unique=True)
    title = Column(String)
    sector = Column(String)
    winning_company = Column(String)
    value_crore = Column(Numeric)
    award_date = Column(Date)
    award_time = Column(Time)
    source_portal = Column(String)
    source_url = Column(String)