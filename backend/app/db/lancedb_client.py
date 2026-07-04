from __future__ import annotations

import os
import lancedb
from pydantic import BaseModel

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)

# Create LanceDB directory
os.makedirs(settings.LANCEDB_PATH, exist_ok=True)

# Connect to LanceDB
db = lancedb.connect(settings.LANCEDB_PATH)

TABLE_NAME = "resumes"


class ResumeSchema(BaseModel):
    vector_id: str
    text: str
    vector: list[float]


# Open or create table
try:
    if TABLE_NAME in db.table_names():
        table = db.open_table(TABLE_NAME)
        logger.info(f"Opened LanceDB table: {TABLE_NAME}")
    else:
        table = db.create_table(TABLE_NAME, schema=ResumeSchema)
        logger.info(f"Created LanceDB table: {TABLE_NAME}")
except Exception as e:
    logger.error(f"LanceDB initialization failed: {e}")
    raise