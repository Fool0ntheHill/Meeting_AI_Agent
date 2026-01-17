# Windows 上安装 Python 3.12 指南

## 方法 1: 使用 pyenv-win (推荐)

pyenv-win 是 pyenv 在 Windows 上的实现,可以方便地管理多个 Python 版本。

### 步骤 1: 安装 pyenv-win

**使用 PowerShell 安装** (推荐):

```powershell
# 以管理员身份运行 PowerShell
Invoke-WebRequest -UseBasicParsing -Uri "https://raw.githubusercontent.com/pyenv-win/pyenv-win/master/pyenv-win/install-pyenv-win.ps1" -OutFile "./install-pyenv-win.ps1"; &"./install-pyenv-win.ps1"
```

**或使用 Git 安装**:

```bash
# 克隆仓库
git clone https://github.com/pyenv-win/pyenv-win.git "$HOME\.pyenv"
```

### 步骤 2: 配置环境变量

安装完成后,需要配置环境变量:

1. 打开 "系统属性" → "高级" → "环境变量"
2. 在 "用户变量" 中添加:
   - `PYENV`: `%USERPROFILE%\.pyenv\pyenv-win`
   - `PYENV_ROOT`: `%USERPROFILE%\.pyenv\pyenv-win`
   - `PYENV_HOME`: `%USERPROFILE%\.pyenv\pyenv-win`

3. 在 "Path" 变量中添加:
   - `%PYENV%\bin`
   - `%PYENV%\shims`

4. 重启 PowerShell 或 CMD

### 步骤 3: 验证 pyenv-win 安装

```bash
# 检查 pyenv 版本
pyenv --version

# 查看可安装的 Python 版本
pyenv install --list
```

### 步骤 4: 安装 Python 3.12

```bash
# 安装 Python 3.12.8 (或最新的 3.12.x 版本)
pyenv install 3.12.8

# 查看已安装的版本
pyenv versions
```

### 步骤 5: 在项目中设置 Python 3.12

```bash
# 进入项目目录
cd D:\Programs\Meeting_AI_Agent

# 设置本地 Python 版本
pyenv local 3.12.8

# 验证版本
python --version
# 应该显示: Python 3.12.8
```

### 步骤 6: 创建虚拟环境并安装依赖

```bash
# 创建虚拟环境
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate

# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证安装
python -c "import pyhub; print('pyhub OK')"
```

---

## 方法 2: 直接安装 Python 3.12 (简单快速)

如果你不想使用 pyenv-win,可以直接安装 Python 3.12。

### 步骤 1: 下载 Python 3.12

1. 访问 [Python 官网下载页面](https://www.python.org/downloads/)
2. 下载 Python 3.12.x (Windows installer 64-bit)
3. 推荐下载最新的 3.12 版本 (例如 3.12.8)

### 步骤 2: 安装 Python 3.12

1. 运行下载的安装程序
2. **重要**: 勾选 "Add Python 3.12 to PATH"
3. 选择 "Customize installation"
4. 确保勾选:
   - pip
   - py launcher
   - for all users (optional)
5. 在 "Advanced Options" 中:
   - 可以自定义安装路径 (例如 `C:\Python312`)
   - 勾选 "Add Python to environment variables"
6. 点击 "Install"

### 步骤 3: 配置 Python 优先级

如果系统上有多个 Python 版本,需要确保 Python 3.12 优先:

**方法 A: 使用 py launcher**

```bash
# 查看所有已安装的 Python 版本
py --list

# 使用 Python 3.12
py -3.12 --version

# 创建虚拟环境
py -3.12 -m venv venv
```

**方法 B: 修改环境变量**

1. 打开 "系统属性" → "高级" → "环境变量"
2. 在 "Path" 中,将 Python 3.12 的路径移到最前面:
   - `C:\Python312\`
   - `C:\Python312\Scripts\`
3. 重启 PowerShell 或 CMD

### 步骤 4: 创建虚拟环境

```bash
# 进入项目目录
cd D:\Programs\Meeting_AI_Agent

# 使用 Python 3.12 创建虚拟环境
py -3.12 -m venv venv

# 或者 (如果 Python 3.12 已在 PATH 中)
python -m venv venv

# 激活虚拟环境
.\venv\Scripts\activate

# 验证版本
python --version
# 应该显示: Python 3.12.x
```

### 步骤 5: 安装依赖

```bash
# 升级 pip
python -m pip install --upgrade pip

# 安装项目依赖
pip install -r requirements.txt

# 验证安装
python -c "import pyhub; print('pyhub OK')"
```

---

## 方法 3: 使用 Chocolatey (包管理器)

如果你使用 Chocolatey:

```bash
# 安装 Python 3.12
choco install python312

# 验证安装
python --version
```

---

## 验证安装成功

完成安装后,运行以下命令验证:

```bash
# 1. 检查 Python 版本
python --version
# 应该显示: Python 3.12.x

# 2. 检查 pip 版本
pip --version

# 3. 检查虚拟环境是否激活
where python
# 应该显示虚拟环境中的 python.exe 路径

# 4. 测试 pyhub
python -c "import pyhub; print('pyhub 安装成功')"

# 5. 运行配置检查
python scripts/check_config.py --config config/test.yaml

# 6. 运行单元测试
pytest tests/unit/ -v
```

---

## 常见问题

### Q1: pyenv 命令找不到

**问题**: `pyenv: command not found`

**解决**:
1. 确认环境变量已正确配置
2. 重启 PowerShell 或 CMD
3. 以管理员身份运行 PowerShell

### Q2: Python 版本没有切换

**问题**: `python --version` 仍然显示 3.14.2

**解决**:
1. 确认虚拟环境已激活: `.\venv\Scripts\activate`
2. 检查 PATH 环境变量顺序
3. 使用 `py -3.12` 明确指定版本
4. 重启终端

### Q3: pip 安装依赖失败

**问题**: `pip install` 报错

**解决**:
```bash
# 升级 pip
python -m pip install --upgrade pip

# 清理缓存
pip cache purge

# 重新安装
pip install -r requirements.txt
```

### Q4: 虚拟环境激活失败

**问题**: PowerShell 执行策略限制

**解决**:
```powershell
# 以管理员身份运行 PowerShell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser

# 然后重新激活虚拟环境
.\venv\Scripts\activate
```

---

## 推荐的完整流程

```bash
# 1. 安装 Python 3.12 (选择上述任一方法)

# 2. 进入项目目录
cd D:\Programs\Meeting_AI_Agent

# 3. 创建虚拟环境
python -m venv venv

# 4. 激活虚拟环境
.\venv\Scripts\activate

# 5. 验证 Python 版本
python --version
# 应该显示: Python 3.12.x

# 6. 升级 pip
python -m pip install --upgrade pip

# 7. 安装依赖
pip install -r requirements.txt

# 8. 验证安装
python -c "import pyhub; print('pyhub OK')"

# 9. 运行测试
python scripts/test_e2e_limited.py --audio test_data/meeting.wav --skip-speaker-recognition --config config/test.yaml
```

---

## 下一步

安装完成后:
1. ✅ 确认 Python 版本为 3.12.x
2. ✅ 运行配置检查: `python scripts/check_config.py --config config/test.yaml`
3. ✅ 运行单元测试: `pytest tests/unit/ -v`
4. ✅ 运行端到端测试: `python scripts/test_e2e_limited.py --audio <your_audio> --skip-speaker-recognition`

---

**提示**: 推荐使用虚拟环境,这样可以隔离项目依赖,避免与系统 Python 冲突。
