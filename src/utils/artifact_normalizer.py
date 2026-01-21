"""
Artifact 内容格式标准化工具

将不同格式的 artifact content 统一转换为标准格式,供前端使用。
"""

from typing import Dict, Any, List, Optional
import json
from src.utils.logger import get_logger

logger = get_logger(__name__)


class ArtifactNormalizer:
    """Artifact 内容标准化器"""
    
    # 标准格式版本
    STANDARD_VERSION = "v3"
    
    @staticmethod
    def normalize(content: Any, artifact_type: str = "meeting_minutes") -> Dict[str, Any]:
        """
        将 artifact content 标准化为统一格式
        
        Args:
            content: 原始内容(可能是字符串、字典或列表)
            artifact_type: artifact 类型
            
        Returns:
            标准化后的内容字典,包含:
            - format_version: 格式版本标识
            - normalized: 标准化后的内容
            - original_format: 原始格式类型
        """
        # 1. 解析 content
        parsed_content = ArtifactNormalizer._parse_content(content)
        
        # 2. 检测格式版本
        format_type = ArtifactNormalizer._detect_format(parsed_content)
        
        # 3. 转换为标准格式
        normalized = ArtifactNormalizer._convert_to_standard(parsed_content, format_type)
        
        return {
            "format_version": ArtifactNormalizer.STANDARD_VERSION,
            "original_format": format_type,
            "normalized": normalized,
        }
    
    @staticmethod
    def _parse_content(content: Any) -> Any:
        """解析 content,处理双重 JSON 编码"""
        if isinstance(content, str):
            try:
                parsed = json.loads(content)
                # 如果解析后还是字符串,再解析一次
                if isinstance(parsed, str):
                    parsed = json.loads(parsed)
                return parsed
            except json.JSONDecodeError:
                logger.warning("Failed to parse content as JSON")
                return content
        return content
    
    @staticmethod
    def _detect_format(content: Any) -> str:
        """
        检测 content 的格式类型
        
        返回:
        - "v3_structured": 最新的结构化格式 (有 title, topics, action_items 等)
        - "v2_markdown": Markdown 格式 (有 meeting_minutes 字段包含 Markdown)
        - "v1_array": 旧的数组格式 (数组包含会议概要、讨论要点等)
        - "generic_dict": 通用字典格式 (可以尝试智能映射)
        - "unknown": 未知格式
        """
        if isinstance(content, dict):
            # 检查是否是 v3 格式
            if "title" in content and "topics" in content and "action_items" in content:
                return "v3_structured"
            
            # 检查是否是 v2 格式
            if "meeting_minutes" in content and isinstance(content["meeting_minutes"], str):
                # 检查是否包含 Markdown 标记
                if "##" in content["meeting_minutes"]:
                    return "v2_markdown"
            
            # 检查是否是 v1 格式
            if "会议概要" in content or "讨论要点" in content:
                return "v1_array"
            
            # 其他字典格式 - 尝试智能映射
            if len(content) > 0:
                return "generic_dict"
            
            return "unknown"
        
        elif isinstance(content, list):
            # 检查是否是 v1 格式
            if len(content) > 0 and isinstance(content[0], dict):
                first_item = content[0]
                if "会议概要" in first_item or "讨论要点" in first_item:
                    return "v1_array"
            
            return "unknown"
        
        return "unknown"
    
    @staticmethod
    def _convert_to_standard(content: Any, format_type: str) -> Dict[str, Any]:
        """
        将内容转换为标准格式
        
        标准格式:
        {
            "title": "会议标题",
            "summary": "会议概要",
            "topics": [
                {
                    "title": "主题标题",
                    "content": "主题内容",
                    "key_points": ["要点1", "要点2"]
                }
            ],
            "decisions": ["决策1", "决策2"],
            "action_items": [
                {
                    "title": "行动项标题",
                    "assignee": "负责人",
                    "description": "描述"
                }
            ],
            "participants": ["参与者1", "参与者2"],
            "metadata": {}
        }
        """
        if format_type == "v3_structured":
            return ArtifactNormalizer._normalize_v3(content)
        
        elif format_type == "v2_markdown":
            return ArtifactNormalizer._normalize_v2(content)
        
        elif format_type == "v1_array":
            return ArtifactNormalizer._normalize_v1(content)
        
        elif format_type == "generic_dict":
            return ArtifactNormalizer._normalize_generic(content)
        
        else:
            # 未知格式,返回原始内容
            return {
                "title": "未知格式",
                "summary": "无法解析的内容格式",
                "raw_content": content,
            }
    
    @staticmethod
    def _normalize_v3(content: Dict) -> Dict[str, Any]:
        """标准化 v3 格式 (已经是标准格式,直接返回)"""
        return {
            "title": content.get("title", "会议纪要"),
            "summary": content.get("overall_summary", ""),
            "topics": ArtifactNormalizer._extract_topics_v3(content.get("topics", [])),
            "decisions": ArtifactNormalizer._extract_decisions_v3(content.get("topics", [])),
            "action_items": ArtifactNormalizer._normalize_action_items_v3(content.get("action_items", [])),
            "participants": content.get("participants", []),
            "metadata": {
                "date": content.get("date"),
                "time": content.get("time"),
            }
        }
    
    @staticmethod
    def _normalize_v2(content: Dict) -> Dict[str, Any]:
        """标准化 v2 格式 (Markdown 格式)"""
        markdown_text = content.get("meeting_minutes", "")
        
        # 解析 Markdown 文本
        sections = ArtifactNormalizer._parse_markdown(markdown_text)
        
        return {
            "title": "会议纪要",
            "summary": sections.get("会议概要", ""),
            "topics": ArtifactNormalizer._extract_topics_from_markdown(sections.get("讨论要点", "")),
            "decisions": ArtifactNormalizer._extract_list_from_markdown(sections.get("决策事项", "")),
            "action_items": ArtifactNormalizer._extract_action_items_from_markdown(sections.get("行动项", "")),
            "participants": [],
            "metadata": {}
        }
    
    @staticmethod
    def _normalize_v1(content: List) -> Dict[str, Any]:
        """标准化 v1 格式 (数组格式)"""
        if not content or not isinstance(content, list):
            return {
                "title": "会议纪要",
                "summary": "",
                "topics": [],
                "decisions": [],
                "action_items": [],
                "participants": [],
                "metadata": {}
            }
        
        first_item = content[0]
        
        return {
            "title": "会议纪要",
            "summary": first_item.get("会议概要", ""),
            "topics": ArtifactNormalizer._extract_topics_v1(first_item.get("讨论要点", [])),
            "decisions": first_item.get("决策事项", []),
            "action_items": ArtifactNormalizer._extract_action_items_v1(first_item.get("行动项", [])),
            "participants": [],
            "metadata": {
                "other": first_item.get("其他", "")
            }
        }
    
    # ========== Helper Methods ==========
    
    @staticmethod
    def _extract_topics_v3(topics: List[Dict]) -> List[Dict]:
        """从 v3 格式提取主题"""
        result = []
        for topic in topics:
            result.append({
                "title": topic.get("title", ""),
                "content": topic.get("key_points", []),
                "key_points": topic.get("key_points", []),
            })
        return result
    
    @staticmethod
    def _extract_decisions_v3(topics: List[Dict]) -> List[str]:
        """从 v3 格式提取决策"""
        decisions = []
        for topic in topics:
            decisions.extend(topic.get("decisions", []))
        return decisions
    
    @staticmethod
    def _normalize_action_items_v3(action_items: List[Dict]) -> List[Dict]:
        """标准化 v3 格式的行动项"""
        result = []
        for item in action_items:
            result.append({
                "title": item.get("title", ""),
                "assignee": item.get("assignee", ""),
                "description": item.get("description", ""),
                "deadline": item.get("deadline"),
            })
        return result
    
    @staticmethod
    def _parse_markdown(text: str) -> Dict[str, str]:
        """解析 Markdown 文本为章节"""
        sections = {}
        current_section = None
        current_content = []
        
        for line in text.split("\n"):
            if line.startswith("## "):
                # 保存上一个章节
                if current_section:
                    sections[current_section] = "\n".join(current_content).strip()
                
                # 开始新章节
                current_section = line[3:].strip()
                current_content = []
            else:
                current_content.append(line)
        
        # 保存最后一个章节
        if current_section:
            sections[current_section] = "\n".join(current_content).strip()
        
        return sections
    
    @staticmethod
    def _extract_topics_from_markdown(text: str) -> List[Dict]:
        """从 Markdown 文本提取主题"""
        topics = []
        lines = text.split("\n")
        current_topic = None
        
        for line in lines:
            line = line.strip()
            if line.startswith("**") and line.endswith("**"):
                # 新主题
                if current_topic:
                    topics.append(current_topic)
                current_topic = {
                    "title": line.strip("*"),
                    "content": [],
                    "key_points": []
                }
            elif line.startswith("- ") and current_topic:
                # 要点
                current_topic["key_points"].append(line[2:])
        
        if current_topic:
            topics.append(current_topic)
        
        return topics
    
    @staticmethod
    def _extract_list_from_markdown(text: str) -> List[str]:
        """从 Markdown 文本提取列表项"""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("- ") or line.startswith("* "):
                items.append(line[2:])
            elif line and not line.startswith("#"):
                items.append(line)
        return items
    
    @staticmethod
    def _extract_action_items_from_markdown(text: str) -> List[Dict]:
        """从 Markdown 文本提取行动项"""
        items = []
        for line in text.split("\n"):
            line = line.strip()
            if line.startswith("**[") and "]**" in line:
                # 格式: **[负责人]** 描述
                parts = line.split("]**", 1)
                assignee = parts[0].replace("**[", "").strip()
                description = parts[1].strip() if len(parts) > 1 else ""
                items.append({
                    "title": description[:50] + "..." if len(description) > 50 else description,
                    "assignee": assignee,
                    "description": description,
                    "deadline": None,
                })
        return items
    
    @staticmethod
    def _extract_topics_v1(topics: Any) -> List[Dict]:
        """从 v1 格式提取主题"""
        if isinstance(topics, list):
            return [
                {
                    "title": str(topic) if not isinstance(topic, dict) else topic.get("title", ""),
                    "content": [str(topic)] if not isinstance(topic, dict) else [],
                    "key_points": [str(topic)] if not isinstance(topic, dict) else [],
                }
                for topic in topics
            ]
        return []
    
    @staticmethod
    def _extract_action_items_v1(items: Any) -> List[Dict]:
        """从 v1 格式提取行动项"""
        if isinstance(items, list):
            return [
                {
                    "title": str(item) if not isinstance(item, dict) else item.get("title", ""),
                    "assignee": "",
                    "description": str(item) if not isinstance(item, dict) else item.get("description", ""),
                    "deadline": None,
                }
                for item in items
            ]
        return []
    
    @staticmethod
    def _normalize_generic(content: Dict) -> Dict[str, Any]:
        """
        智能标准化通用字典格式
        
        使用语义映射来识别可能的字段：
        - 标题相关: title, 标题, 主题, 会议主题, subject, topic
        - 概要相关: summary, 概要, 总结, 会议概要, overview
        - 主题相关: topics, 议题, 讨论内容, 讨论要点, discussions
        - 决策相关: decisions, 决策, 决定, 决策事项
        - 行动项相关: action_items, actions, 行动项, 待办, 任务, todos
        - 参与者相关: participants, 参与者, 与会人员, attendees
        """
        # 定义语义映射规则
        title_keys = ["title", "标题", "主题", "会议主题", "subject", "topic", "会议标题"]
        summary_keys = ["summary", "概要", "总结", "会议概要", "overview", "overall_summary", "整体总结"]
        topics_keys = ["topics", "议题", "讨论内容", "讨论要点", "discussions", "discussion_points", "要点"]
        decisions_keys = ["decisions", "决策", "决定", "决策事项", "resolutions"]
        action_keys = ["action_items", "actions", "行动项", "待办", "任务", "todos", "tasks", "待办事项"]
        participants_keys = ["participants", "参与者", "与会人员", "attendees", "members"]
        
        # 提取字段
        title = ArtifactNormalizer._find_value_by_keys(content, title_keys, "会议纪要")
        summary = ArtifactNormalizer._find_value_by_keys(content, summary_keys, "")
        topics_raw = ArtifactNormalizer._find_value_by_keys(content, topics_keys, [])
        decisions_raw = ArtifactNormalizer._find_value_by_keys(content, decisions_keys, [])
        actions_raw = ArtifactNormalizer._find_value_by_keys(content, action_keys, [])
        participants_raw = ArtifactNormalizer._find_value_by_keys(content, participants_keys, [])
        
        # 标准化 topics
        topics = ArtifactNormalizer._normalize_topics_generic(topics_raw)
        
        # 标准化 decisions
        decisions = ArtifactNormalizer._normalize_list_generic(decisions_raw)
        
        # 标准化 action_items
        action_items = ArtifactNormalizer._normalize_actions_generic(actions_raw)
        
        # 标准化 participants
        participants = ArtifactNormalizer._normalize_list_generic(participants_raw)
        
        # 收集其他未映射的字段
        mapped_keys = set()
        for keys in [title_keys, summary_keys, topics_keys, decisions_keys, action_keys, participants_keys]:
            mapped_keys.update(keys)
        
        other_fields = {k: v for k, v in content.items() if k not in mapped_keys}
        
        return {
            "title": title,
            "summary": summary,
            "topics": topics,
            "decisions": decisions,
            "action_items": action_items,
            "participants": participants,
            "metadata": {
                "other_fields": other_fields,
                "note": "通过智能映射转换的通用格式"
            }
        }
    
    @staticmethod
    def _find_value_by_keys(data: Dict, keys: List[str], default: Any) -> Any:
        """在字典中查找第一个匹配的键的值"""
        for key in keys:
            if key in data:
                return data[key]
        return default
    
    @staticmethod
    def _normalize_topics_generic(topics_raw: Any) -> List[Dict]:
        """标准化通用格式的主题"""
        if isinstance(topics_raw, list):
            result = []
            for item in topics_raw:
                if isinstance(item, dict):
                    # 字典格式
                    result.append({
                        "title": item.get("title") or item.get("标题") or item.get("主题") or "",
                        "content": item.get("content") or item.get("内容") or [],
                        "key_points": item.get("key_points") or item.get("要点") or item.get("关键点") or [],
                    })
                elif isinstance(item, str):
                    # 字符串格式
                    result.append({
                        "title": item,
                        "content": [item],
                        "key_points": [item],
                    })
            return result
        elif isinstance(topics_raw, str):
            # 单个字符串
            return [{
                "title": "讨论内容",
                "content": [topics_raw],
                "key_points": [topics_raw],
            }]
        return []
    
    @staticmethod
    def _normalize_list_generic(items: Any) -> List[str]:
        """标准化通用格式的列表"""
        if isinstance(items, list):
            result = []
            for item in items:
                if isinstance(item, str):
                    result.append(item)
                elif isinstance(item, dict):
                    # 尝试提取描述性字段
                    desc = (item.get("description") or 
                           item.get("描述") or 
                           item.get("content") or 
                           item.get("内容") or 
                           str(item))
                    result.append(desc)
                else:
                    result.append(str(item))
            return result
        elif isinstance(items, str):
            return [items]
        return []
    
    @staticmethod
    def _normalize_actions_generic(actions_raw: Any) -> List[Dict]:
        """标准化通用格式的行动项"""
        if isinstance(actions_raw, list):
            result = []
            for item in actions_raw:
                if isinstance(item, dict):
                    result.append({
                        "title": (item.get("title") or 
                                 item.get("标题") or 
                                 item.get("任务") or 
                                 item.get("description") or 
                                 item.get("描述") or "")[:100],
                        "assignee": (item.get("assignee") or 
                                    item.get("负责人") or 
                                    item.get("责任人") or ""),
                        "description": (item.get("description") or 
                                       item.get("描述") or 
                                       item.get("内容") or ""),
                        "deadline": item.get("deadline") or item.get("截止日期"),
                    })
                elif isinstance(item, str):
                    result.append({
                        "title": item[:100],
                        "assignee": "",
                        "description": item,
                        "deadline": None,
                    })
            return result
        return []
