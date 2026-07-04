from __future__ import annotations
from app.core.logging_config import get_logger
from app.db.lancedb_client import table

logger = get_logger(__name__)

def upsert_resume_embedding(doc_id: str, text: str, embedding: list[float], metadata: dict | None = None) -> None:
    data = [{"vector_id": doc_id, "text": text, "vector": embedding, **(metadata or {})}]
    table.add(data, mode="overwrite")
    logger.info(f"Upserted resume {doc_id} into LanceDB")

def delete_resume_embedding(doc_id: str) -> None:
    table.delete(f"vector_id = '{doc_id}'")
    logger.info(f"Deleted resume {doc_id}")

def _get_score_column(df):
    if "_distance" in df.columns:
        return "_distance"
    elif "score" in df.columns:
        return "score"
    else:
        raise RuntimeError(f"No score column found. Columns: {list(df.columns)}")

def vector_search(query_embedding: list[float], top_k: int = 100) -> list[tuple[str, float]]:
    df = table.search(query_embedding).limit(top_k).to_pandas()
    if df.empty:
        return []
    
    score_col = _get_score_column(df)
    return [(str(row["vector_id"]), 1.0 / (1.0 + float(row[score_col]))) for _, row in df.iterrows()]

def hybrid_search(query_embedding: list[float], query_text: str, candidate_ids: list[str] | None = None, top_k: int = 100) -> list[tuple[str, float]]:
    try:
        search = table.search(query_embedding)
        
        if candidate_ids:
            if len(candidate_ids) == 1:
                search = search.where(f"vector_id == '{candidate_ids[0]}'")
            else:
                conditions = " OR ".join([f"vector_id == '{cid}'" for cid in candidate_ids])
                search = search.where(conditions)

        df = search.limit(top_k).to_pandas()
        if df.empty:
            return []

        score_col = _get_score_column(df)
        
        results = []
        for _, row in df.iterrows():
            similarity = 1.0 / (1.0 + float(row[score_col]))
            results.append((str(row["vector_id"]), similarity))
        return results

    except Exception:
        logger.exception("Search failed")
        raise

def chroma_is_ready() -> bool:
    return table is not None