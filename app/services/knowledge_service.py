"""Service for syncing analysis results to the knowledge graph."""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.knowledge import KnowledgePoint, UserKnowledge
from datetime import datetime


async def sync_analysis_to_knowledge(db: AsyncSession, user_id: int, analysis_result: dict):
    """Take analysis result and create/update UserKnowledge records.
    
    Maps extracted knowledge names to existing KnowledgePoint records,
    calculates scores based on confidence/severity, and creates UserKnowledge entries.
    """
    extracted = analysis_result.get("extractedKnowledge", [])
    weak = analysis_result.get("weakPoints", [])
    
    if not extracted and not weak:
        return
    
    # Get all knowledge points for matching
    result = await db.execute(select(KnowledgePoint))
    all_kps = result.scalars().all()
    name_to_kp = {kp.name: kp for kp in all_kps}
    
    # Build weak point map for score calculation
    weak_names = {w.get("name", ""): w.get("severity", "medium") for w in weak}
    
    now = datetime.now()
    
    for item in extracted:
        name = item.get("name", "")
        confidence = item.get("confidence", 0.5)
        
        # Try exact match first, then fuzzy (contains)
        kp = name_to_kp.get(name)
        if not kp:
            for kp_name, kp_obj in name_to_kp.items():
                if name in kp_name or kp_name in name:
                    kp = kp_obj
                    break
        
        if not kp:
            continue
        
        # Calculate score: confidence-based, reduced if weak
        if name in weak_names:
            severity = weak_names[name]
            if severity == "high":
                score = min(confidence * 100, 60.0)
            elif severity == "medium":
                score = min(confidence * 100, 75.0)
            else:
                score = confidence * 100
        else:
            score = max(confidence * 100, 70.0)
        
        # Check if UserKnowledge already exists for this user+knowledge
        existing = await db.execute(
            select(UserKnowledge).where(
                UserKnowledge.user_id == user_id,
                UserKnowledge.knowledge_id == kp.id,
            )
        )
        uk = existing.scalar_one_or_none()
        
        if uk:
            # Update: take weighted average (70% old + 30% new)
            uk.score = round(uk.score * 0.7 + score * 0.3, 1)
            uk.exam_date = now
        else:
            uk = UserKnowledge(
                user_id=user_id,
                knowledge_id=kp.id,
                score=round(score, 1),
                exam_date=now,
            )
            db.add(uk)
    
    await db.commit()