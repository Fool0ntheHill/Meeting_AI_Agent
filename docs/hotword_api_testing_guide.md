# 热词管理 API 测试指南

## 概述

本指南介绍如何测试热词管理 API 功能,包括客户端单元测试和完整的 API 集成测试。

## 前置条件

### 1. 环境准备

```bash
# 确保虚拟环境已激活
.\venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置检查

确认 `config/test.yaml` 包含火山引擎凭证:

```yaml
volcano:
  access_key: "your_access_key"
  secret_key: "your_secret_key"
  app_id: "your_app_id"
```

### 3. 数据库准备

```bash
# 删除旧数据库(应用 schema 变更)
rm meeting_agent.db test_meeting_agent.db
```

## 测试步骤

### 阶段 1: 客户端单元测试

测试火山引擎热词客户端的基本功能,不调用实际 API。

```bash
python scripts/test_volcano_hotword_client.py
```

**测试内容**:
- ✅ 客户端初始化
- ✅ HMAC-SHA256 签名生成
- ✅ 请求头生成
- ✅ API 方法结构验证

**预期输出**:
```
============================================================
火山引擎热词客户端测试
============================================================
✅ 客户端初始化成功
✅ SHA256 哈希生成成功
✅ HMAC-SHA256 签名生成成功
✅ 请求头生成成功
✅ 所有方法存在
============================================================
✅ 所有测试通过
============================================================
```

### 阶段 2: 启动 API 服务器

在一个终端窗口启动服务器:

```bash
python main.py
```

**预期输出**:
```
INFO:     Uvicorn running on http://0.0.0.0:8000
INFO:     Application startup complete.
```

**验证服务器**:
- 访问 http://localhost:8000/docs 查看 API 文档
- 检查 `/api/v1/hotword-sets` 端点是否存在

### 阶段 3: API 集成测试

在另一个终端窗口运行集成测试:

```bash
python scripts/test_hotwords_api.py
```

**⚠️ 重要提示**:
- 此测试会调用实际的火山引擎 API
- 可能产生少量费用(创建/删除热词库)
- 测试完成后会自动清理创建的资源

**测试流程**:

1. **创建全局热词集**
   - 上传 `test_data/hotwords_medical.txt`
   - 调用火山 API 创建热词库
   - 保存到数据库

2. **创建租户热词集**
   - 上传 `test_data/hotwords_tech.txt`
   - 指定租户作用域

3. **列出热词集**
   - 查询所有热词集
   - 验证返回数据

4. **获取热词集详情**
   - 不含预览
   - 含预览(从火山 API 获取)

5. **更新热词集**
   - 更新名称和描述
   - 更新热词文件

6. **删除热词集**
   - 删除火山热词库
   - 删除数据库记录
   - 验证删除成功

**预期输出**:
```
============================================================
热词管理 API 测试
============================================================
✅ 热词集创建成功
✅ 查询到 2 个热词集
✅ 热词集详情获取成功
✅ 热词集已更新
✅ 热词集已删除
============================================================
✅ 所有测试完成
============================================================
```

## 测试数据

### 医疗术语热词 (`test_data/hotwords_medical.txt`)

```
心电图|10
血压|10
糖尿病|10
高血压|10
...
```

### 技术术语热词 (`test_data/hotwords_tech.txt`)

```
人工智能|10
机器学习|10
深度学习|10
神经网络|10
...
```

**格式说明**:
- 每行一个热词
- 格式: `词语|权重`
- 权重范围: 1-10
- 文件大小: < 8MB
- 编码: UTF-8

## 手动测试

### 使用 curl

#### 1. 创建热词集

```bash
curl -X POST http://localhost:8000/api/v1/hotword-sets \
  -H "Authorization: Bearer test_api_key_12345" \
  -F "name=测试热词库" \
  -F "scope=global" \
  -F "asr_language=zh-CN" \
  -F "description=测试用热词库" \
  -F "hotwords_file=@test_data/hotwords_medical.txt"
```

#### 2. 列出热词集

```bash
curl -X GET http://localhost:8000/api/v1/hotword-sets \
  -H "Authorization: Bearer test_api_key_12345"
