#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""检查 task_295eb9a492a54181 的说话人数据"""

from src.database.session import get_session
from src.database.repositories import TranscriptRepository, SpeakerMappingRepository

db = get_session()

# 检查 transcript segments
transcript_repo = TranscriptRepository(db)
transcript = transcript_repo.get_by_task_id('task_295eb9a492a54181')

if transcript:
    segments = transcript.get_segments_list()
    print(f"Transcript segments (前3条):")
    for i, seg in enumerate(segments[:3]):
        print(f"  [{i}] speaker: {seg.get('speaker')}")
else:
    print("Transcript not found")

# 检查 SpeakerMapping
print("\nSpeakerMapping:")
speaker_mapping_repo = SpeakerMappingRepository(db)
mappings = speaker_mapping_repo.get_by_task_id('task_295eb9a492a54181')
for m in mappings:
    print(f"  {m.speaker_label} -> {m.speaker_name} (speaker_id: {m.speaker_id})")

db.close()
