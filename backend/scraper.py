import re
import os
import asyncio
import logging
from datetime import datetime
from typing import List

from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from sqlalchemy.exc import SQLAlchemyError

from backend.db import SessionLocal, Tender


# -------------------------------
# CONFIGURATION
# -------------------------------
SCRAPER_URL = os.getenv(
    "SCRAPER_URL",
    "https://eprocure.gov.in/eprocure/app?page=ResultOfTenders"
)

MAX_RETRIES = 3


# -------------------------------
# LOGGING SETUP
# -------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)


# -------------------------------
# VALUE EXTRACTION
# -------------------------------
def extract_value_in_crores(raw_text: str) -> float:
    try:
        text = raw_text.lower().replace(',', '').strip()

        match = re.search(r'(\d+\.?\d*)', text)
        if not match:
            return 0

        value = float(match.group(1))

        if 'crore' in text or 'cr' in text:
            return value
        elif 'lakh' in text or 'lac' in text:
            return value / 100
        elif 'rs' in text or '₹' in text:
            return value / 10000000
        else:
            if value > 10000000:
                return value / 10000000
            return value

    except Exception:
        return 0


# -------------------------------
# SECTOR CLASSIFICATION
# -------------------------------
def classify_sector(title: str) -> str:
    title_lower = title.lower()

    if any(k in title_lower for k in ['road', 'highway', 'bridge', 'rail']):
        return "Infrastructure"

    if any(k in title_lower for k in ['power', 'solar', 'energy']):
        return "Energy"

    if any(k in title_lower for k in ['defence', 'missile', 'drdo']):
        return "Defense"

    return "Others"


# -------------------------------
# FETCH PAGE WITH RETRY
# -------------------------------
async def fetch_page(page, url: str):
    for attempt in range(MAX_RETRIES):
        try:
            await page.goto(url, timeout=60000)
            await page.wait_for_selector("table", timeout=15000)
            return await page.content()
        except Exception as e:
            logging.warning(f"Retry {attempt+1}/{MAX_RETRIES} failed: {e}")
            await asyncio.sleep(2)

    raise Exception("Failed to load page after retries")


# -------------------------------
# MAIN SCRAPER
# -------------------------------
async def scrape_cppp_data():
    logging.info("🚀 Starting scraper...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            html = await fetch_page(page, SCRAPER_URL)
            soup = BeautifulSoup(html, "html.parser")

            table = soup.find("table")
            if not table:
                logging.error("❌ No table found")
                return {"status": "error"}

            rows = table.find_all("tr")[1:]

            db = SessionLocal()
            new_tenders: List[Tender] = []
            tenders_added = 0

            for row in rows:
                cols = row.find_all("td")

                if len(cols) < 6:
                    continue

                # -------------------------------
                # COLUMN MAPPING
                # -------------------------------
                tender_id = cols[1].text.strip()
                title = " ".join(cols[3].text.split())

                if len(title) < 10:
                    continue

                raw_value = cols[4].text.strip()
                award_date_str = cols[5].text.strip()

                value_cr = extract_value_in_crores(raw_value)
                if value_cr <= 0:
                    continue

                # -------------------------------
                # DUPLICATE CHECK
                # -------------------------------
                existing = db.query(Tender).filter(
                    Tender.tender_id == tender_id
                ).first()

                if existing:
                    continue

                # -------------------------------
                # DATE PARSING
                # -------------------------------
                try:
                    date_obj = datetime.strptime(
                        award_date_str, "%d-%b-%Y %I:%M %p"
                    )
                    award_date = date_obj.date()
                    award_time = date_obj.time()
                except Exception:
                    award_date = datetime.now().date()
                    award_time = datetime.now().time()

                # -------------------------------
                # CREATE OBJECT
                # -------------------------------
                tender = Tender(
                    tender_id=tender_id,
                    title=title,
                    sector=classify_sector(title),
                    winning_company="N/A",
                    value_crore=value_cr,
                    award_date=award_date,
                    award_time=award_time,
                    source_portal="CPPP",
                    source_url=SCRAPER_URL
                )

                new_tenders.append(tender)

            # -------------------------------
            # BULK INSERT
            # -------------------------------
            if new_tenders:
                db.bulk_save_objects(new_tenders)
                db.commit()
                tenders_added = len(new_tenders)

            db.close()

            logging.info(f"✅ Added {tenders_added} tenders")

            return {
                "status": "success",
                "tenders_added": tenders_added
            }

        except SQLAlchemyError as db_error:
            logging.error(f"DB Error: {db_error}")
            return {"status": "error", "message": "DB failure"}

        except Exception as e:
            logging.error(f"Scraper Error: {e}")
            return {"status": "error", "message": str(e)}

        finally:
            await browser.close()


# -------------------------------
# RUN (LOCAL TESTING)
# -------------------------------
async def main():
    result = await scrape_cppp_data()
    logging.info(result)


if __name__ == "__main__":
    asyncio.run(main())