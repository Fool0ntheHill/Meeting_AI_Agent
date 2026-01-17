# 火山引擎 ASR V3 API 迁移说明

## 问题描述

原实现使用火山引擎 ASR V1 API,导致 403 Forbidden 认证错误。经过诊断发现需要迁移到 V3 API (bigmodel 大模型版本)。

## 解决方案

### 1. API 端点更新

**V1 API (旧版,已废弃)**:
```
Submit: https://openspeech.bytedance.com/api/v1/auc/submit
Query:  https://openspeech.bytedance.com/api/v1/auc/query
```

**V3 API (新版,大模型)**:
```
Submit: https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/submit
Query:  https://openspeech-direct.zijieapi.com/api/v3/auc/bigmodel/query
Resource ID: volc.bigasr.auc
```

### 2. 认证方式更新

**V1 API 认证 (不再有效)**:
```python
headers = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer; {access_key}",
}

request_body = {
    "app": {
        "appid": app_id,
        "token": access_key,
        "cluster": cluster_id,
    },
    ...
}
```

**V3 API 认证 (正确方式)**:
```python
headers = {
    "X-Api-App-Key": app_id,
    "X-Api-Access-Key": access_key,
    "X-Api-Resource-Id": "volc.bigasr.auc",
    "X-Api-Request-Id": task_id,
    "X-Api-Sequence": "-1",
}

request_body = {
    "user": {"uid": "user_id"},
    "audio": {"url": audio_url},
    "request": {
        "model_name": "bigmodel",
        "enable_speaker_info": True,
        ...
    },
}
```

### 3. 请求体结构更新

**V1 API 请求体**:
```json
{
  "app": {
    "appid": "xxx",
    "token": "xxx",
    "cluster": "xxx"
  },
  "user": {"uid": "xxx"},
  "audio": {"url": "xxx", "format": "xxx"},
  "additions": {
    "use_itn": "True",
    "use_punc": "True",
    "with_speaker_info": "True",
    "language": ""
  }
}
```

**V3 API 请求体**:
```json
{
  "user": {"uid": "xxx"},
  "audio": {"url": "xxx", "format": "xxx"},
  "request": {
    "model_name": "bigmodel",
    "enable_channel_split": false,
    "enable_ddc": true,
    "enable_speaker_info": true,
    "enable_punc": true,
    "enable_itn": true,
    "language": "",
    "corpus": {
      "correct_table_name": "",
      "context": ""
    }
  }
}
```

### 4. 响应格式更新

**V1 API 响应**:
- 状态码在 JSON body 的 `resp.code` 字段
- 结果在 JSON body 的 `resp` 字段

**V3 API 响应**:
- 状态码在 HTTP Header 的 `X-Api-Status-Code` 字段
- 消息在 HTTP Header 的 `X-Api-Message` 字段
- 结果在 JSON body 的 `result` 字段
- 需要保存 `X-Tt-Logid` 用于后续查询

### 5. 状态码映射

**V1 API 状态码**:
- `1000`: 成功
- `1002`: 认证失败
- `1003`: 超频
- `2000/2001`: 处理中/排队中

**V3 API 状态码**:
- `20000000`: 成功
- `20000001`: 处理中
- `20000002`: 排队中
- `4xxxxxxx`: 客户端错误
- `5xxxxxxx`: 服务器错误

### 6. TOS 存储集成

为了让火山引擎 ASR 能够访问私有 TOS 存储桶中的音频文件,实现了完整的 TOS SDK 集成:

**实现的功能**:
- 真实的文件上传 (使用 TOS SDK)
- 预签名 URL 生成 (24小时有效期)
- 文件下载和删除
- 异步操作支持

**关键代码**:
```python
# 初始化 TOS 客户端
self.client = tos.TosClientV2(
    ak=access_key,
    sk=secret_key,
    endpoint=f"tos-{region}.volces.com",
    region=region,
)

# 生成预签名 URL
result = self.client.pre_signed_url(
    http_method=tos.HttpMethodType.Http_Method_Get,
    bucket=self.bucket,
    key=object_key,
    expires=86400,  # 24小时
)
presigned_url = result.signed_url
```

## 修改的文件

1. **src/providers/volcano_asr.py**
   - 更新 API 端点为 V3
   - 更新认证方式为 X-Api-* headers
   - 更新请求体结构
   - 更新响应解析逻辑
   - `_submit_task()` 返回 `(task_id, x_tt_logid)` 元组
   - `_poll_result()` 接受 `x_tt_logid` 参数
   - `get_task_status()` 接受 `x_tt_logid` 参数

2. **src/utils/storage.py**
   - 实现真实的 TOS SDK 集成
   - 实现 `upload_file()` 方法
   - 实现 `download_file()` 方法
   - 实现 `delete_file()` 方法
   - 实现 `generate_presigned_url()` 方法
   - 所有操作使用 `asyncio.run_in_executor()` 实现异步

3. **scripts/diagnose.py**
   - 更新诊断信息显示 V3 API 端点
   - 更新认证信息显示
   - 添加预签名 URL 生成步骤
   - 使用预签名 URL 进行 ASR 测试

## 测试结果

运行诊断脚本验证:
```bash
python scripts/diagnose.py --audio "test_data/20251229ONE产品和业务规则中心的设计讨论会议.ogg" --config config/test.yaml
```

**测试结果**:
- ✅ TOS 上传成功
- ✅ 预签名 URL 生成成功
- ✅ 火山引擎 ASR V3 API 认证成功
- ✅ ASR 转写成功 (126个分段, 479秒音频)
- ✅ 说话人分离正常
- ✅ 文本识别准确

## 配置要求

不需要修改配置文件,V3 API 使用相同的配置参数:
- `access_key`: Access Key (用于 X-Api-Access-Key header)
- `app_id`: 应用 ID (用于 X-Api-App-Key header)
- `tos_bucket`: TOS 存储桶名称
- `tos_region`: TOS 区域

**注意**: `cluster_id` 在 V3 API 中不再使用,但保留在配置中以保持向后兼容。

## 参考资料

- 火山引擎 ASR V3 API 文档
- 参考实现: `AI参考文件夹/1_ASR转写/volcano_transcriber_v3.py`
- TOS SDK 文档: https://www.volcengine.com/docs/6349/74822

## 迁移日期

2026-01-14
