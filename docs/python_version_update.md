# Python 版本更新说明

## 问题背景

在测试过程中发现 pyhub 库不支持 Python 3.14,导致音频处理时出现二进制数据输出问题。

## 解决方案

### 1. 更新 Python 版本要求

已将项目的 Python 版本要求从 `>=3.11` 更新为 `>=3.12,<3.14`,确保使用 Python 3.12 版本。

**修改的文件**: `pyproject.toml`

**具体更改**:
- `requires-python`: `>=3.11` → `>=3.12,<3.14`
- `tool.black.target-version`: `py311` → `py312`
- `tool.ruff.target-version`: `py311` → `py312`
- `tool.mypy.python_version`: `3.11` → `3.12`

### 2. 创建限制输出长度的测试脚本

为了避免音频二进制数据输出问题,创建了新的测试脚本 `scripts/test_e2e_limited.py`,该脚本会:

**主要特性**:
- 自动截断过长的字符串输出 (默认 100-500 字符)
- 将字节数据转换为可读的长度信息,而不是输出原始二进制
- 限制异常堆栈输出长度 (1000-2000 字符)
- 限制会议纪要内容显示 (最多显示 5 个关键要点和行动项)

**核心函数**:
- `truncate_string()`: 截断字符串到指定长度
- `truncate_bytes()`: 将字节数据转换为可读格式
- `safe_repr()`: 安全地表示对象,递归处理字典和列表

## 使用方法

### 1. 确保使用 Python 3.12

```bash
# 检查 Python 版本
python --version

# 应该显示 Python 3.12.x
```

### 2. 运行限制输出的测试脚本

```bash
# 基本测试
python scripts/test_e2e_limited.py --audio test_data/meeting.wav

# 跳过说话人识别
python scripts/test_e2e_limited.py --audio test_data/meeting.wav --skip-speaker-recognition

# 测试多个音频文件
python scripts/test_e2e_limited.py --audio part1.wav part2.wav --file-order 0 1

# 指定配置文件
python scripts/test_e2e_limited.py --audio meeting.wav --config config/test.yaml
```

## 预期效果

使用 Python 3.12 和限制输出的测试脚本后:
- ✅ 不再出现音频二进制数据输出问题
- ✅ 测试输出更加清晰易读
- ✅ pyhub 库正常工作
- ✅ 所有音频处理功能正常

## 注意事项

1. **必须使用 Python 3.12**: 不要使用 Python 3.14,会导致 pyhub 兼容性问题
2. **推荐使用限制输出版本**: 对于日常测试,推荐使用 `test_e2e_limited.py` 而不是 `test_e2e.py`
3. **完整输出需求**: 如果需要查看完整的原始输出,可以使用原始的 `test_e2e.py` 脚本

## 相关文件

- `pyproject.toml` - Python 版本配置
- `scripts/test_e2e_limited.py` - 限制输出的测试脚本
- `scripts/test_e2e.py` - 原始测试脚本 (保留)
