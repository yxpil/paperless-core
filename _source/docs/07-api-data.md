---
code: PLS-DOC-07
title: 接口规范与数据模型说明书
subtitle: 第 7 分册 · REST、WebSocket、错误码、表结构与存储规范
version: V1.0
date: 2026 年 11 月 5 日
secret: 内部公开
phase: 开发 / 联调 / 集成
org: 无纸化会议系统项目组
scope: 本册是前后端联调与第三方集成的唯一契约。凡与实现不一致的契约，以实现改回契约或走变更流程为处理方式。
output: 07 接口规范与数据模型说明书 V1.0.docx
---

# 1 总则

## 1.1 协议栈

对外提供三类接口：REST over HTTPS（配置、查询、上传下载）、WebSocket over TLS（会话内实时事件）、MQTT over TLS（设备指令与状态）。三类接口共用身份模型与错误码体系。字符编码统一 UTF-8，时间统一使用毫秒级 Unix 时间戳（字段名以 At 结尾表示时间点，以 Ms 结尾表示时长），金额与时长使用整数最小单位。

## 1.2 版本策略

REST 版本体现在路径前缀 /api/v1；WebSocket 版本体现在事件信封的 v 字段；MQTT 版本体现在主题的第二段。v1 生命周期内只允许新增字段与新增接口，不允许修改既有字段语义、删除字段或改变状态码语义。破坏性变更以 v2 并行提供，v1 保留不少于 12 个月并给出迁移指引。

## 1.3 命名与格式

路径使用复数名词与短横线，资源动作用子路径表达，例如 /api/v1/meetings/{id}/start。字段使用小写下划线。布尔字段以 is、has、allow 开头。枚举值为大写下划线，例如 SECRET、INTERNAL、PUBLIC。空值统一使用 null，不使用空字符串表示缺失。

# 2 REST 规范

## 2.1 请求约定

表 1 通用请求头

| 请求头 | 必填 | 说明 |
| Authorization | 是 | Bearer 加访问令牌 |
| X-Tenant-Id | 是 | 租户标识，必须与令牌声明一致 |
| X-Request-Id | 是 | 客户端生成的请求标识，用于链路追踪 |
| X-Terminal-Id | 条件必填 | 终端类请求必须携带，用于能力判定 |
| Idempotency-Key | 写操作必填 | 幂等键，建议 UUIDv7 |
| Accept-Language | 否 | 语言偏好，默认 zh-CN |

## 2.2 响应约定

成功响应统一为 { "code": 0, "data": ..., "traceId": "..." }；失败响应统一为 { "code": 错误码, "message": "可读说明", "details": {...}, "traceId": "..." }。HTTP 状态码承载语义类别，业务错误码承载具体原因，两者必须对应：401 对应 2xxx，403 对应 2003，404 对应 x002，409 对应状态冲突类，429 对应限流，5xx 对应 8xxx。

## 2.3 分页与查询

列表接口统一使用 page 与 pageSize（默认 20，上限 100），或游标方式 cursor 与 limit。排序使用 sort 参数，格式为字段名加冒号加 asc 或 desc，多字段以逗号分隔。过滤参数使用字段名直接作为查询参数，范围查询使用字段名加 From 与 To。禁止在 URL 中传递复杂 JSON。

## 2.4 文件上传

上传分三步：申请上传凭证（返回对象存储的预签名地址与分片策略）→ 客户端直传对象存储 → 回调确认并触发转帧。单文件上限 500 MB，分片大小 8 MB，支持断点续传。上传凭证有效期 15 分钟，过期需重新申请。

# 3 认证、授权与注册

## 3.1 令牌

访问令牌为 JWT，有效期 15 分钟，载荷包含 sub、tenant、roles、terminal、exp、jti；刷新令牌有效期 7 天，单次使用并轮换，重放即判定为令牌泄露并强制该用户全部会话下线。令牌签名算法在标准环境使用 HS256，国密环境使用 SM2 签名并对关键字段附加 SM3 摘要。

## 3.2 授权判定

