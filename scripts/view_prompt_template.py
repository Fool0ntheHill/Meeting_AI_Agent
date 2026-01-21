#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看提示词模板"""

import sqlite3

template_id = "meeting_minutes_detailed_summary"

conn = sqlite3.connect("meeting_agent.db")
cursor = conn.cursor()

cursor.execute("""
    SELECT template_id, title, description, prompt_body, artifact_type, supported_languages
    FROM prompt_templates
    WHERE template_id = ?
""", (template_id,))

row = cursor.fetchone()

if row:
    print(f"Template ID: {row[0]}")
    print(f"Title: {row[1]}")
    print(f"Description: {row[2]}")
    print(f"Artifact Type: {row[4]}")
    print(f"Supported Languages: {row[5]}")
    print(f"\n{'='*60}")
    print("Prompt Body:")
    print(f"{'='*60}")
    print(row[3])
else:
    print(f"Template {template_id} not found")

conn.close()
