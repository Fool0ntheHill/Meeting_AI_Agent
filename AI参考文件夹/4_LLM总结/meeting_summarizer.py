#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
会议纪要生成模块
使用大模型将对话转写为结构化的会议纪要

功能：
1. 格式化转写文本
2. 支持多种策略（通用、头脑风暴、面试等）
3. 调用 LLM 生成 Markdown 格式纪要

依赖：
- openai: OpenAI SDK (兼容火山引擎方舟/豆包等)
"""

import os
import json
from typing import List, Dict, Optional
from datetime import datetime


class MeetingSummarizer:
    """会议纪要生成器"""
    
    # 策略类型
    STRATEGY_GENERAL = "general"
    STRATEGY_BRAINSTORMING = "brainstorming"
    STRATEGY_INTERVIEW = "interview"
    STRATEGY_CUSTOM = "custom"
    
    # Token 限制（预留空间给输出）
    MAX_INPUT_TOKENS = 12000  # 假设使用 16k 模型
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: str = "gpt-3.5-turbo-16k",
        verbose: bool = True
    ):
        """
        初始化会议纪要生成器
        
        Args:
            api_key: LLM API Key（从环境变量读取）
            base_url: LLM API Base URL（从环境变量读取）
            model: 模型名称
            verbose: 是否打印详细日志
        """
        self.api_key = api_key or os.getenv("LLM_API_KEY")
        self.base_url = base_url or os.getenv("LLM_BASE_URL")
        self.model = model
        self.verbose = verbose
        
        if not self.api_key:
            raise ValueError("LLM_API_KEY 未设置，请设置环境变量或传入参数")
        
        # 初始化 OpenAI 客户端
        try:
            from openai import OpenAI
            
            client_kwargs = {"api_key": self.api_key}
            if self.base_url:
                client_kwargs["base_url"] = self.base_url
            
            self.client = OpenAI(**client_kwargs)
            
            if self.verbose:
                print(f"[MeetingSummarizer] 初始化成功")
                print(f"  模型: {self.model}")
                if self.base_url:
                    print(f"  Base URL: {self.base_url}")
        except ImportError:
            raise ImportError("请安装 openai 库: pip install openai")
    
    def _log(self, message: str):
        """打印日志"""
        if self.verbose:
            print(f"[MeetingSummarizer] {message}")
    
    def _format_transcript(self, utterances: List[Dict]) -> str:
        """
        格式化转写文本为适合 LLM 阅读的格式
        
        优化：合并同一说话人的连续发言，减少 Token 消耗
        
        Args:
            utterances: 转写片段列表
        
        Returns:
            格式化的文本字符串
        """
        self._log("格式化转写文本...")
        
        if not utterances:
            return ""
        
        formatted_lines = []
        current_speaker = None
        current_texts = []
        current_start_time = None
        
        for utt in utterances:
            speaker = utt.get('speaker', 'Unknown')
            text = utt.get('text', '').strip()
            start_time = utt.get('start_time', 0)
            
            if not text:
                continue
            
            # 格式化时间戳
            timestamp = self._format_timestamp(start_time)
            
            # 如果是同一个说话人，合并文本
            if speaker == current_speaker:
                current_texts.append(text)
            else:
                # 输出上一个说话人的内容
                if current_speaker and current_texts:
                    combined_text = ' '.join(current_texts)
                    formatted_lines.append(
                        f"[{self._format_timestamp(current_start_time)}] {current_speaker}: {combined_text}"
                    )
                
                # 开始新的说话人
                current_speaker = speaker
                current_texts = [text]
                current_start_time = start_time
        
        # 输出最后一个说话人的内容
        if current_speaker and current_texts:
            combined_text = ' '.join(current_texts)
            formatted_lines.append(
                f"[{self._format_timestamp(current_start_time)}] {current_speaker}: {combined_text}"
            )
        
        formatted_text = '\n'.join(formatted_lines)
        
        self._log(f"格式化完成，共 {len(formatted_lines)} 段对话")
        
        return formatted_text
    
    def _format_timestamp(self, milliseconds: int) -> str:
        """
        将毫秒转换为 HH:MM:SS 格式
        
        Args:
            milliseconds: 毫秒数
        
        Returns:
            格式化的时间字符串
        """
        seconds = milliseconds // 1000
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    
    def _get_system_prompt(
        self,
        strategy_type: str,
        custom_instruction: Optional[str] = None
    ) -> str:
        """
        根据策略类型返回 System Prompt
        
        Args:
            strategy_type: 策略类型
            custom_instruction: 自定义指令（仅用于 custom 策略）
        
        Returns:
            System Prompt 字符串
        """
        base_instruction = """你是一个专业的会议纪要助手。你的任务是将会议对话转写为结构化的会议纪要。

