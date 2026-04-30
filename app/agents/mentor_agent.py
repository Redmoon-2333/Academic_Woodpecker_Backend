"""AI Mentor agent with tool-calling, RAG, context-aware tutoring, and conversation memory."""
import uuid
from typing import Any, AsyncIterator, Dict, List, Optional

from langchain.agents import create_agent
from langchain_core.tools import tool

from app.agents.llm_client import get_llm
from app.agents.rag_engine import RAGEngine

# --- Checkpointer: prefer SqliteSaver for persistence, fall back to MemorySaver ---
try:
    from langgraph.checkpoint.sqlite import SqliteSaver

    checkpointer = SqliteSaver.from_conn_string("checkpoints.db")
except ImportError:
    from langgraph.checkpoint.memory import MemorySaver

    checkpointer = MemorySaver()


# --- Tools available to the AI mentor ---

@tool
def search_knowledge(query: str) -> str:
    """搜索内置知识库中与查询相关的知识点信息。输入某个知识点名称。"""
    knowledge_base = {
        "贝叶斯定理": "P(A|B) = P(B|A)*P(A)/P(B)。用于根据新证据更新概率估计。核心概念：先验概率、后验概率、似然。",
        "线性代数": "研究向量、矩阵和线性变换的数学分支，广泛应用于机器学习、计算机图形学。核心：矩阵运算、特征值、线性空间。",
        "微积分": "研究函数的变化率和累积量，分微分和积分。核心：极限、导数、积分、微分方程。",
        "数据结构": "常见结构：数组O(1)访问、链表O(n)访问O(1)插入、树O(log n)、哈希表O(1)平均。",
        "傅里叶变换": "时域↔频域转换。连续: F(ω)=∫f(t)e^(-iωt)dt, 离散: FFT O(n log n)。应用：信号处理、图像压缩。",
        "操作系统": "四大模块：进程管理(调度算法)、内存管理(虚拟内存/分页)、文件系统(inode)、I/O。",
        "概率论": "基础：概率空间、条件概率、全概率公式、贝叶斯定理。进阶：随机变量、分布(正态/泊松)、大数定律、中心极限定理。",
        "算法": "排序(O(n log n))、搜索(二分O(log n))、动态规划(最优子结构)、贪心(局部最优)、图算法(DFS/BFS/Dijkstra)。",
    }
    for key, value in knowledge_base.items():
        if key in query:
            return f"📖 **{key}**\n{value}"
    return f"关于'{query}'的知识：这是重要的学习概念，建议从基础定义入手，逐步理解其应用场景和核心原理。"


@tool
def search_user_documents(query: str) -> str:
    """从用户上传的学习文档中搜索相关内容。输入搜索关键词，返回文档中匹配的片段。用于查找用户自己的笔记、试卷内容。"""
    try:
        engine = RAGEngine()
        docs = engine.similarity_search(query, k=3)
        if not docs:
            return "未在用户上传的文档中找到相关内容。建议用户上传相关学习资料以便更好地分析。"
        results = []
        for i, doc in enumerate(docs, 1):
            snippet = doc.page_content[:300]
            results.append(f"📄 文档片段{i}:\n{snippet}...")
        return "\n\n".join(results)
    except Exception:
        return "搜索文档时出现异常，请稍后重试。"


@tool
def recommend_resources(topic: str) -> str:
    """为特定知识点推荐学习资源。输入知识点名称。"""
    resources = {
        "贝叶斯定理": "📚 1.《概率论与数理统计》教材第3章\n2. B站 3Blue1Brown「贝叶斯定理」可视化\n3. 知乎「贝叶斯定理的直观理解」",
        "线性代数": "📚 1.《线性代数及其应用》Gilbert Strang\n2. 中国大学MOOC「线性代数」\n3. B站「线性代数的本质」系列",
        "微积分": "📚 1.《高等数学》同济第七版\n2. 3Blue1Brown「微积分的本质」\n3. 网易云课堂「高等数学精讲」",
        "算法": "📚 1.《算法导论》CLRS\n2. LeetCode 刷题\n3. B站「算法图解」系列",
        "数据结构": "📚 1.《数据结构与算法分析》\n2. GeeksforGeeks 教程\n3. GitHub 开源算法实现",
    }
    for key, value in resources.items():
        if key in topic:
            return value
    return f"针对'{topic}'推荐：\n1. 相关教材与参考书\n2. B站/MOOC在线视频课程\n3. 实战练习与项目"


@tool
def get_student_status() -> str:
    """获取学生当前的整体学习状态、薄弱知识点、掌握率等信息。"""
    return (
        "📊 学生学情概览：\n"
        "- 整体知识掌握率：78%\n"
        "- 🔴 薄弱(需重点加强)：概率论(55%)、算法(55%)\n"
        "- 🟡 预警(需要巩固)：线性代数(70%)、操作系统(70%)\n"
        "- 🟢 掌握(已达标)：微积分(88%)、数据结构(88%)、电磁学(85%)\n"
        "- 已分析文档：12份\n"
        "- 学习建议：优先攻克概率论和算法，每天安排1-2小时针对性练习"
    )


