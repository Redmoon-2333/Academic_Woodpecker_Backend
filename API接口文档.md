# 学业啄木鸟 — 完整 API 接口文档

> 后端版本：1.0.0 | 基础地址：`http://localhost:8765` | 统一响应格式见底部

---

## 目录

1. [认证模块](#1-认证模块)
2. [学情仪表盘](#2-学情仪表盘)
3. [数据上传与解析](#3-数据上传与解析)
4. [资源推荐](#4-资源推荐)
5. [AI 助手](#5-ai-助手)
6. [学习计划](#6-学习计划)
7. [学习记录](#7-学习记录)
8. [今日推送](#8-今日推送)
9. [统一响应格式](#9-统一响应格式)
10. [接口总览表](#10-接口总览表)

---

## 1. 认证模块

### POST /api/auth/register — 用户注册

**无需认证**

```json
// 请求体
{ "username": "zhangsan", "password": "123456", "nickname": "张三", "email": "optional", "studentId": "optional" }
// 响应 (200)
{ "code": 200, "message": "success", "data": { "id": 1, "username": "zhangsan", "nickname": "张三", "role": "student" } }
// 错误 (400) — 用户名已存在
{ "code": 400, "message": "用户名已存在", "data": null }
```

### POST /api/auth/login — 用户登录

**无需认证**

```json
// 请求体
{ "username": "demo", "password": "demo123" }
// 响应 (200)
{ "code": 200, "message": "success", "data": {
    "token": "eyJhbGciOiJI...",
    "userInfo": { "id": 1, "username": "demo", "nickname": "演示用户", "role": "student" }
}}
// 错误 (401)
{ "code": 401, "message": "用户名或密码错误", "data": null }
```

### GET /api/auth/current-user — 获取当前用户

**需认证** `Authorization: Bearer <token>`

```json
// 响应 (200)
{ "code": 200, "data": { "id": 1, "username": "demo", "nickname": "演示用户", "avatar": null, "role": "student" }}
```

---

## 2. 学情仪表盘

### GET /api/dashboard/overview — 学情概览

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": {
    "knowledgeRate": 78.5,       // 知识点掌握率 (%)
    "docCount": 12,              // 已分析文档数
    "lastDiagnosis": "2026-05-07", // 最近一次诊断日期
    "growthRate": 0.05,          // 较上次增长率
    "studyHours": "12.5小时",     // 累计学习时长
    "consecutiveDays": 7          // 连续学习天数
}}
```

### GET /api/dashboard/knowledge-graph — 知识图谱

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": { "nodes": [
    { "id": 1, "name": "数学", "status": "预警", "statusColor": "yellow",
      "children": [
        { "id": 101, "name": "概率论", "status": "薄弱", "statusColor": "red", "children": [] },
        { "id": 102, "name": "线性代数", "status": "掌握", "statusColor": "emerald", "children": [] }
      ]}
]}}
```

### GET /api/dashboard/knowledge/{knowledge_id} — 知识点详情

**需认证**

```json
// GET /api/dashboard/knowledge/101 → 响应 (200)
{ "code": 200, "data": {
    "id": 101, "name": "概率论", "status": "薄弱",
    "description": "研究随机现象的数学分支，核心：概率空间、条件概率...",
    "examFrequency": "高", "difficultyLevel": "中",
    "weakPoints": ["条件概率理解不深", "贝叶斯公式应用错误"],
    "recommendedResources": [{ "id": 1, "title": "概率论强化训练", "type": "video" }],
    "historicalScores": [{ "date": "2026-05-01", "score": 55.0 }]
}}
```

---

## 3. 数据上传与解析

### POST /api/analysis/upload — 上传文件

**需认证** | Content-Type: `multipart/form-data`

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| file | File | ✅ | 支持 PDF/JPG/PNG/TXT |
| fileType | string | | 成绩单/试卷/笔记等 |

```json
// 响应 (200)
{ "code": 200, "data": {
    "fileId": "42", "fileName": "专业成绩单.pdf", "fileSize": "125.3KB",
    "uploadStatus": "processing",
    "previewUrl": "/uploads/abc123_专业成绩单.pdf"
}}
```

> 文件上传后**异步**进行 AI 分析（OCR → 提取 → 同步知识图谱），不阻塞接口返回。

### GET /api/analysis/progress/{file_id} — 解析进度

**需认证**

```json
// 响应 (200) — 处理中
{ "code": 200, "data": {
    "fileId": "42", "status": "parsing", "stage": "正在提取文本...", "progress": 45,
    "stages": [
        { "name": "文本提取", "status": "completed" },
        { "name": "大纲匹配", "status": "processing" },
        { "name": "薄弱项识别", "status": "pending" },
        { "name": "报告生成", "status": "pending" }
    ]
}}
// 响应 (200) — 完成
{ "code": 200, "data": { "fileId": "42", "status": "completed", "progress": 100, "stages": [...] }}
// 响应 (200) — 失败
{ "code": 200, "data": { "fileId": "42", "status": "failed", "progress": 0, "stages": [...] }}
```

### GET /api/analysis/result/{file_id} — 分析结果

**需认证** | 仅在 status=completed 时可用

```json
// 响应 (200)
{ "code": 200, "data": {
    "fileId": "42", "analyzedAt": "2026-05-07 01:30:00",
    "originalFile": { "url": "/uploads/...", "name": "专业成绩单.pdf" },
    "extractedKnowledge": [
        { "name": "概率论", "confidence": 0.95 },
        { "name": "线性代数", "confidence": 0.88 }
    ],
    "weakPoints": [
        { "name": "概率论", "severity": "high" },
        { "name": "线性代数", "severity": "medium" }
    ],
    "suggestions": ["重点复习条件概率与贝叶斯定理", "每天安排1小时专项练习"],
    "summary": "本次分析发现学生概率论掌握率为55%，线性代数72%..."
}}
```

### GET /api/analysis/history — 历史记录

**需认证** | `?page=1&pageSize=10`

```json
// 响应 (200)
{ "code": 200, "data": {
    "total": 12, "page": 1, "pageSize": 10,
    "records": [
        { "id": 42, "fileName": "成绩单.pdf", "uploadTime": "2026-05-07 01:30", "status": "已分析" }
    ]
}}
```

### PUT /api/analysis/result/{file_id} — 手动校正

**需认证**

```json
// 请求体
{ "extractedKnowledge": [{"name": "概率论", "confidence": 0.7}], "weakPoints": [...], "suggestions": [...] }
// 响应 (200)
{ "code": 200, "message": "校正成功" }
```

---

## 4. 资源推荐

### GET /api/resources — 资源列表

**可选认证** | 支持筛选：`?type=video&difficulty=入门&tag=数学&page=1&pageSize=10`

```json
// 响应 (200)
{ "code": 200, "data": {
    "total": 20, "page": 1, "pageSize": 10,
    "resources": [
        { "id": 1, "title": "概率论强化训练", "platform": "B站", "type": "video",
          "difficulty": "进阶", "rating": 4.5, "url": "https://...", "thumbnail": null,
          "reason": "适合薄弱知识点的强化学习", "summary": "覆盖条件概率、贝叶斯定理等核心概念" }
    ]
}}
```

### GET /api/resources/search?keyword=概率论 — 搜索

```json
// 响应结构同上，按标题/平台/标签搜索
```

### GET /api/resources/{resource_id} — 资源详情

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": {
    "id": 1, "title": "概率论强化训练", "platform": "B站", "type": "video",
    "difficulty": "进阶", "url": "https://...", "thumbnail": null,
    "rating": 4.5, "viewCount": 1200, "reason": "...", "summary": "..."
}}
// 错误 (404) — 资源不存在
{ "code": 400, "message": "资源不存在", "data": null }
```

### POST /api/resources/{resource_id}/favorite — 收藏/取消

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": { "resourceId": 1, "isFavorited": true, "favoriteCount": 15 }}
```

### GET /api/resources/favorites — 我的收藏

**需认证** | `?page=1&pageSize=10`

---

## 5. AI 助手

### GET /api/mentor/suggested-actions — 引导提问

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": [
    { "id": 1, "text": "帮我制定一个复习计划", "icon": "plan" },
    { "id": 2, "text": "总结我最近的易错类型", "icon": "chart" },
    { "id": 3, "text": "解释一下贝叶斯定理", "icon": "book" },
    { "id": 4, "text": "推荐一些练习题", "icon": "practice" }
]}
```

### POST /api/mentor/chat — AI 对话

**需认证** | `?thread_id=sess-001`（可选，多轮对话记忆）

```json
// 请求体
{
    "message": "概率论怎么学？",
    "context": {
        "weakPoints": ["概率论", "算法"],
        "currentTopic": "概率论"
    }
}
// 响应 (200)
{ "code": 200, "data": {
    "messageId": "123", "threadId": "sess-001",
    "content": "根据你的学情，概率论当前掌握率55%，建议从基础概念...",
    "timestamp": "2026-05-07 10:30:00",
    "suggestedQuestions": ["这个知识点还有哪些常见题型？", "帮我对比两个概念"],
    "relatedResources": [{ "id": 1, "title": "相关学习资料", "type": "video" }]
}}
```

> **thread_id 机制：** 同一 thread_id 的对话自动共享上下文，实现多轮对话记忆（基于 LangGraph Checkpoint）。

### POST /api/mentor/chat/stream — SSE 流式对话

**需认证** | Content-Type: `text/event-stream`

请求体同上，响应为 SSE 流：

```
data: 根据
data: 你的
data: 学情，概率论
data: 当前掌握率...
```

### GET /api/mentor/history — 对话历史

**需认证** | `?page=1&pageSize=10`

```json
{ "code": 200, "data": { "total": 10, "page": 1, "messages": [
    { "id": "1", "role": "user", "content": "概率论怎么学？", "timestamp": "..." },
    { "id": "2", "role": "assistant", "content": "根据你的学情...", "timestamp": "..." }
]}}
```

### DELETE /api/mentor/history — 清空历史

**需认证** → `{ "code": 200, "message": "聊天历史已清空" }`

---

## 6. 学习计划

### POST /api/plan/generate — 生成学习计划

**需认证** | 调用 AI 生成，响应较慢（~30s）

```json
// 请求体
{ "targetDate": "2026-07-01", "focusAreas": ["概率论", "算法"], "dailyHours": 3 }
// 响应 (200)
{ "code": 200, "data": {
    "planId": "11",
    "weeks": [{
        "weekNumber": 1, "theme": "第1周 基础巩固",
        "tasks": [
            { "day": 1, "content": "复习概率论第一章", "resources": ["教材", "B站视频"] }
        ]
    }],
    "createdAt": "2026-05-07"
}}
```

### GET /api/plan/current — 当前计划（今日目标版）

**需认证** | 适配前端「今日推送」页面

```json
// 响应 (200)
{ "code": 200, "data": {
    "planId": 11,
    "todayGoals": [
        { "id": "goal_11_1", "title": "复习概率论第一章", "estimatedMinutes": 30, "completed": false },
        { "id": "goal_11_2", "title": "完成练习题1-5", "estimatedMinutes": 45, "completed": false }
    ],
    "studyTips": [
        "建议先复习基础知识再做题",
        "注意劳逸结合，每学习45分钟休息10分钟"
    ]
}}
```

> 若无计划 → `{ "planId": null, "todayGoals": [], "studyTips": ["上传成绩单即可生成学习计划"] }`

### PUT /api/plan/{plan_id}/progress — 更新进度

**需认证**

```json
// 请求体
{ "weekNumber": 1, "day": 1, "completed": true }
// 响应 (200)
{ "code": 200, "message": "进度已更新" }
```

---

## 7. 学习记录

### POST /api/learning/records — 创建记录

**需认证**

```json
// 请求体
{ "resource_id": 1, "action": "studied", "duration_seconds": 1800 }
// action: viewed | studied | completed
// 响应 (200)
{ "code": 200, "data": { "id": 1, "action": "studied", "content": "学习了课程内容：《...》", "duration_seconds": 1800, "created_at": "..." }}
```

### GET /api/learning/records — 记录列表

**需认证** | `?page=1&pageSize=20&action=studied`

### GET /api/learning/stats — 学习统计

**需认证**

```json
// 响应 (200)
{ "code": 200, "data": {
    "total_viewed": 45, "total_studied": 30, "total_completed": 12,
    "total_duration_minutes": 360.0,
    "today_records": 5, "streak_days": 7
}}
```

| 字段 | 说明 |
|------|------|
| total_viewed | 累计浏览资源数 |
| total_studied | 累计学习次数 |
| total_completed | 累计完成任务数 |
| total_duration_minutes | 累计学习时长（分钟） |
| today_records | 今日学习记录数 |
| streak_days | 连续学习天数 |

---

## 8. 今日推送

> **全部需认证**

### GET /api/today/push — 推送头部

```json
{ "code": 200, "data": {
    "date": "2026-05-07",
    "weather": "多云",                // 晴/多云/阴/小雨/雨（根据月份模拟）
    "suggestedStudyHours": 4,         // 基于薄弱点数量动态计算（2~5小时）
    "status": "良好",                 // 最佳(≥15h) / 良好(≥8h) / 一般
    "weeklyGrowthRate": 0.25          // 较上周学习时长增长率
}}
```

### GET /api/today/recommendations — 今日推荐

基于用户薄弱知识点匹配资源库：

```json
{ "code": 200, "data": { "recommendations": [
    { "type": "video", "typeLabel": "视频", "difficulty": "进阶",
      "title": "概率论强化训练", "platform": "B站", "duration": "45分钟",
      "reason": "根据你当前的薄弱知识点「概率论」，推荐加强学习",
      "url": "https://...", "thumbnail": "https://..." },
    { "type": "exercise", "typeLabel": "练习", "difficulty": "中级",
      "title": "算法专项练习", "platform": "15题", "duration": null,
      "reason": "薄弱知识点「算法」需要针对性练习",
      "url": "https://...", "thumbnail": null }
]}}
```

> 若无匹配资源 → 返回通用推荐，含默认学习指导文章。

### GET /api/today/progress — 学习进度

```json
{ "code": 200, "data": {
    "weeklyStudyHours": 12.5,          // 本周总学习时长
    "weeklyGrowthRate": 0.25,          // 较上周增长率
    "knowledgeRate": 0.78,             // 知识点掌握率 (0~1)
    "knowledgeGrowthRate": 0.02,       // 掌握率较上周提升
    "weeklyTrend": [
        { "day": "Mon", "hours": 2.5, "isToday": false },
        { "day": "Tue", "hours": 3.0, "isToday": false },
        { "day": "Wed", "hours": 1.5, "isToday": false },
        { "day": "Thu", "hours": 3.5, "isToday": true },
        { "day": "Fri", "hours": 0,   "isToday": false },
        { "day": "Sat", "hours": 0,   "isToday": false },
        { "day": "Sun", "hours": 0,   "isToday": false }
    ]
}}
```

### GET /api/today/goals — 今日目标

```json
{ "code": 200, "data": {
    "planId": 11,
    "todayGoals": [
        { "id": "goal_11_1", "title": "复习概率论第一章", "estimatedMinutes": 30, "completed": false }
    ],
    "studyTips": ["建议先复习基础知识再做题", "注意劳逸结合"]
}}
```

### PUT /api/today/goals/{goal_id} — 更新目标状态

**需认证** | goal_id 格式：`goal_{planId}_{taskIndex}`

```json
// 请求体
{ "completed": true }
// 响应 (200)
{ "code": 200, "message": "目标状态已更新" }
// 错误 (404) — 目标不存在
```

### POST /api/today/start-study — 开始学习

**需认证**

```json
// 响应 (200)
{ "code": 200, "message": "success", "data": { "sessionId": "sess_20260507_a1b2c3" }}
```

> sessionId 格式：`sess_{日期}_{6位随机hex}`，用于追踪单次学习会话。

---

## 9. 统一响应格式

所有接口使用统一 `UnifiedResponse[T]` 封装：

```typescript
// 成功
{ "code": 200, "message": "success", "data": T }

// 业务错误
{ "code": 400 | 401 | 403 | 404, "message": "错误描述", "data": null }
```

**HTTP 状态码：**

| HTTP | code | 含义 |
|------|------|------|
| 200 | 200 | 成功 |
| 400 | 400 | 请求参数错误 / 业务规则拒绝 |
| 401 | 401 | 未认证或 Token 无效 |
| 403 | 403 | 无权限 |
| 404 | 404 | 资源不存在 |
| 500 | 500 | 服务器内部错误 |

**认证方式：** `Authorization: Bearer <JWT_TOKEN>`（Token 有效期 7 天）

---

## 10. 接口总览表

| # | 方法 | 路径 | 认证 | 说明 |
|---|------|------|------|------|
| 1 | POST | `/api/auth/register` | ❌ | 用户注册 |
| 2 | POST | `/api/auth/login` | ❌ | 用户登录 |
| 3 | GET | `/api/auth/current-user` | ✅ | 当前用户信息 |
| 4 | GET | `/api/dashboard/overview` | ✅ | 学情概览 |
| 5 | GET | `/api/dashboard/knowledge-graph` | ✅ | 知识图谱 |
| 6 | GET | `/api/dashboard/knowledge/{id}` | ✅ | 知识点详情 |
| 7 | POST | `/api/analysis/upload` | ✅ | 上传文件分析 |
| 8 | GET | `/api/analysis/progress/{id}` | ✅ | 分析进度 |
| 9 | GET | `/api/analysis/result/{id}` | ✅ | 分析结果 |
| 10 | GET | `/api/analysis/history` | ✅ | 历史记录 |
| 11 | PUT | `/api/analysis/result/{id}` | ✅ | 手动校正 |
| 12 | GET | `/api/resources` | - | 资源列表 |
| 13 | GET | `/api/resources/search` | - | 搜索资源 |
| 14 | GET | `/api/resources/{id}` | - | 资源详情 |
| 15 | POST | `/api/resources/{id}/favorite` | ✅ | 收藏/取消 |
| 16 | GET | `/api/resources/favorites` | ✅ | 我的收藏 |
| 17 | GET | `/api/mentor/suggested-actions` | ✅ | 引导提问 |
| 18 | POST | `/api/mentor/chat` | ✅ | AI 对话 |
| 19 | POST | `/api/mentor/chat/stream` | ✅ | SSE 流式对话 |
| 20 | GET | `/api/mentor/history` | ✅ | 对话历史 |
| 21 | DELETE | `/api/mentor/history` | ✅ | 清空历史 |
| 22 | POST | `/api/plan/generate` | ✅ | 生成学习计划 |
| 23 | GET | `/api/plan/current` | ✅ | 当前计划（今日目标版） |
| 24 | PUT | `/api/plan/{id}/progress` | ✅ | 更新计划进度 |
| 25 | POST | `/api/learning/records` | ✅ | 创建学习记录 |
| 26 | GET | `/api/learning/records` | ✅ | 学习记录列表 |
| 27 | GET | `/api/learning/stats` | ✅ | 学习统计 |
| **28** | GET | `/api/today/push` | ✅ | **今日推送头部** |
| **29** | GET | `/api/today/recommendations` | ✅ | **今日推荐** |
| **30** | GET | `/api/today/progress` | ✅ | **今日进度** |
| **31** | GET | `/api/today/goals` | ✅ | **今日目标** |
| **32** | PUT | `/api/today/goals/{id}` | ✅ | **更新目标状态** |
| **33** | POST | `/api/today/start-study` | ✅ | **开始学习** |

> 加粗 = 本次新增接口。总计 33 个 API 端点。

---

**文档版本**：v2.0 | **更新时间**：2026-05-07 | **后端版本**：学业啄木鸟 1.0.0
