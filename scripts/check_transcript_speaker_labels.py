"""检查数据库中转写记录的说话人标签"""

import json
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.database.session import session_scope
from src.database.repositories import TranscriptRepository

with session_scope() as db:
    repo = TranscriptRepository(db)
    transcript = repo.get_by_task_id('task_1c8f2c5d561048db')
    
    if transcript:
        segments = json.loads(transcript.segments)
        print(f"转写记录包含 {len(segments)} 个片段")
        print(f"\n前5个片段的说话人标签:")
        for i, seg in enumerate(segments[:5]):
            print(f"{i+1}. speaker='{seg['speaker']}' - {seg['text'][:50]}...")
    else:
        print("未找到转写记录")
