from app.agents.llm_client import get_llm, get_llm_creative, get_embedding
from app.agents.mentor_agent import create_mentor_agent, chat_with_mentor, get_suggested_questions
from app.agents.analysis_chain import analysis_chain, AnalysisChain
from app.agents.plan_generator import plan_generator, PlanGenerator


def __getattr__(name: str):
    if name == "RAGEngine":
        from app.agents.rag_engine import RAGEngine as _RAGEngine

        return _RAGEngine
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "get_llm",
    "get_llm_creative",
    "get_embedding",
    "RAGEngine",
    "create_mentor_agent",
    "chat_with_mentor",
    "get_suggested_questions",
    "analysis_chain",
    "AnalysisChain",
    "plan_generator",
    "PlanGenerator",
]