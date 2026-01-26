# 企业微信图片显示问题分析总结

## 问题

用户报告：复制会议纪要到企业微信后，图片展示不出来。

## 调查结果

### 当前后端图片处理逻辑

通过代码审查发现：**当前后端没有任何图片处理逻辑**

1. **Gemini LLM** (`src/providers/gemini_llm.py`)
   - 生成 Markdown 格式内容
   - 如果包含图片，直接使用 Gemini 返回的格式
   - 不做任何转换

2. **Markdown 转换器** (`src/utils/markdown_converter.py`)
   - 只处理文本格式转换（JSON → Markdown）
   - **不处理图片**

3. **Artifact 生成服务** (`src/services/artifact_generation.py`)
   - 直接存储 LLM 返回的内容
   - **不做任何图片处理**

### 数据流

```
Gemini → Markdown (可能含图片) → 数据库 → 前端 → 企微 ❌
```

## 可能的原因

1. **图片格式不兼容**
   - 企微可能不支持 Markdown 图片语法 `![](url)`
   - 企微可能不支持外部 URL 链接
   - 需要 base64 内联图片或企微图片 API

2. **图片来源问题**
   - Gemini 生成的可能是外部链接
   - 企微无法访问外部链接
   - 链接可能已过期

3. **复制粘贴限制**
   - 企微文档的复制粘贴功能可能有限制
   - 不支持某些 HTML 或 Markdown 格式

## 对比测试文件

用户提到的测试文件：`D:\Programs\meeting AI web test\gen_test_html.py`

**需要查看该文件的图片处理逻辑**，可能包含：
- 图片格式转换（URL → base64）
- 图片标签替换（Markdown → HTML）
- 企微 API 调用

## 解决方案

### 方案 1: 添加图片格式转换（推荐）

在 `src/utils/markdown_converter.py` 中添加：
- 检测 Markdown 图片语法
- 下载外部图片
- 转换为 base64 内联格式
- 替换原始图片标签

### 方案 2: 使用企微图片消息 API

在发送通知时：
- 提取图片
- 文本和图片分开发送
- 使用 `/msg/send_wecom_image` API

### 方案 3: 禁止 Gemini 生成图片

在 System Instruction 中：
- 明确要求不生成图片
- 使用表格或列表代替图表

## 已创建的工具

### 1. 诊断脚本

**文件**: `scripts/check_image_handling.py`

**功能**:
- 检查指定任务的 artifact 是否包含图片
- 分析图片格式（Markdown、HTML、base64 等）
- 显示图片相关内容片段

**使用**:
```bash
python scripts/check_image_handling.py task_1c8f2c5d561048db
```

### 2. 文档

**文件**: `docs/IMAGE_HANDLING_WECOM.md`

**内容**:
- 详细的问题分析
- 当前后端逻辑说明
- 可能的原因分析
- 三种解决方案
- 诊断步骤
- 代码示例

## 下一步行动

1. **运行诊断脚本**
   ```bash
   python scripts/check_image_handling.py <task_id>
   ```

2. **查看测试文件**
   - 用户需要提供测试文件内容
   - 或者描述测试文件的图片处理逻辑

3. **选择并实现解决方案**
   - 根据测试文件的逻辑
   - 选择最合适的方案
   - 在后端实现图片处理

4. **测试验证**
   - 生成包含图片的 artifact
   - 复制到企微
   - 验证图片是否正常显示

## 相关文件

- ✅ `scripts/check_image_handling.py` - 诊断脚本（新建）
- ✅ `docs/IMAGE_HANDLING_WECOM.md` - 详细文档（新建）
- 📝 `src/utils/markdown_converter.py` - 需要添加图片处理
- 📝 `src/providers/gemini_llm.py` - 可能需要调整
- 📝 `scripts/test_wecom_notification.py` - 可能需要扩展

## 总结

当前后端**没有图片处理逻辑**，直接存储和返回 Gemini 生成的 Markdown 内容。如果企微无法显示图片，需要：

1. 先诊断确认 artifact 中是否包含图片
2. 查看测试文件的处理逻辑
3. 在后端添加图片格式转换
4. 或者在发送企微通知时单独处理图片

**等待用户提供测试文件内容或描述其图片处理逻辑，以便实现相同的处理方式。**
