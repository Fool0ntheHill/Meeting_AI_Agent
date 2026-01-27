# -*- coding: utf-8 -*-
"""GSUC OAuth2.0 authentication provider."""

import base64
from typing import Dict, Optional
from urllib.parse import urlencode

import httpx
from Crypto.Cipher import AES

from src.utils.logger import get_logger

logger = get_logger(__name__)


class GSUCAuthProvider:
    """
    GSUC OAuth2.0 认证提供商
    
    功能:
    1. 生成 GSUC 登录 URL
    2. 处理 GSUC 回调，获取用户信息
    3. 生成 access_token (加密 code + appid + appsecret)
    
    使用方式:
        provider = GSUCAuthProvider(appid, appsecret, encryption_key)
        
        # 生成登录 URL
        login_url = provider.get_login_url(redirect_uri, state)
        
        # 获取用户信息
        user_info = await provider.get_user_info(code)
    """
    
    def __init__(
        self,
        appid: str,
        appsecret: str,
        encryption_key: str,
        login_url: str = "https://gsuc.gamesci.com.cn/sso/login",
        userinfo_url: str = "https://gsuc.gamesci.com.cn/sso/userinfo",
        timeout: int = 30
    ):
        """
        初始化 GSUC 认证提供商
        
        Args:
            appid: 应用 ID (向运维申请)
            appsecret: 应用密钥 (向运维申请)
            encryption_key: 加密密钥 (向运维申请)
            login_url: GSUC 登录页面 URL
            userinfo_url: GSUC 用户信息 API URL
            timeout: 请求超时时间(秒)
        """
        self.appid = appid
        self.appsecret = appsecret
        self.encryption_key = encryption_key
        self.login_url = login_url
        self.userinfo_url = userinfo_url
        self.timeout = timeout
        
        logger.info(f"GSUC Auth Provider initialized: appid={appid}")
    
    def get_login_url(self, redirect_uri: str, state: Optional[str] = None) -> str:
        """
        生成 GSUC 登录 URL
        
        Args:
            redirect_uri: 回调地址 (需要在 GSUC 白名单中)
            state: 状态参数 (用于防止 CSRF 攻击)
            
        Returns:
            str: GSUC 登录 URL
            
        Example:
            >>> provider.get_login_url("http://localhost:8000/api/v1/auth/gsuc/callback", "random123")
            'https://gsuc.gamesci.com.cn/sso/login?appid=gs10001&redirect_uri=http%3A%2F%2Flocalhost%3A8000%2Fapi%2Fv1%2Fauth%2Fgsuc%2Fcallback&state=random123'
        """
        params = {
            "appid": self.appid,
            "redirect_uri": redirect_uri,
        }
        
        if state:
            params["state"] = state
        
        url = f"{self.login_url}?{urlencode(params)}"
        logger.debug(f"Generated GSUC login URL: {url}")
        return url
    
    def _encrypt_access_token(self, code: str) -> str:
        """
        生成 access_token
        
        加密方式: AES-256-CBC 加密 (code + appid + appsecret)
        
        迁移自 Python 2 遗留代码，保持算法逻辑不变:
        1. 开头加上 16 位随机数
        2. 补齐文本长度为 32 的倍数
        3. 使用 AES-256-CBC 加密 (key 的前 16 字节作为 IV)
        
        Args:
            code: GSUC 返回的授权 code
            
        Returns:
            str: Base64 编码的加密结果
        """
        import random
        import string
        
        try:
            # 解码 Base64 密钥
            key = base64.b64decode(self.encryption_key)
            if len(key) != 32:
                logger.error(f"Invalid encryption key length: {len(key)}, expected 32")
                raise ValueError("Encryption key must be 32 bytes after base64 decode")
        except Exception as e:
            logger.error(f"Failed to decode encryption key: {e}")
            raise ValueError(f"Invalid encryption key: {e}")
        
        # 拼接字符串: code + appid + appsecret
        text = f"{code}{self.appid}{self.appsecret}"
        
        # 开头加上 16 位随机数 (Python 3: string.ascii_letters + string.digits)
        random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
        text_random = random_prefix + text
        
        # 判断补齐文本长度为 32 的倍数
        add_num = 32 - (len(text_random) % 32)
        if add_num == 0:
            add_num = 32
        
        # 补齐 (Python 3: chr(add_num) * add_num)
        text_all = text_random + chr(add_num) * add_num
        
        # 加密数据 (使用 key 的前 16 字节作为 IV)
        iv = key[:16]
        cipher = AES.new(key, AES.MODE_CBC, iv)
        
        try:
            # 加密
            ciphertext = cipher.encrypt(text_all.encode('utf-8'))
            
            # Base64 编码
            access_token = base64.b64encode(ciphertext).decode('utf-8')
            
            logger.debug(f"Generated access_token for code: {code[:10]}...")
            return access_token
            
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise ValueError(f"Failed to encrypt access token: {e}")
    
    async def get_user_info(self, code: str) -> Dict:
        """
        获取用户信息
        
        Args:
            code: GSUC 返回的授权 code
            
        Returns:
            Dict: 用户信息
                {
                    "rc": 0,
                    "msg": "success",
                    "appid": "gs10001",
                    "uid": 1003,
                    "account": "zhangsan",
                    "username": "张三",
                    "avatar": "https://...",
                    "thumb_avatar": "https://..."
                }
                
        Raises:
            GSUCAuthError: 认证失败
            httpx.HTTPError: 网络请求失败
        """
        # 调试日志：加密密钥信息
        try:
            key = base64.b64decode(self.encryption_key)
            logger.debug(f"Encryption key length: {len(key)} bytes (expected 32)")
        except Exception as e:
            logger.error(f"Failed to decode encryption key: {e}")
            raise GSUCAuthError(f"加密密钥配置错误: {e}")
        
        # 生成 access_token
        try:
            access_token = self._encrypt_access_token(code)
            logger.debug(f"Generated access_token: {access_token[:50]}...")
        except Exception as e:
            logger.error(f"Failed to generate access_token: {e}")
            raise GSUCAuthError(f"生成 access_token 失败: {e}")
        
        # 构建请求参数
        params = {
            "code": code,
            "access_token": access_token
        }
        
        # 发起请求
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                logger.info(f"Requesting GSUC user info: code={code[:10]}...")
                logger.debug(f"Request URL: {self.userinfo_url}")
                logger.debug(f"Request params: code={code[:20]}..., access_token={access_token[:50]}...")
                
                response = await client.get(self.userinfo_url, params=params)
                
                # 调试日志：响应状态
                logger.debug(f"GSUC response status: {response.status_code}")
                logger.debug(f"GSUC response headers: {dict(response.headers)}")
                
                # 如果是 500 错误，记录响应体
                if response.status_code == 500:
                    logger.error(f"GSUC returned 500 error")
                    logger.error(f"Response body: {response.text[:500]}")
                    raise GSUCAuthError(f"GSUC 服务器错误 (500)，可能是加密密钥不匹配或 code 已失效")
                
                response.raise_for_status()
                
                data = response.json()
                logger.debug(f"GSUC response data: {data}")
                
                # 检查返回码
                if data.get("rc") != 0:
                    error_msg = data.get("msg", "Unknown error")
                    logger.error(f"GSUC auth failed: rc={data.get('rc')}, msg={error_msg}")
                    raise GSUCAuthError(f"GSUC 认证失败: {error_msg}", data.get("rc"))
                
                logger.info(f"GSUC auth success: uid={data.get('uid')}, account={data.get('account')}")
                return data
                
            except httpx.HTTPError as e:
                logger.error(f"GSUC API request failed: {e}")
                logger.error(f"Request URL: {self.userinfo_url}")
                logger.error(f"Request params: code={code[:20]}...")
                raise
    
    async def verify_and_get_user(self, code: str) -> Dict:
        """
        验证 code 并获取用户信息 (简化接口)
        
        Args:
            code: GSUC 返回的授权 code
            
        Returns:
            Dict: 用户信息
                {
                    "uid": 1003,
                    "account": "zhangsan",
                    "username": "张三",
                    "avatar": "https://...",
                    "thumb_avatar": "https://..."
                }
                
        Raises:
            GSUCAuthError: 认证失败
        """
        user_info = await self.get_user_info(code)
        
        # 提取关键字段
        return {
            "uid": user_info["uid"],
            "account": user_info["account"],
            "username": user_info["username"],
            "avatar": user_info.get("avatar", ""),
            "thumb_avatar": user_info.get("thumb_avatar", "")
        }


class GSUCAuthError(Exception):
    """GSUC 认证错误"""
    
    def __init__(self, message: str, error_code: Optional[int] = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)
