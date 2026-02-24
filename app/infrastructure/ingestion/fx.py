from datetime import datetime


def ingest_hmrc_monthly():
    started_at = datetime.utcnow().isoformat()
    records_processed = 0
    return {"source": "HMRC", "type": "monthly", "started_at": started_at, "records_processed": records_processed}


def ingest_ecb_daily():
    started_at = datetime.utcnow().isoformat()
    records_processed = 0
    return {"source": "ECB", "type": "daily", "started_at": started_at, "records_processed": records_processed}

