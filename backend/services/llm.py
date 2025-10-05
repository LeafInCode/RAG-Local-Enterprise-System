import os

from langchain_community.chat_models import QianfanChatEndpoint

from backend.core.config import settings
from backend.services.vector_store import vector_store
from backend.utils.logger import logger


class LLMType:
    QIANFAN = "qianfan"
    # OPENAI = "openai"


def _ensure_env_keys() -> None:
    if not os.getenv("QIANFAN_AK") or not os.getenv("QIANFAN_SK"):
        raise RuntimeError("Please set QIANFAN_AK and QIANFAN_SK in your environment.")


class LLMService:
    def __init__(
        self, llm_type: str = LLMType.QIANFAN, model: str = "ERNIE-4.0-Turbo-8k", timeout: int = 60
    ):
        self.llm_type = llm_type
        self.model = model
        self.timeout = timeout

        self.llm = self._init_llm()

    def _init_llm(self) -> QianfanChatEndpoint:
        """根据类型初始化LLM"""
        if self.llm_type == LLMType.QIANFAN:
            _ensure_env_keys()
            return QianfanChatEndpoint(model=self.model, timeout=self.timeout)
        else:
            raise ValueError(f"Unsupported LLM type: {self.llm_type}")

    def _count_tokens(self, text: str) -> int:
        """估算文本的 token 数量
        简单估算：中文按1个token计算，英文按1个单词计算，其他字符按1/2计算

        这种估算方法不够精确，但对于大多数场景已经足够
        复杂的token计算需要依赖具体的tokenizer，不同模型的tokenizer不同
        这里为了简化逻辑，采用简单估算法，实际应用中应根据具体模型选择合适的tokenizer
        """
        if not isinstance(text, str):
            text = str(text)
        chinese_chars = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
        english_words = len(text.split())
        # 其他字符按 1/2 的比例计算
        other_chars = len(text) - chinese_chars
        estimated_tokens = chinese_chars + english_words + other_chars // 2
        return estimated_tokens

    def _truncate_text(self, text: str, max_length: int) -> str:
        """根据 token 数量截断文本"""
        if self._count_tokens(text) <= max_length:
            return text

        # 简单截断：按比例截断文本
        truncation_ratio = max_length / self._count_tokens(text)
        truncated_length = int(len(text) * truncation_ratio * 0.9)  # 留 10% 余量
        truncated_text = text[:truncated_length]

        # 找合适的截断点
        last_stop = max(
            truncated_text.rfind("。"),
            truncated_text.rfind("！"),
            truncated_text.rfind("？"),
            truncated_text.rfind("\n"),
            truncated_text.rfind(" "),
        )
        if last_stop > 0:
            truncated_text = truncated_text[: last_stop + 1]

        return truncated_text

    def retrieve_context(self, query: str, top_k: int = 5) -> list[str]:
        """从向量数据库中检索与查询相关的上下文"""
        results = vector_store.query(query_text=query, top_k=top_k)

        # 处理检索到的文档，确保单个文档不超过最大内容长度
        processed_docs = []
        for item in results:
            # 兼容不同格式：LangChain Document 或 dict
            if isinstance(item, dict):
                doc = item.get("document") or item.get("page_content") or str(item)
            else:
                # LangChain Document
                doc = getattr(item, "page_content", str(item))

            if self._count_tokens(doc) > settings.MAX_CONTEXT_LENGTH:
                truncated_doc = self._truncate_text(doc, settings.MAX_CHUNK_LENGTH)
                logger.warning(
                    f"Document truncated from {self._count_tokens(doc)} to "
                    f"{self._count_tokens(truncated_doc)} tokens."
                )
                processed_docs.append(truncated_doc)
            else:
                processed_docs.append(doc)

        return processed_docs

    def generate_answer(self, query: str, context_docs: list[str]) -> str:
        """基于上下文调用 LLM 生成答案"""
        # 计算查询和提示词模板的token数量
        prompt_template = """你是一个企业内部知识助手。请基于以下文档内容回答问题。
如果无法从文档中找到答案，请明确回答“未找到相关信息”。

文档内容:
{context}

问题: {query}

答案:"""

        # 拼接上下文（编号更清晰）
        context = "\n\n".join([f"【片段{i + 1}】\n{doc}" for i, doc in enumerate(context_docs)])

        # 计算可用上下文长度
        fixed_prompt_tokens = self._count_tokens(prompt_template.format(context="", query=""))
        available_len = settings.MAX_CONTEXT_LENGTH - fixed_prompt_tokens - settings.SAFE_MARGIN

        selected = []
        cur_len = 0
        for doc in context_docs:
            doc_len = self._count_tokens(doc)
            if cur_len + doc_len <= available_len:
                selected.append(doc)
                cur_len += doc_len
            else:
                remain = available_len - cur_len
                if remain > 100:
                    truncated = self._truncate_text(doc, remain)
                    selected.append(truncated)
                    cur_len += self._count_tokens(truncated)
                break

        context = "\n\n".join([f"【片段{i + 1}】\n{doc}" for i, doc in enumerate(selected)])
        final_prompt = prompt_template.format(context=context, query=query)

        logger.info(f"Selected {len(selected)} context chunks, total tokens: {cur_len}")
        logger.debug(f"Final prompt preview (truncated): {final_prompt[:500]}...")

        try:
            response = self.llm.invoke(final_prompt, temperature=0.2)
            logger.info(f"llm raw response: {response}")

            if hasattr(response, "content"):
                content = response.content
                return content.strip() if isinstance(content, str) else str(content)
            elif isinstance(response, str):
                return response.strip()
            else:
                return str(response)
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            return "抱歉，处理您的请求时发生错误，请稍后再试。"

    def ask(self, query: str, top_k: int = 5) -> str:
        """综合检索和生成，返回最终答案"""
        context_docs = self.retrieve_context(query, top_k)
        if not context_docs:
            return "未找到相关信息"
        return self.generate_answer(query, context_docs)


llm_service = LLMService()