接口级权限通过注解声明，例如 meeting:control、document:read。运行时判定分三步：角色是否具备该权限、ABAC 属性是否满足（会议密级、材料授权、终端类型、时间窗）、租户是否匹配。任一步不通过返回 2003，并在审计中记录被拒绝的资源与原因。

## 3.3 网页端接入流程

网页端为免安装形态，接入流程分五步：访问统一入口地址，服务端返回租户选择页（单租户环境自动跳过）；选择认证方式（账号密码、企业统一身份、扫码）；认证成功后校验终端白名单与 IP 段；首次登录要求修改初始密码并绑定双因子；进入会议列表页，只显示授权给本人的会议。

网页端默认能力为只读加受限交互：不允许本地上传材料、不允许下载源文件、不允许发起同屏。若单位需要网页端具备完整能力，需在策略中显式开启并接受相应的安全评估结论。

## 3.4 账号开通流程

账号来源有三种：管理员批量导入（Excel 模板，含账号、姓名、部门、角色）、组织同步（LDAP 或 AD 增量同步，每 15 分钟一次）、自助注册（仅限允许的场景，注册后进入待审核状态，由管理员审批）。三种来源写入同一张用户表，来源字段区分，避免重复账号。账号状态机为 pending、active、locked、disabled，锁定与停用均需记录原因与操作人。

## 3.5 终端注册流程

终端首次接入调用注册接口，提交序列号、型号、系统版本、能力集与会议室绑定码。服务端校验白名单后签发终端 ID 与设备证书，写入台账并触发配置下发。注册接口不需要用户令牌，改用绑定码加设备指纹校验，绑定码有效期 10 分钟且一次性使用。

# 4 错误码

表 2 错误码表

| 码段 | 类别 | 示例 | HTTP 状态 |
| 1001 至 1099 | 通用请求错误 | 1001 参数错误、1002 资源不存在、1003 状态冲突、1005 限流 | 400、404、409、429 |
| 2001 至 2099 | 认证与授权 | 2001 未认证、2002 令牌过期、2003 权限不足、2005 双因子未完成 | 401、403 |
| 3001 至 3099 | 会议 | 3002 状态不允许、3003 时间冲突、3004 到会率不足、3005 主控冲突 | 400、409 |
| 4001 至 4099 | 材料 | 4002 转帧失败、4003 版本已作废、4004 密级越权、4006 文件过大 | 400、403、413 |
| 5001 至 5099 | 同步 | 5001 房间不存在、5002 rev 跳号、5003 补拉窗口超限、5004 主控离线 | 400、409、410 |
| 6001 至 6099 | 表决 | 6001 表决已关闭、6002 重复投票、6003 无表决权、6004 计时已结束 | 400、409 |
| 7001 至 7099 | 设备 | 7001 设备离线、7002 指令超时、7003 驱动不支持、7004 能力不足 | 400、503 |
| 8001 至 8099 | 系统 | 8001 内部错误、8002 依赖不可用、8003 存储不足、8004 加解密失败 | 500、503 |

错误码一经发布不得复用。新增错误码必须同步更新本册与 OpenAPI 定义，并在契约测试中断言。

# 5 主要接口

## 5.1 会议

表 3 会议接口

| 方法 | 路径 | 说明 |
| GET | /api/v1/meetings | 查询会议列表，支持状态、密级、时间范围过滤 |
| POST | /api/v1/meetings | 创建会议 |
| GET | /api/v1/meetings/{id} | 查询会议详情与议程 |
| PATCH | /api/v1/meetings/{id} | 修改会议基本信息 |
| POST | /api/v1/meetings/{id}/publish | 发布会议，转待开始并触发预载 |
| POST | /api/v1/meetings/{id}/start | 开局，创建房间 |
| POST | /api/v1/meetings/{id}/pause | 暂停 |
| POST | /api/v1/meetings/{id}/resume | 恢复 |
| POST | /api/v1/meetings/{id}/close | 结束并冻结过程数据 |
| POST | /api/v1/meetings/{id}/cancel | 取消会议 |
| POST | /api/v1/meetings/{id}/agenda | 新增或调整议程项 |
| PUT | /api/v1/meetings/{id}/attendees | 设置参会名单 |

