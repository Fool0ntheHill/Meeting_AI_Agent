# 企业微信图片显示问题分析

## 问题描述

用户报告：复制会议纪要到企业微信后，图片无法显示。

## 当前后端图片处理逻辑

### 现状分析

通过代码审查，发现**当前后端没有任何图片处理逻辑**：

1. **Gemini LLM 生成内容** (`src/providers/gemini_llm.py`)
   - Gemini 生成 Markdown 格式的内容
   - 如果包含图片，可能是 Markdown 图片语法：`![alt](url)`
   - 直接返回原始 Markdown 内容

2. **Markdown 转换器** (`src/utils/markdown_converter.py`)
   - 只处理文本格式转换（JSON → Markdown）
   - **不处理图片**

3. **Artifact 存储** (`src/services/artifact_generation.py`)
   - 直接存储 Gemini 返回的内容
   - **不做任何图片处理**

### 数据流

```
Gemini LLM → Markdown (可能包含图片) → 数据库 → 前端 → 企业微信
                                                              ↓
                                                         ❌ 图片无法显示
```

## 可能的原因

### 1. 图片格式不兼容

企业微信可能不支持某些图片格式：
- ❌ 外部 URL 链接（企微可能无法访问）
- ❌ Markdown 图片语法（企微可能不解析）
- ✅ Base64 内联图片（需要特定格式）
- ✅ 企微图片消息 API（需要调用 API）

### 2. 图片来源问题

Gemini 生成的图片可能是：
- 外部链接（如 Google 图片、公网 URL）
- 企微无法访问的内网链接
- 临时链接（已过期）

### 3. 复制粘贴限制

企业微信文档的复制粘贴功能可能：
- 不支持 Markdown 图片语法
- 不支持 HTML `<img>` 标签
- 需要特定的图片格式

## 对比测试文件

用户提到的测试文件：`D:\Programs\meeting AI web test\gen_test_html.py`

**需要查看该文件的图片处理逻辑**，可能包含：

1. **图片格式转换**
   ```python
   # 可能的处理逻辑
   import base64
   
   def convert_image_to_base64(image_url):
       # 下载图片
       response = requests.get(image_url)
       # 转换为 base64
       base64_str = base64.b64encode(response.content).decode()
       # 返回 data URI
       return f"data:image/png;base64,{base64_str}"
   ```

2. **图片标签替换**
   ```python
   # 替换 Markdown 图片为 HTML
   content = content.replace(
       "![alt](url)",
       '<img src="data:image/png;base64,..." />'
   )
   ```

3. **企微 API 调用**
   ```python
   # 使用企微图片消息 API
   send_wecom_image(to=["user"], msg=base64_image)
   ```

## 解决方案

### 方案 1: 添加图片格式转换（推荐）

在 `src/utils/markdown_converter.py` 中添加图片处理：

```python
import re
import base64
import requests

class MarkdownConverter:
    
    @staticmethod
    def convert_images_for_wecom(content: str) -> str:
        """
        转换图片格式以适配企业微信
        
        Args:
            content: Markdown 内容
            
        Returns:
            str: 转换后的内容
        """
        # 查找所有 Markdown 图片
        pattern = r'!\[([^\]]*)\]\(([^\)]+)\)'
        
        def replace_image(match):
            alt_text = match.group(1)
            image_url = match.group(2)
            
            try:
                # 如果是外部链接，下载并转换为 base64
                if image_url.startswith('http'):
                    response = requests.get(image_url, timeout=5)
                    base64_str = base64.b64encode(response.content).decode()
                    # 返回 base64 格式
                    return f'<img src="data:image/png;base64,{base64_str}" alt="{alt_text}" />'
                else:
                    # 保持原样
                    return match.group(0)
            except Exception as e:
                logger.warning(f"Failed to convert image {image_url}: {e}")
                # 转换失败，保持原样
                return match.group(0)
        
        return re.sub(pattern, replace_image, content)
```

### 方案 2: 使用企微图片消息 API

在发送通知时，单独处理图片：

```python
# 在 scripts/test_wecom_notification.py 中
def send_artifact_with_images(to: list, content: str):
    """发送包含图片的会议纪要"""
    
    # 1. 提取图片
    images = extract_images(content)
    
    # 2. 发送文本内容（移除图片）
    text_content = remove_images(content)
    send_wecom_markdown(to=to, msg=text_content)
    
    # 3. 单独发送图片
    for image in images:
        send_wecom_image(to=to, msg=image_base64)
```

### 方案 3: 禁止 Gemini 生成图片

在提示词中明确要求不生成图片：

```python
# 在 GLOBAL_SYSTEM_INSTRUCTION 中添加
"""
3. **图片限制原则**：
   - 不要在输出中包含图片、图表或其他非文本内容
   - 如果需要展示数据，使用 Markdown 表格或列表
"""
```

## 诊断步骤

### 1. 检查当前 artifact 是否包含图片

```bash
python scripts/check_image_handling.py task_1c8f2c5d561048db
```

### 2. 查看测试文件的图片处理逻辑

```bash
# 请提供测试文件内容
type "D:\Programs\meeting AI web test\gen_test_html.py"
```

### 3. 测试企微图片消息 API

```bash
python scripts/test_wecom_notification.py
```

## 下一步行动

1. **运行诊断脚本**，确认 artifact 中是否包含图片
2. **查看测试文件**，了解正确的图片处理逻辑
3. **选择解决方案**，根据实际需求实现图片处理
4. **测试验证**，确保企微可以正常显示图片

## 相关文件

- `src/providers/gemini_llm.py` - LLM 生成逻辑
- `src/utils/markdown_converter.py` - Markdown 转换
- `src/services/artifact_generation.py` - Artifact 生成
- `scripts/test_wecom_notification.py` - 企微通知测试
- `scripts/check_image_handling.py` - 图片处理诊断（新建）
