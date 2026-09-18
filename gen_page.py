# -*- coding: utf-8 -*-
"""生成 行隅·全国助残岗位导航 展示页（自包含单文件 HTML）"""
import json, re, html, datetime, urllib.parse, os

# ================= 站点所有权验证（请勿删除） =================
# 本站由创建者本人原创开发。创建者持有一个「私密标识」，可随时通过页面 #verify 验证所有权。
# 私密标识不会明文出现在任何生成的页面/代码中，页面只保存其哈希指纹。
# 设置方式（按优先级）：环境变量 OWN_KEY > 本目录 own_key.txt > 内置默认值
_own_key = os.environ.get('OWN_KEY', '')
if not _own_key:
    try:
        with open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'own_key.txt'), encoding='utf-8') as _f:
            _own_key = _f.read().strip()
    except Exception:
        _own_key = ''
if not _own_key:
    _own_key = 'xingyu-origin-2026'   # 默认占位，请设置为你自己的私密标识
def _djb2(s):
    h = 5381
    for ch in s:
        h = ((h * 33) + ord(ch)) & 0xFFFFFFFF
    return format(h, '08x')
OWN_HASH = _djb2(_own_key)
# ================================================================

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, 'jobs_national.json'), encoding='utf-8') as f:
    data = json.load(f)
with open(os.path.join(BASE, 'articles.json'), encoding='utf-8') as f:
    articles = json.load(f)
try:
    with open(os.path.join(BASE, 'logo_b64.txt'), encoding='utf-8') as f:
        LOGO_B64 = f.read().strip()
except Exception:
    LOGO_B64 = ''

# 广告位：从 ads.json 读取（可配置，为空则显示占位）
try:
    with open(os.path.join(BASE, 'ads.json'), encoding='utf-8') as f:
        ADS = json.load(f)
except Exception:
    ADS = {'top': [], 'bottom': []}

jobs = data['jobs']
updated_at = data['updated_at']
total_mh = data.get('total_mh', 0)

# 精简字段，只留展示所需
rows = []
seen_codes = set()
for j in jobs:
    _cd = str(j.get('code', ''))
    if _cd in seen_codes:
        continue
    seen_codes.add(_cd)
    rows.append({
        'n': j.get('name', ''),
        'o': j.get('org', ''),
        'l': j.get('loc', ''),
        'c': j.get('city', ''),
        'p': j.get('prov', ''),
        'd': j.get('dist', ''),
        'e': j.get('edu', ''),
        'm': j.get('num', ''),
        't': j.get('type', ''),
        'pb': j.get('published', ''),
        'up': j.get('updated', ''),
        'dl': j.get('deadline', ''),
        'dy': (j.get('duty') or '')[:80],
        's': j.get('source', ''),
        'u': j.get('url', ''),
        'mh': 1 if j.get('is_mh') else 0,
        'ds': j.get('dis_str', ''),
        'st': j.get('status', 'active'),
        'cd': str(j.get('code', '')),
        'ow': j.get('owner', ''),
    })
total = len(rows)

# 城市->岗位 映射（用于首字母索引）
city_letters = {}
for r in rows:
    city = r['c'] or r['p'] or '其他'
    r['city_key'] = city
    if city not in city_letters:
        city_letters[city] = {'letter': letter_of(city) if False else '', 'count': 0}
    city_letters[city]['count'] += 1

# 从原始 JSON 的 by_letter 拿首字母映射（脚本已算好）
by_letter = data.get('by_letter', {})
city_letter_map = {}
for letter, cities in by_letter.items():
    for city in cities:
        city_letter_map[city] = letter

# 城市总数 & 字母集合
all_cities = sorted(city_letters.keys())
letters_used = sorted(set(city_letter_map.get(c, '#') for c in all_cities))

def esc(s):
    return html.escape(str(s), quote=True)

def _is_off(r):
    """Python 端判断岗位是否已过期/失效（与前端 fmtDeadline 逻辑一致）"""
    if r.get('st') == 'expired':
        return True
    dl = r.get('dl') or ''
    m = re.search(r'(\d{4})[年/\-](\d{1,2})[月/\-](\d{1,2})', dl)
    if not m:
        return False
    try:
        d = datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    except ValueError:
        return False
    return d < datetime.datetime.now()

import re as _re
_DETAIL_RE = _re.compile(r'jobDetail|/job[/?]|job/detail|id=\d', _re.I)
def detail_url(r):
    """详情跳转：有独立岗位详情页就用它；只有公告/列表页的岗位跳天眼查公司页，避免跳到来源站主页。"""
    u = r['u'] or ''
    if _DETAIL_RE.search(u):
        return u
    name = r['o'] or ''
    if name:
        return 'https://www.tianyancha.com/search?key=' + urllib.parse.quote(name)
    return u

# 构建精简 JS 数据（控制体积）
js_rows = []
for r in rows:
    js_rows.append({
        'n': r['n'], 'o': r['o'], 'l': r['l'], 'c': r['c'], 'e': r['e'], 'm': r['m'],
        't': r['t'], 'pb': r['pb'], 'dl': r['dl'], 'dy': r['dy'], 's': r['s'], 'u': r['u'], 'st': r['st'],
        'mh': r['mh'], 'ds': r['ds'], 'cd': r['cd'], 'du': detail_url(r), 'ow': r['ow'],
    })
# 分片：岗位数据按每片 600 条拆成独立 js 文件，页面按需加载；首片内嵌 HTML 保证首屏秒开
# chunk 文件用回调函数交付数据（window.__chunkCb(idx, data)），避免依赖 script onload 时序
CHUNK_SIZE = 600
chunks = [js_rows[i:i+CHUNK_SIZE] for i in range(0, len(js_rows), CHUNK_SIZE)]
for ci, ck in enumerate(chunks):
    with open(os.path.join(BASE, 'jobs_chunk_%d.js' % ci), 'w', encoding='utf-8') as f:
        f.write('window.__chunkCb(%d,%s);' % (ci, json.dumps(ck, ensure_ascii=False)))
js_chunk0 = json.dumps(chunks[0], ensure_ascii=False)
chunk_total = len(chunks)

# 全量统计在 Python 端算好写死，避免 JS 分片加载期间数字跳变

city_js = []
for city in all_cities:
    city_js.append({'name': city, 'letter': city_letter_map.get(city, '#'), 'count': city_letters[city]['count']})
js_cities = json.dumps(city_js, ensure_ascii=False)

