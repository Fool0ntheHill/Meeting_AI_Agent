# 火山引擎 Access Key 配置指南

## 问题描述

在测试热词管理 API 时遇到以下错误：

```
InvalidAccessKey: The security token[SrfaymE6iu2XSOEAg_C-6vc5PynqTbkT] included in the request is invalid.
```

这说明当前的 Access Key 无法访问热词管理 API。

## 原因分析

1. **权限不足**: 当前 Access Key 可能只有 ASR 转写权限，没有热词管理权限
2. **Key 过期**: Access Key 可能已过期或被撤销
3. **服务未开通**: 热词管理服务可能需要单独开通

## 解决方案

### 方案 1: 检查现有 Access Key 权限

1. 登录火山引擎控制台
   - 访问: https://console.volcengine.com/iam/keymanage/

2. 找到当前使用的 Access Key
   - Access Key: `SrfaymE6iu2XSOEAg_C-6vc5PynqTbkT`

3. 检查权限
   - 查看该 Key 是否有 "语音识别" 或 "热词管理" 相关权限
   - 确认是否有 "Boosting Table" 相关的 API 权限

4. 如果权限不足
   - 编辑 Access Key，添加热词管理权限
   - 或者创建新的 Access Key（见方案 2）

### 方案 2: 创建新的 Access Key

1. 在火山引擎控制台创建新的 Access Key
   - 访问: https://console.volcengine.com/iam/keymanage/
   - 点击 "创建访问密钥"

2. 配置权限
   - 确保勾选以下权限:
     - ✅ 语音识别 (ASR)
     - ✅ 热词管理 (Boosting Table)
     - ✅ 对象存储 (TOS) - 如果需要

3. 保存 Access Key 和 Secret Key
   - **重要**: 立即保存 Secret Key，关闭后无法再次查看

4. 更新配置文件
   - 编辑 `config/test.yaml`
   - 更新 `volcano.access_key` 和 `volcano.secret_key`

```yaml
volcano:
  access_key: "YOUR_NEW_ACCESS_KEY"
  secret_key: "YOUR_NEW_SECRET_KEY"
  app_id: "6543693041"
  # ... 其他配置
```

### 方案 3: 联系技术支持

如果以上方案都无法解决问题：

1. 联系火山引擎技术支持
   - 说明需要使用热词管理 API
   - 提供 App ID: `6543693041`
   - 询问如何开通热词管理权限

2. 确认服务状态
   - 确认热词管理服务是否已开通
   - 确认 App ID 是否有权限使用该服务

## 验证步骤

更新 Access Key 后，按以下步骤验证：

### 1. 测试列出热词库（只读操作）

```bash
python scripts/test_volcano_api_direct.py
```

如果成功，应该看到：
```
✅ 列出热词库成功:
   热词库数量: 0
   (当前没有热词库)
```

### 2. 测试创建热词库（写操作）

继续运行测试脚本，按 Enter 测试创建：

如果成功，应该看到：
```
✅ 创建热词库成功:
   BoostingTableID: xxx
   词数: 3
   字符数: xxx
```

### 3. 运行完整 API 测试

```bash
# 启动 API 服务器
$env:APP_ENV="test"; python main.py

# 在另一个终端运行测试
python scripts/test_hotwords_api.py
```

如果成功，应该看到：
```
✅ 热词集创建成功
✅ 查询到 2 个热词集
✅ 热词集详情获取成功
✅ 热词集已更新
✅ 热词集已删除
✅ 所有测试完成
```

## 常见问题

### Q1: 为什么 ASR 可以用，但热词管理不行？

A: 火山引擎的不同服务可能需要不同的权限。ASR 转写和热词管理是两个独立的服务，需要分别授权。

### Q2: 如何确认 Access Key 有哪些权限？

A: 在火山引擎控制台的 IAM 管理页面，可以查看每个 Access Key 的详细权限列表。

### Q3: 创建新 Access Key 会影响现有功能吗？

A: 不会。可以同时拥有多个 Access Key，每个用于不同的服务。建议为不同环境（开发/测试/生产）使用不同的 Key。

### Q4: 热词管理 API 是否收费？

A: 具体收费标准请参考火山引擎官方文档或联系销售。通常热词库的创建和管理本身不收费，但使用热词库进行 ASR 转写可能会有额外费用。

## 参考文档

- [火山引擎 IAM 密钥管理](https://console.volcengine.com/iam/keymanage/)
- [火山引擎语音识别文档](https://www.volcengine.com/docs/6369/67268)
- [热词管理 API 文档](../api%20docs/火山热词管理API.txt)

## 下一步

Access Key 配置完成后：

1. ✅ 运行测试验证功能
2. ✅ 继续 Task 21（如果有）
3. ✅ 将热词管理集成到主流程