要求：
1. 严格输出 Markdown 格式
2. 不要添加任何闲聊或额外说明
3. 保持客观中立，忠实记录会议内容
4. 使用清晰的标题和列表结构
"""
        
        if strategy_type == self.STRATEGY_GENERAL:
            return base_instruction + """
请生成标准会议纪要，包含以下部分：

## 会议主题
简要概括会议的核心主题（1-2句话）

## 参会人员
列出所有参会人员

## 核心结论
- 列出会议达成的主要结论和决策
- 每条结论用一个要点表示

## 讨论要点
- 记录重要的讨论内容
- 按主题分类整理

## 待办事项 (ToDo)
- 列出需要跟进的任务
- 格式：[负责人] 任务描述

## 其他
记录其他重要信息
"""
        
        elif strategy_type == self.STRATEGY_BRAINSTORMING:
            return base_instruction + """
这是一次头脑风暴会议，请侧重记录创意和发散性思维：

## 会议主题
简要概括头脑风暴的核心问题

## 参会人员
列出所有参会人员

## 创意点
- 记录所有提出的创意和想法
- 保留发散性思维，不要过早评判

## 分歧点
- 记录存在争议或不同意见的地方
- 客观呈现各方观点

## 潜在方案
- 整理出可行的解决方案
- 标注每个方案的优缺点

## 下一步行动
- 列出需要进一步探索的方向
"""
        
        elif strategy_type == self.STRATEGY_INTERVIEW:
            return base_instruction + """
这是一次面试或 HR 评估会议，请侧重记录候选人评估：

## 面试信息
- 候选人姓名
- 面试职位
- 面试官

## 候选人能力评估
- 技术能力
- 沟通表达
- 问题解决能力
- 团队协作

## 优点
列出候选人的突出优势

## 缺点/待改进
列出需要关注的问题

## 面试官建议
- 是否推荐录用
- 建议的职级/薪资范围
- 其他建议

## 关键对话摘录
记录重要的问答片段
"""
        
        elif strategy_type == self.STRATEGY_CUSTOM:
            if not custom_instruction:
                raise ValueError("custom 策略需要提供 custom_instruction")
            
            return base_instruction + f"""
自定义要求：
{custom_instruction}

请根据上述要求生成会议纪要。
"""
        
        else:
            raise ValueError(f"未知的策略类型: {strategy_type}")
    
    def _check_token_limit(self, text: str) -> bool:
        """
        检查文本是否超过 Token 限制
        
        简单估算：1 Token ≈ 4 字符（英文）或 1.5 字符（中文）
        
        Args:
            text: 输入文本
        
        Returns:
            是否超过限制
        """
        # 简单估算（中文为主）
        estimated_tokens = len(text) / 1.5
        
        if estimated_tokens > self.MAX_INPUT_TOKENS:
            self._log(f"⚠️  文本过长，估算 Token: {estimated_tokens:.0f} > {self.MAX_INPUT_TOKENS}")
            return False
        
        return True
    
    def _truncate_text(self, text: str) -> str:
        """
        截断过长的文本
        
        TODO: 实现 Map-Reduce 策略进行分段总结
        
        Args:
            text: 原始文本
        
        Returns:
            截断后的文本
        """
        max_chars = int(self.MAX_INPUT_TOKENS * 1.5)
        
        if len(text) <= max_chars:
            return text
        
        self._log(f"文本过长，截断到 {max_chars} 字符")
        self._log("⚠️  建议实现 Map-Reduce 策略以处理长文本")
        
        # 简单截断（保留前面部分）
        truncated = text[:max_chars]
        truncated += "\n\n[... 文本过长，已截断 ...]"
        
        return truncated
    
    def generate_minutes(
        self,
        transcript_text: str,
        strategy_type: str = STRATEGY_GENERAL,
        custom_instruction: Optional[str] = None
    ) -> str:
        """
        生成会议纪要
        
        Args:
            transcript_text: 格式化的对话文本
            strategy_type: 策略类型
            custom_instruction: 自定义指令（仅用于 custom 策略）
        
        Returns:
            Markdown 格式的会议纪要
        """
        self._log(f"开始生成会议纪要（策略: {strategy_type}）...")
        
        # 检查文本长度
        if not self._check_token_limit(transcript_text):
            transcript_text = self._truncate_text(transcript_text)
        
        # 获取 System Prompt
        system_prompt = self._get_system_prompt(strategy_type, custom_instruction)
        
        # 构造 User Prompt
        user_prompt = f"""请根据以下会议对话生成会议纪要：

