import re
import asyncio
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright
from datetime import datetime

# correct import
from backend.db import SessionLocal, Tender


# -------------------------------
# Utility Functions
# -------------------------------

def extract_value_in_crores(raw_text):
    try:
        text = raw_text.lower().replace(',', '').strip()

        match = re.search(r'(\d+\.?\d*)', text)
        if not match:
            return 0

        value = float(match.group(1))

        # detect unit
        if 'crore' in text or 'cr' in text:
            return value

        elif 'lakh' in text or 'lac' in text:
            return value / 100

        else:
            # if small number → already in crores
            if value < 1000:
                return value

            # otherwise assume rupees
            return value / 10000000

    except:
        return 0


def classify_sector(title):
    title_lower = title.lower()

    if any(k in title_lower for k in ['highway', 'road', 'bridge', 'railway']):
        return "Infrastructure"

    if any(k in title_lower for k in ['power', 'solar', 'energy']):
        return "Energy"

    if any(k in title_lower for k in ['defence', 'missile', 'drdo']):
        return "Defense"

    return "Others"


# -------------------------------
# MAIN SCRAPER
# -------------------------------

async def scrape_cppp_data():
    URL = "https://eprocure.gov.in/eprocure/app?page=ResultOfTenders"

    print("🚀 Starting scraper for CPPP...")

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        try:
            await page.goto(URL, timeout=60000)
            await page.wait_for_selector("table", timeout=15000)

            html = await page.content()
            soup = BeautifulSoup(html, "html.parser")

            table = soup.find("table")

            if not table:
                print("❌ No table found")
                await browser.close()
                return {"status": "error", "message": "No table found"}

            rows = table.find_all("tr")[1:]

            db = SessionLocal()
            tenders_added = 0

            for row in rows:
                cols = row.find_all("td")

                if len(cols) < 7:
                    continue

                tender_id = cols[0].text.strip()
                title = cols[2].text.strip()
                winner = cols[4].text.strip()
                raw_value = cols[5].text.strip()
                award_date_str = cols[6].text.strip()

                value_cr = extract_value_in_crores(raw_value)

                # debug
                print("VALUE:", value_cr)

                # skip invalid values
                if value_cr <= 0 or value_cr >= 100000:
                    continue

                # avoid duplicates
                existing = db.query(Tender).filter(
                    Tender.tender_id == tender_id
                ).first()

                if existing:
                    continue

                # parse date safely
                try:
                    date_obj = datetime.strptime(
                        award_date_str, "%d-%b-%Y %I:%M %p"
                    )
                    award_date = date_obj.date()
                    award_time = date_obj.time()
                except:
                    award_date = datetime.now().date()
                    award_time = datetime.now().time()

                # IMPORTANT: do NOT set id manually
                new_tender = Tender(
                    tender_id=tender_id,
                    title=title,
                    sector=classify_sector(title),
                    winning_company=winner,
                    value_crore=value_cr,
                    award_date=award_date,
                    award_time=award_time,
                    source_portal="CPPP",
                    source_url=URL
                )

                db.add(new_tender)
                tenders_added += 1

            db.commit()
            db.close()
            await browser.close()

            print(f"✅ Added {tenders_added} tenders")

            return {
                "status": "success",
                "tenders_added": tenders_added
            }

        except Exception as e:
            await browser.close()
            print(f"❌ Scraper Error: {e}")

            return {
                "status": "error",
                "message": str(e)
            }


# -------------------------------
# RUN BLOCK
# -------------------------------

async def main():
    result = await scrape_cppp_data()
    print(result)


if __name__ == "__main__":
    asyncio.run(main())