## 5.2 材料

表 4 材料接口

| 方法 | 路径 | 说明 |
| GET | /api/v1/documents | 查询材料列表 |
| POST | /api/v1/documents/upload-ticket | 申请上传凭证 |
| POST | /api/v1/documents | 登记材料并触发转帧 |
| GET | /api/v1/documents/{id} | 查询材料元信息与版本 |
| POST | /api/v1/documents/{id}/versions | 上传新版本，旧版自动作废 |
| GET | /api/v1/documents/{id}/pages/{no} | 获取页帧地址（带鉴权与时效） |
| PUT | /api/v1/documents/{id}/grants | 设置授权条目 |
| GET | /api/v1/documents/{id}/export | 导出带水印的 PDF |
| DELETE | /api/v1/documents/{id} | 逻辑删除并回收页帧 |

## 5.3 房间与同步

表 5 房间接口

| 方法 | 路径 | 说明 |
| POST | /api/v1/rooms/{meetingId}/join | 加入房间，返回房间信息与当前 rev |
| GET | /api/v1/rooms/{meetingId}/state | 获取房间快照 |
| GET | /api/v1/rooms/{meetingId}/events | 按 rev 区间补拉事件 |
| POST | /api/v1/rooms/{meetingId}/host | 移交主控权 |
| POST | /api/v1/rooms/{meetingId}/detach | 从端脱会 |
| POST | /api/v1/rooms/{meetingId}/follow | 从端回归跟随 |

## 5.4 表决、纪要与设备

表 6 表决与纪要接口

| 方法 | 路径 | 说明 |
| POST | /api/v1/votes | 创建表决项 |
| POST | /api/v1/votes/{id}/open | 开启表决并启动计时 |
| POST | /api/v1/votes/{id}/ballots | 提交选票，幂等 |
| POST | /api/v1/votes/{id}/close | 关闭并生成结果快照 |
| GET | /api/v1/votes/{id}/result | 查询结果与指纹 |
| GET | /api/v1/minutes/{meetingId} | 获取纪要 |
| PUT | /api/v1/minutes/{meetingId} | 保存纪要草稿 |
| POST | /api/v1/minutes/{meetingId}/signoff | 提交签审或签发 |
| POST | /api/v1/minutes/{meetingId}/resolutions | 决议转任务 |

表 7 设备与运维接口

| 方法 | 路径 | 说明 |
| POST | /api/v1/devices/register | 终端注册 |
| GET | /api/v1/devices | 查询设备台账与在线状态 |
| POST | /api/v1/devices/{id}/command | 下发设备指令 |
| GET | /api/v1/devices/{id}/health | 查询健康指标 |
| GET | /api/v1/audits | 查询审计流水 |
| GET | /api/v1/stats/overview | 运行看板汇总 |

# 6 WebSocket 协议

## 6.1 连接与握手

连接地址为 /ws/v1?roomId={roomId}&terminalId={terminalId}，握手阶段携带访问令牌（Authorization 头或子协议参数）。服务端校验令牌、终端绑定关系与房间权限，通过后分配连接 ID 并下发 room.joined。握手失败返回 401 并关闭连接，不进入重试循环，避免无效重连放大压力。

## 6.2 事件信封

所有消息使用统一信封，字段固定。服务端产生的事件 from 为 server，客户端产生的事件必须携带 opId 用于去重。客户端不得在信封中增加自定义字段，扩展信息一律放入 payload。

```typescript
interface Envelope<T> {
  v: 1;
  rev: number;
  type: string;
  roomId: string;
  ts: number;
  from: string;
  opId?: string;
  payload: T;
  ack?: boolean;   // 客户端置 true 表示要求服务端回执
}
```

## 6.3 事件表

表 8 实时事件定义

