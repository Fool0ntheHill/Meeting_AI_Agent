#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成 OpenAPI 规范文件 (YAML 格式)"""

import json
import sys
import yaml
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.api.app import create_app

# 创建应用实例
app = create_app()


def generate_openapi_yaml():
    """生成 OpenAPI YAML 文件"""
    # 获取 OpenAPI schema
    openapi_schema = app.openapi()
    
    # 输出路径
    output_dir = Path("docs/api_references")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # 保存为 JSON
    json_path = output_dir / "openapi.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(openapi_schema, f, indent=2, ensure_ascii=False)
    print(f"✅ Generated: {json_path}")
    
    # 保存为 YAML
    yaml_path = output_dir / "openapi.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(openapi_schema, f, allow_unicode=True, sort_keys=False, default_flow_style=False)
    print(f"✅ Generated: {yaml_path}")
    
    # 统计信息
    paths_count = len(openapi_schema.get("paths", {}))
    schemas_count = len(openapi_schema.get("components", {}).get("schemas", {}))
    
    print(f"\n📊 API Statistics:")
    print(f"  - Total Endpoints: {paths_count}")
    print(f"  - Total Schemas: {schemas_count}")
    print(f"  - API Version: {openapi_schema['info']['version']}")
    
    return openapi_schema


if __name__ == "__main__":
    print("🚀 Generating OpenAPI specification...\n")
    generate_openapi_yaml()
    print("\n✨ Done!")
