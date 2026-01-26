"""
检查当前后端的图片处理逻辑

用于对比后端和测试文件的图片处理差异
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.database.session import get_session
from src.database.models import Artifact
from src.utils.logger import get_logger

logger = get_logger(__name__)


def check_artifact_images(task_id: str):
    """检查指定任务的 artifact 中是否包含图片"""
    session = get_session()
    
    try:
        # 查询任务的所有 artifacts
        artifacts = session.query(Artifact).filter(
            Artifact.task_id == task_id
        ).order_by(Artifact.version.desc()).all()
        
        if not artifacts:
            print(f"❌ 未找到任务 {task_id} 的 artifacts")
            return
        
        print(f"\n📊 任务 {task_id} 的 Artifacts 分析")
        print("=" * 80)
        
        for artifact in artifacts:
            print(f"\n🔍 Artifact ID: {artifact.artifact_id}")
            print(f"   类型: {artifact.artifact_type}")
            print(f"   版本: {artifact.version}")
            print(f"   创建时间: {artifact.created_at}")
            
            # 检查内容中是否包含图片相关标记
            content = artifact.content
            
            # 检查各种图片格式
            image_markers = {
                "Markdown 图片": "![",
                "HTML img 标签": "<img",
                "Base64 图片": "data:image",
                "外部图片链接": "http",
            }
            
            found_images = []
            for marker_name, marker in image_markers.items():
                if marker in content:
                    found_images.append(marker_name)
            
            if found_images:
                print(f"   ✅ 发现图片标记: {', '.join(found_images)}")
                
                # 显示图片相关内容的片段
                print(f"\n   📝 图片相关内容片段:")
                lines = content.split('\n')
                for i, line in enumerate(lines):
                    if any(marker in line for marker in image_markers.values()):
                        print(f"      第 {i+1} 行: {line[:100]}...")
            else:
                print(f"   ℹ️  未发现图片标记")
            
            # 显示内容长度
            print(f"   📏 内容长度: {len(content)} 字符")
            
            # 显示内容预览（前 500 字符）
            print(f"\n   📄 内容预览:")
            print(f"   {content[:500]}")
            if len(content) > 500:
                print(f"   ... (还有 {len(content) - 500} 字符)")
        
        print("\n" + "=" * 80)
        print("\n💡 当前后端图片处理逻辑:")
        print("   1. Gemini LLM 生成 Markdown 内容（可能包含图片）")
        print("   2. 后端直接存储 Markdown 内容，不做任何图片处理")
        print("   3. 前端接收 Markdown 内容并渲染")
        print("\n⚠️  如果企微无法显示图片，可能的原因:")
        print("   1. Gemini 生成的图片格式不被企微支持")
        print("   2. 图片是外部链接，企微无法访问")
        print("   3. 需要将图片转换为 base64 或企微支持的格式")
        print("\n📋 建议:")
        print("   1. 查看测试文件 'D:\\Programs\\meeting AI web test\\gen_test_html.py'")
        print("   2. 对比测试文件的图片处理逻辑")
        print("   3. 在后端添加图片格式转换逻辑（如果需要）")
        
    finally:
        session.close()


def main():
    """主函数"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python check_image_handling.py <task_id>")
        print("示例: python check_image_handling.py task_1c8f2c5d561048db")
        return
    
    task_id = sys.argv[1]
    check_artifact_images(task_id)


if __name__ == "__main__":
    main()
