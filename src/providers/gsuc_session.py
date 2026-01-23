# -*- coding: utf-8 -*-
"""
GSUC Session 管理器

用于验证 GSUC SESSIONID 并获取用户信息
"""

import json
from typing import Dict, Optional

import httpx

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GSUCSessionManager:
    """
    GSUC Session 管理器
    
    功能:
    1. 验证 SESSIONID 有效性
    2. 获取用户信息
    3. 缓存用户信息 (使用 Redis)
    
    注意:
        - SESSIONID 由 GSUC 服务器生成
        - 前端从 Cookie 读取 SESSIONID 并放入 Token header
        - 后端从 Token header 提取 SESSIONID 进行验证
    """
    
    def __init__(
        self,
        gsuc_api_url: str = "https://gsuc.gamesci.com.cn",
        timeout: int = 10,
        redis_client=None,
        cache_ttl: int = 300  # 5 分钟缓存
    ):
        """
        初始化 GSUC Session 管理器
        
        Args:
            gsuc_api_url: GSUC API 基础 URL
            timeout: HTTP 请求超时时间（秒）
            redis_client: Redis 客户端（可选，用于缓存）
            cache_ttl: 缓存过期时间（秒）
        """
        self.gsuc_api_url = gsuc_api_url
        self.timeout = timeout
        self.redis_client = redis_client
        self.cache_ttl = cache_ttl
    
    async def verify_session(self, session_id: str) -> Optional[Dict]:
        """
        验证 SESSIONID 并获取用户信息
        
        流程:
        1. 先从 Redis 缓存中查找
        2. 如果缓存未命中，调用 GSUC API 验证
        3. 将用户信息缓存到 Redis
        
        Args:
            session_id: GSUC SESSIONID
            
        Returns:
            Dict: 用户信息
                {
                    "user_id": "user_gsuc_1003",
                    "tenant_id": "tenant_gsuc_1003",
                    "username": "张三",
                    "account": "zhangsan",
                    "uid": "1003"
                }
            None: Session 无效或过期
        """
        # 1. 先从缓存中查找
        if self.redis_client:
            try:
                cached = self.redis_client.get(f"gsuc_session:{session_id}")
                if cached:
                    logger.debug(f"GSUC session found in cache: {session_id[:20]}...")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")
        
        # 2. 调用 GSUC API 验证
        try:
            user_info = await self._verify_with_gsuc_api(session_id)
            
            if not user_info:
                logger.warning(f"GSUC session verification failed: {session_id[:20]}...")
                return None
            
            # 3. 缓存用户信息
            if self.redis_client:
                try:
                    self.redis_client.setex(
                        f"gsuc_session:{session_id}",
                        self.cache_ttl,
                        json.dumps(user_info)
                    )
                    logger.debug(f"GSUC session cached: {session_id[:20]}...")
                except Exception as e:
                    logger.warning(f"Redis cache write failed: {e}")
            
            return user_info
            
        except Exception as e:
            logger.error(f"GSUC session verification error: {e}")
            return None
    
    async def _verify_with_gsuc_api(self, session_id: str) -> Optional[Dict]:
        """
        调用 GSUC API 验证 Session
        
        注意:
            - 需要向 GSUC 团队确认验证接口
            - 当前实现为示例，需要根据实际 API 调整
        
        Args:
            session_id: GSUC SESSIONID
            
        Returns:
            Dict: 用户信息
            None: 验证失败
        """
        async with httpx.AsyncClient() as client:
            try:
                # 方案 A: 如果 GSUC 提供专门的验证接口
                # 需要向 GSUC 团队确认接口地址和参数
                response = await client.get(
                    f"{self.gsuc_api_url}/sso/verify",
                    cookies={"SESSIONID": session_id},
                    timeout=self.timeout
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # 假设 GSUC 返回格式为:
                    # {
                    #     "rc": 0,
                    #     "uid": "1003",
                    #     "account": "zhangsan",
                    #     "username": "张三",
                    #     "avatar": "https://..."
                    # }
                    
                    if data.get("rc") == 0:
                        uid = data.get("uid")
                        return {
                            "user_id": f"user_gsuc_{uid}",
                            "tenant_id": f"tenant_gsuc_{uid}",
                            "username": data.get("username", ""),
                            "account": data.get("account", ""),
                            "uid": uid,
                            "avatar": data.get("avatar", "")
                        }
                
                logger.warning(f"GSUC API returned non-200 status: {response.status_code}")
                return None
                
            except httpx.TimeoutException:
                logger.error(f"GSUC API timeout after {self.timeout}s")
                return None
            except Exception as e:
                logger.error(f"GSUC API call failed: {e}")
                return None
    
    def invalidate_session(self, session_id: str):
        """
        使 Session 缓存失效
        
        用于用户退出登录时清除缓存
        
        Args:
            session_id: GSUC SESSIONID
        """
        if self.redis_client:
            try:
                self.redis_client.delete(f"gsuc_session:{session_id}")
                logger.info(f"GSUC session cache invalidated: {session_id[:20]}...")
            except Exception as e:
                logger.warning(f"Redis cache delete failed: {e}")
    
    async def get_user_info(self, session_id: str) -> Optional[Dict]:
        """
        获取用户信息（verify_session 的别名）
        
        Args:
            session_id: GSUC SESSIONID
            
        Returns:
            Dict: 用户信息
            None: Session 无效
        """
        return await self.verify_session(session_id)


# 全局单例（可选）
_session_manager: Optional[GSUCSessionManager] = None


def get_session_manager(
    gsuc_api_url: str = "https://gsuc.gamesci.com.cn",
    redis_client=None
) -> GSUCSessionManager:
    """
    获取全局 GSUC Session 管理器单例
    
    Args:
        gsuc_api_url: GSUC API 基础 URL
        redis_client: Redis 客户端
        
    Returns:
        GSUCSessionManager: Session 管理器实例
    """
    global _session_manager
    
    if _session_manager is None:
        _session_manager = GSUCSessionManager(
            gsuc_api_url=gsuc_api_url,
            redis_client=redis_client
        )
    
    return _session_manager
