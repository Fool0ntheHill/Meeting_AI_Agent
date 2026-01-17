#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""查看指定文件夹中的任务"""

import sqlite3
import sys

def check_folder_tasks(folder_name=None):
    """查看文件夹及其任务"""
    conn = sqlite3.connect('meeting_agent.db')
    cursor = conn.cursor()
    
    # 1. 列出所有文件夹
    cursor.execute('SELECT folder_id, name, owner_user_id, created_at FROM folders ORDER BY created_at DESC')
    folders = cursor.fetchall()
    
    print("=" * 80)
    print("所有文件夹:")
    print("=" * 80)
    if folders:
        for folder_id, name, owner, created_at in folders:
            print(f"  文件夹ID: {folder_id}")
            print(f"  名称: {name}")
            print(f"  所有者: {owner}")
            print(f"  创建时间: {created_at}")
            print("-" * 80)
    else:
        print("  (没有文件夹)")
    
    # 2. 如果指定了文件夹名称，查找该文件夹
    if folder_name:
        cursor.execute('SELECT folder_id FROM folders WHERE name = ?', (folder_name,))
        result = cursor.fetchone()
        
        if not result:
            print(f"\n✗ 未找到名为 '{folder_name}' 的文件夹")
            conn.close()
            return
        
        folder_id = result[0]
        print(f"\n找到文件夹: {folder_name} (ID: {folder_id})")
        
        # 3. 查询该文件夹中的任务
        cursor.execute('''
            SELECT task_id, name, meeting_type, state, is_deleted, created_at 
            FROM tasks 
            WHERE folder_id = ?
            ORDER BY created_at DESC
        ''', (folder_id,))
        
        tasks = cursor.fetchall()
        
        print("\n" + "=" * 80)
        print(f"文件夹 '{folder_name}' 中的任务:")
        print("=" * 80)
        
        if tasks:
            for task_id, name, meeting_type, state, is_deleted, created_at in tasks:
                status = "已删除" if is_deleted else "活跃"
                task_name = name if name else "(未命名)"
                print(f"  任务ID: {task_id}")
                print(f"  名称: {task_name}")
                print(f"  会议类型: {meeting_type}")
                print(f"  状态: {state}")
                print(f"  是否删除: {status}")
                print(f"  创建时间: {created_at}")
                print("-" * 80)
            print(f"\n总计: {len(tasks)} 个任务")
        else:
            print("  (该文件夹为空)")
    
    # 4. 统计根目录（无文件夹）的任务
    cursor.execute('''
        SELECT COUNT(*) 
        FROM tasks 
        WHERE folder_id IS NULL AND (is_deleted = 0 OR is_deleted IS NULL)
    ''')
    root_count = cursor.fetchone()[0]
    
    print("\n" + "=" * 80)
    print(f"根目录（无文件夹）任务数: {root_count}")
    print("=" * 80)
    
    conn.close()

if __name__ == "__main__":
    folder_name = sys.argv[1] if len(sys.argv) > 1 else None
    check_folder_tasks(folder_name)
