# 热词集成指南

## 概述

本文档说明如何将全局热词集成到 ASR 转写流程中，以提升专业术语和人名的识别准确率。

## 架构

```
┌─────────────────────────────────────────────────────────────┐
│                      热词集成流程                              │
└─────────────────────────────────────────────────────────────┘

1. 上传热词到火山引擎
   ├── 读取 docs/external_api_docs/volcano_hotword_api.txt
   ├── 调用火山热词管理 API
   └── 获取 BoostingTableID

2. 配置全局热词
   ├── 将 BoostingTableID 添加到配置文件
   └── volcano.boosting_table_id: "xxx"

3. ASR 自动使用热词
   ├── VolcanoASR 读取配置中的 boosting_table_id
   ├── 在提交转写任务时传递热词 ID
   └── 火山引擎使用热词提升识别准确率
```

## 快速开始

### 1. 上传全局热词

运行以下命令将热词上传到火山引擎：

```bash
python scripts/upload_global_hotwords.py
```

脚本会：
- 读取 `docs/external_api_docs/volcano_hotword_api.txt` 中的热词
- 检查是否已存在名为 `global_hotwords` 的热词库
- 如果存在则更新，否则创建新的热词库
- 返回 `BoostingTableID`

输出示例：
```
============================================================
热词库上传成功！
============================================================
BoostingTableID: 1234567890abcdef
BoostingTableName: global_hotwords
WordCount: 45
WordSize: 450
CreateTime: 2026-01-15T10:30:00Z
UpdateTime: 2026-01-15T10:30:00Z
============================================================

请将以下配置添加到您的配置文件中:

volcano:
  boosting_table_id: "1234567890abcdef"

============================================================
```

### 2. 更新配置文件

将返回的 `BoostingTableID` 添加到配置文件中：

**开发环境** (`config/development.yaml`):
```yaml
volcano:
  access_key: ${VOLCANO_ACCESS_KEY}
  secret_key: ${VOLCANO_SECRET_KEY}
  app_id: ${VOLCANO_APP_ID}
  cluster_id: ${VOLCANO_CLUSTER_ID}
  tos_bucket: ${VOLCANO_TOS_BUCKET}
  tos_region: cn-beijing
  api_endpoint: https://openspeech.bytedance.com/api/v1/asr
  boosting_table_id: "1234567890abcdef"  # 添加这一行
  max_retries: 3
  timeout: 300
```

**生产环境** (`config/production.yaml`):
```yaml
volcano:
  # ... 其他配置 ...
  boosting_table_id: ${VOLCANO_BOOSTING_TABLE_ID}  # 从环境变量读取
```

或者设置环境变量：
```bash
export VOLCANO_BOOSTING_TABLE_ID="1234567890abcdef"
```

### 3. 验证集成

运行测试脚本验证热词集成：

```bash
python scripts/test_hotword_integration.py
```

脚本会：
- 检查配置中的 `boosting_table_id`
- 验证热词库是否存在
- 确认 ASR 配置正确

输出示例：
```
============================================================
测试热词集成
============================================================
✓ 配置中已设置 boosting_table_id: 1234567890abcdef

检查热词库...
✓ 热词库存在: global_hotwords
  - 热词数量: 45
  - 更新时间: 2026-01-15T10:30:00Z
  - 预览: Gradle, Figma, JSON, YAML, Git...

测试 ASR 配置...
✓ ASR 提供商已配置
  - 全局热词 ID: 1234567890abcdef
  - ASR 调用时将自动使用全局热词

============================================================
热词集成测试完成！
============================================================

说明:
- 全局热词已配置并可用
- 所有 ASR 转写任务将自动使用全局热词
- 如需更新热词，请重新运行 upload_global_hotwords.py
```

## 热词格式

热词文件格式（`docs/external_api_docs/volcano_hotword_api.txt`）：

```
词语|权重
Gradle|10
Figma|10
JSON|10
蓝为一|10
范玮雯|10
```

- 每行一个热词
- 格式：`词语|权重`
- 权重范围：1-10（10 为最高优先级）
- 支持中英文混合

## 热词优先级

系统支持两种热词：

