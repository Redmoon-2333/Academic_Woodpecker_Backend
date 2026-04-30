"""LLM client - singleton factory for ECNU OpenAI-compatible API."""
from functools import lru_cache
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from app.config import settings
from app.core.logging import get_logger

logger = get_logger("llm_client")


def _init_langfuse():
    """Initialize LangFuse tracing if credentials are configured. Returns callback or None."""
    try:
        if settings.LANGFUSE_PUBLIC_KEY and settings.LANGFUSE_SECRET_KEY:
            from langfuse.langchain import CallbackHandler
            logger.info("LangFuse tracing enabled")
            return CallbackHandler(
                public_key=settings.LANGFUSE_PUBLIC_KEY,
                secret_key=settings.LANGFUSE_SECRET_KEY,
                host=settings.LANGFUSE_HOST,
            )
        else:
            logger.debug("LangFuse credentials not configured, skipping")
    except ImportError:
        logger.warning("LangFuse not installed, skipping tracing")
    return None


_langfuse_handler = _init_langfuse()
logger.info(f"LLM client initialized: model={settings.LLM_MODEL}, api_base={settings.ECNU_API_BASE}")


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """Get cached ChatOpenAI with LangFuse tracing if configured."""
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.ECNU_API_KEY,
        openai_api_base=settings.ECNU_API_BASE,
        temperature=0.7,
        max_tokens=2048,
    )
    if _langfuse_handler:
        llm.callbacks = [_langfuse_handler]
    return llm


@lru_cache(maxsize=1)
def get_llm_creative() -> ChatOpenAI:
    """Get cached ChatOpenAI with LangFuse tracing if configured."""
    llm = ChatOpenAI(
        model=settings.LLM_MODEL,
        openai_api_key=settings.ECNU_API_KEY,
        openai_api_base=settings.ECNU_API_BASE,
        temperature=0.9,
        max_tokens=4096,
    )
    if _langfuse_handler:
        llm.callbacks = [_langfuse_handler]
    return llm


@lru_cache(maxsize=1)
def get_embedding() -> OpenAIEmbeddings:
    """Get cached embeddings instance with LangFuse tracing if configured."""
    emb = OpenAIEmbeddings(
        model="text-embedding-ada-002",
        openai_api_key=settings.ECNU_API_KEY,
        openai_api_base=settings.ECNU_API_BASE,
    )
    if _langfuse_handler:
        emb.callbacks = [_langfuse_handler]
    return emb