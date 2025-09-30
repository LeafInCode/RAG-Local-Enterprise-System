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
        truncated_length = int(len(text) * truncation_ratio * 0.95)  # 留 5% 余量

        # 确保截断在句子结束处附近
        truncated_text = text[:truncated_length]
        last_period = truncated_text.rfind("。")
        last_exclamation = truncated_text.rfind("！")
        last_question = truncated_text.rfind("？")
        last_newline = truncated_text.rfind("\n")
        last_space = truncated_text.rfind(" ")

        # 选择合适的截断点
        truncate_points = max(
            last_period, last_exclamation, last_question, last_newline, last_space
        )
        if truncate_points > 0:
            truncated_text = truncated_text[: truncate_points + 1]  # 包含截断符号

        return truncated_text

    def retrieve_context(self, query: str, top_k: int = 5) -> list[str]:
        """从向量数据库中检索与查询相关的上下文"""
        results = vector_store.query(query_text=query, top_k=top_k)

        # 处理检索到的文档，确保单个文档不超过最大内容长度
        processed_docs = []
        for item in results:
            doc = item["document"]
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

        # 计算固定部分的token数量
        fixed_prompt_length = self._count_tokens(prompt_template.format(context="", query=query))
        available_context_length = (
            settings.MAX_CONTEXT_LENGTH - fixed_prompt_length - settings.SAFE_MARGIN
        )

        # 智能选择和排序上下文文档，优先选择最相关且较短的文档
        selected_contexts = []
        current_length = 0

        # 按照相关性排序（假设vector_store返回的结果已经排序）
        for doc in context_docs:
            doc_length = self._count_tokens(doc)

            # 如果加入当前文档不会超过总长度限制，则加入
            if current_length + doc_length <= available_context_length:
                selected_contexts.append(doc)
                current_length += doc_length
            else:
                # 尝试截断当前文档并加入剩余空间
                remaining_length = available_context_length - current_length
                if remaining_length > 100:  # 确保剩余空间足够添加有意义的内容
                    truncated_doc = self._truncate_text(doc, remaining_length)
                    selected_contexts.append(truncated_doc)
                    current_length += self._count_tokens(truncated_doc)
                    break
                else:
                    break

        logger.info(
            f"Selected {len(selected_contexts)} context chunks, total tokens: {current_length}"
        )

        # 构建最终的上下文
        context = "\n".join(selected_contexts)
        final_prompt = prompt_template.format(context=context, query=query)

        # 最终检查总长度
        total_tokens = self._count_tokens(final_prompt)
        if total_tokens > settings.MAX_CONTEXT_LENGTH:
            logger.warning(
                f"Final prompt exceeds max context length: "
                f"{total_tokens} > {settings.MAX_CONTEXT_LENGTH}"
            )
            # 再次截断整个上下文
            adjusted_context = self._truncate_text(context, available_context_length - 100)
            final_prompt = prompt_template.format(context=adjusted_context, query=query)

        try:
            response = self.llm.invoke(
                input=final_prompt,
                temperature=0.2,
            )
            return getattr(response, "content", str(response)).strip()
        except Exception as e:
            logger.error(f"Error generating answer: {str(e)}")
            # 降级策略：如果上下文过长导致错误，尝试使用更少的上下文
            if len(selected_contexts) > 1:
                logger.info("Trying with fewer context chunks...")
                reduced_context = "\n".join(selected_contexts[: len(selected_contexts) // 2])
                reduced_prompt = prompt_template.format(context=reduced_context, query=query)
                try:
                    response = self.llm.invoke(
                        input=reduced_prompt,
                        temperature=0.2,
                    )
                    return getattr(response, "content", str(response)).strip()
                except Exception as e2:
                    logger.error(f"Failed even with reduced context: {str(e2)}")
                    return "抱歉，处理您的请求时发生错误，请尝试简化问题或减少查询内容。"
            return "抱歉，处理您的请求时发生错误，请稍后再试。"

    def ask(self, query: str, top_k: int = 5) -> str:
        """综合检索和生成，返回最终答案"""
        context_docs = self.retrieve_context(query, top_k)
        if not context_docs:
            return "未找到相关信息"
        return self.generate_answer(query, context_docs)


llm_service = LLMService()
