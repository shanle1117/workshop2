# React Chatbot Setup Guide

本项目已集成 React 和 react-markdown 来渲染 Markdown 格式的聊天消息。

## 安装步骤

1. **安装 Node.js 依赖**
   ```bash
   npm install
   ```

2. **构建 React 组件**
   ```bash
   npm run build
   ```
   
   这将编译 React 组件到 `frontend/dist/chatbot-react.js`

3. **开发模式（自动重新编译）**
   ```bash
   npm run dev
   ```

## 使用说明

### 生产环境
1. 运行 `npm run build` 构建 React 组件
2. 确保 Django 的静态文件配置包含 `frontend/dist/` 目录
3. 运行 Django 服务器

### 开发环境
1. 在一个终端运行 `npm run dev`（监听文件变化并自动重新编译）
2. 在另一个终端运行 Django 服务器
3. 修改 `src/react/Chatbot.jsx` 后会自动重新编译

## 文件结构

```
├── src/
│   └── react/
│       ├── Chatbot.jsx      # React 聊天组件（使用 react-markdown）
│       └── index.jsx        # React 入口文件
├── frontend/
│   ├── index.html           # 主 HTML 文件（已更新为使用 React）
│   ├── style.css            # 样式文件
│   └── dist/                # Webpack 编译输出目录
│       └── chatbot-react.js # 编译后的 React 组件
├── package.json             # Node.js 依赖配置
└── webpack.config.js        # Webpack 构建配置
```

## React-Markdown 特性

- ✅ 支持标准 Markdown 语法
- ✅ 支持 GitHub Flavored Markdown (GFM)
- ✅ 自动转义 HTML，防止 XSS 攻击
- ✅ 自动为链接添加 `target="_blank"` 和 `rel="noopener noreferrer"`
- ✅ 支持代码块、列表、表格、引用等所有 Markdown 特性

## 从旧版本迁移

如果你之前使用的是 `marked.js` 版本（`frontend/chat.js`），现在可以：

1. **保留旧版本**：`frontend/chat.js` 仍然存在，可以在 `frontend/main.html` 中继续使用
2. **使用新版本**：`frontend/index.html` 已更新为使用 React 版本

## 故障排除

### 构建错误
- 确保已安装所有依赖：`npm install`
- 检查 Node.js 版本（建议 v16+）

### React 组件未加载
- 确保已运行 `npm run build`
- 检查浏览器控制台是否有错误
- 确认 `frontend/dist/chatbot-react.js` 文件存在

### Markdown 未渲染
- 检查浏览器控制台是否有 react-markdown 相关错误
- 确认后端返回的消息包含有效的 Markdown 语法

