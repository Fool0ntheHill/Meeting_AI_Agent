# Meeting AI Frontend（React + TS + Ant Design + Zustand）

> 严格对齐参考文档与 `frontend-types.ts`。支持真实后端 `http://localhost:8000/api/v1`，可切换本地 Mock（MSW）。

## 快速开始
1. 安装依赖  
   `npm install`
2. 环境变量（示例 `env.example`，本地可复制为 `.env.local`）  
   ```
   VITE_API_BASE_URL=http://localhost:8000
   VITE_API_PREFIX=/api/v1
   VITE_ENABLE_MOCK=false
   VITE_ENABLE_DEVTOOLS=true
   VITE_LOG_LEVEL=debug
   ```
3. 启动后端  
   ```
   python main.py      # API
   python worker.py    # Worker
   ```
4. 启动前端  
   `npm run dev`，浏览器访问 `http://localhost:5173`

## 技术栈与目录
- React + TypeScript + Vite + Ant Design v5
- 状态：Zustand（auth/task/artifact/template/task-runner/createTaskDraft）
- 请求：Axios 拦截器（401/403 清 Token 跳登录，422/429/500 统一提示）
- Markdown：Vditor（懒加载，DOMPurify sanitize）
- Mock：MSW（`VITE_ENABLE_MOCK=true` 时启用）

```
src/
  api/           // 统一请求封装与各模块 API
  store/         // auth / task / artifact / template / task-runner / createTaskDraft
  pages/         // login, tasks, workbench, workspace, templates, billing, profile
  components/    // TemplateSelector, MarkdownEditor, StatusTag, Loading...
  utils/         // polling, sanitize, auth-storage
  mocks/         // MSW handlers
  config/env.ts  // 环境变量读取与 API_URL 拼装
  types/         // frontend-types.ts
```

## 核心功能对照
- 登录页：用户名直登（dev），401/403 自动清 Token 跳登录；企业微信扫码占位（Phase 2）。
- 任务列表：筛选（全部/进行中/完成/失败）、刷新、分页，行点击进入工作台（转写/纪要编辑）。
- 创建任务：三步流程（上传 → 排序 → 配置）；上传支持类型/大小校验并读取音频时长；模板必选；提交后进入“任务处理工作台”。
- 任务处理工作台（临时页）：沉浸式进度看板 + 控制栏；支持暂停/继续/中止/删除；右侧展示任务配置快照与实时产出预览；底部日志流。
- 工作台：左右分屏；左侧音频+逐字稿（点击时间戳跳播，单点/全局说话人修正，文本可改）；右侧纪要版本 Tabs（JSON.parse content）、预览/手动编辑（Vditor）、重新生成产生新版本；溯源/导出占位；反馈区隐私勾选默认关闭。
- 模板中心/弹窗：搜索、分类，应用模板。
- 计费/个人中心：账单列表示例，账号信息与退出。

## Mock 使用
- 开关：`.env` 中 `VITE_ENABLE_MOCK=true`
- 逻辑：入口 `main.tsx` 若开启将启动 `msw`，提供登录、任务、状态、转写、纪要等示例数据。
- Mock 环境下创建任务失败会自动生成本地 taskId 并跳转至临时工作台，便于体验流程。

## 路由
`/login`、`/tasks`、`/tasks/create`、`/tasks/create/sort`、`/tasks/create/config`、`/tasks/:id/workbench`、`/tasks/:id`（重定向到 `/workspace/:id`）、`/workspace/:id`、`/templates`、`/billing`、`/profile`

## 关键自检
- 认证：401/403 清 Token 跳登录；Token 24h，提前 5 分钟可扩展 refresh。
- 轮询：指数退避 2-10s，完成/失败即停。
- 纪要：`artifact.content` 统一 JSON.parse，重新生成新增版本不覆盖。
- 说话人修正：单点/全局映射，提交不触发自动再生成（可选）。
- 安全：Markdown sanitize，图片上传校验占位；上传音频不手动设置 Content-Type。

## 脚本
- `npm run dev` 开发
- `npm run build` 生产构建
- `npm run preview` 预览
- `npm run lint` 基本检查
