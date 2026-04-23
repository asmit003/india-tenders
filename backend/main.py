from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ✅ Import scraper + DB
from backend.scraper import scrape_cppp_data
from backend.db import SessionLocal, Tender


# -------------------------------
# Pydantic Response Model
# -------------------------------
class TenderResponse(BaseModel):
    tender_id: str
    title: str
    sector: str
    winning_company: str
    value_crore: float
    award_date: str

    class Config:
        from_attributes = True


# -------------------------------
# FastAPI App
# -------------------------------
app = FastAPI(title="India High-Value Tenders API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# -------------------------------
# Health Check
# -------------------------------
@app.get("/")
def health_check():
    return {"status": "Online", "message": "Tender API is running!"}


# -------------------------------
# Get Tenders
# -------------------------------
@app.get("/api/tenders", response_model=list[TenderResponse])
def get_tenders():
    db = SessionLocal()
    tenders = db.query(Tender).order_by(Tender.award_date.desc()).limit(50).all()
    db.close()
    return tenders


# -------------------------------
# Trigger Scraper (BACKGROUND)
# -------------------------------
@app.get("/api/trigger-scrape")
async def trigger_scrape(background_tasks: BackgroundTasks):
    background_tasks.add_task(scrape_cppp_data)
    return {"status": "Scraper started in background"}