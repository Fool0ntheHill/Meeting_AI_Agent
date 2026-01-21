# Gemini 模型配置说明

## 当前使用的模型

**模型名称**: `gemini-3-pro-preview`

**配置位置**: `config/development.yaml`

```yaml
gemini:
  api_keys:
    - AIzaSyBVdYD5kXLV2aOC3LNJ9Oj_CP6v7S9XqI4
  model: gemini-3-pro-preview  # ← 当前使用的模型
  max_tokens: 60000
  temperature: 0.7
  max_retries: 3
  timeout: 300
```

## 模型对比

| 模型 | 特点 | 适用场景 |
|------|------|---------|
| `gemini-3-pro-preview` | 最新预览版，性能强大 | **当前使用** - 会议纪要生成 |
| `gemini-2.0-flash-exp` | 实验版，速度快 | 快速原型开发 |
| `gemini-1.5-pro` | 稳定版，长上下文 | 生产环境 |
| `gemini-1.5-flash` | 轻量版，成本低 | 简单任务 |

## 为什么选择 gemini-3-pro-preview？

1. **最新功能**: 支持最新的 System Instruction 和结构化输出
2. **长上下文**: 支持 60000 tokens，适合长会议转写
3. **高质量**: 生成的会议纪要质量更高
4. **预览版**: 可以提前体验最新功能

## 如何更改模型？

### 方法 1: 修改配置文件

编辑 `config/development.yaml`:

```yaml
gemini:
  model: gemini-1.5-pro  # 改为其他模型
```

### 方法 2: 环境变量

```bash
export GEMINI_MODEL=gemini-1.5-pro
```

### 方法 3: 代码中指定

```python
from src.config.models import GeminiConfig

config = GeminiConfig(
    api_keys=["your-api-key"],
    model="gemini-1.5-pro",  # 指定模型
    max_tokens=8192,
    temperature=0.7
)
```

## 验证当前模型

```bash
python -c "from src.config.loader import get_config; config = get_config(); print(f'当前使用的 Gemini 模型: {config.gemini.model}')"
```

输出：
```
当前使用的 Gemini 模型: gemini-3-pro-preview
```

## 注意事项

### API 兼容性

不同模型的 API 可能有细微差异：

- ✅ `gemini-3-pro-preview`: 完全支持 System Instruction
- ✅ `gemini-2.0-flash-exp`: 支持 System Instruction
- ⚠️ `gemini-1.5-pro`: 支持 System Instruction（需要最新 SDK）
- ⚠️ `gemini-1.5-flash`: 支持 System Instruction（需要最新 SDK）

### Token 限制

不同模型的 token 限制不同：

| 模型 | 输入 Token | 输出 Token |
|------|-----------|-----------|
| `gemini-3-pro-preview` | 1,000,000+ | 60,000 |
| `gemini-2.0-flash-exp` | 1,000,000+ | 8,192 |
| `gemini-1.5-pro` | 2,000,000 | 8,192 |
| `gemini-1.5-flash` | 1,000,000 | 8,192 |

### 价格差异

不同模型的价格不同（参考配置）：

```yaml
pricing:
  gemini_flash_per_token: 0.00002  # Flash 系列
  gemini_pro_per_token: 0.00005    # Pro 系列
```

## 文档中的示例

**注意**: 文档中的某些示例可能使用了 `gemini-2.0-flash-exp` 作为示例，但实际运行时会使用配置文件中指定的模型（`gemini-3-pro-preview`）。

这是正常的，因为：
1. 示例代码只是演示 API 调用方式
2. 实际模型名称从配置文件读取
3. 不影响功能实现

## 相关文档

- [配置文件说明](../config/development.yaml)
- [Gemini SDK 升级](./summaries/GEMINI_SDK_UPGRADE_FINAL.md)
- [System Instruction 说明](./SYSTEM_INSTRUCTION_QUICK_REF.md)

## 总结

✅ 当前使用: `gemini-3-pro-preview`  
✅ 配置位置: `config/development.yaml`  
✅ 支持功能: System Instruction + 结构化输出  
✅ Token 限制: 60,000 输出 tokens  
✅ 文档示例: 可能显示其他模型名称（仅作示例）  
