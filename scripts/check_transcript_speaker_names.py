#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 transcript 中的说话人名称"""

import sqlite3
import json

task_id = "task_097021e3d3944092"

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

# 查询 transcript
cursor.execute("""
    SELECT transcript_id, segments, full_text
    FROM transcripts
    WHERE task_id = ?
""", (task_id,))

row = cursor.fetchone()

if row:
    print(f"Task ID: {task_id}")
    print(f"Transcript ID: {row[0]}")
    
    # 解析 segments
    segments = json.loads(row[1])
    
    print(f"\n前 10 个 segments:")
    for i, seg in enumerate(segments[:10], 1):
        speaker = seg.get("speaker", "Unknown")
        text = seg.get("text", "")
        print(f"{i}. {speaker}: {text}")
    
    # 检查 full_text
    full_text = row[2]
    print(f"\nFull text (前 500 字):")
    print(full_text[:500])
    
    # 检查说话人名称
    print(f"\n说话人名称检查:")
    if "林煜东" in full_text:
        print("  ✓ 包含: 林煜东")
    if "林雨东" in full_text:
        print("  ⚠️  包含: 林雨东")
    if "speaker_linyudong" in full_text:
        print("  ✗ 包含: speaker_linyudong")
    if "蓝为一" in full_text:
        print("  ✓ 包含: 蓝为一")
    if "speaker_lanweiyi" in full_text:
        print("  ✗ 包含: speaker_lanweiyi")
else:
    print(f"Task {task_id} 没有 transcript")

# 查询 speaker_mappings
cursor.execute("""
    SELECT speaker_label, speaker_name, speaker_id
    FROM speaker_mappings
    WHERE task_id = ?
""", (task_id,))

mappings = cursor.fetchall()

if mappings:
    print(f"\nSpeaker mappings:")
    for mapping in mappings:
        print(f"  {mapping[0]} -> {mapping[1]} (ID: {mapping[2]})")
else:
    print(f"\nTask {task_id} 没有 speaker mappings")

conn.close()
