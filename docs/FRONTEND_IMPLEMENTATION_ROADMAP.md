# 前端实施路线图

**项目**: 会议纪要 Agent 前端  
**更新日期**: 2026-01-16

---

## 🎯 总体策略

采用 **MVP (最小可行产品)** 策略，分三个阶段实施：

1. **Phase 1**: 核心流程打通 (P0)
2. **Phase 2**: 完善用户体验 (P1)
3. **Phase 3**: 增强功能 (P2)

---

## 📅 Phase 1: 核心流程 (1-2 周)

### 目标
实现最小可用版本，能够完成完整的会议纪要生成流程。

### 功能清单

#### 1.1 用户认证 (2 天)
- [x] 后端接口已就绪
- [ ] 登录页面 UI
- [ ] Token 管理
- [ ] 自动跳转

**技术要点**:
```typescript
// 简单的 Token 管理
class Auth {
  login(username: string): Promise<void>
  logout(): void
  isAuthenticated(): boolean
  getToken(): string | null
}
```

#### 1.2 创建任务 (3 天)
- [x] 后端接口已就绪
- [ ] 任务创建表单
- [ ] 音频文件处理 (临时方案: 使用测试文件)
- [ ] 模板选择下拉框
- [ ] 参数输入表单

**临时方案**:
```typescript
// 使用固定的测试文件路径
const audioFiles = [
  { file_path: "test_data/meeting.wav", speaker_id: "speaker_001" }
];
```

**待后端补充**: 音频上传接口

#### 1.3 任务状态查询 (2 天)
- [x] 后端接口已就绪
- [ ] 状态轮询逻辑
- [ ] 进度条组件
- [ ] 状态标签组件

**技术要点**:
```typescript
// 智能轮询 (指数退避)
async function pollStatus(taskId: string) {
  let interval = 2000;  // 初始 2 秒
  const maxInterval = 10000;  // 最大 10 秒
  
  while (true) {
    const status = await api.getTaskStatus(taskId);
    if (status.state === 'success' || status.state === 'failed') break;
    
    await sleep(interval);
    interval = Math.min(interval * 1.5, maxInterval);
  }
}
```

#### 1.4 查看会议纪要 (2 天)
- [x] 后端接口已就绪
- [ ] 纪要展示页面
- [ ] 内容解析 (JSON.parse)
- [ ] 格式化显示

**技术要点**:
```typescript
// 安全解析 artifact.content
const content: MeetingMinutes = JSON.parse(artifact.content);
```

### Phase 1 交付标准
- ✅ 用户可以登录
- ✅ 用户可以创建任务 (使用测试文件)
- ✅ 用户可以查看任务进度
- ✅ 用户可以查看生成的会议纪要

---

## 📅 Phase 2: 完善体验 (2-3 周)

### 目标
完善核心功能，提升用户体验。

### 功能清单

#### 2.1 任务列表 (2 天)
- [x] 后端接口已就绪
- [ ] 任务列表页面
- [ ] 分页组件
- [ ] 状态筛选 (前端实现或等待后端)
- [ ] 刷新按钮

**待后端补充**: 状态筛选参数

#### 2.2 音频上传 (3 天)
- [ ] 等待后端实现上传接口
- [ ] 文件选择组件
- [ ] 拖拽上传
- [ ] 上传进度显示
- [ ] 文件格式验证

**阻塞**: 需要后端先实现上传接口

#### 2.3 重新生成 (2 天)
- [x] 后端接口已就绪
- [ ] 模板切换 UI
- [ ] 参数编辑表单
- [ ] 成本预估显示
- [ ] 生成进度提示

#### 2.4 任务确认 (2 天)
- [x] 后端接口已就绪
- [ ] 确认页面 UI
- [ ] 确认项清单
- [ ] 责任人输入
- [ ] 提交验证

#### 2.5 转写文本查看 (2 天)
- [ ] 等待后端实现获取接口
- [ ] 转写文本展示
- [ ] 按说话人分段
- [ ] 时间戳显示

**待后端补充**: 获取转写文本接口

### Phase 2 交付标准
- ✅ 用户可以查看任务列表
- ✅ 用户可以上传音频文件
- ✅ 用户可以重新生成纪要
- ✅ 用户可以确认任务
- ✅ 用户可以查看转写文本

---

## 📅 Phase 3: 增强功能 (2-3 周)

### 目标
添加高级功能，提升产品竞争力。

### 功能清单

#### 3.1 转写编辑 (3 天)
- [x] 后端接口已就绪
- [ ] 富文本编辑器
- [ ] 保存修正
- [ ] 重新生成选项

#### 3.2 说话人修正 (2 天)
- [x] 后端接口已就绪
- [ ] 说话人列表
- [ ] 名称编辑
- [ ] 批量修正

#### 3.3 版本管理 (3 天)
- [x] 后端接口已就绪
- [ ] 版本历史列表
- [ ] 版本对比
- [ ] 版本切换

#### 3.4 模板管理 (3 天)
- [x] 后端接口已就绪
- [ ] 模板列表页面
- [ ] 创建模板表单
- [ ] 编辑模板
- [ ] 删除模板