| 事件 | 发起方 | payload 要点 | 需回执 |
| view.sync | 主控端 | docId、page、zoom、scrollX、scrollY、pointer | 否 |
| view.detach | 从端 | 无 | 否 |
| view.follow | 从端 | 目标 rev 或 latest | 是 |
| annot.add | 任意端 | page、strokes（含 points、width、color） | 是 |
| annot.erase | 任意端 | page、strokeIds | 是 |
| board.op | 白板端 | page、objects | 是 |
| presence | 任意端 | state、battery、rtt、queueDepth | 否 |
| host.changed | 服务端 | from、to、reason | 否 |
| sync.degraded | 服务端 | level、reasons、suggestions | 否 |
| room.closed | 服务端 | meetingId、原因 | 否 |

## 6.4 心跳、重连与限流

客户端每 10 秒发送一次 ping，服务端回 pong 并携带服务端时间，用于时钟偏差估算。连续 3 次无响应视为断线。重连采用指数退避，初始 1 秒、上限 30 秒、带抖动。服务端对单连接限流：入站 60 条每秒、出站 200 条每秒，超限丢弃低优先级事件并下发降级通知，不直接断开连接。

## 6.5 消息示例

```json
{
  "v": 1,
  "rev": 42,
  "type": "view.sync",
  "roomId": "room-20261105-001",
  "ts": 1793864400123,
  "from": "t-A301-01",
  "payload": {
    "docId": "doc-8f21",
    "page": 12,
    "zoom": 1.0,
    "scrollX": 0,
    "scrollY": 0,
    "pointer": { "x": 0.42, "y": 0.61, "visible": true }
  }
}
```

```json
{
  "code": 4004,
  "message": "该材料密级高于当前终端允许范围",
  "details": { "docId": "doc-8f21", "requiredLevel": "SECRET" },
  "traceId": "1f2a9c7e-3b41-4c88-9d10-5e6f7a8b9c01"
}
```

# 7 数据模型

## 7.1 通用字段

所有业务表包含 id（雪花 ID，字符串存储）、tenant_id、created_at、updated_at、created_by、updated_by、deleted_at。id 使用 64 位雪花算法生成，序列化为字符串以避免前端精度丢失。逻辑删除通过 deleted_at 实现，唯一索引必须包含 deleted_at 或改用部分索引，防止“软删除后无法重新创建”。

## 7.2 关键表结构

```sql
-- 会议主表
CREATE TABLE meeting (
  id            varchar(32) PRIMARY KEY,
  tenant_id     varchar(32) NOT NULL,
  title         varchar(200) NOT NULL,
  secret_level  varchar(16) NOT NULL DEFAULT 'INTERNAL',
  status        varchar(16) NOT NULL DEFAULT 'DRAFT',
  room_code     varchar(64) NOT NULL,
  host_user_id  varchar(32) NOT NULL,
  start_at      timestamptz NOT NULL,
  end_at        timestamptz,
  attendee_min  int NOT NULL DEFAULT 0,
  created_at    timestamptz NOT NULL DEFAULT now(),
  deleted_at    timestamptz
);
CREATE INDEX idx_meeting_tenant_time ON meeting (tenant_id, start_at DESC);
CREATE UNIQUE INDEX uk_meeting_room ON meeting (tenant_id, room_code) WHERE deleted_at IS NULL;

-- 材料版本表
CREATE TABLE doc_version (
  id           varchar(32) PRIMARY KEY,
  tenant_id    varchar(32) NOT NULL,
  doc_id       varchar(32) NOT NULL,
  version      int NOT NULL,
  sha256       char(64) NOT NULL,
  page_count   int NOT NULL DEFAULT 0,
  status       varchar(16) NOT NULL DEFAULT 'CONVERTING',
  object_key   text NOT NULL,
  created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX uk_doc_version ON doc_version (doc_id, version);

-- 事件归档表（按月分区）
CREATE TABLE room_event (
  id          varchar(32) NOT NULL,
  tenant_id   varchar(32) NOT NULL,
  meeting_id  varchar(32) NOT NULL,
  rev         bigint NOT NULL,
  type        varchar(32) NOT NULL,
  payload     jsonb NOT NULL,
  ts          timestamptz NOT NULL,
  PRIMARY KEY (meeting_id, rev)
) PARTITION BY RANGE (ts);
```

## 7.3 枚举字典

表 9 主要枚举