```

#### 3. 获取热词集详情

```bash
curl -X GET "http://localhost:8000/api/v1/hotword-sets/{hotword_set_id}?include_preview=true" \
  -H "Authorization: Bearer test_api_key_12345"
```

#### 4. 更新热词集

```bash
curl -X PUT http://localhost:8000/api/v1/hotword-sets/{hotword_set_id} \
  -H "Authorization: Bearer test_api_key_12345" \
  -F "name=更新后的名称" \
  -F "description=更新后的描述"
```

#### 5. 删除热词集

```bash
curl -X DELETE http://localhost:8000/api/v1/hotword-sets/{hotword_set_id} \
  -H "Authorization: Bearer test_api_key_12345"
```

### 使用 Swagger UI

1. 访问 http://localhost:8000/docs
2. 点击 "Authorize" 按钮
3. 输入: `Bearer test_api_key_12345`
4. 测试各个端点

## 常见问题

### 1. 配置文件不存在

**错误**: `MissingConfigError: 配置文件不存在: config\development.yaml`

**解决**:
```bash
# 确保使用测试环境
export APP_ENV=test  # Linux/Mac
set APP_ENV=test     # Windows CMD
$env:APP_ENV="test"  # Windows PowerShell
```

### 2. 数据库 schema 错误

**错误**: `no such column: hotword_sets.word_count`

**解决**:
```bash
# 删除旧数据库
rm meeting_agent.db test_meeting_agent.db

# 重启服务器(会自动创建新数据库)
python main.py
```

### 3. 火山 API 认证失败

**错误**: `创建热词库失败: 认证失败`

**可能原因**:
1. Access Key 或 Secret Key 错误
2. App ID 错误
3. Multipart 签名问题

**解决**:
1. 检查 `config/test.yaml` 中的凭证
2. 确认凭证有热词管理权限
3. 如果是签名问题,考虑使用火山官方 SDK

### 4. 无法连接到 API 服务器

**错误**: `ConnectionError: 无法连接到 API 服务器`

**解决**:
```bash
# 确保服务器已启动
python main.py

# 检查端口是否被占用
netstat -ano | findstr :8000  # Windows
lsof -i :8000                 # Linux/Mac
```

## 调试技巧

### 1. 查看详细日志

```bash
# 设置日志级别为 DEBUG
# 在 config/test.yaml 中:
log:
  level: DEBUG
```

### 2. 检查数据库内容

```bash
# 使用 SQLite 客户端
sqlite3 test_meeting_agent.db

# 查询热词集
SELECT * FROM hotword_sets;

# 退出
.quit
```

### 3. 测试单个端点

修改 `scripts/test_hotwords_api.py`,注释掉不需要的测试:

```python
def main():
    # test_create_hotword_set()
    # test_list_hotword_sets()
    test_get_hotword_set("hs_xxx")  # 只测试这个
    # test_update_hotword_set("hs_xxx")
    # test_delete_hotword_set("hs_xxx")
```

## 性能测试

### 并发创建测试

```python
import concurrent.futures

def create_hotword_set(index):
    # 创建热词集
    ...

with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
    futures = [executor.submit(create_hotword_set, i) for i in range(100)]
    results = [f.result() for f in futures]
```

### 大文件测试

创建包含大量热词的文件:

```python
# 生成 10000 个热词
with open("test_data/hotwords_large.txt", "w", encoding="utf-8") as f:
    for i in range(10000):
        f.write(f"热词{i}|10\n")
```

## 下一步

测试通过后:

1. ✅ 验证火山 API 集成正确
2. ✅ 确认数据库记录正确
3. ⏳ 继续 Task 21(如果有)
4. ⏳ 集成热词到 ASR 转写流程

## 参考文档

- [火山引擎热词管理 API 文档](../api%20docs/火山热词管理API.txt)
- [Task 20 完成总结](../TASK_20_COMPLETION_SUMMARY.md)
- [API 实现总结](../API_IMPLEMENTATION_SUMMARY.md)
