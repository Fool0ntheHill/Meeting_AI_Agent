# Azure 语音服务配置说明

## 📋 配置信息

### 可用的密钥和地区

根据 `config/AzureSecretKey.csv`，有两个可用的配置：

| 地区 | Region Code | 订阅密钥 | 状态 |
|------|-------------|---------|------|
| **美国东部** | `eastus` | `5JNmdKpRY4CLnbIT8OCrfgvWDSLn5ppJkLAUNqeVZwEQLTlsoJltJQQJ99BLACYeBjFXJ3w3AAAYACOGtfnj` | ✅ **推荐使用** |
| **东亚** | `eastasia` | `D3ZM0cJKA7PiysigJnIpJoKigjsqpbIJ5eeEEA5f3OwsOE07aFbjJQQJ99BLAC3pKaRXJ3w3AAAYACOGPnhH` | ⚠️ 不支持说话人分离 |

---

## ⚠️ 重要说明

### 为什么使用 eastus 而不是 eastasia？

**原因**：`eastasia` 区域**不支持说话人分离（diarization）功能**

```python
# Azure转写器代码中的注释（第 36 行）
# 注意：eastasia区域不支持diarization
```

**说话人分离（Diarization）**：
- 识别"谁在什么时候说话"
- 将音频分段并标记说话人（Speaker 1, Speaker 2...）
- 这是会议转写的核心功能

**因此**：
- ✅ **使用 `eastus`** - 支持完整功能
- ❌ **不使用 `eastasia`** - 功能受限

---

## 🔧 当前配置

### 测试脚本配置（`test_scripts/azure_test.py`）

```python
AZURE_CONFIG = {
    "subscription_key": "5JNmdKpRY4CLnbIT8OCrfgvWDSLn5ppJkLAUNqeVZwEQLTlsoJltJQQJ99BLACYeBjFXJ3w3AAAYACOGtfnj",
    "region": "eastus",  # ✅ 使用 eastus
    "config": {
        "locales": ["zh-CN", "en-US"],  # 中英文混合
        "profanityFilterMode": "None",  # 不过滤脏词
        "diarization": {
            "enabled": True,  # ✅ 启用说话人分离
            "maxSpeakers": 10
        }
    }
}
```

---

## 📊 Azure 转写器功能

### 支持的功能

1. **本地文件直接上传** ✅
   - 无需先上传到云存储
   - 无需提供 URL

2. **文件限制**
   - 最大文件大小：300MB
   - 最大时长：2小时
   - 超过限制会自动切分

3. **说话人分离（Diarization）** ✅
   - 仅在 `eastus` 等特定区域可用
   - `eastasia` 不支持

4. **多语言支持** ✅
   - 中英文混合：`["zh-CN", "en-US"]`

5. **Fast Transcription API** ✅
   - API 版本：`2024-11-15`
   - 端点：`https://eastus.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe`

---

## 🚀 使用方法

### 1. 运行测试

```bash
# 运行 Azure 测试
python test_scripts/azure_test.py
```

### 2. 批量测试

```bash
# 批量测试多个文件
python test_scripts/azure_batch_test.py
```

### 3. 在代码中使用

```python
from transcribers.azure_transcriber import AzureTranscriber

# 创建转写器
transcriber = AzureTranscriber(
    subscription_key="5JNmdKpRY4CLnbIT8OCrfgvWDSLn5ppJkLAUNqeVZwEQLTlsoJltJQQJ99BLACYeBjFXJ3w3AAAYACOGtfnj",
    region="eastus",
    config={
        "locales": ["zh-CN", "en-US"],
        "diarization": {
            "enabled": True,
            "maxSpeakers": 10
        }
    }
)

# 转写单个文件
result = transcriber.test_single_file(
    audio_path="test.ogg",
    ground_truth_path="test-transcript.txt"
)
```

---

## 🔍 验证配置

### 检查密钥是否有效

```python
import requests

subscription_key = "5JNmdKpRY4CLnbIT8OCrfgvWDSLn5ppJkLAUNqeVZwEQLTlsoJltJQQJ99BLACYeBjFXJ3w3AAAYACOGtfnj"
region = "eastus"
endpoint = f"https://{region}.api.cognitive.microsoft.com/speechtotext/transcriptions:transcribe?api-version=2024-11-15"

headers = {
    "Ocp-Apim-Subscription-Key": subscription_key,
    "Content-Type": "application/json"
}

# 发送测试请求
response = requests.post(endpoint, headers=headers, json={})
print(f"状态码: {response.status_code}")
print(f"响应: {response.text}")
```

---

## 📝 配置文件位置

| 文件 | 路径 | 说明 |
|------|------|------|
| 密钥配置 | `config/AzureSecretKey.csv` | 存储密钥和地区 |
| 转写器实现 | `transcribers/azure_transcriber.py` | Azure 转写器类 |
| 测试脚本 | `test_scripts/azure_test.py` | 单次测试 |
| 批量测试 | `test_scripts/azure_batch_test.py` | 批量测试 |

---

## ⚡ 性能指标

根据之前的测试结果：

| 指标 | 值 | 评级 |
|------|-----|------|
| **时间戳精度** | 848ms | 良好 🥉 |
| **CER（字错误率）** | 待测试 | - |
| **DER（说话人错误率）** | 待测试 | - |
| **RTF（实时因子）** | 待测试 | - |

**排名**：
1. 🥇 Volcano: 348ms
2. 🥈 iFly: 801ms
3. 🥉 **Azure: 848ms**
4. Tencent: 1186ms
5. Google: 4010ms

---

## 🔐 安全提醒

⚠️ **注意**：
- 密钥是敏感信息，不要提交到公开仓库
- `config/AzureSecretKey.csv` 应该在 `.gitignore` 中
- 定期轮换密钥以提高安全性

---

## 📞 获取新密钥

如果需要新的密钥：

1. 访问 [Azure 门户](https://portal.azure.com)
2. 创建或选择"语音服务"资源
3. 在"密钥和终结点"页面查看：
   - 密钥 1 / 密钥 2
   - 区域
   - 终结点

---

## ✅ 总结

### 当前配置状态

- ✅ **Azure 转写器可用**
- ✅ **使用 eastus 地区**（支持说话人分离）
- ✅ **密钥已配置**
- ✅ **支持本地文件上传**
- ✅ **支持中英文混合**
- ✅ **支持说话人分离**

### 推荐使用场景

- ✅ 需要说话人分离的会议转写
- ✅ 中英文混合音频
- ✅ 文件大小 < 300MB
- ✅ 时长 < 2小时

---

**配置确认时间**: 2025-01-12  
**当前使用地区**: eastus  
**说话人分离**: 已启用  
**配置状态**: ✅ 可用
