# AGENTS.md — 编码助手行为指南

> 本文件指导 AI 编程助手在与项目交互时的行为规范和决策原则。

---

## 一、基本行为准则

1. **优先查询，后做假设** — 在提议代码变更前，先 `read_file` 确认当前文件状态
2. **最小变更边界** — 只修改实现功能所必需的文件，不超过需求范围
3. **可审计** — 每次修改需在 commit message 中说明变更动机

## 二、编码优先顺序

在修改代码时，按以下优先级做决策：

```
正确性 → 可读性 → 可维护性 → 性能
```

- **不要**为性能优化而牺牲代码清晰度
- **不要**引入项目尚未使用的第三方依赖
- **不要**在非关键路径上过度工程化

## 三、CI/CD 防护

提交前在脑中预检：

| 检查项 | 命令 |
|--------|------|
| ruff 检查 | `ruff check backend/ --statistics` — 应 0 errors |
| mypy 类型 | `mypy app --ignore-missing-imports --follow-imports=silent --implicit-optional` — 应 Success（详见 pyproject.toml） |
| 后端测试 | `python -m pytest tests/ -v` — 应全部通过 |
| 前端编译 | `cd frontend && npx tsc --noEmit` — 应 0 errors |

如果修改涉及新增 Python 依赖，同步更新 `backend/requirements.txt`。

## 四、文件修改守则

### 4.1 Python 文件

- 添加新 `import` 后，确认文件顶部 import 分组正确（标准库 → 第三方 → 本地）
- 不要删除看似"未使用"的 `Depends(get_db)` 参数——FastAPI 通过依赖注入解析
- 新函数加上类型注解和 docstring

### 4.2 TypeScript/React 文件

- 新组件文件放在 `components/` 对应子目录下
- 页面级组件放在 `pages/` 目录
- Zustand store 在 `stores/` 目录中统一管理
- API 调用在 `services/api.ts` 中定义

### 4.3 数据库 Schema

- 模型修改在 `backend/app/models/` 中对应的文件
- `to_dict()` 方法必须返回前端需要的所有字段
- 新表需在 `app/models/__init__.py` 中导出

## 五、响应格式

### 5.1 Bug 修复

```
## 问题
[描述现象和根因]

## 修复
[文件路径]: [具体改动]

## 验证
[建议的验证方式]
```

### 5.2 新功能

```
## 功能
[一句话说明]

## 涉及文件
- backend/xxx.py: [改动说明]
- frontend/xxx.tsx: [改动说明]

## 注意事项
[潜在影响和测试要点]
```

## 六、部署注意事项

1. 后端依赖变更后，提醒用户执行 `pip install -r requirements.txt`
2. 前端依赖变更后，提醒用户执行 `npm install`
3. 新增系统依赖（如 `poppler-utils`）需更新部署文档
4. 数据库表结构变更后服务会自动建表（`Base.metadata.create_all`）

## 七、语言

- 所有代码注释、文档、commit message 使用 **简体中文**
- 变量名、函数名使用 **英文**（Python/TS 标准命名规范）
- 终端输出、日志使用 **中文**（用户可见部分）

## 八、避免的误区

| 误区 | 正确做法 |
|------|---------|
| 在 except 中直接 raise 捕获的异常 | 用 `raise ... from e` 或 `raise ... from None` |
| 使用 `a["key"]` 直接取字典值 | 用 `a.get("key", default)` 防止 KeyError |
| 假设 `scalar()` 返回非 None | 加 `or 0` / `or ""` 安全处理 |
| 直接修改 `requirements.txt` 不通知用户 | 修改后必须在回复中提醒执行 `pip install` |
