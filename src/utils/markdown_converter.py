"""
Markdown 转换器 - 后端的"万能转接头"

将所有格式的 artifact content 统一转换为 Markdown，保证前端永远不会白屏。
"""

import json
from typing import Any, Dict
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MarkdownConverter:
    """将任意格式的 artifact 转换为 Markdown"""
    
    @staticmethod
    def convert(content: Any, artifact_type: str = "meeting_minutes") -> Dict[str, str]:
        """
        将任意格式转换为统一的 Markdown 格式
        
        Args:
            content: 原始内容（可能是字符串、字典、列表等）
            artifact_type: artifact 类型
            
        Returns:
            Dict: {"title": "标题", "content": "Markdown 内容"}
        """
        try:
            # 1. 解析 content
            parsed = MarkdownConverter._parse_content(content)
            
            # 2. 检测格式并转换
            if isinstance(parsed, dict):
                # 情况 1: 已经是 Markdown 格式 {"content": "...", "metadata": {...}}
                if "content" in parsed and isinstance(parsed["content"], str):
                    return MarkdownConverter._extract_markdown_format(parsed)
                
                # 情况 2: 结构化 JSON (v3 格式)
                if "title" in parsed and "topics" in parsed:
                    return MarkdownConverter._convert_structured_json(parsed)
                
                # 情况 3: Markdown 字符串格式 (v2 格式)
                if "meeting_minutes" in parsed:
                    return MarkdownConverter._convert_markdown_string(parsed)
                
                # 情况 4: 旧的中文键格式
                if "会议概要" in parsed or "讨论要点" in parsed:
                    return MarkdownConverter._convert_chinese_keys(parsed)
                
                # 情况 5: 通用字典格式
                return MarkdownConverter._convert_generic_dict(parsed)
            
            elif isinstance(parsed, list):
                # 情况 6: 数组格式 (v1 格式)
                if len(parsed) > 0 and isinstance(parsed[0], dict):
                    return MarkdownConverter._convert_array_format(parsed)
            
            elif isinstance(parsed, str):
                # 情况 7: 纯字符串（可能已经是 Markdown）
                return {
                    "title": "会议纪要",
                    "content": parsed
                }
            
            # 情况 8: 完全未知格式 - 兜底策略
            return MarkdownConverter._fallback_json_block(parsed)
            
        except Exception as e:
            logger.error(f"Failed to convert to Markdown: {e}", exc_info=True)
            # 最终兜底：返回错误信息，但保证不会让前端崩溃
            return {
                "title": "内容解析失败",
                "content": f"```\n无法解析的内容格式\n错误: {str(e)}\n```"
            }
    
    @staticmethod
    def _parse_content(content: Any) -> Any:
        """解析 content，处理双重 JSON 编码"""
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                # 如果解析后还是字符串，再解析一次
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                return parsed
            except json.JSONDecodeError:
                return content
        return content
    
    @staticmethod
    def _extract_markdown_format(data: Dict) -> Dict[str, str]:
        """提取已经是 Markdown 格式的数据"""
        title = "会议纪要"
        if "metadata" in data and isinstance(data["metadata"], dict):
            title = data["metadata"].get("title", title)
        
        return {
            "title": title,
            "content": data["content"]
        }
    
    @staticmethod
    def _convert_structured_json(data: Dict) -> Dict[str, str]:
        """转换结构化 JSON (v3 格式)"""
        lines = []
        
        # 标题
        title = data.get("title", "会议纪要")
        
        # 基本信息
        if data.get("date") or data.get("time"):
            lines.append("## 基本信息\n")
            if data.get("date"):
                lines.append(f"**日期**: {data['date']}\n")
            if data.get("time"):
                lines.append(f"**时间**: {data['time']}\n")
            lines.append("\n")
        
        # 参与者
        if data.get("participants"):
            lines.append("**参与者**: " + "、".join(data["participants"]) + "\n\n")
        
        # 会议概要
        if data.get("overall_summary"):
            lines.append("## 会议概要\n\n")
            lines.append(data["overall_summary"] + "\n\n")
        
        # 讨论议题
        if data.get("topics"):
            lines.append("## 讨论议题\n\n")
            for topic in data["topics"]:
                lines.append(f"### {topic.get('title', '未命名议题')}\n\n")
                
                if topic.get("key_points"):
                    for point in topic["key_points"]:
                        lines.append(f"- {point}\n")
                    lines.append("\n")
                
                if topic.get("decisions"):
                    lines.append("**决策**:\n")
                    for decision in topic["decisions"]:
                        lines.append(f"- ✅ {decision}\n")
                    lines.append("\n")
        
        # 行动项
        if data.get("action_items"):
            lines.append("## 行动项\n\n")
            for item in data["action_items"]:
                assignee = item.get("assignee", "待分配")
                title_text = item.get("title") or item.get("description", "")
                deadline = item.get("deadline")
                
                line = f"- [ ] **[{assignee}]**: {title_text}"
                if deadline:
                    line += f" (截止: {deadline})"
                lines.append(line + "\n")
        
        return {
            "title": title,
            "content": "".join(lines)
        }
    
    @staticmethod
    def _convert_markdown_string(data: Dict) -> Dict[str, str]:
        """转换 Markdown 字符串格式 (v2 格式)"""
        content = data.get("meeting_minutes", "")
        
        # 尝试从 Markdown 中提取标题
        title = "会议纪要"
        if "##" in content:
            lines = content.split("\n")
            for line in lines:
                if line.startswith("## "):
                    title = line.replace("## ", "").strip()
                    break
        
        return {
            "title": title,
            "content": content
        }
    
    @staticmethod
    def _convert_chinese_keys(data: Dict) -> Dict[str, str]:
        """转换中文键格式"""
        lines = []
        
        # 映射中文键到章节
        key_mapping = {
            "会议概要": "## 会议概要",
            "讨论要点": "## 讨论要点",
            "决策事项": "## 决策事项",
            "行动项": "## 行动项",
            "其他": "## 其他"
        }
        
        for key, header in key_mapping.items():
            if key in data:
                lines.append(f"{header}\n\n")
                value = data[key]
                
                if isinstance(value, list):
                    for item in value:
                        lines.append(f"- {item}\n")
                elif isinstance(value, str):
                    lines.append(f"{value}\n")
                
                lines.append("\n")
        
        return {
            "title": "会议纪要",
            "content": "".join(lines)
        }
    
    @staticmethod
    def _convert_generic_dict(data: Dict) -> Dict[str, str]:
        """转换通用字典格式"""
        lines = []
        
        # 尝试提取标题
        title_keys = ["title", "标题", "主题", "subject"]
        title = "会议纪要"
        for key in title_keys:
            if key in data:
                title = str(data[key])
                break
        
        # 遍历所有键值对
        for key, value in data.items():
            if key in title_keys:
                continue  # 跳过已经用作标题的键
            
            lines.append(f"## {key}\n\n")
            
            if isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        # 嵌套字典，展开显示
                        for k, v in item.items():
                            lines.append(f"- **{k}**: {v}\n")
                    else:
                        lines.append(f"- {item}\n")
            elif isinstance(value, dict):
                for k, v in value.items():
                    lines.append(f"**{k}**: {v}\n\n")
            else:
                lines.append(f"{value}\n")
            
            lines.append("\n")
        
        return {
            "title": title,
            "content": "".join(lines)
        }
    
    @staticmethod
    def _convert_array_format(data: list) -> Dict[str, str]:
        """转换数组格式 (v1 格式)"""
        if not data or not isinstance(data[0], dict):
            return MarkdownConverter._fallback_json_block(data)
        
        # 取第一个元素
        first_item = data[0]
        return MarkdownConverter._convert_chinese_keys(first_item)
    
    @staticmethod
    def _fallback_json_block(data: Any) -> Dict[str, str]:
        """兜底策略：将未知格式包装在 JSON 代码块中"""
        logger.warning(f"Unknown format, using JSON fallback: {type(data)}")
        
        try:
            json_str = json.dumps(data, ensure_ascii=False, indent=2)
        except Exception:
            json_str = str(data)
        
        content = f"""## 原始内容

> ⚠️ 此内容格式无法自动解析，以下是原始数据：

```json
{json_str}
```
"""
        
        return {
            "title": "会议纪要（原始格式）",
            "content": content
        }
