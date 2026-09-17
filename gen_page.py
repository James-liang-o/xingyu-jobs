# -*- coding: utf-8 -*-
"""生成 行隅·全国助残岗位导航 展示页（自包含单文件 HTML）"""
import json, re, html, datetime, urllib.parse, os

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, 'jobs_national.json'), encoding='utf-8') as f:
    data = json.load(f)

jobs = data['jobs']
updated_at = data['updated_at']
total = data['total']
total_mh = data.get('total_mh', 0)

# 精简字段，只留展示所需
rows = []
for j in jobs:
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
    })

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

# 构建精简 JS 数据（控制体积）
js_rows = []
for r in rows:
    js_rows.append({
        'n': r['n'], 'o': r['o'], 'l': r['l'], 'c': r['c'], 'e': r['e'], 'm': r['m'],
        't': r['t'], 'pb': r['pb'], 'dl': r['dl'], 'dy': r['dy'], 's': r['s'], 'u': r['u'],
    })
js_data = json.dumps(js_rows, ensure_ascii=False)

city_js = []
for city in all_cities:
    city_js.append({'name': city, 'letter': city_letter_map.get(city, '#'), 'count': city_letters[city]['count']})
js_cities = json.dumps(city_js, ensure_ascii=False)

HTML_DOC = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>行隅 · 全国助残岗位导航</title>
<link rel="icon" href="data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><rect width='100' height='100' rx='22' fill='%234F46E5'/><text x='50' y='68' font-size='52' text-anchor='middle' fill='white' font-family='sans-serif' font-weight='bold'>行</text></svg>">
<style>
  :root{
    --primary:#4F46E5; --primary-dark:#3730A3; --primary-light:#818CF8; --primary-bg:#EEF2FF;
    --bg:#F4F5F7; --card:#FFFFFF; --text:#1F2937; --sub:#6B7280; --line:#E5E7EB;
    --warn:#DC2626; --ok:#059669;
  }
  *{box-sizing:border-box;margin:0;padding:0}
  body{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei","Segoe UI",sans-serif;background:var(--bg);color:var(--text);padding-bottom:40px}
  /* 顶部 */
  .header{background:var(--primary);color:#fff;padding:20px 16px 14px;position:sticky;top:0;z-index:20;box-shadow:0 2px 8px rgba(79,70,229,.25)}
  .header .logo{font-size:20px;font-weight:700;display:flex;align-items:center;gap:8px}
  .header .logo .dot{width:30px;height:30px;border-radius:9px;background:#fff;color:var(--primary);display:flex;align-items:center;justify-content:center;font-weight:800;font-size:17px}
  .header .meta{font-size:12px;opacity:.85;margin-top:6px}
  /* 搜索 */
  .searchbar{padding:10px 16px;background:var(--primary);}
  .searchbar input{width:100%;border:none;border-radius:10px;padding:10px 14px;font-size:16px;outline:none;background:#fff}
  /* 城市索引条 */
  .letterbar{background:#fff;border-bottom:1px solid var(--line);padding:8px 10px;position:sticky;top:118px;z-index:15;box-shadow:0 1px 4px rgba(0,0,0,.04)}
  .letterbar .wrap{display:flex;gap:4px;overflow-x:auto;scrollbar-width:none}
  .letterbar .wrap::-webkit-scrollbar{display:none}
  .letterbar .ltr{flex:0 0 auto;width:32px;height:32px;line-height:32px;text-align:center;border-radius:8px;font-size:14px;font-weight:600;color:var(--sub);cursor:pointer}
  .letterbar .ltr.on{background:var(--primary);color:#fff}
  .letterbar .ltr.dis{color:#D1D5DB;cursor:default}
  .letterbar .all{flex:0 0 auto;padding:0 12px;height:32px;line-height:32px;border-radius:8px;font-size:13px;font-weight:600;color:var(--primary);background:var(--primary-bg);cursor:pointer}
  /* 城市标签区 */
  .citytag{padding:10px 16px;background:#fff;border-bottom:1px solid var(--line)}
  .citytag .ttl{font-size:12px;color:var(--sub);margin-bottom:8px}
  .citytag .tags{display:flex;flex-wrap:wrap;gap:8px}
  .citytag .tag{padding:6px 12px;border-radius:16px;font-size:13px;background:var(--primary-bg);color:var(--primary-dark);cursor:pointer}
  .citytag .tag.on{background:var(--primary);color:#fff}
  /* 列表 */
  .list{padding:12px 16px;display:flex;flex-direction:column;gap:10px}
  .card{background:var(--card);border-radius:12px;padding:14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
  .card .row1{display:flex;justify-content:space-between;align-items:flex-start;gap:10px}
  .card .nm{font-size:16px;font-weight:700;color:var(--text);flex:1}
  .card .badge{flex:0 0 auto;font-size:11px;padding:3px 8px;border-radius:6px}
  .badge.new{background:#FEE2E2;color:var(--warn)}
  .badge.hot{background:#D1FAE5;color:var(--ok)}
  .badge.norm{background:var(--primary-bg);color:var(--primary)}
  .card .org{font-size:13px;color:var(--sub);margin-top:4px;display:flex;align-items:center;gap:4px}
  .card .info{display:flex;flex-wrap:wrap;gap:6px 12px;margin-top:8px;font-size:12px;color:var(--sub)}
  .card .info .i{display:flex;align-items:center;gap:3px}
  .card .duty{font-size:12px;color:var(--sub);margin-top:6px;line-height:1.5}
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
  /* 统计条 */
  .stat{display:flex;gap:16px;padding:10px 16px;background:#fff;border-bottom:1px solid var(--line);font-size:12px;color:var(--sub)}
  .stat b{color:var(--primary);font-size:15px}
</style>
</head>
<body>
<div class="header">
  <div class="logo"><span class="dot">行</span>行隅 · 全国助残岗位导航</div>
  <div class="meta">数据更新：__UPDATED__ · 共 __TOTAL__ 条岗位 · __CITIES__ 个城市</div>
</div>
<div class="searchbar"><input id="q" placeholder="搜索岗位名称、公司、城市…" autocomplete="off"></div>
<div class="letterbar"><div class="wrap" id="letters"></div></div>
<div class="stat"><span>岗位 <b id="stTotal">__TOTAL__</b></span><span>城市 <b id="stCity">__CITIES__</b></span><span>当前显示 <b id="stShow">0</b></span></div>
<div class="citytag"><div class="ttl" id="cityHint">选择城市查看岗位</div><div class="tags" id="tags"></div></div>
<div class="list" id="list"></div>
<div class="empty" id="empty" style="display:none">没有找到符合条件的岗位，换个关键词试试</div>
<div class="disclaimer"><b>免责声明：</b>本页所有岗位信息均采集自公开渠道（中国残联就业服务平台、各地残联与人社部门官网等），仅供求职者参考。信息版权归原发布方所有，岗位真实性、时效性与联系方式以原发布方为准，请自行核实后再联系。本站仅为信息导航，不代投、不代招、不收取任何费用。若原岗位已招满或过期，以原平台为准。</div>

<script>
var JOBS = __JS_DATA__;
var CITIES = __JS_CITIES__;
var curLetter = '全部', curCity = '全部', kw = '';

// 字母条
var LETTERS = ['全部'].concat([...new Set(CITIES.map(function(c){return c.letter}))].sort());
var lettersEl = document.getElementById('letters');
LETTERS.forEach(function(L){
  var d = document.createElement('div');
  d.className = 'ltr' + (L==='全部'?' all':'') + (L==='#'?' dis':'');
  d.textContent = L;
  if(L==='#'){
    d.addEventListener('click', function(){});
  } else {
    d.addEventListener('click', function(){ curLetter = L; renderCities(); render(); });
  }
  lettersEl.appendChild(d);
});

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
  all.className = 'tag' + (curCity==='全部'?' on':'');
  all.textContent = '全部城市 ('+ list.reduce(function(a,c){return a+c.count},0) +')';
  all.addEventListener('click', function(){ curCity='全部'; renderCities(); render(); });
  tagEl.appendChild(all);
  list.forEach(function(c){
    var s = document.createElement('span');
    s.className = 'tag' + (curCity===c.name?' on':'');
    s.textContent = c.name + ' (' + c.count + ')';
    s.addEventListener('click', function(){ curCity = c.name; renderCities(); render(); });
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

function render(){
  var el = document.getElementById('list'); el.innerHTML = '';
  var shown = 0;
  JOBS.forEach(function(j){
    if(curCity!=='全部' && j.c!==curCity) return;
    if(curLetter!=='全部'){
      var c = CITIES.filter(function(x){return x.name===j.c})[0];
      if(!c || c.letter!==curLetter) return;
    }
    if(kw){
      var s = (j.n+j.o+j.c+j.s).toLowerCase();
      if(s.indexOf(kw.toLowerCase())<0) return;
    }
    shown++;
    var card = document.createElement('div'); card.className = 'card';
    var dl = fmtDeadline(j.dl), pb = fmtTime(j.pb);
    var badge = '<span class="badge new">新发布</span>';
    if(dl==='已截止') badge = '<span class="badge norm">已截止</span>';
    else if(dl && dl.indexOf('天后截止')>=0) badge = '<span class="badge hot">即将截止</span>';
    card.innerHTML =
      '<div class="row1"><div class="nm">'+j.n+'</div>'+badge+'</div>'+
      '<div class="org">'+j.o+'</div>'+
      '<div class="info">'+
        '<span class="i">📍 '+j.l+'</span>'+
        (j.e?'<span class="i">学历：'+j.e+'</span>':'')+
        (j.m?'<span class="i">招 '+j.m+' 人</span>':'')+
        (j.t?'<span class="i">'+j.t+'</span>':'')+
      '</div>'+
      (j.dy?'<div class="duty">'+j.dy+'</div>':'')+
      '<div class="foot"><div class="time">'+pb+(dl?' · <span class="dl">'+dl+'</span>':'')+'</div>'+
      '<div class="btns">'+
        '<a class="btn orig" target="_blank" rel="noopener" href="'+j.u+'">原平台</a>'+
        '<a class="btn ghost" target="_blank" rel="noopener" href="'+companyUrl(j.o)+'">查公司</a>'+
      '</div></div>';
    el.appendChild(card);
  });
  document.getElementById('stShow').textContent = shown;
  document.getElementById('empty').style.display = shown ? 'none' : 'block';
}

// 搜索
document.getElementById('q').addEventListener('input', function(e){
  kw = e.target.value.trim();
  if(kw){ curLetter='全部'; curCity='全部'; renderCities(); }
  render();
});

renderCities();
render();
</script>
</body>
</html>
"""

HTML_DOC = HTML_DOC.replace('__UPDATED__', esc(updated_at)).replace('__TOTAL__', str(total)).replace('__CITIES__', str(len(all_cities)))
HTML_DOC = HTML_DOC.replace('__JS_DATA__', js_data).replace('__JS_CITIES__', js_cities)

out = os.path.join(BASE, '行隅_全国岗位导航.html')
with open(out, 'w', encoding='utf-8') as f:
    f.write(HTML_DOC)
print('written:', out, len(HTML_DOC), 'bytes')
