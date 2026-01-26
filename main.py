#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
GSUC 单点登录 (SSO) 回调接口实现

功能:
1. 实现 Python 2 -> Python 3 的 AES 加密算法迁移
2. 处理 GSUC OAuth2.0 回调
3. 验证用户并生成 SessionID
4. 重定向到前端

使用方式:
    uvicorn main:app --host 0.0.0.0 --port 8000 --reload
"""

import base64
import random
import string
from typing import Optional

import httpx
from Crypto.Cipher import AES
from fastapi import FastAPI, Query, HTTPException
from fastapi.responses import RedirectResponse

# ============================================================================
# 配置参数
# ============================================================================

APP_ID = "app_meeting_agent"
APP_SECRET = "G22PT4zLJZRgf6WXWF8V5yXrCpXNu9kQSvLwtXwSIOw="
GSUC_URL = "https://gsuc.gamesci.com.cn/sso/userinfo"
FRONTEND_URL = "http://localhost:5173"

# ============================================================================
# 创建 FastAPI 应用
# ============================================================================

app = FastAPI(
    title="GSUC SSO Service",
    description="GSUC 单点登录回调服务",
    version="1.0.0"
)


# ============================================================================
# 加密函数 (Python 2 -> Python 3 迁移)
# ============================================================================

def encrypt(text: str, key: str) -> Optional[str]:
    """
    AES-256-CBC 加密函数 (从 Python 2 迁移到 Python 3)
    
    算法逻辑:
    1. Base64 解码密钥，验证长度为 32 字节
    2. 在文本开头添加 16 位随机字符
    3. 补齐文本长度为 32 的倍数
    4. 使用 AES-256-CBC 加密 (IV = key[:16])
    5. Base64 编码返回
    
    Args:
        text: 待加密的文本
        key: Base64 编码的 32 字节密钥
        
    Returns:
        str: Base64 编码的加密结果，失败返回 None
        
    Legacy Code (Python 2):
        text_random = ''.join(random.sample(string.letters + string.digits, 16)) + text
        
    Python 3 Changes:
        - string.letters -> string.ascii_letters
        - random.sample -> random.choices (允许重复)
        - Exception, e -> Exception as e
        - 显式处理 bytes/str 转换
    """
    try:
        # 解码 Base64 密钥
        key_bytes = base64.b64decode(key)
        
        # 验证密钥长度为 32 字节 (AES-256)
        if len(key_bytes) != 32:
            print(f"错误: 密钥长度为 {len(key_bytes)} 字节，期望 32 字节")
            return None
            
    except Exception as e:
        print(f"错误: 密钥解码失败 - {e}")
        return None
    
    # 开头加上 16 位随机数
    # Python 2: string.letters -> Python 3: string.ascii_letters
    # Python 2: random.sample (不重复) -> Python 3: random.choices (允许重复)
    random_prefix = ''.join(random.choices(string.ascii_letters + string.digits, k=16))
    text_random = random_prefix + text
    
    # 判断补齐 text 长度为 32 的倍数
    add_num = 32 - (len(text_random) % 32)
    if add_num == 0:
        add_num = 32
    
    # 补齐 (Python 3: chr() 返回 str，需要转换为 bytes)
    text_all = text_random + chr(add_num) * add_num
    
    # 加密数据
    # 使用 key 的前 16 字节作为 IV (与 Python 2 代码保持一致)
    iv = key_bytes[:16]
    cryptor = AES.new(key_bytes, AES.MODE_CBC, iv)
    
    try:
        # Python 3: 需要显式编码为 bytes
        ciphertext = cryptor.encrypt(text_all.encode('utf-8'))
        
        # Base64 编码并返回 str
        return base64.b64encode(ciphertext).decode('utf-8')
        
    except Exception as e:
        print(f"错误: 加密失败 - {e}")
        return None


# ============================================================================
# API 路由
# ============================================================================

@app.get("/")
async def root():
    """根路径 - 服务状态"""
    return {
        "service": "GSUC SSO Service",
        "status": "running",
        "endpoints": {
            "callback": "/api/v1/auth/callback",
            "health": "/health"
        }
    }


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}


@app.get("/api/v1/auth/callback")
async def gsuc_callback(
    code: str = Query(..., description="GSUC 返回的授权 code")
):
    """
    GSUC OAuth2.0 回调接口
    
    流程:
    1. 接收 GSUC 返回的 code
    2. 使用加密算法生成 access_token
    3. 请求 GSUC 用户信息 API
    4. 验证返回结果 (rc == 0)
    5. 生成 SessionID
    6. 重定向到前端，携带 token
    
    Args:
        code: GSUC 返回的授权 code
        
    Returns:
        RedirectResponse: 重定向到前端
        
    Raises:
        HTTPException: 400 参数错误
        HTTPException: 401 认证失败
        HTTPException: 500 服务器错误
    """
    print(f"\n{'='*60}")
    print(f"收到 GSUC 回调请求")
    print(f"{'='*60}")
    print(f"Code: {code[:20]}..." if len(code) > 20 else f"Code: {code}")
    
    # 步骤 1: 生成 access_token
    # 加密内容: code + APP_ID + APP_SECRET
    text_to_encrypt = code + APP_ID + APP_SECRET
    
    print(f"\n生成 access_token...")
    print(f"  待加密文本长度: {len(text_to_encrypt)} 字符")
    
    access_token = encrypt(text_to_encrypt, APP_SECRET)
    
    if not access_token:
        print(f"✗ 加密失败")
        raise HTTPException(
            status_code=500,
            detail="生成 access_token 失败"
        )
    
    print(f"✓ access_token 生成成功")
    print(f"  Token (前50字符): {access_token[:50]}...")
    
    # 步骤 2: 请求 GSUC 用户信息 API
    print(f"\n请求 GSUC 用户信息...")
    print(f"  URL: {GSUC_URL}")
    print(f"  参数: code={code[:20]}..., access_token={access_token[:30]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(
                GSUC_URL,
                params={
                    "code": code,
                    "access_token": access_token
                }
            )
            
            # 检查 HTTP 状态码
            response.raise_for_status()
            
            # 解析 JSON 响应
            data = response.json()
            
            print(f"✓ GSUC API 响应成功")
            print(f"  响应数据: {data}")
            
    except httpx.HTTPError as e:
        print(f"✗ GSUC API 请求失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"GSUC API 请求失败: {str(e)}"
        )
    except Exception as e:
        print(f"✗ 解析响应失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"解析 GSUC 响应失败: {str(e)}"
        )
    
    # 步骤 3: 验证返回结果
    rc = data.get("rc")
    
    if rc != 0:
        error_msg = data.get("msg", "未知错误")
        print(f"✗ GSUC 认证失败: rc={rc}, msg={error_msg}")
        raise HTTPException(
            status_code=401,
            detail=f"GSUC 认证失败: {error_msg}"
        )
    
    print(f"✓ GSUC 认证成功")
    
    # 步骤 4: 提取用户信息
    uid = data.get("uid")
    account = data.get("account")
    username = data.get("username", account)
    
    if not uid or not account:
        print(f"✗ 用户信息不完整: uid={uid}, account={account}")
        raise HTTPException(
            status_code=500,
            detail="用户信息不完整"
        )
    
    print(f"  用户信息:")
    print(f"    UID: {uid}")
    print(f"    Account: {account}")
    print(f"    Username: {username}")
    
    # 步骤 5: 生成 SessionID
    session_id = f"session_{account}_{uid}"
    
    print(f"\n✓ 生成 SessionID: {session_id}")
    
    # 步骤 6: 重定向到前端
    redirect_url = f"{FRONTEND_URL}?token={session_id}"
    
    print(f"\n重定向到前端:")
    print(f"  URL: {redirect_url}")
    print(f"{'='*60}\n")
    
    return RedirectResponse(url=redirect_url)


# ============================================================================
# 测试端点 (可选)
# ============================================================================

@app.get("/api/v1/auth/test-encrypt")
async def test_encrypt(
    text: str = Query(..., description="待加密的文本"),
    key: str = Query(APP_SECRET, description="加密密钥 (Base64)")
):
    """
    测试加密功能
    
    用于验证加密算法是否正确实现
    
    Args:
        text: 待加密的文本
        key: Base64 编码的密钥
        
    Returns:
        dict: 加密结果
    """
    result = encrypt(text, key)
    
    if result:
        return {
            "success": True,
            "input_text": text,
            "input_length": len(text),
            "encrypted": result,
            "encrypted_length": len(result)
        }
    else:
        return {
            "success": False,
            "error": "加密失败"
        }


# ============================================================================
# 启动说明
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    
    print("=" * 60)
    print("GSUC SSO 服务启动")
    print("=" * 60)
    print(f"配置:")
    print(f"  APP_ID: {APP_ID}")
    print(f"  GSUC_URL: {GSUC_URL}")
    print(f"  FRONTEND_URL: {FRONTEND_URL}")
    print()
    print(f"启动命令:")
    print(f"  uvicorn main:app --host 0.0.0.0 --port 8000 --reload")
    print()
    print(f"测试端点:")
    print(f"  健康检查: http://localhost:8000/health")
    print(f"  加密测试: http://localhost:8000/api/v1/auth/test-encrypt?text=hello")
    print(f"  回调接口: http://localhost:8000/api/v1/auth/callback?code=xxx")
    print("=" * 60)
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