#### 3.5 导出功能 (2 天)
- [ ] 导出为 PDF
- [ ] 导出为 Word
- [ ] 复制到剪贴板

#### 3.6 热词管理 (2 天)
- [x] 后端接口已就绪
- [ ] 热词集列表
- [ ] 创建热词集
- [ ] 上传热词文件

### Phase 3 交付标准
- ✅ 用户可以编辑转写文本
- ✅ 用户可以修正说话人
- ✅ 用户可以查看版本历史
- ✅ 用户可以管理模板
- ✅ 用户可以导出纪要
- ✅ 用户可以管理热词

---

## 🛠️ 技术栈建议

### 前端框架
**推荐**: React + TypeScript

**理由**:
- 生态成熟，组件丰富
- TypeScript 提供类型安全
- 团队熟悉度高

### UI 组件库
**推荐**: Ant Design

**理由**:
- 企业级组件库
- 中文文档完善
- 开箱即用的表单、表格、上传等组件

### 状态管理
**推荐**: Zustand

**理由**:
- 轻量级 (< 1KB)
- API 简单直观
- 无需 Provider 包裹

### HTTP 客户端
**推荐**: Axios

**理由**:
- 拦截器支持
- 自动转换 JSON
- 请求/响应拦截

### 其他工具
- **文件上传**: react-dropzone
- **富文本编辑**: Quill
- **PDF 导出**: jsPDF
- **Word 导出**: docx

---

## 📦 项目结构建议

```
frontend/
├── src/
│   ├── api/                 # API 客户端
│   │   ├── client.ts        # 基础客户端
│   │   ├── auth.ts          # 认证相关
│   │   ├── tasks.ts         # 任务相关
│   │   ├── artifacts.ts     # 衍生内容相关
│   │   └── templates.ts     # 模板相关
│   │
│   ├── components/          # 通用组件
│   │   ├── Layout/          # 布局组件
│   │   ├── TaskCard/        # 任务卡片
│   │   ├── StatusBadge/     # 状态标签
│   │   └── ProgressBar/     # 进度条
│   │
│   ├── pages/               # 页面组件
│   │   ├── Login/           # 登录页
│   │   ├── TaskList/        # 任务列表
│   │   ├── TaskCreate/      # 创建任务
│   │   ├── TaskDetail/      # 任务详情
│   │   ├── MinutesView/     # 纪要查看
│   │   └── TemplateManage/  # 模板管理
│   │
│   ├── stores/              # 状态管理
│   │   ├── authStore.ts     # 认证状态
│   │   ├── taskStore.ts     # 任务状态
│   │   └── uiStore.ts       # UI 状态
│   │
│   ├── types/               # 类型定义
│   │   └── api.ts           # API 类型 (从 docs/frontend-types.ts 复制)
│   │
│   ├── utils/               # 工具函数
│   │   ├── format.ts        # 格式化工具
│   │   ├── validation.ts    # 验证工具
│   │   └── export.ts        # 导出工具
│   │
│   ├── App.tsx              # 根组件
│   └── main.tsx             # 入口文件
│
├── public/                  # 静态资源
├── package.json
└── tsconfig.json
```

---

## 🚀 快速开始

### 1. 初始化项目

```bash
# 使用 Vite 创建项目
npm create vite@latest meeting-agent-frontend -- --template react-ts

cd meeting-agent-frontend
npm install

# 安装依赖
npm install axios zustand antd react-router-dom
npm install react-dropzone quill jspdf docx

# 安装开发依赖
npm install -D @types/node
```

### 2. 配置环境变量

```bash
# .env.development
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

### 3. 复制类型定义

```bash
# 从后端文档复制类型定义
cp ../docs/frontend-types.ts src/types/api.ts
```

### 4. 实现 API 客户端

```typescript
// src/api/client.ts
import axios from 'axios';

const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
  timeout: 30000,
});

// 请求拦截器
client.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 响应拦截器
client.interceptors.response.use(
  response => response.data,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;
```

### 5. 启动开发服务器

```bash
npm run dev
```

---

## 📊 进度追踪

### Phase 1 进度 (0/4)
- [ ] 用户认证
- [ ] 创建任务
- [ ] 状态查询
- [ ] 查看纪要

### Phase 2 进度 (0/5)
- [ ] 任务列表
- [ ] 音频上传
- [ ] 重新生成
- [ ] 任务确认
- [ ] 转写查看

### Phase 3 进度 (0/6)
- [ ] 转写编辑
- [ ] 说话人修正
- [ ] 版本管理
- [ ] 模板管理
- [ ] 导出功能
- [ ] 热词管理

---

## 🔗 相关文档

- **API 缺口分析**: `docs/FRONTEND_API_GAPS_AND_TODOS.md`
- **完整开发指南**: `docs/FRONTEND_DEVELOPMENT_GUIDE.md`
- **功能清单**: `docs/FRONTEND_FEATURE_CHECKLIST.md`
- **快速参考**: `docs/FRONTEND_QUICK_REFERENCE.md`

---

## 📞 支持

如有问题，请查阅文档或联系后端团队。

**维护者**: 前端开发团队  
**最后更新**: 2026-01-16
