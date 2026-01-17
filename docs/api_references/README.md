# API 参考文档

本目录包含 Meeting Minutes Agent API 的完整参考文档。

## 文档列表

### 1. OpenAPI 规范

- **[openapi.yaml](./openapi.yaml)** - OpenAPI 3.1.0 规范文件 (YAML 格式)
- **[openapi.json](./openapi.json)** - OpenAPI 3.1.0 规范文件 (JSON 格式)

这些文件包含所有 API 端点的完整定义,包括:
- 请求/响应格式
- 数据模型 Schema
- 参数说明
- 错误码定义

**使用方式**:
- 导入到 Swagger Editor: https://editor.swagger.io/
- 导入到 Postman 生成集合
- 用于代码生成工具 (如 OpenAPI Generator)

### 2. API 使用指南

- **[API_USAGE_GUIDE.md](./API_USAGE_GUIDE.md)** - 完整的 API 使用指南

包含内容:
- 快速开始教程
- 认证方式说明
- 核心流程图解
- 所有端点详细说明
- 错误处理指南
- 常见场景示例代码
- 最佳实践建议

### 3. Postman 集合

- **[postman_collection.json](./postman_collection.json)** - Postman 集合文件

包含所有 API 端点的示例请求,可直接导入 Postman 使用。

**导入步骤**:
1. 打开 Postman
2. 点击 Import 按钮
3. 选择 `postman_collection.json` 文件
4. 配置环境变量:
   - `base_url`: `http://localhost:8000/api/v1`
   - `api_key`: `test-api-key`

## 在线文档

启动 API 服务器后,可以访问以下在线文档:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **OpenAPI JSON**: http://localhost:8000/openapi.json

## 生成文档

如需重新生成 OpenAPI 规范文件:

```bash
python scripts/generate_openapi.py
```

这将生成:
- `docs/api_references/openapi.json`
- `docs/api_references/openapi.yaml`

## 相关文档

- [快速测试指南](../testing/快速测试指南.md)
- [数据库设计](../database_design_improvements.md)
- [任务确认 API](../task_confirmation_api.md)
- [热词 API 测试指南](../hotword_api_testing_guide.md)

## 更新日志

- **2026-01-14**: 初始版本,包含所有 Phase 1 API 端点
- API 版本: 1.0.0
- 文档版本: 1.0.0