1. **全局热词**（从配置读取）
   - 适用于所有转写任务
   - 包含常用专业术语和人名
   - 通过 `volcano.boosting_table_id` 配置

2. **用户自定义热词**（通过 API 创建）
   - 适用于特定任务
   - 通过热词管理 API 创建
   - 优先级高于全局热词

**优先级规则**：
```
用户自定义热词 > 全局热词
```

如果任务指定了用户自定义热词，则使用用户热词；否则使用全局热词。

## 更新热词

### 更新全局热词

1. 编辑 `docs/external_api_docs/volcano_hotword_api.txt`
2. 运行上传脚本：
   ```bash
   python scripts/upload_global_hotwords.py
   ```
3. 脚本会自动更新现有热词库（无需修改配置）

### 查看热词库

使用火山热词客户端查看热词库：

```python
from src.config.loader import get_config
from src.providers.volcano_hotword import VolcanoHotwordClient

config = get_config()
client = VolcanoHotwordClient(
    app_id=config.volcano.app_id,
    access_key=config.volcano.access_key,
    secret_key=config.volcano.secret_key,
)

# 列出所有热词库
tables = client.list_boosting_tables()
print(tables)

# 获取特定热词库详情
table = client.get_boosting_table(config.volcano.boosting_table_id)
print(table)
```

## 热词限制

根据火山引擎 API 限制：

- **单个热词库最大词数**：1000 个
- **单个词最大长度**：10 个字符（中文）/ 30 字节
- **热词库总数限制**：10 个
- **所有热词库总词数**：5000 个

## 故障排查

### 问题 1：配置中未设置 boosting_table_id

**症状**：
```
✗ 配置中未设置 boosting_table_id
```

**解决方案**：
1. 运行 `python scripts/upload_global_hotwords.py`
2. 将返回的 `BoostingTableID` 添加到配置文件

### 问题 2：热词库不存在

**症状**：
```
✗ 热词库不存在或无法访问
```

**解决方案**：
1. 检查 `boosting_table_id` 是否正确
2. 重新运行 `python scripts/upload_global_hotwords.py`
3. 更新配置文件中的 `boosting_table_id`

### 问题 3：热词未生效

**可能原因**：
1. 配置未正确设置
2. 热词格式不正确
3. 热词权重过低

**解决方案**：
1. 运行 `python scripts/test_hotword_integration.py` 验证配置
2. 检查热词文件格式
3. 提高热词权重（建议 8-10）

## API 参考

### 火山热词管理 API

详见：`docs/external_api_docs/volcano_hotword_management_api.txt`

主要接口：
- `CreateBoostingTable` - 创建热词库
- `UpdateBoostingTable` - 更新热词库
- `GetBoostingTable` - 获取热词库详情
- `ListBoostingTable` - 列出热词库
- `DeleteBoostingTable` - 删除热词库

### 热词客户端

详见：`src/providers/volcano_hotword.py`

```python
from src.providers.volcano_hotword import VolcanoHotwordClient

client = VolcanoHotwordClient(
    app_id="your_app_id",
    access_key="your_access_key",
    secret_key="your_secret_key",
)

# 创建热词库
result = client.create_boosting_table(
    name="my_hotwords",
    hotwords_content="词语1|10\n词语2|9\n",
)

# 更新热词库
result = client.update_boosting_table(
    boosting_table_id="xxx",
    hotwords_content="新词语|10\n",
)

# 获取热词库
table = client.get_boosting_table("xxx")

# 删除热词库
client.delete_boosting_table("xxx")
```

## 相关文档

- [火山热词管理 API 文档](external_api_docs/volcano_hotword_management_api.txt)
- [热词 API 测试指南](hotword_api_testing_guide.md)
- [火山 ASR V3 迁移文档](volcano_asr_v3_migration.md)

## 总结

热词集成流程：

1. ✅ 上传全局热词：`python scripts/upload_global_hotwords.py`
2. ✅ 配置 `boosting_table_id`
3. ✅ 验证集成：`python scripts/test_hotword_integration.py`
4. ✅ ASR 自动使用热词

完成后，所有转写任务将自动使用全局热词，提升专业术语和人名的识别准确率。
