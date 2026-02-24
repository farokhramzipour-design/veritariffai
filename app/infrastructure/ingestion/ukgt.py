from datetime import datetime


def ingest_delta():
    started_at = datetime.utcnow().isoformat()
    records_processed = 0
    return {"source": "UKGT", "type": "delta", "started_at": started_at, "records_processed": records_processed}


def ingest_full():
    started_at = datetime.utcnow().isoformat()
    records_processed = 0
    return {"source": "UKGT", "type": "full", "started_at": started_at, "records_processed": records_processed}

