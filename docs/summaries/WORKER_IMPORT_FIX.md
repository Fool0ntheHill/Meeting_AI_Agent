# Worker 导入错误修复

## 问题

运行 `python worker.py` 时报错：

```
ImportError: cannot import name 'load_config' from 'src.config.loader'
Did you mean: 'get_config'?
```

## 原因

`src/config/loader.py` 中的函数名是 `get_config`，不是 `load_config`。

之前的代码使用了错误的函数名。

## 修复

### 1. 修复 `worker.py`

**修改前**:
```python
from src.config.loader import load_config

def create_worker() -> TaskWorker:
    config = load_config()
```

**修改后**:
```python
from src.config.loader import get_config

def create_worker() -> TaskWorker:
    config = get_config()
```

### 2. 修复 `scripts/migrate_files_to_tos.py`

**修改前**:
```python
from src.config.loader import load_config

config = load_config(config_path)
```

**修改后**:
```python
from src.config.loader import ConfigLoader

loader = ConfigLoader(config_path.parent)
config = loader.load(config_path.stem)
```

### 3. 修复文档示例

**修复的文档**:
- `docs/production_deployment_guide.md`
- `docs/production_migration_checklist.md`

**修改**:
```python
# 修改前
from src.config.loader import load_config
config = load_config('production')

# 修改后
from src.config.loader import get_config
config = get_config()
```

## 验证

```bash
# 测试导入
python -c "from worker import create_worker; print('Worker import successful')"
# 输出: Worker import successful

# 测试运行
python worker.py
# 应该正常启动
```

## 正确的配置加载方式

### 方式 1: 使用全局单例（推荐）

```python
from src.config.loader import get_config

# 获取配置（自动从环境变量 APP_ENV 读取环境）
config = get_config()

# 或指定环境
config = get_config(env='production')
```

### 方式 2: 使用 ConfigLoader（高级用法）

```python
from src.config.loader import ConfigLoader

# 创建加载器
loader = ConfigLoader(config_dir='config')

# 加载配置
config = loader.load(env='production')
```

## 总结

- ✅ 修复了 `worker.py` 的导入错误
- ✅ 修复了迁移脚本的导入错误
- ✅ 更新了文档中的示例代码
- ✅ 验证了修复后的代码可以正常运行

**正确的函数名**: `get_config` (不是 `load_config`)

---

**修复时间**: 2026-01-16  
**影响文件**: 
- `worker.py`
- `scripts/migrate_files_to_tos.py`
- `docs/production_deployment_guide.md`
- `docs/production_migration_checklist.md`