@tool
def generate_practice_questions(topic: str) -> str:
    """根据知识点生成分层次的练习建议。输入知识点名称。"""
    return (
        f"📝 「{topic}」分层练习方案：\n\n"
        f"🟢 基础层（巩固概念）：\n"
        f"1. 用思维导图梳理{topic}核心概念\n"
        f"2. 完成教材课后基础题(第1-5题)\n\n"
        f"🟡 进阶层（加深理解）：\n"
        f"1. 综合应用题：将{topic}与其他知识点结合\n"
        f"2. 真题实战：近3年相关考题限时训练\n\n"
        f"🔴 挑战层（冲刺高分）：\n"
        f"1. 竞赛/考研难度题目\n"
        f"2. 尝试用{topic}解决一个实际问题"
    )


AVAILABLE_TOOLS = [
    search_knowledge,
    search_user_documents,  # NEW: RAG-powered document search
    recommend_resources,
    get_student_status,
    generate_practice_questions,
]


def _build_system_prompt(context: Optional[Dict] = None) -> str:
    weak_points = context.get("weakPoints", []) if context else []
    current_topic = context.get("currentTopic", "") if context else ""
    weak_str = "、".join(weak_points) if weak_points else "暂无明确数据"

    return f"""你是「学业啄木鸟」AI学习助手，正在进行一对一深度辅导。

🎯 当前学生背景：
- 薄弱知识点：{weak_str}
- 当前学习主题：{current_topic}
- 你可以调用 search_user_documents 工具搜索学生上传的学习资料

📋 教学策略（重要！）：
1. 优先用 search_user_documents 查找学生自己上传的笔记/试卷，基于真实数据给出分析
2. 如果文档无相关内容，用 search_knowledge 查找内置知识
3. 难度匹配学生水平（薄弱→从基础讲起，掌握→可讲进阶）
4. 主动调用工具，不要说"我帮你查一下"然后不查
5. 回复要耐心、鼓励、条理清晰

🗣️ 回复格式：
- 用中文，公式用 $...$ LaTeX 格式
- 代码用 ``` 代码块
- 结构化：先说结论 → 再讲细节 → 最后总结"""


def create_mentor_agent(context: Optional[Dict] = None):
    """Create agent with LangGraph checkpoint for conversation memory.

    Args:
        context: Optional dict with weakPoints (list) and currentTopic (str).

    Returns:
        A compiled langgraph agent with checkpoint-based memory.
    """
    llm = get_llm()
    system_prompt = _build_system_prompt(context)

    return create_agent(
        llm,
        tools=AVAILABLE_TOOLS,
        system_prompt=system_prompt,
        checkpointer=checkpointer,
    )


async def chat_with_mentor(
    user_message: str,
    context: Optional[Dict[str, Any]] = None,
    thread_id: Optional[str] = None,
) -> str:
    """Send message to agent and get response. Maintains memory via thread_id.

    Args:
        user_message: The student's question or message.
        context: Optional student context (weakPoints, currentTopic).
        thread_id: Conversation thread ID for multi-turn memory. Auto-generated if None.

    Returns:
        The mentor's response text.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    agent = create_mentor_agent(context)

    config = {"configurable": {"thread_id": thread_id}}
    result = await agent.ainvoke(
        {"messages": [("user", user_message)]},
        config=config,
    )

    messages = result.get("messages", [])
    for msg in reversed(messages):
        if hasattr(msg, "content") and getattr(msg, "type", "") == "ai":
            return msg.content
    return "抱歉，我暂时无法回答这个问题。"


async def chat_with_mentor_stream(
    user_message: str,
    context: Optional[Dict] = None,
    thread_id: Optional[str] = None,
) -> AsyncIterator[str]:
    """Stream agent response token by token. Maintains memory via thread_id.

    Args:
        user_message: The student's question or message.
        context: Optional student context (weakPoints, currentTopic).
        thread_id: Conversation thread ID for multi-turn memory. Auto-generated if None.

    Yields:
        Content chunks from the AI response as they arrive.
    """
    if thread_id is None:
        thread_id = str(uuid.uuid4())

    agent = create_mentor_agent(context)
    config = {"configurable": {"thread_id": thread_id}}

    async for event in agent.astream_events(
        {"messages": [("user", user_message)]},
        config=config,
        version="v2",
    ):
        kind = event.get("event", "")
        if kind == "on_chat_model_stream":
            chunk = event.get("data", {}).get("chunk", None)
            if chunk and hasattr(chunk, "content") and chunk.content:
                yield chunk.content


def get_suggested_questions() -> List[Dict[str, Any]]:
    """Get preset suggested questions based on student context."""
    return [
        {"id": 1, "text": "帮我制定一个复习计划", "icon": "plan"},
        {"id": 2, "text": "总结我最近的易错类型", "icon": "chart"},
        {"id": 3, "text": "解释一下贝叶斯定理", "icon": "book"},
        {"id": 4, "text": "推荐一些练习题", "icon": "practice"},
    ]