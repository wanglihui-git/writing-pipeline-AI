"""
千问大模型客户端封装
"""
import dashscope
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
from app.config import settings
from app.utils.logger import logger

# 配置 API Key
dashscope.api_key = settings.qwen_api_key
dashscope.base_http_api_url = settings.qwen_api_base


class QwenClient:
    """千问 API 客户端"""
    
    def __init__(self):
        self.chat_model = settings.qwen_chat_model
        self.summary_model = settings.qwen_summary_model
        self.embedding_model = settings.qwen_embedding_model
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def chat(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2000
    ) -> str:
        """调用千问聊天接口
        
        Args:
            prompt: 用户输入
            system_prompt: 系统提示词
            model: 模型名称（不指定则使用默认 chat_model）
            temperature: 温度参数（0-1，越高越随机）
            max_tokens: 最大生成 token 数
            
        Returns:
            生成的文本
        """
        model = model or self.chat_model
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info(f"调用千问 API: model={model}, temperature={temperature},prompt={prompt[:300]}..., system_prompt={system_prompt[:50] if system_prompt else 'N/A'}")
            
            response = dashscope.Generation.call(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                result_format='message'
            )
            
            if response.status_code == 200:
                result = response.output.choices[0].message.content
                logger.info(f"千问响应成功: {len(result)} 字符,result={result[:100]}")
                return result
            else:
                error_msg = f"千问 API 错误: {response.code} - {response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"千问调用异常: {str(e)}")
            raise
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def embed(self, text: str) -> List[float]:
        """生成文本 Embedding 向量
        
        Args:
            text: 待向量化的文本
            
        Returns:
            向量列表
        """
        try:
            logger.debug(f"生成 Embedding: {len(text)} 字符")
            
            response = dashscope.TextEmbedding.call(
                model=self.embedding_model,
                input=text
            )
            
            if response.status_code == 200:
                output = response.output
                logger.debug(f"Embedding output 类型: {type(output)}, 内容: {output}")
                # 兼容 dict / 类dict对象 和属性访问两种返回格式
                try:
                    # 优先尝试字典方式访问（覆盖 dict 及类 dict 对象）
                    embedding = output["embeddings"][0]["embedding"]
                except (TypeError, KeyError, IndexError):
                    try:
                        # 回退到属性访问
                        embedding = output.embeddings[0].embedding
                    except AttributeError:
                        logger.error(f"Embedding 返回结构无法解析, output keys: {output.keys() if hasattr(output, 'keys') else 'N/A'}, output={output}")
                        raise
                logger.debug(f"Embedding 生成成功: {len(embedding)} 维")
                return embedding
            else:
                error_msg = f"Embedding API 错误: {response.code} - {response.message}"
                logger.error(error_msg)
                raise Exception(error_msg)
                
        except Exception as e:
            logger.error(f"Embedding 生成异常: {str(e)}")
            raise
    
# 全局实例
qwen_client = QwenClient()