{transcript_text}
"""
        
        # 调用 LLM
        try:
            self._log("调用 LLM API...")
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            minutes = response.choices[0].message.content.strip()
            
            self._log(f"✓ 纪要生成成功，长度: {len(minutes)} 字符")
            
            return minutes
            
        except Exception as e:
            self._log(f"✗ LLM 调用失败: {e}")
            raise
    
    def process_summary(
        self,
        json_path: str,
        strategy: str = STRATEGY_GENERAL,
        custom_instruction: Optional[str] = None,
        output_path: str = "meeting_minutes.md"
    ) -> str:
        """
        处理会议纪要生成的完整流程
        
        Args:
            json_path: 输入 JSON 文件路径
            strategy: 策略类型
            custom_instruction: 自定义指令
            output_path: 输出 Markdown 文件路径
        
        Returns:
            生成的会议纪要文本
        """
        self._log("=" * 80)
        self._log("会议纪要生成流程")
        self._log("=" * 80)
        
        # 1. 读取 JSON
        self._log(f"\n[1] 读取 JSON 文件: {json_path}")
        
        try:
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            utterances = data.get('result', {}).get('utterances', [])
            
            if not utterances:
                raise ValueError("JSON 文件中没有 utterances 数据")
            
            self._log(f"  ✓ 读取成功，共 {len(utterances)} 个片段")
            
        except Exception as e:
            self._log(f"  ✗ 读取失败: {e}")
            raise
        
        # 2. 格式化文本
        self._log(f"\n[2] 格式化对话文本...")
        transcript_text = self._format_transcript(utterances)
        
        if not transcript_text:
            raise ValueError("格式化后的文本为空")
        
        self._log(f"  ✓ 格式化完成，文本长度: {len(transcript_text)} 字符")
        
        # 3. 生成纪要
        self._log(f"\n[3] 生成会议纪要...")
        minutes = self.generate_minutes(
            transcript_text=transcript_text,
            strategy_type=strategy,
            custom_instruction=custom_instruction
        )
        
        # 4. 保存文件
        self._log(f"\n[4] 保存会议纪要: {output_path}")
        
        try:
            # 添加元数据
            metadata = f"""---
生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
策略类型: {strategy}
输入文件: {json_path}
---

"""
            
            full_content = metadata + minutes
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            
            self._log(f"  ✓ 保存成功")
            
        except Exception as e:
            self._log(f"  ✗ 保存失败: {e}")
            raise
        
        self._log("\n" + "=" * 80)
        self._log("✓ 会议纪要生成完成")
        self._log("=" * 80)
        
        return minutes


# ==================== 使用示例 ====================

def main():
    """使用示例"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python meeting_summarizer.py <json_path> [strategy]")
        print("\n策略类型:")
        print("  general        - 通用会议纪要（默认）")
        print("  brainstorming  - 头脑风暴会议")
        print("  interview      - 面试/HR 评估")
        print("  custom         - 自定义（需要额外参数）")
        print("\n示例:")
        print("  python meeting_summarizer.py final_meeting_record.json")
        print("  python meeting_summarizer.py final_meeting_record.json brainstorming")
        sys.exit(1)
    
    json_path = sys.argv[1]
    strategy = sys.argv[2] if len(sys.argv) > 2 else "general"
    
    # 初始化
    summarizer = MeetingSummarizer(
        model="gpt-3.5-turbo-16k",  # 或其他兼容模型
        verbose=True
    )
    
    # 生成纪要
    summarizer.process_summary(
        json_path=json_path,
        strategy=strategy,
        output_path="meeting_minutes.md"
    )


if __name__ == "__main__":
    main()