| 字段 | 取值 | 说明 |
| meeting.status | DRAFT、READY、LIVE、PAUSED、CLOSED、ARCHIVED、CANCELED | 会议生命周期 |
| meeting.secret_level | PUBLIC、INTERNAL、SECRET | 密级，影响分发与缓存 |
| doc_version.status | CONVERTING、READY、FAILED、SUPERSEDED | 材料版本状态 |
| attendee.role | HOST、MEMBER、OBSERVER、RECORDER | 会议内角色 |
| vote_item.status | DRAFT、OPEN、CLOSED、CANCELED | 表决状态 |
| terminal.status | PENDING、ACTIVE、OFFLINE、RETIRED | 终端状态 |
| audit.action | LOGIN、VIEW、ANNOTATE、EXPORT、DELETE、CONFIG | 审计动作 |

# 8 缓存与存储规范

## 8.1 Redis 键规范

表 10 Redis 键设计

| 键模式 | 类型 | 过期 | 用途 |
| room:{id}:rev | string | 24 小时 | 房间版本号 |
| room:{id}:evt | stream | 2 小时或 2000 条 | 事件日志，支撑补拉 |
| room:{id}:members | hash | 随连接 | 在线成员与能力集 |
| room:{id}:view | string | 24 小时 | 当前视口快照 |
| sess:{jti} | string | 令牌有效期 | 会话与令牌黑名单 |
| policy:{uid}:{res}:{act} | string | 60 秒 | 授权判定缓存 |
| idem:{key} | string | 10 分钟 | 幂等结果 |
| lock:{name} | string | 30 秒 | 分布式锁，需带持有者标识 |
| rate:{tenant}:{api}:{win} | string | 窗口长度 | 限流计数 |

键命名禁止使用空格与中文，禁止使用业务自增 ID 直接拼接而成的高基数键。所有键必须设置过期时间，除成员表等随连接生命周期清理的键外。

## 8.2 对象存储规范

表 11 桶与路径

| 桶 | 用途 | 路径规则 | 生命周期 |
| pls-src | 材料源文件 | {tenant}/{yyyy}/{mm}/{docId}/v{version}/source.{ext} | 随会议归档，保留 6 个月后转冷 |
| pls-page | 页帧与缩略图 | {tenant}/{docId}/v{version}/p{no}@{scale}.webp | 30 天 |
| pls-export | 导出件 | {tenant}/{meetingId}/{exportId}.pdf | 7 天 |
| pls-audit | 审计归档 | {tenant}/{yyyy}/{mm}/audit-{date}.jsonl.gz | 长期 |

所有桶默认私有，访问一律通过带时效的预签名地址，有效期不超过 5 分钟。桶策略禁止匿名读，禁止跨租户前缀访问。

# 9 契约治理

## 9.1 OpenAPI 管理

接口契约以 OpenAPI 3.1 文件形式随代码提交，位于 apps/api/openapi.yaml，由装饰器自动生成并由 CI 校验。校验项包括：路径与实现一致、字段类型一致、必填一致、错误码在表内、示例可解析。契约变更必须在合并请求中单独列出，便于评审关注。

## 9.2 契约测试

六端共用 packages/contracts，类型由 OpenAPI 生成，不允许手写重复类型。CI 中执行两类契约测试：一是后端实现与 OpenAPI 的比对，二是六端客户端对录制事件流的回放断言。任何一端修改字段而未更新契约，测试立即失败。

## 9.3 兼容性检查

发布前执行兼容性检查脚本，比对新旧 OpenAPI：删除字段、修改字段类型、收紧必填、修改枚举取值均判定为破坏性变更，必须走 v2 或撤回。检查结果作为发布审批的必要材料。

# 10 集成约定

第三方系统接入必须遵循四条规则：使用独立的集成账号与最小权限，不得复用管理员账号；所有调用必须携带 X-Request-Id 并在对方系统可查；不得直接访问数据库或对象存储，只能走开放接口；数据回传必须使用约定的格式与频率，异常时进入重试队列而不是静默丢弃。违反上述规则的接入申请一律驳回。
