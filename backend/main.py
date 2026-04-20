import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, String, Numeric, Date, Time, Integer, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

# 1. Database Setup
# Render will inject your Supabase URL into this environment variable
DATABASE_URL = os.getenv("DATABASE_URL") 
# Fix for SQLAlchemy connecting to postgres (needs postgresql://)
if DATABASE_URL and DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# 2. Database Model (Matches the Supabase table you just created)
class Tender(Base):
    __tablename__ = "tenders"
    id = Column(String, primary_key=True)
    tender_id = Column(String, unique=True)
    title = Column(String)
    sector = Column(String)
    winning_company = Column(String)
    value_crore = Column(Numeric)
    award_date = Column(Date)
    award_time = Column(Time)
    source_portal = Column(String)
    source_url = Column(String)

# 3. FastAPI App Setup
app = FastAPI(title="India High-Value Tenders API")

# Allow the frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 4. API Endpoint
@app.get("/")
def health_check():
    return {"status": "Online", "message": "Tender API is running!"}

@app.get("/api/tenders")
def get_tenders():
    db = SessionLocal()
    tenders = db.query(Tender).order_by(Tender.award_date.desc()).limit(50).all()
    db.close()
    return {"status": "success", "data": tenders}
