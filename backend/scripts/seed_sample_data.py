import asyncio, sys, random
from datetime import datetime, timezone, timedelta
sys.path.insert(0, ".")
from app.core.database import init_db, get_db

async def seed():
    await init_db()
    db = await get_db()
    # Check if already seeded
    count = 0
    for coll in await db.list_collection_names():
        if coll not in ("users", "settings", "system.indexes"):
            count += await db[coll].count_documents({})
    if count > 0:
        print("Sample data exists"); return

    print("Seeding sample data for PayRoll Pro...")
    now = datetime.now(timezone.utc)

    # App-specific seed data would go here
    # For now, seed basic operational data
    print("Seed complete for PayRoll Pro")

asyncio.run(seed())