HTML_DOC = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data: https:; font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'">
<link rel="manifest" href="manifest.webmanifest">
<meta name="theme-color" content="#2B6DE8">
<link rel="apple-touch-icon" href="icons/icon-192.png">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="行隅">
<meta name="referrer" content="strict-origin-when-cross-origin">
<!-- xingyu-origin: 本站由创建者原创开发，所有权指纹 __OWN_HASH__（#verify 可验证） -->
<title>行隅 · 心智障碍就业导航 - 全国助残岗位信息平台</title>
<meta name="description" content="行隅：为心智障碍（智力残疾、精神残疾）求职者提供全国可投岗位信息导航，聚合中国残联就业服务平台等公开渠道岗位，附就业政策、机构案例、企业故事、投稿与交流，帮助心智障碍青年实现就业。">
<meta name="keywords" content="心智障碍就业,智力残疾就业,精神残疾就业,残疾人岗位,助残就业,支持性就业,行隅">
<meta property="og:title" content="行隅 · 心智障碍就业导航">
<meta property="og:description" content="全国心智障碍可投岗位信息导航，帮助心智障碍青年实现就业。">
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%234F46E5'/><text x='50' y='68' font-size='52' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>行</text></svg>">
<style>
  :root{
    --primary:#4F46E5; --primary-dark:#3730A3; --primary-light:#818CF8; --primary-bg:#EEF2FF;
    --bg:#F4F5F7; --card:#FFFFFF; --text:#1F2937; --sub:#6B7280; --line:#E5E7EB;
    --warn:#DC2626; --ok:#059669; --ink:#1F2937;
  }
  /* 深色模式（html.dark） */
  html.dark{
    --primary:#6366F1; --primary-dark:#818CF8; --primary-bg:#1E293B;
    --bg:#0F172A; --card:#1E293B; --text:#F1F5F9; --sub:#94A3B8; --line:#334155; --ink:#F1F5F9;
  }
  html.dark .header{background:#1E293B}
  html.dark .searchbar{background:#0F172A}
  html.dark .letterbar{background:#1E293B;border-color:#334155}
  html.dark .citytag{background:#1E293B}
  html.dark .notice{background:#172554;border-color:#1E3A8A;color:#DBEAFE}
  html.dark .tieba-banner{background:linear-gradient(135deg,#134E4A,#0F766E)}
  html.dark .zone-big{background:#1E293B;border-color:#334155}
  html.dark .zone-ico{background:linear-gradient(135deg,#6366F1,#818CF8)}
  html.dark .col-big{background:#1E293B;border-color:#334155}
  html.dark .disclaimer{background:#431407;border-color:#7C2D12;color:#FDBA74}
  html.dark .disclaimer b{color:#FDBA74}
  html.dark .dt-card{background:#1E293B}
  html.dark .ap-card{background:#1E293B;border-color:#334155}
  html.dark .adbar{background:#1E293B;border-color:#334155}
  html.dark .empty{color:#94A3B8}
  html.dark .site-footer{color:#94A3B8}
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;background:var(--bg);color:var(--text);padding-bottom:40px}
  /* 顶部 */
  .header{background:var(--primary);color:#fff;padding:14px 16px 12px;position:sticky;top:0;z-index:20;box-shadow:0 2px 8px rgba(79,70,229,.25)}
  .header .htop{display:flex;align-items:center;justify-content:space-between;gap:10px}
  .header .logo{font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px;min-width:0}
  .header .logo img{flex:0 0 auto}
  .header .logo .lname{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .header .logo .dot{width:30px;height:30px;border-radius:9px;background:#fff;color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:17px}
  .header .meta{font-size:12px;opacity:.85;margin-top:6px}
  .header .gear{flex:0 0 auto;width:40px;height:40px;border-radius:10px;border:1px solid rgba(255,255,255,.35);background:rgba(255,255,255,.16);color:#fff;display:flex;align-items:center;justify-content:center;cursor:pointer}
  .header .gear:active{background:rgba(255,255,255,.3)}
  /* 筛选栏（漏斗入口） */
  .filterbar{display:flex;align-items:center;gap:10px;padding:8px 16px;background:var(--primary)}
  .filterbar .fbtn{display:inline-flex;align-items:center;gap:6px;background:#fff;color:var(--primary);border:none;border-radius:10px;padding:8px 14px;font-size:14px;font-weight:600;cursor:pointer;line-height:1.4}
  .filterbar .fbtn svg{flex:0 0 auto}
  .filterbar .fp-meta{font-size:12px;color:#fff;opacity:.92;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;text-align:right}
  /* 筛选面板（右侧抽屉） */
  .fpmask{position:fixed;inset:0;z-index:9996;background:rgba(0,0,0,.35);display:none}
  .fpanel{position:absolute;top:0;right:0;bottom:0;width:min(320px,85vw);background:var(--card);box-shadow:-4px 0 16px rgba(0,0,0,.12);padding:20px 16px;overflow-y:auto}
  .fp-ttl{font-size:15px;font-weight:700;margin-bottom:14px;color:var(--text)}
  .fp-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px}
  .fp-item{display:flex;flex-direction:column;align-items:center;gap:6px;padding:14px 8px;border:1px solid var(--line);background:var(--card);border-radius:12px;font-size:13px;color:var(--text);cursor:pointer}
  .fp-item.on{border-color:var(--primary);background:var(--primary-bg);color:var(--primary);font-weight:600}
  .fp-item svg{width:22px;height:22px;stroke:var(--primary)}
  .fp-item.on svg{stroke:var(--primary)}
  .fp-close{margin-top:14px;width:100%;padding:11px;border:1px solid var(--line);background:none;border-radius:10px;font-size:14px;color:var(--sub);cursor:pointer}
  .iv-say{background:var(--bg);border:1px solid var(--line);border-radius:12px;padding:11px 13px;margin-bottom:10px;font-size:15px;line-height:1.6}
  .iv-say b{color:var(--primary)}
  .iv-opt{display:block;width:100%;text-align:left;background:var(--card);border:1px solid var(--line);border-radius:12px;padding:11px 13px;margin:7px 0;font-size:15px;line-height:1.5;color:var(--text);cursor:pointer}
  .iv-opt:active{background:var(--bg)}
  .iv-fb{margin-top:11px;padding:11px 13px;border-radius:12px;background:rgba(13,148,136,.08);border:1px solid rgba(13,148,136,.28);font-size:14px;line-height:1.7;color:var(--text)}
  .iv-fb b{color:var(--primary)}
  /* 设置面板（齿轮弹出） */
  .setmask{position:fixed;inset:0;z-index:9997;background:rgba(0,0,0,.5);display:none;align-items:center;justify-content:center;padding:20px}
  .setbox{background:var(--card);border-radius:14px;padding:18px;width:100%;max-width:340px}
  .sp-head{display:flex;align-items:center;justify-content:space-between;font-size:16px;font-weight:700;margin-bottom:14px;color:var(--text)}
  .sp-x{background:none;border:none;font-size:18px;color:var(--sub);cursor:pointer;padding:2px 6px}
  .sp-row{display:flex;align-items:center;gap:10px;margin-bottom:12px}
  .sp-k{flex:0 0 44px;font-size:14px;color:var(--text)}
  .sp-row input[type=range]{flex:1;accent-color:var(--primary)}
  .sp-v{flex:0 0 42px;font-size:13px;color:var(--sub);text-align:right}
  .sp-btn{flex:1;background:var(--primary-bg);border:1px solid var(--line);color:var(--primary);font-size:14px;padding:10px 14px;border-radius:10px;cursor:pointer;font-weight:600}
  .sp-btn.on{background:var(--primary);color:#fff;border-color:var(--primary)}
  .sp-tip{font-size:11px;color:var(--sub);line-height:1.5;margin-top:4px}
  html.dark .fpanel,html.dark .setbox{background:#1E293B;border-color:#334155}
  html.dark .fp-item,html.dark .sp-btn{background:#334155;border-color:#475569;color:#E2E8F0}
  html.dark .fp-item.on{background:var(--primary);color:#fff}
  html.dark .fp-item.on svg{stroke:#fff}
  /* 搜索 */
  .searchbar{padding:10px 16px;background:var(--primary);}
  .searchbar input{width:100%;border:none;border-radius:10px;padding:10px 14px;font-size:16px;outline:none;background:#fff}
  /* 城市索引条 */
  .letterbar{background:#fff;border-bottom:1px solid var(--line);padding:8px 10px;position:sticky;top:92px;z-index:15;box-shadow:0 1px 4px rgba(0,0,0,.04)}
  .letterbar .wrap{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
  .letterbar .wrap::-webkit-scrollbar{display:none}
  .letterbar .ltr{flex:0 0 auto;width:32px;height:32px;line-height:32px;text-align:center;border-radius:8px;font-size:14px;font-weight:600;color:var(--sub);cursor:pointer}
  .letterbar .ltr.on{background:var(--primary);color:#fff}
  .letterbar .ltr.dis{color:#D1D5DB;cursor:default}
  .letterbar .all{flex:0 0 auto;padding:0 12px;height:32px;line-height:32px;border-radius:8px;font-size:13px;font-weight:600;color:var(--primary);background:var(--primary-bg);cursor:pointer}
  /* 城市标签区 */
.citytag{padding:10px 16px;background:#fff}
  .citytag .ttl{font-size:12px;color:var(--sub);margin-bottom:8px}
  .citytag .tags{display:flex;flex-wrap:wrap;gap:8px}
  .citytag .tag{padding:6px 12px;border-radius:16px;font-size:13px;background:var(--primary-bg);color:var(--primary-dark);cursor:pointer}
  .citytag .tag.on{background:var(--primary);color:#fff}
  /* 列表 */
  .list{padding:12px 16px;display:flex;flex-direction:column;gap:10px}
  /* 加载更多 */
  .more-wrap{padding:14px 16px 22px;text-align:center}
  .more-btn{display:inline-block;padding:11px 34px;border-radius:24px;border:none;background:var(--primary);color:#fff;font-size:14px;font-weight:600;cursor:pointer;box-shadow:0 2px 8px rgba(79,70,229,.25)}
  .more-btn:hover{opacity:.9}
  .card{background:var(--card);border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .card .row1{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
  .card .nm{font-size:16px;font-weight:700;color:var(--text);flex:1}
  .card .badge{flex:0 0 auto;font-size:11px;padding:3px 8px;border-radius:6px}
  .badge.new{background:#FEE2E2;color:var(--warn)}
  .badge.hot{background:#D1FAE5;color:var(--ok)}
  .badge.norm{background:var(--primary-bg);color:var(--primary)}
  .badge.mh{background:#C7F9CC;color:#0F7B3E;border:1px solid #6EE7A0}
  .badge.soc{background:#2563EB;color:#fff}
  .card .nm a.jlink{color:var(--text);text-decoration:none}
  .card .nm a.jlink:hover{color:var(--primary)}
  .card .ds{font-size:12px;color:#0F7B3E;background:#F0FDF4;border-radius:6px;padding:4px 8px;margin-top:6px;display:inline-block;line-height:1.4}
  .card .org{font-size:13px;color:var(--sub);margin-top:4px;display:flex;align-items:center;gap:4px}
  .card .info{display:flex;flex-wrap:wrap;gap:6px 12px;margin-top:8px;font-size:12px;color:var(--sub)}
  .card .info .i{display:flex;align-items:center;gap:3px}
  .card .duty{font-size:12px;color:var(--sub);margin-top:6px;line-height:1.5}
  .card .tags{display:flex;flex-wrap:wrap;gap:6px;margin-top:8px}
  .card .tag{font-size:11px;color:#2563EB;background:#EFF6FF;border:1px solid #DBEAFE;border-radius:999px;padding:2px 10px;cursor:pointer;line-height:1.7;transition:background .12s}
  .card .tag:hover{background:#DBEAFE}
  .card .tag.mh-tag{color:#065F46;background:#ECFDF5;border-color:#A7F3D0}
  .card .tag.mh-tag:hover{background:#A7F3D0}
  .card .foot{display:flex;justify-content:space-between;align-items:center;margin-top:10px;padding-top:10px;border-top:1px solid var(--line)}
  .card .time{font-size:11px;color:var(--sub)}
  .card .time .dl{color:var(--warn)}
  .card .btns{display:flex;gap:8px}
  .btn{font-size:12px;padding:6px 12px;border-radius:8px;text-decoration:none;display:inline-block}
  .btn.primary{background:var(--primary);color:#fff}
  .btn.ghost{background:var(--primary-bg);color:var(--primary)}
  .btn.orig{background:#F3F4F6;color:var(--sub)}
  /* 空态 */
  .empty{padding:60px 20px;text-align:center;color:var(--sub);font-size:14px}
  /* 免责声明 */
  .disclaimer{margin:16px;padding:12px 14px;background:#FFF7ED;border:1px solid #FED7AA;border-radius:10px;font-size:12px;color:#9A3412;line-height:1.6}
  .disclaimer b{color:#C2410C}
  /* 已选筛选条：职业/心智/城市 tag 多选展示与删除 */
  .filters-bar{display:none;padding:8px 16px;background:#fff;border-bottom:1px solid var(--line)}
  .filters-bar .f-tag{display:inline-flex;align-items:center;gap:5px;font-size:12px;padding:4px 10px;border-radius:14px;margin:2px 6px 2px 0;background:var(--primary-bg);color:var(--primary-dark);cursor:pointer;border:1px solid transparent}
  .filters-bar .f-tag.mh{background:#ECFDF5;color:#065F46;border-color:#A7F3D0}
  .filters-bar .f-tag.city{background:#EFF6FF;color:#1D4ED8;border-color:#BFDBFE}
  .filters-bar .f-tag .x{font-weight:700;opacity:.75}
  .filters-bar .f-tag:hover{opacity:.8}
  .filters-bar .f-clear{display:inline-block;font-size:12px;color:var(--sub);margin-left:6px;cursor:pointer;text-decoration:underline}
  .filters-bar .f-hint{font-size:11px;color:var(--sub);margin-right:8px}
  .tag.on{background:var(--primary);color:#fff;border-color:var(--primary)}
  .tag.mh-tag.on{background:#065F46;color:#fff;border-color:#065F46}
  /* 分享弹窗 */
  .sharemask{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9998;display:none;align-items:center;justify-content:center;padding:20px}
  .sharebox{background:var(--card);border-radius:14px;padding:20px;width:100%;max-width:320px;text-align:center}
  .sharebox h3{font-size:15px;margin-bottom:12px}
  .sharebox .qrimg{width:180px;height:180px;margin:0 auto;border:1px solid var(--line);border-radius:8px;overflow:hidden}
  .sharebox .qrimg img{width:100%;height:100%;display:block}
  .sharebox .share-links{display:flex;gap:8px;margin-top:14px}
  .sharebox .share-links a{flex:1;padding:9px;border-radius:8px;font-size:13px;color:#fff;text-decoration:none}
  .sharebox .close-share{margin-top:12px;font-size:13px;color:var(--sub);cursor:pointer}
  /* 访问统计 */
  .pv{font-size:11px;color:var(--sub);margin-top:4px}
  .pv b{font-weight:600}

  /* 公告条 */
  .notice{background:linear-gradient(90deg,#EEF2FF,#E0E7FF);border-bottom:1px solid #C7D2FE;padding:9px 16px;font-size:13px;color:#3730A3;display:flex;align-items:center;gap:8px;cursor:pointer}
  .notice .ntag{flex:0 0 auto;background:var(--primary);color:#fff;font-size:11px;padding:2px 8px;border-radius:10px;font-weight:600}
  .notice .ntxt{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
  .notice .ngo{flex:0 0 auto;color:var(--primary);font-weight:600}
  .notice .ntag.teal{background:#0D9488}
  /* 贴吧社区大横幅 */
  .tieba-banner{display:flex;align-items:center;justify-content:space-between;gap:12px;margin:10px 16px;padding:14px 16px;border-radius:14px;background:linear-gradient(135deg,#0D9488,#0F766E);color:#fff;cursor:pointer;box-shadow:0 2px 10px rgba(13,148,136,.28)}
  .tb-left{flex:1;min-width:0}
  .tb-badge{display:inline-block;background:rgba(255,255,255,.22);font-size:11px;padding:2px 9px;border-radius:10px;margin-bottom:5px;font-weight:600;letter-spacing:.5px}
  .tb-title{font-size:16px;font-weight:700;line-height:1.35}
  .tb-sub{font-size:12px;opacity:.94;line-height:1.55;margin-top:3px}
  .tb-go{flex:0 0 auto;background:#fff;color:#0F766E;font-size:14px;font-weight:700;padding:10px 18px;border-radius:10px;white-space:nowrap;box-shadow:0 1px 4px rgba(0,0,0,.12)}
  /* 专栏先大后小：三大专区卡片 */
  .zone-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px}
  .zone-big{background:linear-gradient(160deg,#FFFFFF,#F0F7FF);border:1px solid #D6E6F8;border-radius:16px;padding:18px 14px;text-align:center;cursor:pointer;transition:box-shadow .15s}
  .zone-big:hover{box-shadow:0 3px 12px rgba(37,99,235,.14)}
  .zone-ico{width:44px;height:44px;margin:0 auto 8px;border-radius:12px;background:linear-gradient(135deg,#2563EB,#3B82F6);color:#fff;font-size:22px;font-weight:700;display:flex;align-items:center;justify-content:center}
  .zone-tt{font-size:16px;font-weight:700;color:var(--ink)}
  .zone-sub{font-size:12px;color:var(--sub);margin:4px 0 8px;line-height:1.5}
  .zone-cnt{font-size:12px;color:#2563EB;font-weight:600}
  .zone-go{display:inline-block;margin-top:8px;font-size:13px;font-weight:600;color:#fff;background:#2563EB;border-radius:8px;padding:4px 16px}
  .zone-head{display:flex;align-items:center;gap:10px;margin:0 0 10px}
  .zone-head .zone-head-tt{font-size:15px;font-weight:700;color:var(--ink)}
  @media (max-width:640px){.zone-grid{grid-template-columns:1fr}}
  /* 专区内专栏网格 */
  .col-grp-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px}
  .col-grp-cta{grid-column:1/-1;margin-top:4px;background:#F0FDF4;border:1px dashed #86EFAC;border-radius:10px;padding:10px 12px;font-size:13px;color:#065F46;text-align:center}
  @media (max-width:640px){.col-grp-grid{grid-template-columns:repeat(2,1fr)}}

  /* 关于页（全屏覆盖层） */
  .aboutpage{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:var(--bg);z-index:30;overflow-y:auto;padding:0 16px 30px}
  .aboutpage .ap-head{background:var(--primary);color:#fff;margin:0 -16px;padding:16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:5}
  .aboutpage .back-btn{background:rgba(255,255,255,.18);border:none;color:#fff;font-size:13px;padding:7px 14px;border-radius:8px;cursor:pointer}
  .aboutpage .ap-title{font-size:18px;font-weight:700}
  .aboutpage .ap-card{background:var(--card);border-radius:12px;padding:16px;margin-top:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .aboutpage .ap-card h3{font-size:15px;color:var(--primary);margin-bottom:8px;display:flex;align-items:center;gap:6px}
  .aboutpage .ap-card p{font-size:13px;color:var(--text);line-height:1.8}
  .aboutpage .ap-card ul{margin:6px 0 0 18px;font-size:13px;color:var(--text);line-height:1.9}
  .aboutpage .ap-card .hl{background:var(--primary-bg);border-radius:6px;padding:2px 8px;color:var(--primary-dark);font-weight:600}

  /* 页脚署名 */
  .site-footer{margin:20px 16px 8px;text-align:center;font-size:12px;color:var(--sub);line-height:1.8}
  .site-footer .fm{color:var(--primary);font-weight:600;text-decoration:none}
  .site-footer .ver{color:#94A3B8;font-size:11px;margin-left:4px}

  /* 所有权验证页 */
  .verifypage{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:var(--bg);z-index:30;overflow-y:auto;padding:0 16px 30px}
  .verifypage .ap-head{background:var(--primary);color:#fff;margin:0 -16px;padding:16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:5}
  .verifypage .back-btn{background:rgba(255,255,255,.18);border:none;color:#fff;font-size:13px;padding:7px 14px;border-radius:8px;cursor:pointer}
  .verifypage .ap-title{font-size:18px;font-weight:700}
  .verifypage .ap-card{background:var(--card);border-radius:12px;padding:16px;margin-top:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .verifypage .ap-card h3{font-size:15px;color:var(--primary);margin-bottom:8px}
  .verifypage .ap-card p{font-size:13px;color:var(--text);line-height:1.8}

  /* 岗位详情页（全屏覆盖层） */
  .detailpage{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:var(--bg);z-index:30;overflow-y:auto;padding:0 16px 30px}
  .detailpage .ap-head{background:var(--primary);color:#fff;margin:0 -16px;padding:16px;display:flex;align-items:center;gap:10px;position:sticky;top:0;z-index:5}
  .detailpage .back-btn{background:rgba(255,255,255,.18);border:none;color:#fff;font-size:13px;padding:7px 14px;border-radius:8px;cursor:pointer}
  .detailpage .ap-title{font-size:18px;font-weight:700}
  .dt-card{background:var(--card);border-radius:12px;padding:18px;margin-top:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .dt-name{font-size:19px;font-weight:700;color:var(--text);line-height:1.5}
  .dt-org{font-size:14px;color:var(--sub);margin-top:6px}
  .dt-badges{margin-top:10px;display:flex;flex-wrap:wrap;gap:6px}
  .dt-rows{margin-top:14px;border-top:1px dashed var(--line);padding-top:6px}
  .dt-row{display:flex;gap:12px;padding:9px 0;border-bottom:1px solid #f1f3f7;font-size:14px;line-height:1.6}
  .dt-row:last-child{border-bottom:none}
  .dt-k{flex:0 0 84px;color:var(--sub)}
  .dt-v{flex:1;color:var(--text);word-break:break-all}
  .dt-btns{display:flex;gap:10px;margin-top:16px}
  .dt-btns .btn{flex:1;text-align:center}
  .dt-note{font-size:12px;color:var(--sub);line-height:1.7;margin-top:14px;padding:10px 12px;background:#F7F9FC;border-radius:8px}

  /* 广告位 */
  .adbar{background:#fff;border-bottom:1px solid var(--line);padding:8px 16px;display:flex;align-items:center;gap:10px}
  .adbar .adlabel{font-size:11px;color:var(--sub);background:var(--bg);padding:2px 8px;border-radius:4px;flex:0 0 auto}
  .adbar .adbody{flex:1;font-size:13px;color:var(--text)}
  .adbar a{color:var(--primary);text-decoration:none;font-weight:600}
  .adbar .adempty{color:#9CA3AF;font-size:12px}
  /* 城市折叠切换条 */
  .citytoggle{background:#fff;border-bottom:1px solid var(--line);padding:10px 16px;display:flex;align-items:center;justify-content:space-between;cursor:pointer}
  .citytoggle .ct{font-size:13px;font-weight:600;color:var(--primary);display:flex;align-items:center;gap:6px}
  .citytoggle .arrow{transition:transform .2s;font-size:11px;display:inline-block}
  .citytoggle.open .arrow{transform:rotate(180deg)}
  .citytoggle .ctstate{font-size:12px;color:var(--sub)}
  /* 城市区整体（字母条+城市标签），默认收起 */
  .cityzone{display:none;border-bottom:1px solid var(--line);background:#fff}
  .cityzone.show{display:block}
  .letterbar{padding:10px 10px 4px;background:#fff}
  .letterbar .wrap{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
  .letterbar .wrap::-webkit-scrollbar{display:none}
  .letterbar .ltr{flex:0 0 auto;width:32px;height:32px;line-height:32px;text-align:center;border-radius:8px;font-size:14px;font-weight:600;color:var(--sub);cursor:pointer}
  .letterbar .ltr.on{background:var(--primary);color:#fff}
  .letterbar .ltr.dis{color:#D1D5DB;cursor:default}
  .letterbar .all{flex:0 0 auto;padding:0 12px;height:32px;line-height:32px;border-radius:8px;font-size:13px;font-weight:600;color:var(--primary);background:var(--primary-bg);cursor:pointer}
  /* 失效岗位 */
  .card.expired{opacity:.55;background:#F9FAFB}
  .badge.off{background:#E5E7EB;color:#6B7280}
  /* 专栏区 */
  .cols{padding:16px;display:flex;flex-direction:column;gap:16px}
  .col-card{background:var(--card);border-radius:14px;padding:16px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .col-head{display:flex;align-items:center;gap:8px;margin-bottom:12px}
  .col-head .ico{width:30px;height:30px;border-radius:9px;background:var(--primary-bg);color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px}
  .col-head .tt{font-size:16px;font-weight:700}
  .col-head .sub{font-size:11px;color:var(--sub);margin-left:auto}
  .col-item{border-top:1px solid var(--line);padding:10px 0}
  .col-item:first-of-type{border-top:none;padding-top:2px}
  .col-item .t{font-size:14px;font-weight:600;color:var(--text)}
  .col-item .s{font-size:12px;color:var(--sub);margin-top:4px;line-height:1.6}
  .col-item .src{font-size:11px;color:var(--primary);margin-top:4px}
  .col-item .src a{color:var(--primary);text-decoration:none}
  /* 专栏大入口 */
  .cols-title{display:flex;align-items:baseline;gap:10px;padding:0 16px;margin-top:14px}
  .cols-title h2{font-size:19px;font-weight:800;margin:0}
  .cols-title span{font-size:12px;color:var(--sub)}
  .col-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;padding:12px 16px}
  .col-grid > *{grid-column:1/-1}
  .col-grid .col-big{background:var(--card);border-radius:14px;padding:14px 12px;box-shadow:0 1px 3px rgba(0,0,0,.06);cursor:pointer;text-align:center;border:1px solid var(--line);transition:transform .12s,box-shadow .12s;display:flex;flex-direction:column;align-items:center;gap:6px}
  .col-grid .col-big:hover{transform:translateY(-2px);box-shadow:0 4px 12px rgba(79,70,229,.14)}
  .col-grid .col-big .ico{width:40px;height:40px;border-radius:12px;background:var(--primary-bg);color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:19px}
  .col-grid .col-big .tt{font-size:14px;font-weight:700;color:var(--text)}
  .col-grid .col-big .sub{font-size:10px;color:var(--sub);line-height:1.4;min-height:26px}
  .col-grid .col-big .cnt{font-size:11px;color:var(--primary);font-weight:600}
  .col-grid .col-big .go{font-size:12px;color:var(--primary)}
  /* 专栏详情页（全屏 overlay） */
  .colpage{position:fixed;inset:0;background:#F4F5FA;z-index:100;overflow-y:auto;-webkit-overflow-scrolling:touch}
  .colp-head{position:sticky;top:0;background:#fff;padding:14px 16px;display:flex;align-items:center;gap:10px;border-bottom:1px solid var(--line);z-index:2}
  .colp-head .back-btn{border:1px solid var(--line);background:#fff;color:var(--text);border-radius:9px;padding:7px 12px;font-size:13px;cursor:pointer}
  .colp-head .colp-ico{width:30px;height:30px;border-radius:9px;background:var(--primary-bg);color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:15px}
  .colp-head .colp-tt{font-size:16px;font-weight:800}
  .colp-head .colp-sub{font-size:11px;color:var(--sub);margin-left:auto}
  .colp-list{padding:12px 16px 0;display:flex;flex-direction:column;gap:10px}
  .colp-more{padding:16px;text-align:center}
  .colp-more-btn{width:100%;max-width:280px;padding:12px;border:none;border-radius:10px;background:var(--primary);color:#fff;font-size:15px;font-weight:600;cursor:pointer;touch-action:manipulation;-webkit-tap-highlight-color:transparent}
  .colp-more-cnt{font-size:12px;color:var(--sub);margin-top:8px}
  .colp-item{display:block;background:#fff;border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.06);text-decoration:none;color:inherit;border:1px solid var(--line)}
  .colp-item .t{font-size:15px;font-weight:700;color:var(--text);line-height:1.5}
  .colp-item .s{font-size:13px;color:var(--sub);margin-top:6px;line-height:1.7}
  .colp-item .meta{display:flex;align-items:center;gap:8px;margin-top:10px;font-size:11px;color:var(--primary)}
  .colp-item .meta .src{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:60%}
  .colp-item .meta .go{margin-left:auto;font-weight:700}
  /* 收藏 */
  .favbtn{border:1px solid var(--line);background:#fff;border-radius:8px;min-width:34px;height:28px;font-size:15px;cursor:pointer;line-height:1;color:#9CA3AF;flex:0 0 auto}
  .favbtn.on{color:#F59E0B;border-color:#FCD34D;background:#FFFBEB}
  .favtoggle{margin-left:auto;border:1px solid var(--line);background:#fff;border-radius:8px;padding:5px 10px;font-size:12px;cursor:pointer;color:var(--sub)}
  .favtoggle.on{color:var(--primary);border-color:var(--primary);background:var(--primary-bg)}
  @media(max-width:720px){.col-grid{grid-template-columns:repeat(3,1fr);gap:8px;padding:12px 12px}}
  @media(max-width:420px){.col-grid{grid-template-columns:repeat(2,1fr)}}
  /* 投稿区 */
  .submit{margin:0 16px 16px;background:linear-gradient(135deg,#4F46E5,#3730A3);border-radius:14px;padding:20px;color:#fff;text-align:center}
  .submit .t1{font-size:17px;font-weight:700}
  .submit .t2{font-size:13px;opacity:.9;margin-top:6px;line-height:1.6}
  .submit .mail{display:inline-block;margin-top:12px;background:#fff;color:var(--primary);font-weight:700;font-size:15px;padding:8px 18px;border-radius:10px}
  /* 统计条 */
  .stat{display:flex;gap:16px;padding:10px 16px;background:#fff;border-bottom:1px solid var(--line);font-size:12px;color:var(--sub)}
  .stat b{color:var(--primary);font-size:15px}
  /* 数据总览 */
  .statpage{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:var(--bg);z-index:30;overflow-y:auto;padding:0 16px 30px}
  .statcard{background:#fff;border:1px solid var(--line);border-radius:14px;padding:16px;margin-bottom:14px}
  .statcard h3{margin:0 0 12px;font-size:16px;color:var(--main)}
  .stat-sum{display:flex;flex-wrap:wrap;gap:10px}
  .stat-sum .s{flex:1 1 30%;min-width:96px;background:var(--primary-bg);border-radius:12px;padding:12px;text-align:center}
  .stat-sum .s b{display:block;font-size:22px;color:var(--primary);line-height:1.4}
  .stat-sum .s span{font-size:12px;color:var(--sub)}
  .bar-list .br{display:flex;align-items:center;gap:8px;margin:7px 0;font-size:13px}
  .bar-list .br .bn{flex:0 0 96px;color:var(--main);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
  .bar-list .br .bt{flex:0 0 44px;text-align:right;color:var(--primary);font-weight:700}
  .bar-list .br .bw{flex:1;background:var(--primary-bg);border-radius:6px;height:16px;overflow:hidden}
  .bar-list .br .bf{display:block;height:100%;background:var(--primary);border-radius:6px;min-width:2px}
  .bar-pct .pp{display:flex;height:26px;border-radius:8px;overflow:hidden;margin-bottom:10px}
  .bar-pct .pp .pv{background:var(--primary);color:#fff;font-size:12px;line-height:26px;text-align:center}
  .bar-pct .pp .po{background:#F0A6A6;color:#fff;font-size:12px;line-height:26px;text-align:center}
  .bar-pct .lg{font-size:13px;color:var(--sub);display:flex;gap:18px}
  .bar-pct .lg i{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}
  html.dark .statpage{background:transparent}
  html.dark .statcard{background:#1E293B;border-color:#334155}
  /* 求职准备页 */
  .prepage{display:none;position:fixed;top:0;left:0;right:0;bottom:0;background:var(--bg);z-index:30;overflow-y:auto;padding:0 16px 30px}
  /* 打印区（打印时仅显示） */
  .printarea{display:none}
  @media print{
    body *{visibility:hidden}
    .printarea,.printarea *{visibility:visible}
    .printarea{display:block;position:absolute;left:0;top:0;width:100%;background:#fff;color:#000;padding:16px;font-size:12px}
    .printarea h1{font-size:18px;margin:0 0 6px}
    .printarea .pm{color:#555;margin-bottom:10px}
    .printarea .pi{border:1px solid #ccc;border-radius:6px;padding:8px 10px;margin:6px 0;page-break-inside:avoid}
    .printarea .pi b{font-size:13px}
    .printarea .pi .pl{color:#333;font-size:11px;margin-top:3px}
  }
  /* 极简模式（简化版）：大字号大按钮，只留主要内容 */
  body.minmode{font-size:19px}
  body.minmode .card{padding:20px;margin-bottom:16px}
  body.minmode .btn{padding:14px 18px;font-size:16px}
  body.minmode .favbtn{width:52px;height:44px;font-size:22px}
  body.minmode .tag{font-size:15px;padding:7px 12px}
  body.minmode .ad,body.minmode .announce,body.minmode .tieba-banner,body.minmode .meta,body.minmode .disclaimer{display:none}
  body.minmode .fbtn,body.minmode .stat,body.minmode .fpPanel,body.minmode #fpPanel,body.minmode .badge,body.minmode .tag,body.minmode .cols-title,body.minmode .col-grid{display:none}
  body.minmode .stat{font-size:15px}
  body.minmode .card{padding:18px 16px;margin-bottom:14px}
  body.minmode .card .foot{border-top:none;margin-top:10px}
  body.minmode .card .btns .share,body.minmode .card .btns .orig{display:none}
  body.minmode .morewrap button{font-size:17px;padding:14px}
  body.minmode .searchwrap input{font-size:17px;padding:14px 16px}
  body.minmode .fbtn{font-size:16px;padding:11px 16px}
  body.minmode .card .nm{font-size:19px}
  body.minmode .card .org{font-size:15px}
  body.minmode .card .info{font-size:14px}
  html.dark .statcard h3{color:#E2E8F0}
  html.dark .stat-sum .s{background:#0F172A}
  html.dark .bar-list .br .bn{color:#E2E8F0}
  html.dark .bar-list .br .bw{background:#334155}
</style>
</head>
<body>
<div class="header">
  <div class="htop">
    <div class="logo"><img src="data:image/png;base64,UklGRnS8AABXRUJQVlA4WAoAAAAQAAAA/wQA/wQAQUxQSKQ6AAABDzD/ERHyBCQpsiIitOVm2yS7bh5CA3fiVh6ZggMwfDLToTPTkMgNgUsNBBtd9ddf3c37l2cjov8UJMmNG0g1swdDBAyCIBpv8B3btutItm0VWGSmf0KARVyRZctFcyxLkZYAC7no31JhJVFg8RXMfNgYc5A5kdn7QiSN6D8FSXLjSJLPtbUlscELwBvgxrbtOln4UA1hWqM0lUIJhN689+99+pK4DxNF9J+R2zaOdJutHqfNGwAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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UUNaXvybyj+zRXty+e3PAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA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" alt="行隅" style="height:36px;border-radius:8px"> 行隅 · 心智障碍就业导航</div>
    <button class="gear" onclick="openSettings()" title="设置" aria-label="设置"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1-2.83 2.83l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-4 0v-.09a1.65 1.65 0 0 0-1-1.51 1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1 0-4h.09a1.65 1.65 0 0 0 1.51-1 1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 2.83-2.83l.06.06a1.65 1.65 0 0 0 1.82.33h.01a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 4 0v.09a1.65 1.65 0 0 0 1 1.51h.01a1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82v.01a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 0 4h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg></button>
  </div>
  <div class="meta">数据更新：__UPDATED__ · 心智障碍可投  条岗位 · __CITIES__ 个城市</div>
</div>
<div class="adbar"><span class="adlabel">广告位</span><div class="adbody" id="adTop"></div></div>
<div class="notice" onclick="showAbout()">
  <span class="ntag">公告</span>
  <span class="ntxt">行隅 · 心智障碍就业导航正式上线：聚合全国 4000+ 可投岗位，帮助心智障碍青年实现就业。点击查看关于我们</span>
  <span class="ngo">关于 ›</span>
</div>
<div class="tieba-banner" onclick="window.open('https://tieba.baidu.com/f?kw=%E5%BF%83%E7%90%86%E9%9A%9C%E7%A2%8D%E5%B0%B1%E4%B8%9A','_blank','noopener')">
  <div class="tb-left">
    <div class="tb-badge">行隅社区</div>
    <div class="tb-title">心理障碍就业吧 · 官方讨论区</div>
    <div class="tb-sub">来聊聊求职路上的故事和疑问——求职者、家长、机构、志愿者都在这里</div>
  </div>
  <div class="tb-go">前往 ›</div>
</div>
<div class="cols-title"><h2>专栏</h2><span>社会认知 · 真实故事 · 政策教学 · 社会活动</span></div>
<div class="col-grid" id="colGrid"></div>
<div class="searchbar"><input id="q" placeholder="搜索岗位名称、公司、城市…" autocomplete="off"></div>
<div class="filters-bar" id="filtersBar"></div>
<div class="filterbar">
  <button class="fbtn" onclick="toggleFp()" title="筛选与工具"><svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round"><path d="M4 6h16M7 12h10M10 18h4"></path></svg>筛选<svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor"><path d="M6 9l6 6 6-6z"></path></svg></button>
  <span class="fp-meta" id="fpMeta"></span>
</div>
<div class="fpmask" id="fpMask" onclick="if(event.target===this)closeFp()">
  <div class="fpanel" id="fpPanel">
    <div class="fp-ttl">筛选与工具</div>
    <div class="fp-grid">
      <button class="fp-item" id="fpRecent" onclick="toggleRecent()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="9"></circle><path d="M12 7v5l3 3"></path></svg><span>最近3天</span></button>
      <button class="fp-item" id="fpGuide" onclick="openGuide()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="11" cy="11" r="7"></circle><path d="M21 21l-4.35-4.35"></path></svg><span>帮我找岗位</span></button>
      <button class="fp-item" id="fpSoc" onclick="toggleSocFilter()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2l7 3v6c0 5-3.2 8.4-7 11-3.8-2.6-7-6-7-11V5z"></path><path d="M9 12l2 2 4-4"></path></svg><span>国企央企</span></button>
      <button class="fp-item" id="fpHis" onclick="toggleHisMode()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M3 12a9 9 0 1 0 3-6.7L3 8"></path><path d="M3 3v5h5"></path><path d="M12 7v5l3 3"></path></svg><span>历史浏览</span></button>
      <button class="fp-item" id="fpFav" onclick="toggleFavMode()"><svg viewBox="0 0 24 24" width="22" height="22" fill="currentColor" stroke="currentColor" stroke-width="1.4" stroke-linejoin="round"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01z"></path></svg><span>我的收藏</span></button>
      <button class="fp-item" onclick="printList()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M6 9V2h12v7"></path><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg><span>打印清单</span></button>
      <button class="fp-item" onclick="showPrep()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M9 6h6M9 12h6M9 18h6"></path><path d="M5 3h14a1 1 0 0 1 1 1v16a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V4a1 1 0 0 1 1-1z"></path></svg><span>求职准备</span></button>
      <button class="fp-item" onclick="openStats()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 20V10M10 20V4M16 20v-8M22 20H2"></path></svg><span>数据总览</span></button>
      <button class="fp-item" onclick="clearAllFilter()"><svg viewBox="0 0 24 24" width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M18 6L6 18M6 6l12 12"></path></svg><span>清空筛选</span></button>
    </div>
    <button class="fp-close" onclick="closeFp()">收起</button>
  </div>
</div>
<div class="colpage" id="colPage" style="display:none">
  <div class="colp-head">
    <button class="back-btn" onclick="showZoneOf()">← 返回</button>
    <span class="colp-ico" id="colPIco">化</span>
    <span class="colp-tt" id="colPTt">专栏</span>
    <span class="colp-sub" id="colPSub"></span>
  </div>
  <div class="colp-list" id="colPList"></div>
  <div class="colp-more" id="colMoreWrap" style="display:none">
    <button type="button" class="colp-more-btn" id="colMoreBtn">加载更多</button>
    <div class="colp-more-cnt" id="colMoreCnt"></div>
  </div>
</div>
<div class="statpage" id="statsPage" style="display:none">
  <div class="ap-head">
    <button class="back-btn" onclick="showHome()">← 返回首页</button>
    <span class="ap-title">数据总览</span>
  </div>
  <div class="statcard" id="statsSummary"></div>
  <div class="statcard"><h3>城市岗位 TOP10</h3><div class="bar-list" id="statsCity"></div></div>
  <div class="statcard"><h3>岗位类型分布 TOP8</h3><div class="bar-list" id="statsDuty"></div></div>
  <div class="statcard" style="color:var(--sub);font-size:13px;line-height:1.7">数据来源于公开渠道岗位聚合，每日自动更新。统计基于当前已收录的全部岗位，仅供参考。</div>
</div>
<div class="citytoggle" id="cityToggle"><span class="ct">城市筛选 <span class="arrow">▼</span></span><span class="ctstate" id="cityState">展开</span></div>
<div class="cityzone" id="cityZone">
<div class="letterbar"><div class="wrap" id="letters"></div></div>
<div class="citytag"><div class="ttl" id="cityHint">选择城市查看岗位</div><div class="tags" id="tags"></div></div>
</div>


<div class="stat"><span>岗位 <b id="stTotal">__TOTAL__</b></span><span>城市 <b id="stCity">__CITIES__</b></span><span>当前显示 <b id="stShow">0</b></span><span style="margin-left:auto;display:flex;align-items:center;gap:8px;flex-wrap:wrap"><button class="favtoggle" onclick="nearbyJobs()" title="定位到我所在城市，自动筛选该城市岗位"><svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="vertical-align:-2px;margin-right:3px"><path d="M12 21s-7-5.6-7-11a7 7 0 0 1 14 0c0 5.4-7 11-7 11z"></path><circle cx="12" cy="10" r="2.6"></circle></svg>附近岗位</button><button class="favtoggle" id="favToggle" onclick="toggleFavMode()">★ 我的收藏 (<span id="favCount">0</span>)</button><button class="favtoggle" id="favExport" onclick="exportFav()" style="display:none" title="把收藏的岗位整理成文字发给家长/机构">导出收藏</button><label style="display:flex;align-items:center;gap:4px;cursor:pointer"><input type="checkbox" id="onlyValid" checked> 仅看有效</label></span></div>

<div class="list" id="list"></div>
<div class="more-wrap" id="moreWrap" style="display:none"><button class="more-btn" id="moreBtn">加载更多岗位</button></div>
<div class="empty" id="empty" style="display:none">没有找到符合条件的岗位，换个关键词试试</div>
<div class="adbar"><span class="adlabel">广告位</span><div class="adbody" id="adBottom"></div></div>



<div class="submit">
  <div class="t1">想分享你的故事、经验或投稿？</div>
  <div class="t2">欢迎将内容发送至我们的邮箱，审核通过后发布。<br>本平台为纯公益信息导航，不收取任何费用。</div>
  <span class="mail">投稿邮箱：1739528214@qq.com</span>
</div>

<div class="disclaimer"><b>免责声明：</b>本页岗位信息均采集自公开渠道（中国残联就业服务平台、各省市残联与人社部门官网等），仅供求职者参考。信息版权归原发布方所有，岗位真实性、时效性与联系方式以原发布方为准，请自行核实后再联系。<strong>本站仅为公益性信息导航，不代投、不代招、不收取任何费用，与求职者及用人单位之间不存在任何劳动或用工关系，用工安全责任依法由用人单位承担。</strong>建议求职者在监护人陪同下参与求职。若原岗位已招满或过期，以原平台为准。发现虚假或可疑信息，请点击页脚"信息纠错·举报"反馈，我们将及时处理下架。</div>

<div class="aboutpage" id="aboutPage">
  <div class="ap-head">
    <button class="back-btn" onclick="showHome()">← 返回首页</button>
    <span class="ap-title">关于行隅</span>
  </div>
  <div class="ap-card">
    <h3>行隅是什么</h3>
    <p>行隅是一个面向<strong>心智障碍（智力残疾、精神残疾等）求职者</strong>的公益岗位信息导航平台。我们把散落在各官方平台上的助残岗位聚合到一起，让求职者、家长和就业辅导员能在一处找到全国可投的工作机会。</p>
  </div>
  <div class="ap-card">
    <h3>数据从哪里来</h3>
    <p>岗位信息聚合自<strong>中国残联就业服务平台、各省市残联与人社局官网</strong>等公开渠道，每半周自动更新一次，保证时效。信息版权归原发布方所有，仅供参考。</p>
  </div>
  <div class="ap-card">
    <h3>这里有什么</h3>
    <ul>
      <li>全国 <span class="hl">__TOTAL__ 条</span> 助残岗位，按城市、职业、心智等级、有效/失效自由组合筛选</li>
      <li>岗位详情一键跳转原平台，公司信息可查</li>
      <li>两大专区十个专栏：社会认知 · 他们正在做 · 企业故事 · 政策与普法 · 工作教学 · 社会活动 · 支持与服务 · 国际视野 · 企业用工政策 · 企业用工指南</li>
      <li>收藏功能：看中的岗位存下来慢慢看</li>
      <li>无障碍辅助：字号放大、高对比度、朗读、深色模式</li>
    </ul>
  </div>
  <div class="ap-card">
    <h3>企业招聘登记（免费）</h3>
    <p>贵单位有适合心智障碍（智力、精神、自闭症谱系等）求职者的岗位？欢迎免费登记，审核通过后岗位将进入本导航展示，帮助更多需要工作的伙伴找到机会。</p>
    <p>请将以下信息邮件发送至 <span class="hl mailcopy" title="点击复制邮箱">1739528214@qq.com</span>（主题注明"企业招聘登记"）：单位名称、岗位名称、招聘人数、工作地点、学历与年龄要求、适合的残疾类型、薪资待遇、联系方式。</p>
    <p><a class="btn primary" href="mailto:1739528214@qq.com?subject=行隅企业招聘登记&body=单位名称：%0A岗位名称：%0A招聘人数：%0A工作地点：%0A学历要求：%0A年龄要求：%0A适合残疾类型（智力/精神/自闭症/其他）：%0A薪资待遇：%0A联系方式：%0A%0A（本平台为公益信息导航，不收取任何费用）" style="text-decoration:none">立即邮件登记 ›</a></p>
  </div>
  <div class="ap-card">
    <h3>如何投稿与合作</h3>
    <p><strong>投稿</strong>：欢迎分享你的故事、经验或建议，发送至邮箱 <span class="hl mailcopy" title="点击复制邮箱">1739528214@qq.com</span>（点击可复制），审核通过后会在专栏发布。</p>
    <p><strong>合作</strong>：企业想发布助残岗位、公益组织想开展合作、媒体想了解更多，也请邮件联系 <span class="hl mailcopy" title="点击复制邮箱">1739528214@qq.com</span>（主题注明"合作"），我们会尽快回复。本平台为纯公益信息导航，<strong>不向求职者收取任何费用</strong>。</p>
  </div>
  <div class="ap-card">
    <h3>项目原创与保护</h3>
    <p>行隅为<strong>原创项目</strong>，网站、标识、专栏内容与整体设计均由作者原创开发，请勿盗用或冒名使用。</p>
    <p>本站全部代码在公开代码托管平台留有<strong>带时间戳的提交记录</strong>（可精确到分钟、不可篡改），配合页面"所有权验证"指纹，可作为原创时间的最直接证明。</p>
  </div>
  <div class="ap-card">
    <h3>免责声明</h3>
    <p>行隅为<strong>公益性信息导航平台</strong>，仅做公开信息的聚合与展示：<strong>不代投、不代招、不收取任何费用、不与任何企业分成，与求职者及用人单位之间不存在劳动或用工关系</strong>。</p>
    <p>岗位信息采集自中国残联就业服务平台、各省市残联与人社部门官网等公开渠道，真实性、时效性与联系方式以原发布方为准，请自行核实后再联系。用工安全责任依法由用人单位承担。</p>
    <p>建议求职者在监护人陪同下参与求职流程，注意辨别信息，必要时联系当地残联或 12385 服务热线核实。</p>
    <p>发现虚假或可疑信息，请邮件至 <span class="hl">1739528214@qq.com</span> 举报，我们将及时处理下架。</p>
  </div>
</div>

<div class="site-footer">
  <div>© 2026 行隅 · 心智障碍就业导航 · 原创开发 <span class="ver">v2.22</span></div>
  <div><a class="fm" onclick="openShare()" style="cursor:pointer">分享站点 ›</a>　<a href="mailto:1739528214@qq.com?subject=行隅投稿" class="fm">投稿 ›</a>　<a href="mailto:1739528214@qq.com?subject=行隅合作" class="fm">合作 ›</a>　<a href="mailto:1739528214@qq.com?subject=行隅信息纠错%2F举报" class="fm">信息纠错 · 举报 ›</a>　<a href="#about" class="fm">原创项目 · 盗用追责 ›</a>　<a href="#verify" class="fm">所有权验证 ›</a></div>
</div>

<div class="setmask" id="setMask" onclick="if(event.target===this)closeSettings()">
  <div class="setbox">
    <div class="sp-head">设置<button class="sp-x" onclick="closeSettings()" aria-label="关闭">×</button></div>
    <div class="sp-row"><span class="sp-k">字号</span><input type="range" id="zoomRange" min="85" max="140" value="100" oninput="setZoom(this.value)"><b class="sp-v" id="zoomVal">100%</b></div>
    <div class="sp-row"><button class="sp-btn" id="darkBtn" onclick="toggleDark()">深色模式</button></div>
    <div class="sp-row"><button class="sp-btn" id="minBtn" onclick="toggleMin()">简化版</button></div>
    <div class="sp-row"><button class="sp-btn" id="readBtn" onclick="toggleRead()">朗读</button></div>
    <div class="sp-row"><button class="sp-btn" onclick="resetAll()">恢复默认</button></div>
    <div class="sp-tip">简化版 = 最简界面：隐藏横幅和次要内容，只保留搜索、筛选和岗位列表。</div>
  </div>
</div>
<div class="sharemask" id="shareMask" onclick="if(event.target===this)closeShare()">
  <div class="sharebox">
    <h3>分享「行隅」给需要的人</h3>
    <div class="qrimg"><img id="shareQr" alt="微信扫码打开" src="https://api.qrserver.com/v1/create-qr-code/?size=260x260&margin=10&data=https%3A%2F%2Fjames-liang-o.github.io%2Fxingyu-jobs%2F"></div>
    <p style="font-size:12px;color:var(--sub);margin-top:8px">微信扫一扫，打开后可转发给求职者、家长与朋友</p>
    <div class="share-links">
      <a style="background:#07C160" href="javascript:;" onclick="copyShare()">复制链接</a>
      <a style="background:#12B7F5" target="_blank" rel="noopener noreferrer" href="https://connect.qq.com/widget/shareqq/index.html?url=https%3A%2F%2Fjames-liang-o.github.io%2Fxingyu-jobs%2F&title=行隅·心智障碍就业导航&summary=全国助残岗位聚合导航，帮助心智障碍青年实现就业">QQ</a>
    </div>
    <div class="close-share" onclick="closeShare()">关闭</div>
  </div>
</div>

<div class="sharemask" id="guideMask" onclick="if(event.target===this)closeGuide()">
  <div class="sharebox" style="max-width:480px;text-align:left">
    <h3 style="text-align:center">帮我找岗位</h3>
    <div id="gStep" style="font-size:14px;color:var(--text);min-height:120px"></div>
    <div style="display:flex;gap:8px;justify-content:space-between;margin-top:14px">
      <button class="btn ghost" id="gPrev" onclick="guidePrev()" style="display:none">上一步</button>
      <button class="btn" id="gNext" onclick="guideNext()" style="margin-left:auto">下一步</button>
    </div>
    <div class="close-share" style="text-align:center" onclick="closeGuide()">关闭</div>
  </div>
</div>

<div class="sharemask" id="ivMask" onclick="if(event.target===this)closeIv()">
  <div class="sharebox" style="max-width:480px;text-align:left">
    <h3 style="text-align:center">面试陪练</h3>
    <div id="ivProg" style="text-align:center;font-size:12px;color:var(--sub);margin-bottom:8px"></div>
    <div id="ivBox" style="font-size:15px;color:var(--text);min-height:150px"></div>
    <div style="display:flex;gap:8px;justify-content:space-between;margin-top:14px">
      <button class="btn ghost" id="ivPrevBtn" onclick="ivPrev()" style="display:none">上一步</button>
      <button class="btn" id="ivReadBtn" onclick="ivRead()" style="margin-left:auto">朗读</button>
      <button class="btn" id="ivNextBtn" onclick="ivNext()" style="display:none">下一步</button>
    </div>
    <div class="close-share" style="text-align:center" onclick="closeIv()">关闭</div>
  </div>
</div>

<div class="prepage" id="prePage">
  <div class="ap-head">
    <button class="back-btn" onclick="showHome()">← 返回首页</button>
    <span class="ap-title">求职准备清单</span>
  </div>
  <div class="ap-card" style="border:2px solid var(--ac,#2f6bff);background:linear-gradient(135deg,#eef4ff,#f7faff)">
    <h3 style="margin-top:0">面试陪练 <span style="font-size:12px;color:var(--ac,#2f6bff);border:1px solid var(--ac,#2f6bff);border-radius:10px;padding:1px 8px;vertical-align:2px">情景模拟</span></h3>
    <p style="font-size:14px;color:#555;line-height:1.8;margin:8px 0 12px">模拟真实面试：自我介绍、谈时间、谈工资，一步步陪你说到不紧张。说错了也没关系，不判对错，只陪你练。</p>
    <button class="btn" style="width:100%" onclick="openIv()">开始练习</button>
  </div>
  <div class="ap-card">
    <h3>面试/入职要带什么</h3>
    <ul>
      <li>身份证（原件）</li>
      <li>残疾证（如有，带上原件和复印件）</li>
      <li>银行卡（本人名下，用于发工资）</li>
      <li>1 寸或 2 寸照片 2-3 张</li>
      <li>毕业证/培训证（如有）</li>
      <li>紧急联系人电话（写在一张纸上，放包里）</li>
    </ul>
  </div>
  <div class="ap-card">
    <h3>面试当天小贴士</h3>
    <ul>
      <li>提前查好路线，比约定时间早到 10-15 分钟</li>
      <li>不清楚的地方，礼貌地请对方再说一遍</li>
      <li>可以请家人或机构老师陪同，提前和公司说明</li>
      <li>如果面试中感到紧张，先深呼吸，慢慢回答</li>
      <li>记住面试官的名字和电话，方便联系</li>
    </ul>
  </div>
  <div class="ap-card">
    <h3>入职后要确认的事</h3>
    <ul>
      <li>工资怎么发、多久发一次</li>
      <li>每天几点上班、几点下班、怎么休息</li>
      <li>工作内容找谁问、有事请假找谁</li>
      <li>有没有五险一金（社保）</li>
      <li>住宿和吃饭怎么安排</li>
    </ul>
  </div>
  <div class="ap-card">
    <h3>遇到问题怎么办</h3>
    <ul>
      <li>工资没发、被不公平对待 → 找当地劳动保障监察部门，或打 12333</li>
      <li>权益受侵害 → 打 12348 法律援助热线（免费咨询）</li>
      <li>残疾人专项服务 → 打 12385 残疾人服务热线</li>
      <li>紧急情况 → 110（报警）、120（急救）、119（火警）</li>
      <li>心理需要倾诉 → 12356 全国心理援助热线</li>
    </ul>
  </div>
</div>

<div class="printarea" id="printArea"></div>

<div class="verifypage" id="verifyPage">
  <div class="ap-head">
    <button class="back-btn" onclick="showHome()">← 返回首页</button>
    <span class="ap-title">所有权验证</span>
  </div>
  <div class="ap-card">
    <h3>本站原创声明</h3>
    <p>本站（行隅 · 心智障碍就业导航）由创建者本人原创开发。创建者持有一个私密标识，通过下方验证即可当场确认本站所有权。该标识仅保存在创建者本人处，页面与源码中均不出现明文。</p>
  </div>
  <div class="ap-card">
    <h3>输入私密标识</h3>
    <p>请输入创建者私密标识完成验证。标识只在本机进行比对，不联网、不存储、不上传。</p>
    <input id="ownInput" type="password" placeholder="请输入私密标识" autocomplete="off" style="width:100%;padding:10px 14px;border:1px solid var(--line);border-radius:8px;font-size:15px;margin-top:8px">
    <button id="ownBtn" style="width:100%;margin-top:10px;padding:11px;border:none;border-radius:8px;background:var(--primary);color:#fff;font-size:15px;font-weight:600;cursor:pointer">验证</button>
    <div id="ownResult" style="margin-top:10px;font-size:14px;line-height:1.7"></div>
  </div>
</div>

<div class="detailpage" id="detailPage">
  <div class="ap-head">
    <button class="back-btn" onclick="backFromDetail()">← 返回</button>
    <span class="ap-title">岗位详情</span>
  </div>
  <div class="dt-card">
    <div class="dt-name" id="dtName"></div>
    <div class="dt-org" id="dtOrg"></div>
    <div class="dt-badges" id="dtBadges"></div>
    <div class="dt-rows" id="dtRows"></div>
    <div class="dt-btns" id="dtBtns"></div>
    <div class="dt-note">岗位信息聚合自公开渠道，仅供求职导航参考，具体以原平台为准。原平台查看详情可能需要注册登录；信息版权归原发布方所有。本平台为纯公益信息导航，不收取任何费用，与求职者及用人单位之间不存在劳动或用工关系。</div>
    <div class="dt-note" style="margin-top:8px">发现该岗位虚假、可疑或已失效？<a class="fm" href="mailto:1739528214@qq.com?subject=行隅岗位举报：请填写岗位名称&body=举报岗位：请填写岗位名称%0A岗位来源：%0A举报原因：虚假招聘 / 诈骗 / 其他">点击邮件举报 ›</a>（点击后将打开邮件程序，收件人已填好；如未打开，请复制邮箱 <span class="mailcopy" title="点击复制邮箱">1739528214@qq.com</span> 手动发送）我们将及时处理下架。</div>
  </div>
</div>

<script>
// ===== 安全工具 =====
// 邮箱一键复制 + 轻提示
function toast(msg){
  var el = document.getElementById('toast');
  if(!el){
    el = document.createElement('div'); el.id = 'toast';
    el.style.cssText = 'position:fixed;left:50%;bottom:90px;transform:translateX(-50%);background:rgba(0,0,0,.78);color:#fff;padding:10px 18px;border-radius:10px;font-size:14px;z-index:9999;transition:opacity .3s;pointer-events:none';
    document.body.appendChild(el);
  }
  el.textContent = msg; el.style.opacity = '1';
  clearTimeout(el._t); el._t = setTimeout(function(){ el.style.opacity = '0'; }, 2200);
}
document.addEventListener('click', function(e){
  var t = e.target;
  while(t && t !== document){
    if(t.classList && t.classList.contains('mailcopy')){
      var em = '1739528214@qq.com';
      if(navigator.clipboard && navigator.clipboard.writeText){
        navigator.clipboard.writeText(em).then(function(){ toast('邮箱已复制：' + em); }).catch(function(){ toast('邮箱：' + em); });
      } else {
        var ta = document.createElement('textarea');
        ta.value = em; ta.style.cssText = 'position:fixed;opacity:0';
        document.body.appendChild(ta); ta.select();
        try{ document.execCommand('copy'); toast('邮箱已复制：' + em); }catch(_){ toast('邮箱：' + em); }
        document.body.removeChild(ta);
      }
      return;
    }
    t = t.parentNode;
  }
});
// HTML 转义：所有插入 innerHTML 的外部数据必须经过 esc()
function esc(s){
  return String(s == null ? '' : s)
    .replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;')
    .replace(/"/g,'&quot;').replace(/'/g,'&#39;');
}
// 只允许 http/https/mailto 协议，防 javascript: 等危险协议注入
function safeUrl(u){
  if(!u) return '#';
  u = String(u).trim();
  if(/^(https?:|mailto:)/i.test(u)) return u;
  return '#';
}
var JOBS = __JS_CHUNK0__;
var CITIES = __JS_CITIES__;
var CHUNK_TOTAL = __CHUNK_TOTAL__;
var CHUNK_LOADED = 1;
var curLetter = '全部', kw = '';
var selMh = [], selOcc = [], selCities = [];  // tag 多选：心智(OR)、职业(OR)；心智与职业之间为 AND
var recentOnly = false;
var onlyValid = true;

// 分片加载：chunk 文件执行时调用 __chunkCb 把数据交回（不依赖 onload 时序，file:// 与线上均可靠）
window.__chunkCb = function(idx, data){
  JOBS = JOBS.concat(data);
  if(idx + 1 > CHUNK_LOADED) CHUNK_LOADED = idx + 1;
};
function loadChunk(i){
  if(i < CHUNK_TOTAL && CHUNK_LOADED <= i){
    var s = document.createElement('script');
    s.src = 'jobs_chunk_'+i+'.js';
    s.onerror = function(){ if(CHUNK_LOADED <= i) CHUNK_LOADED = i + 1; };
    document.head.appendChild(s);
  }
}
function waitUntil(fn, cb, tries){
  tries = tries || 0;
  if(fn()){ cb && cb(); return; }
  if(tries > 150){ cb && cb(); return; }  // 上限约 9 秒，超时用已加载数据渲染
  setTimeout(function(){ waitUntil(fn, cb, tries + 1); }, 60);
}
// 加载全部剩余分片后回调
function ensureAll(cb){
  if(CHUNK_LOADED >= CHUNK_TOTAL){ cb && cb(); return; }
  for(var i = CHUNK_LOADED; i < CHUNK_TOTAL; i++) loadChunk(i);
  waitUntil(function(){ return CHUNK_LOADED >= CHUNK_TOTAL; }, cb);
}
// 只加载下一片（用于"加载更多"浏览）
function ensureNext(cb){
  if(CHUNK_LOADED >= CHUNK_TOTAL){ cb && cb(); return; }
  var target = CHUNK_LOADED;
  loadChunk(target);
  waitUntil(function(){ return CHUNK_LOADED > target; }, cb);
}

// 字母条：默认收起，点击展开
var cityToggle = document.getElementById('cityToggle');
// 防iframe嵌套冒充本站
try{ if(window.top && window.top !== window.self){ window.top.location.replace(window.self.location.href); } }catch(e){}
var cityZone = document.getElementById('cityZone');
cityToggle.addEventListener('click', function(){
  var open = cityZone.classList.toggle('show');
  cityToggle.classList.toggle('open', open);
  document.getElementById('cityState').textContent = open ? '收起' : '展开';
});
var LETTERS = ['全部'].concat([...new Set(CITIES.map(function(c){return c.letter}))].sort());
var lettersEl = document.getElementById('letters');
LETTERS.forEach(function(L){
  var d = document.createElement('div');
  d.className = 'ltr' + (L==='全部'?' all':'') + (L==='#'?' dis':'');
  d.textContent = L;
  if(L==='#'){
    d.addEventListener('click', function(){});
  } else {
    d.addEventListener('click', function(){ curLetter = L; shownMax = PAGE_SIZE; renderCities(); ensureAll(function(){ render(); }); });
  }
  lettersEl.appendChild(d);
});

// 有效/失效筛选
document.getElementById('onlyValid').addEventListener('change', function(){
  onlyValid = this.checked;
  shownMax = PAGE_SIZE;
  ensureAll(function(){ render(); });
});

// 收藏按钮事件委托
document.getElementById('list').addEventListener('click', function(ev){
  var btn = ev.target.closest ? ev.target.closest('.favbtn') : null;
  if(btn){ ev.preventDefault(); toggleFav(btn.getAttribute('data-c')); }
});
// 广告位渲染
var ADS = {"top": [], "bottom": []};
function renderAds(){
  var top = ADS.top || [], bot = ADS.bottom || [];
  function fill(id, list){
    var el = document.getElementById(id);
    if(list && list.length){
      var a = list[0];
      el.innerHTML = '<a href="'+safeUrl(a.url)+'" target="_blank" rel="noopener noreferrer">'+esc(a.text||'广告')+'</a>';
    } else {
      el.innerHTML = '<span class="adempty">广告位 · 诚招爱心企业</span>';
    }
  }
  fill('adTop', top); fill('adBottom', bot);
}
renderAds();

// 专栏渲染
// ===== 专栏（数据由 articles.json 生成） =====
var COLS_DATA = __COLS_DATA__;
var colTotal = 0;
for(var cki in COLS_DATA){ colTotal += (COLS_DATA[cki] || []).length; }
var COLDEF = {
  'social':  {'ico':'化','tt':'社会化专栏','sub':'帮助心智障碍者融入社会','grp':'job'},
  'doing':   {'ico':'行','tt':'他们正在做','sub':'各地机构与真实案例','grp':'job'},
  'company': {'ico':'企','tt':'企业故事','sub':'在行动的企业','grp':'com'},
  'emp': {'ico':'惠','tt':'企业用工政策','sub':'招用残疾人的税收优惠与补贴','grp':'com'},
  'guide': {'ico':'册','tt':'企业用工指南','sub':'怎么招、怎么留：实操方法与成功案例','grp':'com'},
  'policy':  {'ico':'策','tt':'政策与普法','sub':'国家政策与法律知识','grp':'job'},
  'teach':   {'ico':'学','tt':'工作教学','sub':'实用技能与方法','grp':'job'},
  'activity':{'ico':'动','tt':'社会活动','sub':'可参与的非营利活动','grp':'job'},
  'resource':{'ico':'寻','tt':'资源导航','sub':'去哪里找帮助','grp':'job'},
  'intl':    {'ico':'际','tt':'国际视野','sub':'国际官方发布','grp':'job'},
  'support': {'ico':'助','tt':'支持与服务','sub':'教育·康复·生活·安置','grp':'job'}
};
function colCount(key){ return (COLS_DATA[key]||[]).length; }
// 专栏三区：先显示三个大区，点进区后再显示区内专栏
var COL_GROUPS = [
  ['job',   '求职者专区', '求职者自己看：故事·教学·政策·支持与服务（家长也可参考）'],
  ['com',   '企业专区',   '企业与机构看：助残岗位、公益合作与用工政策']
];
var ZONE_ICO = {'job':'人','com':'企'};
var curZone = '';
function colCard(key){
  var def = COLDEF[key], cnt = colCount(key);
  var d = document.createElement('div');
  d.className = 'col-big';
  d.innerHTML = '<div class="ico">'+def.ico+'</div><div class="tt">'+def.tt+'</div><div class="sub">'+def.sub+'</div><div class="cnt">'+cnt+' 篇内容</div><div class="go">进入专栏 ›</div>';
  d.addEventListener('click', function(){ showCol(key); });
  return d;
}
function zoneCard(grp){
  var g = null;
  COL_GROUPS.forEach(function(x){ if(x[0] === grp) g = x; });
  var keys = Object.keys(COLDEF).filter(function(k){ return COLDEF[k].grp === grp; });
  var cnt = 0;
  keys.forEach(function(k){ cnt += colCount(k); });
  var d = document.createElement('div');
  d.className = 'zone-big';
  d.innerHTML = '<div class="zone-ico">'+ZONE_ICO[grp]+'</div><div class="zone-tt">'+g[1]+'</div><div class="zone-sub">'+g[2]+'</div><div class="zone-cnt">'+keys.length+' 个专栏 · '+cnt+' 篇内容</div><div class="zone-go">进入 ›</div>';
  d.addEventListener('click', function(){ showZone(grp); });
  return d;
}
function showZone(grp){
  curZone = grp;
  var g = null;
  COL_GROUPS.forEach(function(x){ if(x[0] === grp) g = x; });
  var keys = Object.keys(COLDEF).filter(function(k){ return COLDEF[k].grp === grp; });
  var el = document.getElementById('colGrid');
  el.innerHTML = '';
  var head = document.createElement('div');
  head.className = 'zone-head';
  head.innerHTML = '<button class="back-btn" onclick="renderColGrid()">← 返回分区</button><span class="zone-head-tt">'+g[1]+'</span>';
  el.appendChild(head);
  var grid = document.createElement('div');
  grid.className = 'col-grp-grid';
  keys.forEach(function(k){ grid.appendChild(colCard(k)); });
  if(grp === 'com'){
    var cta = document.createElement('div');
    cta.className = 'col-grp-cta';
    cta.innerHTML = '企业想发布助残岗位、开展公益合作？<a class="fm" href="mailto:1739528214@qq.com?subject=行隅合作">邮件联系 ›</a>';
    grid.appendChild(cta);
  }
  el.appendChild(grid);
  window.scrollTo(0, 0);
}
function renderColGrid(){
  curZone = '';
  var el = document.getElementById('colGrid'); el.innerHTML = '';
  var wrap = document.createElement('div');
  wrap.className = 'zone-grid';
  COL_GROUPS.forEach(function(g){ wrap.appendChild(zoneCard(g[0])); });
  el.appendChild(wrap);
}
var colKey = '';
var colShown = 0;
var COL_PAGE = 10;
function showCol(key){
  colKey = key;
  colShown = 0;
  var btn = document.getElementById('colMoreBtn');
  btn.disabled = false;
  btn.style.opacity = '1';
  var def = COLDEF[key] || COLDEF['social'];
  var items = COLS_DATA[key] || [];
  document.getElementById('colPIco').textContent = def.ico;
  document.getElementById('colPTt').textContent = def.tt;
  document.getElementById('colPSub').textContent = items.length + ' 篇 · ' + def.sub;
  document.getElementById('colPList').innerHTML = '';
  if(!items.length){
    document.getElementById('colPList').innerHTML = '<div style="text-align:center;color:var(--sub);padding:40px 0;font-size:14px">内容筹备中，欢迎投稿</div>';
    document.getElementById('colMoreWrap').style.display = 'none';
  } else {
    appendColItems();
  }
  document.getElementById('colPage').style.display = 'block';
  document.getElementById('colPage').scrollTop = 0;
  window.scrollTo(0,0);
}
function appendColItems(){
  var items = COLS_DATA[colKey] || [];
  var list = document.getElementById('colPList');
  var end = Math.min(colShown + COL_PAGE, items.length);
  for(var i = colShown; i < end; i++){
    var it = items[i];
    var a = document.createElement('a');
    a.className = 'colp-item';
    a.href = safeUrl(it.u); a.target = '_blank'; a.rel = 'noopener noreferrer';
    var sum = it.s ? '<div class="s">'+esc(it.s)+'</div>' : '';
    a.innerHTML = '<div class="t">'+esc(it.t)+'</div>'+sum+'<div class="meta"><span class="src">来源：'+esc(it.o)+'</span><span>'+esc(it.d)+'</span><span class="go">阅读全文 ›</span></div>';
    list.appendChild(a);
  }
  colShown = end;
  var mw = document.getElementById('colMoreWrap');
  var btn = document.getElementById('colMoreBtn');
  if(colShown < items.length){
    btn.disabled = false;
    btn.style.opacity = '1';
    mw.style.display = 'block';
    btn.textContent = '加载更多（' + (items.length - colShown) + '）';
    document.getElementById('colMoreCnt').textContent = '已加载 ' + colShown + ' / ' + items.length + ' 篇';
  } else {
    mw.style.display = 'block';
    btn.textContent = '已全部加载';
    btn.disabled = true;
    btn.style.opacity = '.55';
    document.getElementById('colMoreCnt').textContent = '共 ' + items.length + ' 篇';
  }
}
// 事件委托绑定：兼容移动端浏览器绑定时机/重渲染问题，且只触发一次
document.getElementById('colPage').addEventListener('click', function(e){
  var t = e.target;
  while(t && t !== this){
    if(t.id === 'colMoreBtn'){ appendColItems(); return; }
    t = t.parentNode;
  }
});
function showZoneOf(){
  document.getElementById('colPage').style.display = 'none';
  showZone(COLDEF[colKey] ? COLDEF[colKey].grp : 'job');
}
function backFromDetail(){
  document.getElementById('detailPage').style.display = 'none';
  document.getElementById('colPage').style.display = 'none';
  document.getElementById('aboutPage').style.display = 'none';
  document.getElementById('verifyPage').style.display = 'none';
  document.getElementById('statsPage').style.display = 'none';
  document.getElementById('prePage').style.display = 'none';
  renderColGrid();
  try{ window.scrollTo(0, savedScrollY); }catch(e){}
}
function showHome(){
  document.getElementById('prePage').style.display = 'none';
  document.getElementById('statsPage').style.display = 'none';
  document.getElementById('colPage').style.display = 'none';
  document.getElementById('aboutPage').style.display = 'none';
  document.getElementById('verifyPage').style.display = 'none';
  document.getElementById('detailPage').style.display = 'none';
  renderColGrid();
}
function showAbout(){
  document.getElementById('colPage').style.display = 'none';
  document.getElementById('aboutPage').style.display = 'block';
  document.getElementById('verifyPage').style.display = 'none';
  document.getElementById('detailPage').style.display = 'none';
  document.getElementById('aboutPage').scrollTop = 0;
  window.scrollTo(0,0);
}
function showVerify(){
  document.getElementById('colPage').style.display = 'none';
  document.getElementById('aboutPage').style.display = 'none';
  document.getElementById('verifyPage').style.display = 'block';
  document.getElementById('detailPage').style.display = 'none';
  document.getElementById('verifyPage').scrollTop = 0;
  window.scrollTo(0,0);
}
// 岗位详情页（站内展示，避免原平台登录墙）
function findJob(cd){
  for(var i = 0; i < JOBS.length; i++){ if(JOBS[i].cd === cd) return JOBS[i]; }
  return null;
}
var savedScrollY = 0;
function showJob(cd){
  addHis(cd);
  savedScrollY = window.scrollY || document.documentElement.scrollTop || 0;
  var j = findJob(cd);
  if(!j){ ensureAll(function(){ showJob(cd); }); return; }
  document.getElementById('colPage').style.display = 'none';
  document.getElementById('aboutPage').style.display = 'none';
  document.getElementById('verifyPage').style.display = 'none';
  document.getElementById('detailPage').style.display = 'block';
  document.getElementById('detailPage').scrollTop = 0;
  window.scrollTo(0,0);
  document.getElementById('dtName').textContent = j.n;
  document.getElementById('dtOrg').textContent = j.o;
  var isOff = j.st === 'expired' || (j.dl && fmtDeadline(j.dl) === '已截止');
  var dl = fmtDeadline(j.dl);
  var b = isOff ? '<span class="badge off">已失效</span>' : '<span class="badge new">有效</span>';
  if(j.mh) b += '<span class="badge mh">心智障碍可投</span>';
  if(!isOff && dl && dl.indexOf('天后截止') >= 0) b += '<span class="badge hot">即将截止</span>';
  document.getElementById('dtBadges').innerHTML = b;
  var rows = [];
  if(j.ds) rows.push(['适合残疾类型', j.ds]);
  if(j.l) rows.push(['工作地点', j.l]);
  if(j.e) rows.push(['学历要求', j.e]);
  if(j.m) rows.push(['招聘人数', j.m + ' 人']);
  if(j.t) rows.push(['岗位类型', j.t]);
  if(j.dy) rows.push(['岗位分类', j.dy]);
  rows.push(['发布时间', fmtTime(j.pb)]);
  if(dl) rows.push(['截止时间', dl]);
  if(j.s) rows.push(['信息来源', j.s]);
  var rh = '';
  rows.forEach(function(r){
    rh += '<div class="dt-row"><span class="dt-k">' + esc(r[0]) + '</span><span class="dt-v">' + esc(r[1]) + '</span></div>';
  });
  document.getElementById('dtRows').innerHTML = rh;
  document.getElementById('dtBtns').innerHTML =
    '<a class="btn ghost" target="_blank" rel="noopener noreferrer" href="' + safeUrl(j.u) + '">前往原平台</a>' +
    '<a class="btn orig" target="_blank" rel="noopener noreferrer" href="' + companyUrl(j.o) + '">查公司</a>';
}
// 所有权验证：djb2 哈希与页面指纹比对（标识本身不出现、不上传）
var OWN_HASH = '__OWN_HASH__';
function djb2(s){
  var h = 5381;
  for(var i = 0; i < s.length; i++){ h = ((h * 33) + s.charCodeAt(i)) >>> 0; }
  return ('00000000' + h.toString(16)).slice(-8);
}
document.getElementById('ownBtn').addEventListener('click', function(){
  var v = document.getElementById('ownInput').value.trim();
  var res = document.getElementById('ownResult');
  if(!v){ res.innerHTML = '<span style="color:var(--warn)">请输入私密标识</span>'; return; }
  if(djb2(v) === OWN_HASH){
    res.innerHTML = '<div style="background:#F0FDF4;border:1px solid #6EE7A0;border-radius:8px;padding:12px;color:#0F7B3E"><b>✓ 验证通过</b><br>本站所有权确认属于创建者本人。此结果由私密标识当场比对得出，可作为原创证明。</div>';
  } else {
    res.innerHTML = '<span style="color:var(--warn)">标识不匹配，验证失败</span>';
  }
});
document.getElementById('ownInput').addEventListener('keydown', function(e){
  if(e.key === 'Enter'){ document.getElementById('ownBtn').click(); }
});
window.addEventListener('hashchange', function(){
  var m = location.hash.match(/^#col\/(\w+)/);
  if(m && COLDEF[m[1]]){ showCol(m[1]); }
  else if(location.hash === '#about'){ showAbout(); }
  else if(location.hash === '#verify'){ showVerify(); }
  else if(location.hash === '#stats'){ openStats(); }
  else if(location.hash === '#prep'){ showPrep(); }
  else if(location.hash.indexOf('#job/') === 0){ showJob(location.hash.slice(5)); }
  else { showHome(); }
});
renderColGrid();
// PWA：注册 Service Worker（仅 http/https 环境，file:// 跳过）
if('serviceWorker' in navigator && location.protocol.indexOf('http') === 0){
  window.addEventListener('load', function(){
    navigator.serviceWorker.register('sw.js').catch(function(){});
  });
}


// 城市标签
function renderCities(){
  var tagEl = document.getElementById('tags'); tagEl.innerHTML = '';
  var hint = document.getElementById('cityHint');
  if(curLetter === '全部'){
    hint.textContent = '已选：全部城市 — 点击城市可筛选';
  } else {
    hint.textContent = '已选字母「'+curLetter+'」— 点击城市查看岗位';
  }
  var list = CITIES.filter(function(c){ return curLetter==='全部' || c.letter===curLetter; });
  var all = document.createElement('span');
  all.className = 'tag' + (selCities.length===0?' on':'');
  all.textContent = '全部城市 ('+ list.reduce(function(a,c){return a+c.count},0) +')';
  all.addEventListener('click', function(){ selCities = []; shownMax = PAGE_SIZE; renderCities(); renderFilters(); ensureAll(function(){ render(); }); cityZone.classList.remove('show'); cityToggle.classList.remove('open'); document.getElementById('cityState').textContent = '展开'; });
  tagEl.appendChild(all);
  list.forEach(function(c){
    var s = document.createElement('span');
    s.className = 'tag' + (selCities.indexOf(c.name)>=0?' on':'');
    s.textContent = c.name + ' (' + c.count + ')';
    s.addEventListener('click', function(){
      var i = selCities.indexOf(c.name);
      if(i >= 0){ selCities.splice(i,1); } else { selCities.push(c.name); }
      shownMax = PAGE_SIZE; renderCities(); renderFilters(); ensureAll(function(){ render(); });
    });
    tagEl.appendChild(s);
  });
}

// 时间显示：几天前 / 截止
function fmtTime(pb){
  if(!pb) return '';
  var m = pb.match(/(\\d{4})[年\\/-](\\d{1,2})[月\\/-](\\d{1,2})/);
  if(!m) return pb;
  var d = new Date(+m[1], +m[2]-1, +m[3]);
  var diff = Math.floor((Date.now() - d.getTime())/86400000);
  if(diff <= 0) return '今天发布';
  if(diff === 1) return '昨天发布';
  if(diff < 30) return diff + '天前发布';
  return m[1]+'-'+m[2]+'-'+m[3]+'发布';
}
function fmtDeadline(dl){
  if(!dl) return '';
  var m = dl.match(/(\\d{4})[年\\/-](\\d{1,2})[月\\/-](\\d{1,2})/);
  if(!m) return '';
  var d = new Date(+m[1], +m[2]-1, +m[3]);
  var diff = Math.round((d.getTime() - Date.now())/86400000);
  if(diff < 0) return '已截止';
  if(diff === 0) return '今天截止';
  if(diff <= 7) return diff + '天后截止';
  return m[1]+'-'+m[2]+'-'+m[3]+'截止';
}
// 公司跳转（天眼查公开搜索）
function companyUrl(name){
  return 'https://www.tianyancha.com/search?key=' + encodeURIComponent(name);
}
function sourceUrl(s){
  if(s.indexOf('人社局')>=0) return 'https://rsj.sh.gov.cn/tgsgg_17341/20251031/t0035_1436498.html';
  return 'https://www.cdpee.org.cn/';
}

var PAGE_SIZE = 10;
var FAVS = [];
try { FAVS = JSON.parse(localStorage.getItem('xy_favs') || '[]'); } catch(e){ FAVS = []; }
var favMode = false;
var socFilter = false;
function toggleSocFilter(){
  socFilter = !socFilter;
  var b = document.getElementById('fpSoc'); if(b) b.classList.toggle('on', socFilter);
  shownMax = PAGE_SIZE;
  ensureAll(function(){ render(); });
  toast(socFilter ? '只看国企、央企、事业单位岗位' : '已显示全部岗位');
}
function saveFavs(){ try { localStorage.setItem('xy_favs', JSON.stringify(FAVS)); } catch(e){} document.getElementById('favCount').textContent = FAVS.length; }
function isFav(cd){ return cd && FAVS.indexOf(cd) >= 0; }
function toggleFav(cd){
  if(!cd) return;
  var i = FAVS.indexOf(cd);
  if(i >= 0){ FAVS.splice(i,1); } else { FAVS.push(cd); }
  saveFavs(); render();
}
function toggleFavMode(){ favMode = !favMode; document.getElementById('favToggle').classList.toggle('on', favMode); document.getElementById('favToggle').innerHTML = favMode ? '★ 返回全部' : '★ 我的收藏 (<span id="favCount">'+FAVS.length+'</span>)'; document.getElementById('favExport').style.display = favMode ? '' : 'none'; var fb = document.getElementById('fpFav'); if(fb) fb.classList.toggle('on', favMode); shownMax = PAGE_SIZE; ensureAll(function(){ render(); }); }
saveFavs();
var shownMax = PAGE_SIZE;

// ===== 岗位标签：心智等级 + 职业词 =====
function mhRange(j){
  if(!j.ds) return '';
  var set = [];
  j.ds.split(';').forEach(function(p){
    if(/智力|精神|多重/.test(p)){
      var mm = p.match(/(\d+)\s*[-–,，]\s*(\d+)/) || p.match(/(\d+)/);
      if(mm){
        var a = +mm[1], b = mm[2] ? +mm[2] : a;
        for(var x = a; x <= b; x++){ if(set.indexOf(x) < 0) set.push(x); }
      }
    }
  });
  if(!set.length) return '';
  var lo = Math.min.apply(null, set), hi = Math.max.apply(null, set);
  return lo === hi ? (lo + '级') : (lo + '-' + hi + '级');
}
var OC_WORDS = ['普工','操作工','组装','装配','包装','搬运','装卸','保洁','保安','门卫','仓管','库管','快递','物流','配送','分拣','客服','文员','前台','接待','助理','会计','出纳','厨师','帮厨','洗碗','传菜','服务员','收银','理货','导购','营业员','店员','促销','司机','质检','检验','电工','焊工','维修','饲养','种植','园艺','绿化','护理','护工','家政','后勤','面点','烘焙','缝纫','裁剪','美发','按摩','足疗','社工','志愿者','数据标注','标注','软件','开发','测试','运营','编辑','设计','教师','保育','助教','销售','业务','主播','直播','经纪人','饲养员','养殖','餐饮','勤杂','洗车','印刷','装订','模具','数控','车床','钳工','铣工','喷漆','电镀','监理','质量','食品加工','生产工','技术员','工程师','仓库','仓储','物业','值班','巡逻','理货员','外卖','骑手','服务员'];
var OC_SKIP = ['不限','其他','无','以上','以下','相关','专业','岗位','工作','人员','管理','技术','类','职位','全职','兼职','处理'];
function occTags(j){
  var t = (j.n || '') + '|' + (j.dy || '');
  var out = [];
  OC_WORDS.forEach(function(w){ if(out.length < 3 && t.indexOf(w) >= 0) out.push(w); });
  if(out.length < 2 && j.dy){
    // 兜底：从行业分类末段（最具体的岗位名）拆词
    var seg = (j.dy.split('|').pop() || '').trim();
    seg.split(/[\/／、,，]/).forEach(function(w){
      if(out.length >= 2) return;
      w = w.trim().replace(/[员工师岗生技人]$/,'');
      if(w.length >= 2 && w.length <= 6 && OC_SKIP.indexOf(w) < 0){
        var dup = out.some(function(o){ return o.indexOf(w) >= 0 || w.indexOf(o) >= 0; });
        if(!dup) out.push(w);
      }
    });
  }
  return out;
}
function jobTagsHtml(j){
  var h = '';
  var mh = mhRange(j);
  if(mh) h += '<span class="tag mh-tag'+(selMh.indexOf(mh)>=0?' on':'')+'" data-mh="'+mh+'">心智障碍·'+mh+'可投</span>';
  occTags(j).forEach(function(w){ h += '<span class="tag'+(selOcc.indexOf(w)>=0?' on':'')+'" data-occ="'+w+'">'+w+'</span>'; });
  return h;
}
// 已选筛选条渲染（职业/心智/城市 多选展示，可单独删除）
function renderFilters(){
  var bar = document.getElementById('filtersBar');
  var meta = document.getElementById('fpMeta');
  var mcnt = selMh.length + selOcc.length + selCities.length;
  if(meta) meta.textContent = mcnt ? ('已选 ' + mcnt + ' 项') : '';
  var h = '';
  if(selMh.length || selOcc.length || selCities.length){
    h += '<span class="f-hint">已选筛选：</span>';
    selMh.forEach(function(m){ h += '<span class="f-tag mh" data-f="mh:'+m+'">心智·'+m+'<span class="x"> ✕</span></span>'; });
    selOcc.forEach(function(o){ h += '<span class="f-tag" data-f="occ:'+o+'">'+o+'<span class="x"> ✕</span></span>'; });
    selCities.forEach(function(c){ h += '<span class="f-tag city" data-f="city:'+c+'">'+c+'<span class="x"> ✕</span></span>'; });
    h += '<span class="f-clear">清空筛选</span>';
  }
  bar.innerHTML = h;
  bar.style.display = h ? 'block' : 'none';
}
document.getElementById('filtersBar').addEventListener('click', function(e){
  var t = e.target;
  while(t && t !== this){
    if(t.classList && t.classList.contains('f-tag')){
      var f = t.getAttribute('data-f').split(':');
      var v = f.slice(1).join(':');
      if(f[0] === 'mh'){ var i = selMh.indexOf(v); if(i>=0) selMh.splice(i,1); }
      else if(f[0] === 'occ'){ var i2 = selOcc.indexOf(v); if(i2>=0) selOcc.splice(i2,1); }
      else if(f[0] === 'city'){ var i3 = selCities.indexOf(v); if(i3>=0) selCities.splice(i3,1); }
      shownMax = PAGE_SIZE; renderCities(); renderFilters(); ensureAll(function(){ render(); });
      return;
    }
    if(t.classList && t.classList.contains('f-clear')){
      clearAllFilter();
      return;
    }
    t = t.parentNode;
  }
});
function visible(j){
  var isOff = j.st==='expired' || (j.dl && fmtDeadline(j.dl)==='已截止');
  if(onlyValid && isOff) return false;
  if(favMode && !isFav(j.cd)) return false;
  if(recentOnly && !isNewJob(j.pb)) return false;
  if(hisMode && HISTORY.indexOf(j.cd) < 0) return false;
  if(selCities.length){
    if(selCities.indexOf(j.c) < 0) return false;
  } else if(curLetter!=='全部'){
    var c = CITIES.filter(function(x){return x.name===j.c})[0];
    if(!c || c.letter!==curLetter) return false;
  }
  if(selMh.length){
    var r = mhRange(j);
    if(!r || selMh.indexOf(r) < 0) return false;
  }
  if(selOcc.length){
    var oc = occTags(j);
    var hit = false;
    for(var oi = 0; oi < selOcc.length; oi++){ if(oc.indexOf(selOcc[oi]) >= 0){ hit = true; break; } }
    if(!hit) return false;
  }
  if(socFilter && j.ow !== '央企' && j.ow !== '国企' && j.ow !== '事业单位') return false;
  if(kw){
    if(kw.indexOf('心智') === 0){
      var want = kw.replace('心智', '');
      if(mhRange(j) !== want) return false;
    } else {
      var s = (j.n+j.o+j.c+j.s+j.ds+j.dy).toLowerCase();
      var wl = kw.toLowerCase().split(/\s+/);
      for(var wi = 0; wi < wl.length; wi++){
        if(wl[wi] && s.indexOf(wl[wi]) < 0) return false;
      }
    }
  }
  return true;
}
function render(){
  var el = document.getElementById('list'); el.innerHTML = '';
  var shown = 0, total = 0;
  var arr = JOBS.filter(visible);
  if(hisMode){
    var om = {};
    arr.forEach(function(j){ om[j.cd] = j; });
    arr = [];
    HISTORY.forEach(function(cd){ if(om[cd]) arr.push(om[cd]); });
  }
  arr.forEach(function(j){
    total++;
    if(shown >= shownMax) return;
    shown++;
    var isOff = j.st==='expired' || (j.dl && fmtDeadline(j.dl)==='已截止');
    var card = document.createElement('div'); card.className = 'card' + (isOff?' expired':'');
    var dl = fmtDeadline(j.dl), pb = fmtTime(j.pb);
    var socTag = '';
    if(j.ow === '央企' || j.ow === '国企' || j.ow === '事业单位'){
      var socCol = j.ow === '央企' ? '#1D4ED8' : (j.ow === '国企' ? '#2563EB' : '#0D9488');
      socTag = '<span class="badge soc" style="background:'+socCol+'">'+j.ow+'</span>';
    }
    var badge = socTag + (isOff ? '<span class="badge off">已失效</span>' : (isNewJob(j.pb) ? '<span class="badge new">新发布</span>' : ''));
    if(!isOff && dl && dl.indexOf('天后截止')>=0) badge = badge + '<span class="badge hot">即将截止</span>';
    var mhTag = j.mh ? '<span class="badge mh">心智障碍可投</span>' : '';
    var favCls = isFav(j.cd) ? ' on' : '';
    var du = safeUrl(j.du || j.u);
    var nm = esc(j.n), org = esc(j.o), ds = esc(j.ds), loc = esc(j.l);
    var edu = esc(j.e), num = esc(j.m), typ = esc(j.t), dy = esc(j.dy);
    card.innerHTML =
      '<div class="row1"><div class="nm"><a class="jlink" target="_blank" rel="noopener noreferrer" href="'+du+'">'+nm+'</a></div><button class="favbtn'+favCls+'" data-c="'+esc(j.cd)+'" title="收藏">'+(isFav(j.cd)?'★':'☆')+'</button>'+badge+'</div>'+
      '<div class="org">'+org+'</div>'+
      (j.ds?'<div class="ds">适合残疾类型：'+ds+'</div>':'')+
      '<div class="info">'+
        '<span class="i">📍 '+loc+'</span>'+
        (j.e?'<span class="i">学历：'+edu+'</span>':'')+
        (j.m?'<span class="i">招 '+num+' 人</span>':'')+
        (j.t?'<span class="i">'+typ+'</span>':'')+
      '</div>'+
      (j.dy?'<div class="duty">'+dy+'</div>':'')+
      '<div class="tags">'+jobTagsHtml(j)+'</div>'+
      '<div class="foot"><div class="time">'+pb+(dl?' · <span class="dl">'+dl+'</span>':'')+'</div>'+
      '<div class="btns">'+
        '<button class="btn ghost" data-cd="'+esc(j.cd)+'">查看详情</button>'+
        '<button class="btn share" data-scd="'+esc(j.cd)+'">转发</button>'+
        '<a class="btn orig" target="_blank" rel="noopener noreferrer" href="'+companyUrl(j.o)+'">查公司</a>'+
      '</div></div>';
    el.appendChild(card);
  });
  document.getElementById('stShow').textContent = shown;
  document.getElementById('empty').style.display = total ? 'none' : 'block';
  var mw = document.getElementById('moreWrap');
  if(total > shownMax){ mw.style.display = 'block'; }
  else { mw.style.display = 'none'; }
}

// 事件委托：卡片"查看详情"打开站内详情页；点标签多选（职业OR/心智OR，两者之间AND）
document.getElementById('list').addEventListener('click', function(e){
  var t = e.target;
  while(t && t !== this){
    if(t.classList && t.classList.contains('tag')){
      var mh = t.getAttribute('data-mh'), oc = t.getAttribute('data-occ');
      if(mh){
        var i = selMh.indexOf(mh);
        if(i >= 0){ selMh.splice(i,1); } else { selMh.push(mh); }
      }
      if(oc){
        var i2 = selOcc.indexOf(oc);
        if(i2 >= 0){ selOcc.splice(i2,1); } else { selOcc.push(oc); }
      }
      shownMax = PAGE_SIZE; renderFilters(); ensureAll(function(){ render(); });
      return;
    }
    if(t.classList && t.classList.contains('btn') && t.classList.contains('ghost')){
      showJob(t.getAttribute('data-cd'));
      return;
    }
    if(t.tagName === 'A' && t.classList && t.classList.contains('jlink')){
      var c0 = t.closest ? t.closest('.card') : null;
      if(c0){ var fb = c0.querySelector('.favbtn'); if(fb) addHis(fb.getAttribute('data-c')); }
      return;
    }
    if(t.classList && t.classList.contains('btn') && t.classList.contains('share')){
      shareJob(t.getAttribute('data-scd'));
      return;
    }
    t = t.parentNode;
  }
});

// ===== 单条岗位转发（系统分享优先，失败复制文本） =====
function shareJob(cd){
  var j = null;
  for(var i = 0; i < JOBS.length; i++){ if(String(JOBS[i].cd) === String(cd)){ j = JOBS[i]; break; } }
  if(!j){
    ensureAll(function(){ shareJob(cd); });
    return;
  }
  var link = safeUrl(j.du || j.u);
  var lines = [
    '【行隅·岗位推荐】',
    '岗位：' + (j.n || ''),
    '公司：' + (j.o || '—'),
    '地点：' + (j.l || '—'),
    (j.t ? '类型：' + j.t : ''),
    (j.e ? '学历：' + j.e : ''),
    (j.m ? '招聘：' + j.m + ' 人' : ''),
    (j.mh ? '适合：心智障碍人士可投' : ''),
    (j.ds ? '残疾类型：' + j.ds : ''),
    (j.pb ? '发布：' + j.pb : ''),
    '详情：' + (link && link !== '#' ? link : 'https://james-liang-o.github.io/xingyu-jobs/')
  ].filter(function(x){ return x; }).join('\\n');
  var shareText = lines + '\\n—— 来自「行隅」心智障碍就业导航（免费公益平台）';
  if(navigator.share){
    navigator.share({ title: '行隅·岗位推荐', text: shareText }).catch(function(){});
  } else {
    copyText(shareText, '岗位信息已复制，去微信/QQ粘贴发送');
  }
}
function copyText(txt, okMsg){
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(function(){ toast(okMsg); }).catch(function(){ toast(okMsg); });
  } else {
    var ta = document.createElement('textarea');
    ta.value = txt; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    try{ document.execCommand('copy'); toast(okMsg); }catch(_){ toast(okMsg); }
    document.body.removeChild(ta);
  }
}

// ===== 附近岗位：点了才定位，拒绝/失败只提示、不影响使用 =====
var NEAR_CITIES = {'北京市':[116.4,39.9],'上海市':[121.47,31.23],'天津市':[117.2,39.13],'重庆市':[106.55,29.56],
  '广州市':[113.26,23.13],'深圳市':[114.06,22.55],'珠海市':[113.58,22.27],'佛山市':[113.12,23.02],'东莞市':[113.75,23.02],'中山市':[113.39,22.52],'惠州市':[114.42,23.11],'汕头市':[116.68,23.35],'湛江市':[110.36,21.27],
  '杭州市':[120.15,30.29],'宁波市':[121.55,29.88],'温州市':[120.7,28.0],'嘉兴市':[120.76,30.75],'绍兴市':[120.58,30.0],'金华市':[119.65,29.08],'台州市':[121.42,28.66],
  '南京市':[118.8,32.06],'苏州市':[120.62,31.32],'无锡市':[120.3,31.57],'常州市':[119.97,31.81],'南通市':[120.86,31.98],'徐州市':[117.18,34.26],'扬州市':[119.41,32.39],'盐城市':[120.16,33.35],'淮安市':[119.02,33.61],'连云港市':[119.22,34.6],'泰州市':[119.92,32.46],'镇江市':[119.42,32.19],
  '武汉市':[114.31,30.59],'宜昌市':[111.29,30.69],'襄阳市':[112.14,32.04],'荆州市':[112.24,30.33],'黄冈市':[114.87,30.45],
  '成都市':[104.07,30.67],'绵阳市':[104.68,31.47],'德阳市':[104.4,31.13],'宜宾市':[104.62,28.77],'泸州市':[105.44,28.87],'南充市':[106.11,30.84],
  '长沙市':[112.94,28.23],'株洲市':[113.13,27.83],'湘潭市':[112.94,27.83],'岳阳市':[113.13,29.37],'常德市':[111.7,29.03],'衡阳市':[112.57,26.89],
  '郑州市':[113.63,34.75],'洛阳市':[112.45,34.62],'开封市':[114.31,34.8],'新乡市':[113.93,35.3],'南阳市':[112.53,33.0],
  '西安市':[108.94,34.34],'宝鸡市':[107.14,34.36],'咸阳市':[108.71,34.33],'渭南市':[109.51,34.5],
  '济南市':[117.12,36.65],'青岛市':[120.38,36.07],'烟台市':[121.45,37.46],'潍坊市':[119.16,36.71],'临沂市':[118.36,35.1],'济宁市':[116.59,35.41],'淄博市':[118.05,36.81],
  '福州市':[119.3,26.08],'厦门市':[118.09,24.48],'泉州市':[118.68,24.87],'漳州市':[117.65,24.51],'莆田市':[119.01,25.45],'宁德市':[119.55,26.67],
  '合肥市':[117.23,31.82],'芜湖市':[118.43,31.33],'蚌埠市':[117.39,32.92],'阜阳市':[115.81,32.89],
  '南昌市':[115.86,28.68],'赣州市':[114.93,25.83],'九江市':[116.0,29.71],'上饶市':[117.94,28.45],
  '石家庄市':[114.51,38.04],'唐山市':[118.18,39.63],'保定市':[115.46,38.87],'邯郸市':[114.54,36.63],'廊坊市':[116.7,39.52],
  '太原市':[112.55,37.87],'大同市':[113.3,40.08],'临汾市':[111.52,36.09],
  '哈尔滨市':[126.53,45.8],'齐齐哈尔市':[123.92,47.35],'大庆市':[125.1,46.59],'牡丹江市':[129.63,44.58],
  '长春市':[125.32,43.9],'吉林市':[126.55,43.84],'延边州':[129.51,42.9],
  '沈阳市':[123.43,41.8],'大连市':[121.61,38.91],'鞍山市':[122.99,41.11],'抚顺市':[123.96,41.88],'锦州市':[121.13,41.1],
  '呼和浩特市':[111.75,40.84],'包头市':[109.84,40.66],'鄂尔多斯市':[109.78,39.61],
  '昆明市':[102.83,24.88],'大理州':[100.23,25.6],'曲靖市':[103.8,25.49],'玉溪市':[102.55,24.35],
  '贵阳市':[106.63,26.65],'遵义市':[106.93,27.73],
  '南宁市':[108.37,22.82],'桂林市':[110.29,25.27],'柳州市':[109.42,24.33],'北海市':[109.12,21.48],
  '海口市':[110.32,20.03],'三亚市':[109.51,18.25],
  '兰州市':[103.83,36.06],'天水市':[105.72,34.58],'嘉峪关市':[98.29,39.77],
  '西宁市':[101.78,36.62],
  '银川市':[106.23,38.49],
  '乌鲁木齐市':[87.62,43.82],
  '拉萨市':[91.14,29.65],
  '香港特别行政区':[114.17,22.32],'澳门特别行政区':[113.55,22.2]};
function nearbyJobs(){
  if(!('geolocation' in navigator)){
    toast('当前浏览器不支持定位，可在城市筛选中手动选择');
    return;
  }
  toast('正在定位…请允许浏览器获取位置权限');
  navigator.geolocation.getCurrentPosition(function(pos){
    var lat = pos.coords.latitude, lng = pos.coords.longitude;
    var best = null, bestD = 1e9;
    for(var c in NEAR_CITIES){
      var dLat = lat - NEAR_CITIES[c][1], dLng = lng - NEAR_CITIES[c][0];
      var d = dLat*dLat + dLng*dLng;
      if(d < bestD){ bestD = d; best = c; }
    }
    selCities = best ? [best] : [];
    shownMax = PAGE_SIZE; renderFilters();
    ensureAll(function(){
      render();
      if(best) toast('已定位到「' + best + '」，已为你筛选该城市岗位');
      else toast('未能匹配到附近城市，请在城市筛选中手动选择');
    });
  }, function(err){
    toast(err && err.code === 1 ? '未获得定位权限，可在城市筛选中手动选择城市' : '定位失败，可在城市筛选中手动选择城市');
  }, {timeout: 8000, maximumAge: 600000});
}

// ===== 极简模式：大字大按钮，减少干扰 =====
function toggleMin(){
  var on = document.body.classList.toggle('minmode');
  document.getElementById('minBtn').classList.toggle('on', on);
  try{ localStorage.setItem('xy_min', on ? '1' : ''); }catch(e){}
  toast(on ? '已开启极简模式：大字体、大按钮' : '已关闭极简模式');
}
(function(){ try{ if(localStorage.getItem('xy_min') === '1'){ document.body.classList.add('minmode'); document.getElementById('minBtn').classList.add('on'); } }catch(e){} })();

// ===== 历史浏览：点开过的岗位自动记录 =====
var HISTORY = [];
try { HISTORY = JSON.parse(localStorage.getItem('xy_his') || '[]'); }catch(e){ HISTORY = []; }
var hisMode = false;
function saveHis(){ try{ localStorage.setItem('xy_his', JSON.stringify(HISTORY.slice(0, 100))); }catch(e){} }
function addHis(cd){
  if(!cd) return;
  var i = HISTORY.indexOf(String(cd));
  if(i >= 0) HISTORY.splice(i, 1);
  HISTORY.unshift(String(cd));
  saveHis();
}
function toggleHisMode(){
  if(!hisMode && !HISTORY.length){ toast('还没有浏览记录，点开岗位详情后会记录在这里'); return; }
  hisMode = !hisMode;
  var b = document.getElementById('fpHis'); if(b) b.classList.toggle('on', hisMode);
  shownMax = PAGE_SIZE;
  ensureAll(function(){ render(); });
  toast(hisMode ? '显示你最近浏览过的岗位' : '已退出历史浏览');
}

// ===== 清空全部筛选（面板按钮 + 筛选项"清空"共用） =====
function clearAllFilter(){
  selMh = []; selOcc = []; selCities = []; kw = '';
  recentOnly = false; hisMode = false; socFilter = false;
  var a = document.getElementById('fpRecent'); if(a) a.classList.remove('on');
  var b = document.getElementById('fpHis'); if(b) b.classList.remove('on');
  var sc = document.getElementById('fpSoc'); if(sc) sc.classList.remove('on');
  document.getElementById('q').value = '';
  curLetter = '全部'; shownMax = PAGE_SIZE;
  renderCities(); renderFilters(); ensureAll(function(){ render(); });
  toast('已清空全部筛选');
}

// ===== 最近3天新增 =====
function toggleRecent(){
  recentOnly = !recentOnly;
  var b = document.getElementById('fpRecent'); if(b) b.classList.toggle('on', recentOnly);
  shownMax = PAGE_SIZE;
  ensureAll(function(){ render(); });
  toast(recentOnly ? '只看最近 3 天新发布的岗位' : '已取消时间限制');
}

// ===== 帮我找岗位：问答向导 =====
var gStep = 0, gCity = '', gType = '', gShift = '', gEdu = '';
var GUIDE_TYPES = [['生产制造','普工'],['餐饮服务','厨师'],['物流仓储','仓管'],['销售客服','销售'],['文职行政','文员'],['保洁绿化','保洁'],['不限','']];
function openGuide(){ gStep = 0; gCity = ''; gType = ''; gShift = ''; gEdu = ''; renderGuide(); document.getElementById('guideMask').style.display = 'flex'; }
function closeGuide(){ document.getElementById('guideMask').style.display = 'none'; }
function setGCity(c){ gCity = c; var inp = document.getElementById('gCityInp'); if(inp) inp.value = c; }
function setGType(t){ gType = t; renderGuide(); }
function setGShift(s){ gShift = s; renderGuide(); }
function setGEdu(e){ gEdu = e; renderGuide(); }
function renderGuide(){
  var box = document.getElementById('gStep');
  document.getElementById('gPrev').style.display = gStep > 0 ? '' : 'none';
  if(gStep === 0){
    box.innerHTML = '<p style="margin:0 0 10px">第 1 步：你在哪个城市？</p>' +
      '<input id="gCityInp" placeholder="输入城市名，如：上海" style="width:100%;padding:12px;border:1px solid var(--line);border-radius:10px;font-size:16px;box-sizing:border-box">' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-top:12px">' + ['上海','北京','广州','深圳','杭州','南京','武汉','成都','重庆','天津'].map(function(c){ return '<button class="btn ghost" onclick="setGCity(\\''+c+'\\')">'+c+'</button>'; }).join('') + '</div>';
    document.getElementById('gNext').textContent = '下一步';
  } else if(gStep === 1){
    box.innerHTML = '<p style="margin:0 0 10px">第 2 步：想做什么类型的工作？</p>' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px">' + GUIDE_TYPES.map(function(t){ return '<button class="btn'+(gType===t[0]?'':' ghost')+'" onclick="setGType(\\''+t[0]+'\\')">'+t[0]+'</button>'; }).join('') + '</div>';
    document.getElementById('gNext').textContent = '下一步';
  } else if(gStep === 2){
    box.innerHTML = '<p style="margin:0 0 10px">第 3 步：能接受倒班或夜班吗？</p>' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px">' + [['都可以',''],['只接受白班','长白班']].map(function(t){ return '<button class="btn'+(gShift===t[1]?'':' ghost')+'" onclick="setGShift(\\''+t[1]+'\\')">'+t[0]+'</button>'; }).join('') + '</div>';
    document.getElementById('gNext').textContent = '下一步';
  } else {
    box.innerHTML = '<p style="margin:0 0 10px">第 4 步：学历要求？</p>' +
      '<div style="display:flex;flex-wrap:wrap;gap:8px">' + [['不限',''],['初中','初中'],['高中','高中'],['大专及以上','大专']].map(function(t){ return '<button class="btn'+(gEdu===t[1]?'':' ghost')+'" onclick="setGEdu(\\''+t[1]+'\\')">'+t[0]+'</button>'; }).join('') + '</div>';
    document.getElementById('gNext').textContent = '开始找岗位';
  }
}
function guidePrev(){ if(gStep > 0){ gStep--; renderGuide(); } }
function guideNext(){
  if(gStep === 0){ gCity = (document.getElementById('gCityInp') || {}).value ? document.getElementById('gCityInp').value.trim() : gCity; }
  if(gStep < 3){ gStep++; renderGuide(); return; }
  applyGuide();
}
function applyGuide(){
  selCities = gCity ? [gCity] : [];
  var words = [];
  for(var i = 0; i < GUIDE_TYPES.length; i++){ if(GUIDE_TYPES[i][0] === gType && GUIDE_TYPES[i][1]) words.push(GUIDE_TYPES[i][1]); }
  if(gShift) words.push(gShift);
  if(gEdu) words.push(gEdu);
  kw = words.join(' ');
  closeGuide();
  recentOnly = false; var rb = document.getElementById('fpRecent'); if(rb) rb.classList.remove('on');
  curLetter = '全部'; shownMax = PAGE_SIZE;
  renderCities(); renderFilters();
  ensureAll(function(){ render(); });
  toast(gCity ? '已按「' + gCity + '」为你筛选岗位，可在顶部继续调整' : '已为你筛选岗位，可在顶部继续调整');
}


// ===== 面试陪练：情景模拟（不判对错，只给鼓励式示范） =====
var IV_STEPS = [
  {say:'你好，请坐。先简单介绍一下自己吧。', opts:[
    ['您好，我叫××，很高兴来面试。','很好！先问好再说自己的名字，面试官一下就能记住你。'],
    ['（紧张得说不出话）','没关系，紧张很正常，多练几次就好了。可以试着说：“您好，我叫××，很高兴来面试。”'],
    ['你好。','很好！还可以多说一句：“您好，我叫××，很高兴来面试。”这样更完整。']
  ]},
  {say:'你能介绍一下自己吗？以前做过什么工作？', opts:[
    ['我叫××，以前做过包装工，能坐班。','说得真清楚！名字、做过什么、能不能坐班，都是面试官最想听的。'],
    ['我……不知道说什么。','没关系。提前准备一句话就行：“我叫××，以前做过包装工，能坐班。”在家多念几遍，就不紧张了。'],
    ['我什么都能干。','可以再说得具体一点，比如：“我做过包装工，动作快，能坐班。”说得具体，面试官更容易听懂。']
  ]},
  {say:'你能每周工作几天？可以加班吗？', opts:[
    ['可以，我周一到周五都能来。','很好！把时间说清楚，面试官就好安排。'],
    ['我要问一下我妈妈。','可以，拿不准的事问家里很正常。可以这样说：“我想先跟家里人商量一下，明天答复您。”'],
    ['随便。','试试把时间说清楚：“我周一到周五都能来。”这样面试官就知道你的时间了。']
  ]},
  {say:'你对工资有什么要求吗？', opts:[
    ['按公司规定来就行。','可以！如果心里有数，也可以说：“希望不低于××元。”'],
    ['我要先问问家里。','很好，可以说：“我想先问一下家人，明天答复您。”拿不准就问，很稳妥。'],
    ['越多越好。','大家都想多挣，但面试的时候这样说更好：“按公司规定来就行。”或者“希望不低于××元。”']
  ]},
  {say:'好的，我们了解了。你先回去，等通知吧。', opts:[
    ['好的，谢谢您！那我先走了，再见。','很有礼貌！面试结束说谢谢，印象加分。'],
    ['（什么都不说就走）','记得说：“谢谢您，再见。”礼貌的话，面试官会记住你。'],
    ['大概什么时候有消息？','可以问！说：“请问大概什么时候有结果？”问清楚时间，心里踏实。']
  ]}
];
var ivStep = 0, ivPicked = null;
function openIv(){
  ivStep = 0; ivPicked = null;
  closeFp();
  ivRender();
  document.getElementById('ivMask').style.display = 'flex';
}
function closeIv(){
  try{ speechSynthesis.cancel(); }catch(e){}
  document.getElementById('ivMask').style.display = 'none';
}
function ivRender(){
  var box = document.getElementById('ivBox');
  var prog = document.getElementById('ivProg');
  var pb = document.getElementById('ivPrevBtn');
  var nb = document.getElementById('ivNextBtn');
  if(ivStep >= IV_STEPS.length){
    prog.textContent = '练完啦';
    pb.style.display = 'none';
    nb.style.display = 'none';
    box.innerHTML = '<div class="iv-fb" style="font-size:15px;line-height:1.9"><b>练完啦，你真棒！</b><br>面试前可以再练几遍，也可以让家人陪着你一起练。<br>记住：说清楚名字、做过什么、能做多久，就是最棒的自我介绍。<br>紧张的时候深呼吸，慢慢说，没关系的。</div><button class="btn" style="margin-top:14px;width:100%" onclick="openIv()">再练一遍</button>';
    return;
  }
  prog.textContent = '第 ' + (ivStep + 1) + ' 步 / 共 ' + IV_STEPS.length + ' 步';
  pb.style.display = ivStep > 0 ? '' : 'none';
  nb.style.display = ivPicked !== null ? '' : 'none';
  var st = IV_STEPS[ivStep];
  var h = '<div class="iv-say"><b>面试官：</b>' + esc(st.say) + '</div>';
  for(var i = 0; i < st.opts.length; i++){
    var sel = (ivPicked === i) ? ' style="border-color:var(--primary);background:rgba(13,148,136,.07)"' : '';
    h += '<button class="iv-opt"' + sel + ' onclick="ivPick(' + i + ')">' + esc(st.opts[i][0]) + '</button>';
  }
  if(ivPicked !== null){
    h += '<div class="iv-fb"><b>陪练这样说：</b>' + esc(st.opts[ivPicked][1]) + '</div>';
  }
  box.innerHTML = h;
}
function ivPick(i){
  ivPicked = i;
  ivRender();
  try{ speechSynthesis.cancel(); }catch(e){}
  toast('选好啦，看看陪练怎么回应');
}
function ivNext(){
  if(ivStep < IV_STEPS.length){ ivStep++; ivPicked = null; ivRender(); }
  else { closeIv(); }
}
function ivPrev(){
  if(ivStep > 0){ ivStep--; ivPicked = null; ivRender(); }
}
function ivRead(){
  if(ivStep >= IV_STEPS.length){ toast('练习完成，再来一遍吧'); return; }
  if(!('speechSynthesis' in window)){ toast('当前浏览器不支持朗读'); return; }
  var st = IV_STEPS[ivStep];
  var lines = ['面试官说：' + st.say];
  for(var i = 0; i < st.opts.length; i++){ lines.push('可以这样说：' + st.opts[i][0]); }
  var msg = new SpeechSynthesisUtterance(lines.join('。'));
  msg.lang = 'zh-CN'; msg.rate = 0.95;
  speechSynthesis.cancel();
  speechSynthesis.speak(msg);
  toast('正在朗读：面试官的话和回应示范');
}

// ===== 打印 / 保存岗位清单 =====
function printList(){
  ensureAll(function(){
    var list = JOBS.filter(visible);
    if(!list.length){ toast('当前筛选条件下没有岗位可打印'); return; }
    var show = list.slice(0, 300);
    var h = '<h1>行隅 · 岗位清单</h1><div class="pm">生成时间：' + new Date().toLocaleString('zh-CN') + ' · 共 ' + list.length + ' 条' + (list.length > 300 ? '（打印前 ' + 300 + ' 条）' : '') + '</div>';
    show.forEach(function(j){
      var link = safeUrl(j.du || j.u);
      h += '<div class="pi"><b>' + esc(j.n) + '</b> · ' + esc(j.o) + '<div class="pl">' + esc(j.l) + (j.e ? ' · 学历' + esc(j.e) : '') + (j.t ? ' · ' + esc(j.t) : '') + (j.mh ? ' · 心智障碍可投' : '') + (j.pb ? ' · 发布 ' + j.pb : '') + ' · 详情：' + (link && link !== '#' ? link : 'https://james-liang-o.github.io/xingyu-jobs/') + '</div></div>';
    });
    document.getElementById('printArea').innerHTML = h;
    window.print();
  });
}

// ===== 导出收藏 =====
function exportFav(){
  if(!FAVS.length){ toast('还没有收藏的岗位'); return; }
  ensureAll(function(){
    var lines = ['【行隅·我的收藏】共 ' + FAVS.length + ' 条', ''];
    for(var i = 0; i < FAVS.length; i++){
      var j = null;
      for(var k = 0; k < JOBS.length; k++){ if(String(JOBS[k].cd) === String(FAVS[i])){ j = JOBS[k]; break; } }
      if(!j) continue;
      var link = safeUrl(j.du || j.u);
      lines.push((i+1) + '. ' + j.n + '（' + j.o + '，' + j.l + '）' + (j.pb ? ' 发布' + j.pb : '') + ' 详情：' + (link && link !== '#' ? link : 'https://james-liang-o.github.io/xingyu-jobs/'));
    }
    copyText(lines.join('\\n'), '收藏清单已复制，可粘贴发送给家长或机构');
  });
}

// ===== 求职准备页 =====
function showPrep(){
  document.getElementById('prePage').style.display = 'block';
  document.getElementById('prePage').scrollTop = 0;
  window.scrollTo(0, 0);
}

// ===== 数据总览 =====
function openStats(){
  document.getElementById('statsPage').style.display = 'block';
  document.getElementById('statsPage').scrollTop = 0;
  window.scrollTo(0, 0);
  renderStats();
  if(location.hash !== '#stats'){ try{ history.replaceState(null, '', '#stats'); }catch(e){} }
}
// 是否3天内新发布
function isNewJob(pb){
  if(!pb) return false;
  var m = String(pb).match(/(\d{4})[年\/-](\d{1,2})[月\/-](\d{1,2})/);
  if(!m) return false;
  var d = new Date(+m[1], +m[2]-1, +m[3]);
  return Math.floor((Date.now() - d.getTime())/86400000) <= 3;
}
// 渲染数据总览
function renderStats(){
  ensureAll(function(){
    var jobs = JOBS, total = jobs.length, valid = 0, mh = 0, soc = 0, cityCnt = {};
    for(var i = 0; i < total; i++){
      var j = jobs[i];
      if(j.st !== 'expired') valid++;
      if(j.mh) mh++;
      if(j.ow === '央企' || j.ow === '国企' || j.ow === '事业单位') soc++;
      var c = j.c || j.p || '其他';
      cityCnt[c] = (cityCnt[c] || 0) + 1;
    }
    document.getElementById('statsSummary').innerHTML =
      '<div class="stat-sum">'+
        '<div class="s"><b>' + total + '</b><span>岗位总数</span></div>'+
        '<div class="s"><b>' + Object.keys(cityCnt).length + '</b><span>覆盖城市</span></div>'+
        '<div class="s"><b>' + mh + '</b><span>心智可投</span></div>'+
        '<div class="s"><b>' + soc + '</b><span>国企央企事业单位</span></div>'+
        '<div class="s"><b>' + colTotal + '</b><span>专栏文章</span></div>'+
      '</div>';
    var cityTop = Object.keys(cityCnt).map(function(k){ return [k, cityCnt[k]]; }).sort(function(a,b){ return b[1]-a[1]; }).slice(0,10);
    var maxC = cityTop.length ? cityTop[0][1] : 1;
    document.getElementById('statsCity').innerHTML = cityTop.map(function(x){
      return '<div class="br"><span class="bn">'+esc(x[0])+'</span><span class="bw"><span class="bf" style="width:'+Math.max(2, Math.round(x[1]/maxC*100))+'%"></span></span><span class="bt">'+x[1]+'</span></div>';
    }).join('') || '<div style="color:var(--sub)">暂无数据</div>';
    // 职业大类统计：取 duty 第一个分段的干净名称
    var dutyCnt = {};
    for(var k2 = 0; k2 < total; k2++){
      var dy = jobs[k2].dy || '';
      var seg = dy.split('|')[0].trim();
      if(!seg) continue;
      dutyCnt[seg] = (dutyCnt[seg] || 0) + 1;
    }
    var dutyTop = Object.keys(dutyCnt).map(function(k){ return [k, dutyCnt[k]]; }).sort(function(a,b){ return b[1]-a[1]; }).slice(0,8);
    var maxD = dutyTop.length ? dutyTop[0][1] : 1;
    document.getElementById('statsDuty').innerHTML = dutyTop.map(function(x){
      return '<div class="br"><span class="bn">'+esc(x[0])+'</span><span class="bw"><span class="bf" style="width:'+Math.max(2, Math.round(x[1]/maxD*100))+'%"></span></span><span class="bt">'+x[1]+'</span></div>';
    }).join('') || '<div style="color:var(--sub)">暂无数据</div>';
  });
}

// 加载更多：先拉下一片数据，再渲染更多
document.getElementById('moreBtn').addEventListener('click', function(){
  var btn = document.getElementById('moreBtn');
  btn.textContent = '正在加载…';
  shownMax += 20;
  ensureNext(function(){
    btn.textContent = '加载更多岗位';
    render();
  });
});

// 搜索（需全量数据；关键词与已选 tag 叠加，不清空城市/职业选择）
document.getElementById('q').addEventListener('input', function(e){
  kw = e.target.value.trim();
  if(kw){ curLetter='全部'; }
  shownMax = PAGE_SIZE;
  if(kw){
    document.getElementById('stShow').textContent = '…';
    ensureAll(function(){ render(); });
  } else {
    render();
  }
});

renderCities();
render();
renderFilters();

// ===== 设置面板：字号滑条 / 深色 / 简化版 / 朗读 =====
function openSettings(){ document.getElementById('setMask').style.display = 'flex'; }
function closeSettings(){ document.getElementById('setMask').style.display = 'none'; }
function toggleFp(){ var m = document.getElementById('fpMask'); m.style.display = (m.style.display === 'block') ? 'none' : 'block'; }
function closeFp(){ document.getElementById('fpMask').style.display = 'none'; }
var ZOOM_SUPPORT = (function(){ try{ var d = document.documentElement; d.style.zoom = '1'; var ok = d.style.zoom === '1'; d.style.zoom = ''; return ok; }catch(e){ return false; } })();
function setZoom(v){
  v = Math.max(85, Math.min(140, +v || 100));
  try{
    if(ZOOM_SUPPORT){ document.documentElement.style.zoom = (v / 100); }
    else { document.documentElement.style.fontSize = Math.round(16 * v / 100) + 'px'; }
    localStorage.setItem('xy_zoom', v);
  }catch(e){}
  var sv = document.getElementById('zoomVal'); if(sv) sv.textContent = v + '%';
  var sr = document.getElementById('zoomRange'); if(sr) sr.value = v;
}
(function(){ try{ var v = parseInt(localStorage.getItem('xy_zoom'), 10); if(v) setZoom(v); }catch(e){} })();
function resetAll(){
  setZoom(100);
  document.documentElement.classList.remove('dark');
  document.getElementById('darkBtn').classList.remove('on');
  document.body.classList.remove('minmode');
  document.getElementById('minBtn').classList.remove('on');
  try{ localStorage.setItem('xy_dark', ''); localStorage.setItem('xy_min', ''); }catch(e){}
  if(reading){ try{ speechSynthesis.cancel(); }catch(e){} reading = false; var rbn = document.getElementById('readBtn'); rbn.classList.remove('on'); rbn.textContent = '朗读'; }
  toast('已恢复默认设置');
}
function toggleDark(){
  var on = document.documentElement.classList.toggle('dark');
  document.getElementById('darkBtn').classList.toggle('on', on);
  try{ localStorage.setItem('xy_dark', on ? '1' : ''); }catch(e){}
  toast(on ? '已开启深色模式' : '已关闭深色模式');
}
(function(){ try{ if(localStorage.getItem('xy_dark') === '1'){ document.documentElement.classList.add('dark'); document.getElementById('darkBtn').classList.add('on'); } }catch(e){} })();
var reading = false;
function toggleRead(){
  if(reading){
    try{ speechSynthesis.cancel(); }catch(e){}
    reading = false;
    document.getElementById('readBtn').classList.remove('on');
    document.getElementById('readBtn').textContent = '朗读';
    toast('已停止朗读');
    return;
  }
  if(!('speechSynthesis' in window)){ toast('当前浏览器不支持朗读'); return; }
  var lines = [];
  lines.push('行隅，心智障碍就业导航。');
  var heads = document.querySelectorAll('.card .nm');
  for(var i = 0; i < heads.length && i < 15; i++){ lines.push(heads[i].textContent); }
  var msg = new SpeechSynthesisUtterance(lines.join('。'));
  msg.lang = 'zh-CN'; msg.rate = 0.95;
  msg.onend = function(){ reading = false; document.getElementById('readBtn').classList.remove('on'); document.getElementById('readBtn').textContent = '朗读'; };
  reading = true;
  document.getElementById('readBtn').classList.add('on');
  document.getElementById('readBtn').textContent = '停止';
  speechSynthesis.cancel();
  speechSynthesis.speak(msg);
  toast('正在朗读当前列表前 ' + Math.min(heads.length, 15) + ' 条岗位');
}
// ===== 分享 =====
function openShare(){ document.getElementById('shareMask').style.display = 'flex'; }
function closeShare(){ document.getElementById('shareMask').style.display = 'none'; }
function copyShare(){
  var url = 'https://james-liang-o.github.io/xingyu-jobs/';
  if(navigator.clipboard && navigator.clipboard.writeText){
    navigator.clipboard.writeText(url).then(function(){ toast('链接已复制，去微信/QQ粘贴发送'); }).catch(function(){ toast('链接：' + url); });
  } else {
    var ta = document.createElement('textarea');
    ta.value = url; ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta); ta.select();
    try{ document.execCommand('copy'); toast('链接已复制，去微信/QQ粘贴发送'); }catch(_){ toast('链接：' + url); }
    document.body.removeChild(ta);
  }
}
</script>
</body>
</html>
"""

# 专栏数据：从 articles.json 动态构建（结构 {分类: [{t,s,o,d,u}]}）
COLS_KEYS = ['social', 'doing', 'company', 'policy', 'teach', 'activity', 'resource', 'intl', 'support', 'emp', 'guide']
cols_data = {}
for key in COLS_KEYS:
    items = []
    for it in articles.get(key, []):
        items.append({
            't': it.get('title', ''),
            's': it.get('summary', ''),
            'o': it.get('source', ''),
            'd': it.get('date', ''),
            'u': it.get('url', ''),
        })
    cols_data[key] = items
js_cols = json.dumps(cols_data, ensure_ascii=False)

HTML_DOC = HTML_DOC.replace('__UPDATED__', esc(updated_at)).replace('__TOTAL__', str(total)).replace('__CITIES__', str(len(all_cities)))
HTML_DOC = HTML_DOC.replace('__JS_CHUNK0__', js_chunk0).replace('__JS_CITIES__', js_cities)
HTML_DOC = HTML_DOC.replace('__CHUNK_TOTAL__', str(chunk_total))
HTML_DOC = HTML_DOC.replace('__COLS_DATA__', js_cols)
# 所有权指纹注入
HTML_DOC = HTML_DOC.replace('__OWN_HASH__', OWN_HASH)
# 心智障碍可投数
HTML_DOC = HTML_DOC.replace('心智障碍可投  条岗位', '心智障碍可投 ' + str(total_mh) + ' 条岗位')

out = os.path.join(BASE, '行隅_全国岗位导航.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(HTML_DOC)
print('written:', out, len(HTML_DOC), 'bytes')
