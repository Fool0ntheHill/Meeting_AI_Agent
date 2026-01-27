#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查任务 task_7168f79dbb6147cc 的数据"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.database.session import session_scope
from src.database.repositories import TranscriptRepository, SpeakerMappingRepository

with session_scope() as db:
    tr = TranscriptRepository(db)
    sm = SpeakerMappingRepository(db)
    
    # 获取 transcript
    t = tr.get_by_task_id('task_7168f79dbb6147cc')
    
    if t:
        print("✅ Transcript segments (前 5 条):")
        segs = t.get_segments_list()[:5]
        for i, s in enumerate(segs, 1):
            print(f"  [{i}] {s.get('speaker')}: {s.get('text')[:60]}...")
    else:
        print("❌ 没有找到 transcript")
    
    # 获取 speaker mapping
    print("\n✅ SpeakerMapping:")
    maps = sm.get_by_task_id('task_7168f79dbb6147cc')
    for m in maps:
        print(f"  {m.speaker_label} -> {m.speaker_name} (speaker_id={m.speaker_id})")
