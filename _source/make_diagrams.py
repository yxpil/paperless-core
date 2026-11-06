#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""生成文档插图为 PNG（纯 Pillow 绘制，坐标固定，便于复现）。

输出到 _source/images/：
  arch.png      系统总体分层架构
  deploy.png    部署拓扑
  state.png     会议生命周期状态机
  sync.png      同屏同步时序
"""
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

OUT = Path(__file__).resolve().parent / 'images'
OUT.mkdir(parents=True, exist_ok=True)

HEI = 'C:/Windows/Fonts/simhei.ttf'
YAHEI = 'C:/Windows/Fonts/msyh.ttc'

INK = (31, 35, 40)
BLUE = (27, 76, 126)
FILL = (234, 240, 246)
FILL2 = (247, 249, 251)
GRAY = (107, 114, 128)
WHITE = (255, 255, 255)
LINE = (168, 181, 195)
AMBER = (176, 124, 20)


def f(path, size):
    return ImageFont.truetype(path, size)


def rounded(d, box, fill=FILL, outline=BLUE, width=2, radius=10):
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_lines(d, xy, text, font, color=INK, spacing=6, align='center', width=None):
    lines = text.split('\n')
    x, y = xy
    for line in lines:
        w = d.textlength(line, font=font)
        ox = x - w / 2 if align == 'center' else x
        d.text((ox, y), line, font=font, fill=color)
        y += (font.size + spacing)


def block(d, box, text, font, color=INK, spacing=6):
    """在矩形内垂直水平居中绘制多行文本。"""
    x0, y0, x1, y1 = box
    lines = text.split('\n')
    hs = [(font.size + spacing) for _ in lines]
    total = sum(hs) - spacing
    cy = y0 + (y1 - y0 - total) / 2
    for line in lines:
        w = d.textlength(line, font=font)
        d.text((x0 + (x1 - x0 - w) / 2, cy), line, font=font, fill=color)
        cy += font.size + spacing


def arrow(d, start, end, color=BLUE, width=3, head=12):
    d.line([start, end], fill=color, width=width)
    (x1, y1), (x2, y2) = start, end
    ang = math.atan2(y2 - y1, x2 - x1)
    for delta in (0.42, -0.42):
        a = ang + math.pi + delta
        d.line([end, (x2 + head * math.cos(a), y2 + head * math.sin(a))],
               fill=color, width=width)


def label(d, xy, text, font, color=INK, bg=WHITE, pad=4):
    w = d.textlength(text, font=font)
    h = font.size + 4
    d.rectangle([xy[0] - pad, xy[1] - 2, xy[0] + w + pad, xy[1] + h], fill=bg)
    d.text(xy, text, font=font, fill=color)


# ---------------------------------------------------------------- 架构图
def arch():
    W, H = 1800, 1470
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    ft = f(HEI, 40)
    fb = f(YAHEI, 23)
    fs = f(YAHEI, 22)

    d.text((60, 40), 'PaperlessCore 总体分层架构', font=ft, fill=BLUE)
    d.text((60, 96), '终端只做呈现与输入，状态由服务端权威维护；跨端一致靠“事件 + 版本号”，不靠终端之间互传文件。',
           font=fs, fill=GRAY)

    bands = [
        ('终端层', ['PC 客户端\nElectron 28', '平板终端\nAndroid / iOS', '一体机终端\nAndroid 定制',
                  '白板终端\nCanvas 引擎', '网页端\n浏览器', 'TV 大屏端\nWebGL 渲染']),
        ('接入层', ['Nginx / WAF\nTLS 1.3 卸载', 'WebSocket 网关\nws-gateway', '边缘接入网关\nEdge Agent',
                  '媒体接入\nWebRTC · H.264', '开放接口\nOpenAPI 3.1', '静态资源\nCDN / OSS']),
        ('应用服务层', ['会议服务\nmeeting', '材料服务\ndocument', '同步服务\nsync', '白板协同\nboard',
                    '设备管理\ndevice', '身份权限\niam', '纪要服务\nminutes', '审计服务\naudit']),
        ('领域能力层', ['事件总线\nNATS JetStream', '同步引擎\nview-sync · rev', '文件转换管线\nOffice → 页帧',
                    '国密与签章\nSM2 / SM3 / SM4', '通知与提醒\nIM · 短信']),
        ('数据层', ['PostgreSQL 16\n业务主库', 'Redis 7\n缓存 · 锁 · 在线态', 'MinIO\n对象存储',
                  'OpenSearch\n检索与审计']),
        ('基础设施层', ['容器编排\nDocker / K8s', '可观测\nPrometheus · Loki', '备份容灾\nPITR + 异地',
                    '交付流水线\nGitLab CI']),
    ]

    y = 150
    bh, gap = 185, 22
    for name, boxes in bands:
        rounded(d, (60, y, W - 60, y + bh), fill=FILL2, outline=(226, 232, 239), width=2, radius=14)
        d.text((86, y + 16), name, font=f(HEI, 26), fill=BLUE)
        row_y0, row_y1 = y + 58, y + bh - 18
        n = len(boxes)
        x0, x1 = 86, W - 86
        g = 12
        bw = (x1 - x0 - g * (n - 1)) / n
        for idx, text in enumerate(boxes):
            bx = x0 + idx * (bw + g)
            rounded(d, (bx, row_y0, bx + bw, row_y1), fill=FILL)
            block(d, (bx + 8, row_y0, bx + bw - 8, row_y1), text, fb)
        y += bh + gap

    d.text((60, 1410), '说明：六端共用同一套会话协议与渲染内核，能力差异由“能力协商 + 降级策略”消化，不在服务端分叉业务逻辑。',
           font=fs, fill=GRAY)
    img.save(OUT / 'arch.png', dpi=(200, 200))


# ---------------------------------------------------------------- 部署拓扑
def deploy():
    W, H = 1800, 1180
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    ft = f(HEI, 40)
    fh = f(HEI, 28)
    fb = f(YAHEI, 22)
    fs = f(YAHEI, 21)

    d.text((60, 40), '典型部署拓扑（单会议室 + 中心机房）', font=ft, fill=BLUE)
    d.text((60, 96), '会议室侧断网可继续本地会议（边缘网关内置轻量服务），联网后自动补齐差异并回传纪要。',
           font=fs, fill=GRAY)

    rounded(d, (50, 150, 690, 1080), fill=FILL2, outline=LINE, width=2, radius=14)
    d.text((75, 168), '会议室现场（内网 / 隔离 VLAN）', font=fh, fill=BLUE)
    terminals = [('PC 客户端', '主持席 · 双屏'), ('平板终端', '参会席 · 无线'),
                 ('一体机终端', '升降屏 · PoE'), ('白板终端', '协作区'),
                 ('TV 大屏端', '投屏接收'), ('网页端', '列席 · 免安装')]
    for idx, (name, sub) in enumerate(terminals):
        y = 225 + idx * 116
        rounded(d, (75, y, 665, y + 94), fill=WHITE)
        d.text((95, y + 16), name, font=fb, fill=INK)
        d.text((95, y + 50), sub, font=fs, fill=GRAY)
    rounded(d, (75, 930, 665, 1060), fill=(255, 247, 234), outline=AMBER, width=2)
    block(d, (90, 930, 650, 1060),
          '边缘接入网关 Edge Box（ARM Linux / Node.js）\n设备发现 · 串口红外驱动 · 断网续会 · 本地缓存',
          fs, color=INK)

    rounded(d, (750, 150, 1380, 1080), fill=FILL2, outline=LINE, width=2, radius=14)
    d.text((775, 168), '中心机房（等保三级区域）', font=fh, fill=BLUE)
    rounded(d, (790, 228, 1340, 296), fill=FILL)
    block(d, (790, 228, 1340, 296), '负载均衡 / WAF · TLS 1.3 · 国密双证书', fb)
    stacks = [('Node.js 应用集群', 'meeting · document · sync · board · iam'),
              ('WebSocket 网关集群', 'ws-gateway · 会话粘滞 · 万级长连接'),
              ('媒体与转码集群', 'WebRTC SFU · PDF 转帧 worker'),
              ('数据与中间件', 'PostgreSQL 16 · Redis 7 · MinIO · NATS')]
    for idx, (name, sub) in enumerate(stacks):
        y = 326 + idx * 128
        rounded(d, (790, y, 1340, y + 104), fill=WHITE)
        d.text((810, y + 16), name, font=fb, fill=INK)
        d.text((810, y + 52), sub, font=fs, fill=GRAY)
    rounded(d, (790, 872, 1340, 948), fill=WHITE)
    block(d, (790, 872, 1340, 948), '运维通道：VPN / 堡垒机（仅运维网段可达）', fs)
    d.text((790, 972), '备份：每日全量 + 15 分钟 WAL 归档，异地留存 180 天', font=fs, fill=GRAY)

    rounded(d, (1440, 330, 1740, 700), fill=FILL2, outline=LINE, width=2, radius=14)
    d.text((1462, 348), '外部接入', font=fh, fill=BLUE)
    for idx, text in enumerate(['VPN / 零信任网关\n远程参会', '上级单位\n会议数据上报',
                                '短信 / IM 通知\n会议提醒']):
        y = 400 + idx * 96
        rounded(d, (1460, y, 1720, y + 82), fill=WHITE)
        block(d, (1460, y, 1720, y + 82), text, fs)

    arrow(d, (683, 300), (786, 300))
    label(d, (694, 248), 'WSS', fs, BLUE)
    arrow(d, (683, 990), (786, 640), color=AMBER)
    label(d, (688, 1000), 'MQTT', fs, AMBER)
    arrow(d, (1345, 470), (1452, 470), color=LINE)

    d.text((50, 1112), '说明：对外暴露面收敛到负载均衡；应用集群无状态，会话态集中在 Redis，便于水平扩容与灰度发布。',
           font=fs, fill=GRAY)
    img.save(OUT / 'deploy.png', dpi=(200, 200))


# ---------------------------------------------------------------- 状态机
def state():
    W, H = 1800, 800
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    ft = f(HEI, 40)
    fb = f(YAHEI, 26)
    fs = f(YAHEI, 21)

    d.text((60, 40), '会议生命周期状态机（服务端权威）', font=ft, fill=BLUE)
    d.text((60, 96), '任何终端操作都被转换为“事件 + 前置条件”，由服务端在单一事务内校验并推进状态。',
           font=fs, fill=GRAY)

    bw, bh = 290, 132
    boxes = {
        'draft': (80, 190, '草稿 DRAFT', '编排议程与材料'),
        'ready': (480, 190, '待开始 READY', '材料已分发预载'),
        'live': (880, 190, '进行中 LIVE', '同屏 / 批注 / 表决'),
        'closed': (1280, 190, '已结束 CLOSED', '生成纪要初稿'),
        'cancel': (480, 430, '已取消 CANCELED', '材料撤回'),
        'pause': (880, 430, '暂停 PAUSED', '计时与表决冻结'),
        'archived': (1280, 430, '已归档 ARCHIVED', '只读 + 审计留痕'),
    }
    for key, (x, y, title, sub) in boxes.items():
        rounded(d, (x, y, x + bw, y + bh), fill=FILL, radius=16)
        block(d, (x + 10, y + 10, x + bw - 10, y + 60), title, fb)
        block(d, (x + 10, y + 62, x + bw - 10, y + bh - 8), sub, fs, color=GRAY)

    def h_arrow(a, b, text):
        x0, y0 = boxes[a][0], boxes[a][1]
        x1 = boxes[b][0]
        y = y0 + bh / 2
        arrow(d, (x0 + bw, y), (x1 - 8, y))
        mid = (x0 + bw + x1) / 2
        label(d, (mid - 6, y - 44), text, fs, BLUE, bg=WHITE)

    def v_arrow(a, b, text, dx=0):
        x0, y0 = boxes[a][0], boxes[a][1]
        x = x0 + bw / 2 + dx
        y1 = boxes[b][1]
        arrow(d, (x, y0 + bh), (x, y1 - 8))
        label(d, (x + 10, (y0 + bh + y1) / 2 - 16), text, fs, BLUE, bg=WHITE)

    h_arrow('draft', 'ready', '发布')
    h_arrow('ready', 'live', '开局')
    h_arrow('live', 'closed', '结束')
    v_arrow('ready', 'cancel', '取消')
    v_arrow('closed', 'archived', '归档')
    v_arrow('live', 'pause', '暂停', dx=-44)
    arrow(d, (boxes['live'][0] + bw / 2 + 44, boxes['pause'][1]),
          (boxes['live'][0] + bw / 2 + 44, boxes['live'][1] + bh + 8))
    label(d, (boxes['live'][0] + bw / 2 + 54, 356), '恢复', fs, BLUE, bg=WHITE)

    d.text((80, 640), '约束：状态单向前进，唯一例外是“暂停/恢复”；已归档不可编辑，需要修订时新建“修订版会议”并保留原归档快照。',
           font=fs, fill=GRAY)
    d.text((80, 680), '所有状态迁移写入 audit 流水，包含 operatorId、terminalId、trigger、beforeRev、afterRev。',
           font=fs, fill=GRAY)
    img.save(OUT / 'state.png', dpi=(200, 200))


# ---------------------------------------------------------------- 时序图
def sync():
    W, H = 1800, 1020
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    ft = f(HEI, 40)
    fh = f(YAHEI, 24)
    fs = f(YAHEI, 20)

    d.text((60, 40), '同屏同步时序（文档级同屏，非视频流）', font=ft, fill=BLUE)
    d.text((60, 96), '材料集中转页帧后，各端只同步“页码 + 批注增量 + 视口参数”；300 页材料同屏的带宽约为视频方案的 1/200。',
           font=fs, fill=GRAY)

    lifelines = [('主控端\nPC 客户端', 210), ('WS 网关\nws-gateway', 660),
                 ('同步服务\nsync', 1050), ('从端\n平板 / 一体机 / TV', 1490)]
    top, bottom = 200, 900
    for name, x in lifelines:
        rounded(d, (x - 130, top - 76, x + 130, top - 10), fill=FILL, radius=10)
        block(d, (x - 130, top - 76, x + 130, top - 10), name, fh)
        d.line([(x, top - 10), (x, bottom)], fill=LINE, width=2)

    msgs = [
        (210, 660, '① view.open{meetingId, docId:12, page:3}', 300, BLUE),
        (660, 1050, '② 权限校验 + 取房间版本 rev=41', 360, BLUE),
        (1050, 1490, '③ view.sync{rev:42, docId, page, zoom, pointer}', 420, BLUE),
        (1490, 1050, '④ ack{rev:42, renderMs:86}', 476, LINE),
        (210, 660, '⑤ annot.add{strokeBatch, 3 笔}', 545, BLUE),
        (660, 1050, '⑥ 笔迹定序落库 + 广播', 598, BLUE),
        (1050, 1490, '⑦ annot.apply{rev:43, ops}', 650, BLUE),
        (210, 660, '⑧ heartbeat{rtt:12ms}', 725, LINE),
        (1050, 1490, '⑨ clock.sync{offset:+12ms}', 775, LINE),
    ]
    for x1, x2, text, y, color in msgs:
        arrow(d, (x1, y), (x2, y), color=color, width=3, head=12)
        label(d, (min(x1, x2) + 14, y - 34), text, fs, INK)

    d.text((60, 940), '说明：rev 为房间单调递增版本号，从端按 rev 顺序应用；断线重连只补拉 rev 之后的增量，无需全量重传。',
           font=fs, fill=GRAY)
    img.save(OUT / 'sync.png', dpi=(200, 200))


# ---------------------------------------------------------------- 老设备接入
def legacy():
    W, H = 1800, 900
    img = Image.new('RGB', (W, H), WHITE)
    d = ImageDraw.Draw(img)
    ft = f(HEI, 40)
    fh = f(YAHEI, 24)
    fb = f(YAHEI, 22)
    fs = f(YAHEI, 20)

    d.text((60, 40), '老设备五级接入路径', font=ft, fill=BLUE)
    d.text((60, 96), '按设备实际条件选择级别，级别记入设备台账；同一会议室内允许不同级别并存，能力差异由会话策略消化。',
           font=fs, fill=GRAY)

    cols = [(60, 470), (490, 860), (880, 1245), (1265, 1740)]
    heads = ['设备特征', '接入方式', '承载组件', '能力结果']
    y = 145
    d.rectangle([cols[0][0], y, cols[-1][1], y + 56], fill=FILL, outline=LINE)
    for (x0, x1), head in zip(cols, heads):
        d.text((x0 + 16, y + 14), head, font=fh, fill=BLUE)

    rows = [
        ('L0 原生\nAndroid 10+ / iOS 15+ / Win10+', '安装标准客户端', 'desktop / tablet / aio / board',
         '完整能力：同屏、批注、白板协作、表决、设备控制'),
        ('L1 降级\nAndroid 7–9 / Win7 SP1 / 2 GB 内存', '安装精简客户端（ES2017 构建）', '同一套内核的差异化产物',
         '阅读、跟随、批注、签到、表决可用；白板只读'),
        ('L2 显示\n老投影、老电视、无系统屏', 'HDMI 采集或无线投屏盒子', 'media-worker 编码分发',
         '只读呈现，作为视频源广播给其他端'),
        ('L3 硬件\n话筒、升降器、桌牌、环境设备', '串口 / 红外 / 继电器 / TCP 驱动', 'Edge Box 边缘网关',
         '指令可控、状态可采、回执可查'),
        ('L4 不可改造\n封闭专用设备', '人工代操作并录入系统', '会议管理端 + 审计',
         '流程可追溯，不产生终端事件'),
    ]
    y = 201
    rh = 118
    for idx, (a, b, c, e) in enumerate(rows):
        fill = WHITE if idx % 2 == 0 else FILL2
        d.rectangle([cols[0][0], y, cols[-1][1], y + rh], fill=fill, outline=LINE)
        vals = [(a, fb), (b, fb), (c, fb), (e, fb)]
        for (x0, x1), (text, font) in zip(cols, vals):
            block(d, (x0 + 16, y + 6, x1 - 12, y + rh - 6), text, font)
        y += rh

    d.text((60, 830), '说明：L1 与 L0 共用同一套代码，仅构建参数与能力开关不同，避免维护两套应用；L3 的驱动以声明式清单描述，现场无需改代码。',
           font=fs, fill=GRAY)
    img.save(OUT / 'legacy.png', dpi=(200, 200))


if __name__ == '__main__':
    arch()
    deploy()
    state()
    sync()
    legacy()
    print('diagrams ready:', sorted(p.name for p in OUT.glob('*.png')))
