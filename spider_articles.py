# -*- coding: utf-8 -*-
"""
行隅 · 专栏爬虫 v2
来源（全部为公开网页/接口，仅供信息导航）：
  1. 中国残联官网「教育就业-工作动态」列表页（可翻页，主力源）
  2. 中国残联就业服务平台 资讯/公告/法规 接口（首页数据）
  3. 手工核验的真实报道（seed，追加在专栏）
按关键词把内容分类到五个专栏：social / doing / company / policy / teach
输出：articles.json（供 gen_page.py 生成页面）
"""
import urllib.request, ssl, json, re, time, html as htmllib
import urllib.parse

CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE
HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0'}

# 明显无关主题过滤（纯政治/纯内部事务等；活动类不再过滤）
UNRELATED = ['网络安全', '党建', '换届', '党史', '天气预报', '两会', '人大', '政协',
             '学习贯彻', '主题教育', '学习宣传', '读书班', '研讨会召开', '领导小组会议',
             '巡视', '督查', '问责', '述职', '民主生活会']
# 心智障碍相关（最高优先级，命中直接保留）
MH_KEYS = ['智力残疾', '精神残疾', '智力障碍', '精神障碍', '心智障碍', '孤独症', '自闭症',
           '心青年', '星青年', '喜憨儿', '星星的孩子', '特教', '培智', '智障', '唐氏',
           '智力', '精神残疾', '智残', '精残']
# 一般残疾人就业相关（含"残疾"语境即保留）
REL_KEYS = ['残疾人', '残障', '残疾', '助残']

# 专栏分类关键词（按优先级）
COL_RULES = [
    ('activity', ['助残日', '志愿', '运动会', '文艺汇演', '联欢', '汇演', '演出', '展览',
                  '艺术展', '音乐会', '马拉松', '健步', '游园', '夏令营', '开放日', '庆祝',
                  '文化节', '嘉年华', '主题活动', '关爱活动', '融合活动', '社会活动',
                  '交流活动', '联谊', '献爱心', '慰问活动', '趣味', '比赛', '大赛',
                  '展演', '歌咏', '书画', '摄影展', '特奥']),
    ('policy', ['政策', '规划', '办法', '条例', '通知', '意见', '规定', '保障金', '税收', '税务',
                '补贴', '奖励', '认证', '审核', '文件', '方案', '法律', '法规', '权益', '优待',
                '社保', '保险', '托养', '安置', '帮扶', '增收', '就业援助', '春风行动', '就业服务月',
                '保障', '问答', '解读', '措施', '标准', '民生实事']),
    ('teach', ['培训', '教学', '课程', '技能', '实训', '职教', '开班', '学员', '特教',
               '学艺', '讲座', '课堂', '教师', '教育', '职业指导', '测评', '实习', '上岗',
               '培养', '辅导', '职业康复', '职业技能', '就业能力', '提升班', '培训班']),
    ('company', ['企业', '公司', '招聘', '录用', '员工', '车间', '岗位', '合同', '就业基地',
                 '招工', '求职', '应聘', '入职', '用工', '吸纳', '接收', '工厂', '共建',
                 '安置就业', '残疾人就业']),
    ('doing', ['机构', '中心', '协会', '驿站', '工坊', '咖啡', '洗车', '项目', '活动',
               '公益', '扶残', '组织', '基地', '关爱', '赋能', '服务', '帮扶性', '辅助性']),
]

def fetch(url, timeout=20):
    try:
        req = urllib.request.Request(url, headers=HDR)
        with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
            return r.read().decode('utf-8', errors='ignore')
    except Exception as e:
        print('  fetch fail:', url[:60], e)
        return None

def keep(text):
    """是否保留：明显无关的过滤；残疾人/心智障碍相关保留"""
    t = text or ''
    if any(k in t for k in UNRELATED):
        return False
    if any(k in t for k in MH_KEYS):
        return True
    if any(k in t for k in REL_KEYS):
        return True
    return False

def classify(title):
    """按关键词分类到专栏"""
    t = title or ''
    for col, keys in COL_RULES:
        for k in keys:
            if k in t:
                return col
    return 'social'

def crawl_cdpf():
    """中国残联官网 教育就业-工作动态 列表页（可翻页）"""
    out = []
    base = 'https://www.cdpf.org.cn/ywpd/jyjy/jyjygzdt/'
    for p in range(0, 150):
        page = 'index.htm' if p == 0 else f'index{p}.htm'
        t = fetch(base + page)
        if not t:
            break
        items = re.findall(r'<li>\s*<span>([\d\-]+)</span>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S)
        if not items:
            if p > 0:
                break
            # 兼容无 span 的结构
            items = re.findall(r'<a[^>]+href="([^"]+\.htm)"[^>]*title="([^"]{8,80})"', t)
            items = [('', h, ti) for h, ti in items]
        new = 0
        for date, href, title in items:
            title = htmllib.unescape(re.sub(r'\s+', ' ', title)).strip()
            if len(title) < 8 or not keep(title):
                continue
            if not href.startswith('http'):
                href = 'https://www.cdpf.org.cn' + href if href.startswith('/') else base + href
            out.append({'title': title, 'date': date, 'url': href,
                        'source': '中国残联·教育就业', 'summary': ''})
            new += 1
        if new == 0 and p > 0:
            break
        time.sleep(0.5)
    print(f'  [中国残联官网·工作动态] {len(out)} 条')
    return out

def crawl_cdpf_list(base, source, label, maxpage=50):
    """中国残联官网 通用栏目列表页（政策资料/就业培训等）"""
    out = []
    for p in range(0, maxpage):
        page = 'index.htm' if p == 0 else f'index{p}.htm'
        t = fetch(base + page)
        if not t or t.startswith('ERR'):
            break
        items = re.findall(r'<li>\s*<span>([\d\-]+)</span>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S)
        if not items:
            items = re.findall(r'<a[^>]+href="([^"]+\.htm)"[^>]*title="([^"]{8,80})"', t)
            items = [('', h, ti) for h, ti in items]
        new = 0
        for date, href, title in items:
            title = htmllib.unescape(re.sub(r'\s+', ' ', title)).strip()
            if len(title) < 8 or not keep(title):
                continue
            if not href.startswith('http'):
                href = 'https://www.cdpf.org.cn' + href if href.startswith('/') else base + href
            out.append({'title': title, 'date': date, 'url': href,
                        'source': source, 'summary': ''})
            new += 1
        if new == 0 and p > 0:
            break
        time.sleep(0.4)
    print(f'  [{label}] {len(out)} 条')
    return out

def crawl_api(api, source, pages=1, size=20):
    """残联就业服务平台 资讯/公告/法规 接口"""
    out = []
    base = 'https://www.cdpee.org.cn/api/app-jycy-consultation/'
    seen = set()
    for p in range(1, pages + 1):
        try:
            req = urllib.request.Request(f'{base}{api}?pageNum={p}&pageSize={size}', headers=HDR)
            with urllib.request.urlopen(req, timeout=20, context=CTX) as r:
                d = json.loads(r.read().decode('utf-8', errors='ignore'))
            data = d.get('data') or {}
            recs = data.get('records', []) if isinstance(data, dict) else (data or [])
            if not recs:
                break
            for rec in recs:
                cid = rec.get('id')
                if cid in seen:
                    continue
                seen.add(cid)
                title = (rec.get('title') or '').strip()
                if not keep(title):
                    continue
                out.append({
                    'title': title,
                    'summary': (rec.get('conAbstract') or '').strip()[:120],
                    'source': rec.get('source') or source,
                    'date': (rec.get('createTime') or '')[:10].replace('/', '-'),
                    'url': f'https://www.cdpee.org.cn/news/newDetail?id={cid}',
                })
            time.sleep(0.4)
        except Exception as e:
            print(f'  [接口{api}] page{p} ERR {e}')
            break
    print(f'  [接口{api}] {len(out)} 条')
    return out

def _clean_title(x):
    return htmllib.unescape(re.sub(r'\s+', ' ', x)).strip()

def _absurl(base, href):
    """把相对链接绝对化"""
    if not href:
        return ''
    if href.startswith('//'):
        return 'https:' + href
    if href.startswith('http'):
        return href
    return urllib.parse.urljoin(base, href)

def parse_list(base, t):
    """通用列表页解析：适配多种结构，返回 [{title,date,url}]"""
    out = []
    items = re.findall(r'<li>\s*<span>([\d\-]+)</span>\s*<a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', t, re.S)
    if not items:
        items = re.findall(r'<a[^>]+href="([^"]+\.(?:htm|html|shtml))"[^>]*title="([^"]{8,80})"', t)
        items = [('', h, ti) for h, ti in items]
    if not items:
        items = re.findall(r'<a[^>]+href="([^"]+\.(?:htm|html|shtml))"[^>]*>([^<>]{8,60})</a>', t)
        items = [('', h, ti) for h, ti in items]
    for date, href, title in items:
        title = _clean_title(title)
        if len(title) < 8 or not keep(title):
            continue
        if re.search(r'\.(css|js|png|jpg|ico|gif|pdf|doc|zip)', href, re.I):
            continue
        if '更多' in title or '首页' in title or '登录' in title or '注册' in title:
            continue
        out.append({'title': title, 'date': date.strip(), 'url': _absurl(base, href),
                    'source': '', 'summary': ''})
    return out

def crawl_paged(name, base, page_fn, maxpage, sleep=0.4, src_label=None):
    """通用翻页爬取：page_fn(p) 返回第 p 页 URL（p 从 0 开始）"""
    out = []
    for p in range(maxpage):
        url = page_fn(p)
        t = fetch(url)
        if not t or t.startswith('ERR'):
            if p == 0:
                print(f'  [{name}] 首页失败: {str(t)[:30]}')
                return out
            break
        items = parse_list(url, t)
        if not items:
            if p > 0:
                break
        new = 0
        for it in items:
            if not it['source']:
                it['source'] = src_label or name
            out.append(it)
            new += 1
        if new == 0 and p > 0:
            break
        time.sleep(sleep)
    print(f'  [{name}] {len(out)} 条')
    return out

# 中国残联官网更多栏目（宣传文化/体育/康复/维权/政策/公告，可翻页）
CDPF_MORE_COLS = [
    ('中国残联·宣传文化', 'https://www.cdpf.org.cn/ywpd/xcwh/', 30),
    ('中国残联·体育', 'https://www.cdpf.org.cn/ywpd/ty/', 30),
    ('中国残联·康复', 'https://www.cdpf.org.cn/ywpd/kf/', 30),
    ('中国残联·维权', 'https://www.cdpf.org.cn/ywpd/wq/', 30),
    ('中国残联·政策文件', 'https://www.cdpf.org.cn/zwgk/zcwj/', 30),
    ('中国残联·通知公告', 'https://www.cdpf.org.cn/zwgk/ggtz1/', 30),
]

# 省级残联（广东/浙江可翻页，其余爬首页）
PROV_SOURCES = [
    ('广东残联·新闻', 'https://www.gddpf.org.cn/xwzx/index.html',
     lambda p: f'https://www.gddpf.org.cn/xwzx/index.html?page={p+1}', 15),
    ('浙江残联·动态', 'https://www.zjdpf.org.cn/col/col122/index.html',
     lambda p: 'https://www.zjdpf.org.cn/col/col122/index.html' if p == 0 else f'https://www.zjdpf.org.cn/col/col122/index_{p}.html', 15),
    ('海南残联', 'https://www.hidpf.org.cn/', None, 1),
    ('甘肃残联', 'https://www.gsdpf.org.cn/', None, 1),
    ('贵州残联', 'https://www.gzdpf.org.cn/', None, 1),
    ('陕西残联', 'https://www.sxdpf.org.cn/', None, 1),
    ('山东残联', 'https://www.sddpf.org.cn/', None, 1),
    ('重庆残联', 'https://www.cqdpf.org.cn/', None, 1),
    ('安徽残联', 'https://www.ahdpf.org.cn/', None, 1),
    ('中国残疾人网', 'https://www.chinadp.net.cn/', None, 1),
]

# 手工核验的真实报道（seed）
SEED_SOCIAL = [
    {"t": "就业辅导员：心智障碍者就业的“引路人”", "s": "湖南益阳，残联安排就业辅导员周妹一对一帮扶心智障碍青年刘望，联系企业提供切肉、穿串、打包等岗位，反复试岗后刘望选择了穿串工种，上岗前三天辅导员全程陪同，帮助他适应工作。", "u": "http://www.chinanews.com.cn/sh/2024/09-07/10282014.shtml", "o": "中国新闻网", "d": "2024-09-07"},
    {"t": "辅助性就业基地：让心智障碍者有事做、有收入", "s": "青海西宁“嫩芽醇夏”残疾人辅助性就业基地，为有就业意愿的心智障碍者提供就业安置场所，并在咖啡体验馆等场景中融入社会化训练，吸纳爱心组织参与辅导培训。", "u": "http://www.news.cn/mrdx/20241202/4d8243e463bd4e89b6e3733016cc2fbd/c.html", "o": "新华每日电讯", "d": "2024-12-02"},
    {"t": "“小黄车”流动摊位：心智障碍学员的咖啡与西点", "s": "宁波“首善有爱”助残服务综合体启动甬·爱“心”干线项目，利用地铁站点设置助残就业流动摊位，售卖心智障碍学员制作的咖啡、西点、文创产品。", "u": "https://zjnews.zjol.com.cn/zjnews/202412/t20241203_30684754.shtml", "o": "浙江在线", "d": "2024-12-03"},
    {"t": "重庆“星青年”就业驿站：第一份工作，3500元工资", "s": "36岁的莹莹在重庆南岸“小太阳就业驿站”找到人生中第一份工作，拿到3500元工资，用自己挣的钱买了新衣服。这里为成年心智障碍者提供就业岗位与技能支持。", "u": "https://epaper.cqcb.com/html/202512/04/content_510532.html", "o": "重庆晨报", "d": "2025-12-04"},
    {"t": "西宁“智爱共富工坊”：40多名心智障碍者就业", "s": "青海西宁城东区“智爱共富工坊”吸纳40多名智力、精神障碍人士就业，提供手工艺品制作、包装等岗位，帮助他们自食其力、融入社会。", "u": "https://qh.xinhuanet.com/20251204/4d6fc90aa12841a29d7a3e779dd1c76b/c.html", "o": "新华网青海", "d": "2025-12-04"},
    {"t": "天津“星绘咖啡”：首批20名心智障碍员工", "s": "天津首家面向心智障碍者的咖啡店“星绘咖啡”开业，首批20名心智障碍员工经过系统培训后上岗，学习咖啡制作、顾客接待等技能。", "u": "https://m.chinanews.com/wap/detail/chs/zw/10526290.shtml", "o": "中国新闻网", "d": "2025-12-03"},
    {"t": "苏州中德融创工场：为残障人士提供稳定就业", "s": "江苏太仓中德融创工场是一家专为心智障碍人士提供就业机会的社会企业，70多位残障人士在这里获得稳定工作和职业技能培训。", "u": "https://js.news.cn/20251204/98f9c0700a4d4cceae55a91735159107/c.html", "o": "新华网江苏", "d": "2025-12-04"},
    {"t": "32岁孤独症女孩有了第一份工作", "s": "32岁的刘诗羽从西安北稍门坐公交到李家村，在谷本塬手作食品店做胡萝卜手指馒头。这是她32年人生里第一次拥有“工作”的模样。", "u": "https://www.xiancn.com/content/2026-03/31/content_7376752.htm", "o": "西安新闻网", "d": "2026-03-31"},
    {"t": "重庆孤独症少年：7岁学说话，17岁入职快餐店", "s": "重庆孤独症少年吴杰2024年起入职连锁快餐店，靠诚实劳动获得薪水，每天搭乘轨道交通上下班，前厅点餐、后台接单、打包餐品都能独立完成。", "u": "https://m.gmw.cn/2026-06/01/content_1304478958.htm", "o": "光明网", "d": "2026-06-01"},
    {"t": "30岁孤独症青年默飞：咖啡店的兼职生活有了期待", "s": "30岁的默飞是孤独症青年，去年4月起在一家咖啡店兼职，虽然只是每周2次、每次2小时，但他的生活因此充满期待，第一次领工资时骄傲极了。", "u": "http://society.people.com.cn/n1/2026/0402/c428181-40693857.html", "o": "人民网", "d": "2026-04-02"},
    {"t": "大连自闭症青年宇航：分拣磁芯配件月入近3000元", "s": "持证辅导员帮助自闭症青年宇航进入企业，分拣制作磁芯配件是他每天的工作，现在一个月可以挣将近3000元，下班后他还会弹起新学的吉他曲。", "u": "http://www.xinhuanet.com/politics/2019-12/23/c_1125375359.htm", "o": "新华网", "d": "2019-12-23"},
    {"t": "福州孤独症青年郑昱成：第一份工资买了一束花", "s": "20岁的孤独症青年郑昱成在福州乌龙江公园“支持性就业”试点开启第一份工作，用入职后赚到的第一份工资购置鲜花送至公园管理处，感恩助力他逐梦的力量。", "u": "https://www.chinadp.net.cn/magazine/article/zhuce/31964.html", "o": "中国残疾人网", "d": "2026-07-03"},
    {"t": "22岁孤独症青年张宇：第一笔工资给妈妈买围巾", "s": "拿到入职面包坊后的第一笔工资，22岁的孤独症青年张宇走进饰品店为母亲挑了一条围巾。从惧怕机器声响到熟练完成面团称重、揉制、分装，他的蝶变是大龄孤独症青年走向职场的缩影。", "u": "https://edu.cnr.cn/list/20260829/t20260829_527797416.shtml", "o": "央广网", "d": "2026-08-29"},
    {"t": "22岁孤独症青年张雨晨：在科技公司实现就业", "s": "张雨晨两岁多被诊断为典型孤独症，智力不错但存在严重沟通障碍。2023年初，他在融爱融乐支持性就业项目帮助下进入一家科技公司工作，实现稳定就业。", "u": "https://news.cnr.cn/rebang/20230401/t20230401_526202382.shtml", "o": "央广网", "d": "2023-04-01"},
]
SEED_DOING = [
    {"t": "肯德基天使餐厅：为残障员工提供平等工作机会", "s": "肯德基天使餐厅自2012年在深圳诞生，已覆盖全国60多个城市、超70家门店，累计为数百位“天使员工”提供就业机会与成长空间。", "u": "http://www.gd.chinanews.com.cn/wap/2025/2025-12-03/445501.shtml", "o": "广东新闻网", "d": "2025-12-03"},
    {"t": "星巴克“展心计划”：关注心智障碍青年融合就业", "s": "北京星巴克公益基金会启动“展心计划”，支持心智障碍青年融合就业。心智障碍者陈东海是星巴克中国的“阳光伙伴”，和咖啡师伙伴一起学习咖啡、与顾客交流。", "u": "https://www.starbucks.com.cn/about/news/zhanxinjihua/", "o": "星巴克中国", "d": "2021-10-27"},
    {"t": "合肥5家企业：269名智力、精神残疾人实现就业", "s": "合肥市蜀山区残联对接维信诺电子、合肥轨道交通、合肥科技农商行等5家企业，提供270个岗位，安排269位智力、精神和重度肢体残疾人就业。", "u": "https://www.workercn.cn/c/2026-01-26/8718314.shtml", "o": "中工网", "d": "2026-01-26"},
    {"t": "北京工厂十余年吸纳上百名残疾人就业", "s": "2013年，工厂负责人郑雷伟招收了第一名智障女孩进厂，此后十余年间吸纳了上百名残疾人就业，最多时有五十多名残疾员工同时工作。", "u": "https://xinwen.bjd.com.cn/content/s682ec28ce4b0380e186c7900.html", "o": "京报网", "d": "2025-05-22"},
    {"t": "杭州海洋公园：两名“心青年”全职就业", "s": "杭州长乔海洋公园为心智障碍青年提供全职岗位，两名“心青年”在检票、引导等岗位稳定工作，企业还安排专人带教适应。", "u": "https://wap.chinanews.com/wap/detail/chs/zw/10622457.shtml", "o": "中国新闻网", "d": "2026-05-16"},
    {"t": "厦门“星空咖啡”：15名孤独症青年就业", "s": "厦门首家孤独症青年就业咖啡店“星空咖啡”落地，15名孤独症青年经过培训上岗，在咖啡制作、门店服务岗位实现就业。", "u": "https://www.humanrights.cn/2026/04/03/d5c1a0c865964141b26b1ae8e9382e26.html", "o": "中国人权网", "d": "2026-04-03"},
]
SEED_COMPANY = [
    {"t": "喜憨儿洗车：中国残联推广的就业项目", "s": "“喜憨儿”是对心智障碍者的昵称。中国残联向各地推广“喜憨儿洗车”项目，南京江北新区太阳花乐园引入项目创办洗车中心，建立残疾人职业实训基地。", "u": "https://www.mca.gov.cn/n152/n166/c1662004999980005889/content.html", "o": "中华人民共和国民政部", "d": "2025-07-09"},
    {"t": "中山14家企业“共建车间”：198名精神智力残疾人就业", "s": "中山市27家社区康园中心中，11家与企业建立“共建车间”，香山衡器、比亚迪电子、TCL空调、华艺灯饰等14家企业参与，为198名精神、智力、重度肢体残疾人解决就业。", "u": "https://epaper.zsnews.cn/epaper/zsrb/paperdate/20241204/part/4/articleid/2.html", "o": "中山日报", "d": "2024-12-04"},
    {"t": "北京CHAO酒店：孤独症青年走上档案扫描员岗位", "s": "孤独症青年丁丁经就业服务评估后进入CHAO酒店前厅部实习，就业辅导员采用“密集支持—建立自然支持—渐退跟踪”的分阶段模式，他已完成6个月实习。", "u": "https://www.bdpf.org.cn/cms68/web1459/subject/n1/n1459/n1551/n5605/n5612/c134035/content.html", "o": "北京市残疾人联合会", "d": "2026-08-16"},
    {"t": "当“星星的孩子”走向职场", "s": "人民网报道：越来越多孤独症青年在就业辅导员支持下走进企业，从保洁、理货到文创制作，星星的孩子正在被更多职场接纳。", "u": "https://society.people.com.cn/n1/2026/0402/c428181-40693857.html", "o": "人民网", "d": "2026-04-02"},
    {"t": "让长大的“星星”就业之路越走越宽", "s": "报道关注大龄孤独症群体就业：从岗位开发、就业支持到企业接纳，多地探索让长大的星星们有尊严地工作、生活。", "u": "https://m.chinanews.com/wap/detail/chs/zw/10683532.shtml", "o": "中国新闻网", "d": "2026-08-25"},
    {"t": "青岛喜憨儿洗车中心：一寸一寸擦亮人生", "s": "山东青岛喜憨儿洗车中心帮助心智障碍者找到工作。员工吴继麟等心智障碍者在这里冲洗车身、擦车，从被照顾者变成自食其力的人，收获自信与尊严。", "u": "http://society.people.com.cn/n1/2026/0522/c1008-40724961.html", "o": "人民日报", "d": "2026-05-22"},
    {"t": "福州乌龙江公园首位“星青年”试岗", "s": "全国助残日之际，福州乌龙江公园启动面向孤独症青年的“支持性就业”试点项目，20岁的郑昱成作为首位试岗青年在游客服务中心开启人生第一份工作。", "u": "http://www.chinanews.com.cn/sh/2026/05-17/10622950.shtml", "o": "中国新闻网", "d": "2026-05-17"},
    {"t": "全国首家“喜憨儿”洗车行：10年洗了10多万台车", "s": "深圳首家“喜憨儿”洗车行员工都是患有发育迟缓、智力障碍、孤独症、唐氏综合征、脑瘫等疾病的心智障碍者，10年洗了10多万台车，收获自信和尊严。", "u": "http://news.china.com.cn/2026-02/15/content_118335587.shtml", "o": "中国网", "d": "2026-02-15"},
    {"t": "太仓中德融创工场：全员心智障碍员工的正式工厂", "s": "国内首家全员心智障碍人士集中就业的企业，现有40名心智障碍员工和17名支持人员。在精密零件生产线上，孤独症青年和同事们一起完成正式工作。", "u": "https://www.news.cn/politics/20260117/0ed4d97f42b9421bafa4c33cc53e57a0/c.html", "o": "新华网", "d": "2026-01-17"},
    {"t": "合肥6名孤独症孩子签约维信诺电子", "s": "2025年底，合肥维信诺电子与6名刚成年的孤独症孩子签订工作合同，阿甘之家家庭支援中心挂牌“残疾人帮扶性就业基地”，同期实现6名孤独症青年就业。", "u": "https://scl.hefei.gov.cn/ztzl/msgc/18913565.html", "o": "合肥市残疾人联合会", "d": "2026-01-14"},
    {"t": "长春特校开洗衣店：22名自闭症员工融入社会", "s": "长春育龙特殊儿童语言康复培训学校出资开设托弗尔助残洗衣服务公司，现有22名自闭症员工，不以盈利为目的，帮助自闭症患者融入社会生活、享受工作氛围。", "u": "https://m.thepaper.cn/wifiKey_detail.jsp?contid=3085089&from=wifiKey", "o": "澎湃新闻", "d": "2026-08-02"},
    {"t": "华润万家广州：特教学校就业基地助力“心青年”就业", "s": "广州市社会福利院特教学校见习、实训及支持性就业基地在华润万家广州公司揭牌，与心友会携手为“心青年”融入社会、实现自我价值搭建平台。", "u": "https://www.xhby.net/content/s69cf8f3fe4b09a6c3e096de6.html", "o": "新华报业网", "d": "2026-04-03"},
]
SEED_POLICY = [
    {"t": "残疾人就业保障金：企业招残疾人有分档优惠", "s": "用人单位安排残疾人就业比例达到1%（含）以上但未达当地规定比例的，按应缴费额50%缴纳残保金；1%以下的按90%缴纳；在职职工30人（含）以下的企业免征。", "u": "https://www.gov.cn/zhengce/zhengceku/2023-03/28/content_5748750.htm", "o": "中国政府网", "d": "2023-03-26"},
    {"t": "按比例安排残疾人就业：法律规定的比例是多少", "s": "《残疾人就业保障金征收使用管理办法》规定，用人单位安排残疾人就业比例不得低于本单位在职职工总数的1.5%，达不到的要缴纳保障金，超过的享受奖励。", "u": "https://www.gov.cn/zhengce/zhengceku/2015-09/15/content_5650063.htm", "o": "中国政府网", "d": "2015-09-09"},
    {"t": "《促进残疾人就业三年行动方案（2025—2027年）》", "s": "国务院办公厅印发方案，实施残疾人劳动就业权益保障行动，要求依法依规纠治侵害残疾人就业权益的行为，各地审核安排残疾人就业人数不得额外提出户籍等限制条件。", "u": "https://www.gov.cn/zhengce/content/202506/content_7030053.htm", "o": "中国政府网", "d": "2025-06-25"},
    {"t": "残疾人就业条例：保障残疾人的劳动权利", "s": "国家对残疾人就业实行集中就业与分散就业相结合的方针。机关、团体、企业事业单位和民办非企业单位应当按照规定比例安排残疾人就业，并为其选择适当的工种和岗位。", "u": "https://www.gov.cn/zhengce/content/2008-03/28/content_6646.htm", "o": "中国政府网", "d": "2008-03-28"},
    {"t": "残疾人保障法：就业权益的重点保护", "s": "《中华人民共和国残疾人保障法》规定：国家实行按比例安排残疾人就业制度，不得在招聘、晋升、薪酬等环节歧视残疾人，不得因残疾降低工资待遇或单方解除劳动合同。", "u": "http://www.npc.gov.cn/npc/c2/c12435/201905/t20190521_276668.html", "o": "中国人大网", "d": "2018-11-05"},
    {"t": "天津市残疾人就业保障金征收和就业审核政策二十问", "s": "天津市残联详解残保金征收、按比例就业审核、超比例奖励等政策：超比例安排残疾人就业的企业，按每超1人每年最高9600元标准给予奖励；新招用残疾人就业有补贴。", "u": "http://www.tjdpf.org.cn/system/2026/05/06/030098685.shtml", "o": "天津市残疾人联合会", "d": "2026-05-06"},
]
SEED_TEACH = [
    {"t": "福建厦门“三师协同”：可视化、场景化、分步化教学", "s": "针对智力残疾学生认知特点，厦门职高采用“三师协同”教学组，结合岗位实际需求，用可视化、场景化、分步化方法降低学习门槛，让学生听得懂、学得会。", "u": "https://m.thepaper.cn/newsDetail_forward_32483236", "o": "澎湃新闻", "d": "2026-01-28"},
    {"t": "新化县“心青年”洗车技能培训：学会、记住、会用、熟练", "s": "培训采用“理论可视化+分步实操+晚间复盘”模式，专职讲师手把手教学，通过高频重复实操、耐心分层教学，考核合格直接上岗。", "u": "https://cl.hnloudi.gov.cn/ldclh/xxdt/jcdt/202608/f203ff3990d140fab30faafc9598458a.shtml", "o": "娄底市残疾人联合会", "d": "2026-08-11"},
    {"t": "广东慧灵：从职业康复训练到支持性就业", "s": "慧灵为心智障碍者提供职业康复训练、定岗培训、社会适应能力训练以及支持性就业全程跟踪，帮助其掌握保洁、快递、服务等岗位技能。", "u": "http://gd.hlcn.org/home/newsCate/detail/id/190.html", "o": "广东慧灵", "d": "2026-04-17"},
    {"t": "校企协同：13家特教学校与企业共建就业阶梯", "s": "学校与130余家企业建立稳定共建关系，开设砖雕、漆画、酒店服务、中医艾灸等11门特色职教课程，近半数合作企业直接提供实习岗位。", "u": "https://news.gmw.cn/2025-12/16/content_38479090.htm", "o": "光明网", "d": "2025-12-16"},
    {"t": "河北涞水特教：打造职教课程与实训场地", "s": "涞水县特教学校开设现代家政服务与管理、安全保卫服务两个职教专业，建成模拟超市、模拟宾馆、实操厨房、安保训练区等实训场地，超九成初中毕业残障学生升入职高。", "u": "http://he.people.com.cn/n2/2026/0702/c192235-41627912.html", "o": "人民网河北", "d": "2026-07-02"},
    {"t": "浙江：为孤独症学生设计“从结构化到弹性化”职业课程", "s": "浙江特殊教育职业学院与杨绫子学校等合作，以中西面点工艺为试点，为孤独症学生设计阶梯式进阶路径，中职练基础、高职学应变，配套《咖啡制作》等校本教材。", "u": "http://chinateacher.jyb.cn/zgjsb/html/2026-07/15/content_649510.htm", "o": "中国教师报", "d": "2026-07-15"},
]
SEED_ACTIVITY = [
    {"t": "河南省“暖星计划”公益活动启动：关爱孤独症儿童及家庭", "s": "在第18个世界孤独症日到来之际，河南省残联主办“暖星计划——孤独症儿童及家庭关爱行动”公益活动，以“落实关爱行动实施方案，促进孤独症群体全面发展”为主题，构建孤独症儿童全生命周期支持体系。", "u": "https://www.henancjr.org.cn/info/70594", "o": "河南省残疾人联合会", "d": "2025-04-09"},
    {"t": "徐州“星光同行·蓝丝带计划”世界孤独症日公益活动", "s": "徐州残联联合经开区、金龙湖街道等单位举办“星光同行·蓝丝带计划”孤独症日公益活动，通过多元互动形式呼吁社会关注孤独症群体，助力“星星的孩子”融入社会。", "u": "https://xzcl.gov.cn/news_detail?id=11229", "o": "徐州市残疾人联合会", "d": "2025-04-01"},
    {"t": "江阴“星希望”全澄友爱公益跑：为孤独症儿童奔跑", "s": "江阴市残联联合教育局、卫健委、文体广旅局举办第18个世界孤独症关注日暨“星希望”全澄友爱公益跑，吸引爱心人士、志愿者、孤独症儿童照顾者及专业工作者踊跃参与。", "u": "https://cl.jiangyin.gov.cn/doc/2025/04/03/1329874.shtml", "o": "江阴市残联", "d": "2025-04-03"},
    {"t": "阳泉城区残联开展第三十五次全国助残日系列活动", "s": "阳泉市城区残联围绕“弘扬自强与助残精神，凝聚团结奋进力量”主题，于5月12日至20日组织慰问困难残疾人、就业帮扶、文体活动等全国助残日系列活动。", "u": "https://www.sxdpf.org.cn/xwzx/jcdt/art/2025/art_70a570805ccd469cbfc3baa678c27455.html", "o": "山西省残疾人联合会", "d": "2025-05-29"},
    {"t": "深圳“点亮星晴·科技助残”世界孤独症日关爱活动", "s": "深圳市南山区残联指导、晴晴言语康复服务中心主办世界孤独症日关爱活动，近三百人齐聚，以“科技助残”主题将成果转化为对孤独症群体及其他残障人士的支持，助力融入社会。", "u": "http://www.sznews.com/news/content/mb/2025-04/03/content_31526026.htm", "o": "深圳新闻网", "d": "2025-04-03"},
    {"t": "壹基金蓝色行动：第十四年为孤独症群体倡导", "s": "2025年4月2日第18个世界孤独症日，壹基金蓝色行动以“有爱无碍的社区，自主自在的生活”为核心主张，联合50余家企业、430余家社会组织及100余位公众人物共同倡导社会认知与接纳。", "u": "http://cn.chinadaily.com.cn/a/202504/02/WS67ed2bfaa310e29a7c4a7708.html", "o": "中国日报网", "d": "2025-04-02"},
    {"t": "西安公益活动助力“星星的孩子”融入社会", "s": "第18个世界孤独症日前后，西安举办多种公益活动：大学生志愿者陪同40余个心智障碍者家庭的特殊孩子走出家门，走进交大校园参观体验，呼吁社会关注孤独症群体。", "u": "http://sn.news.cn/20250331/89606a21ee584fcab17623d216f96996/c.html", "o": "新华网陕西", "d": "2025-03-31"},
    {"t": "株洲开展世界孤独症日主题系列活动", "s": "为贯彻《孤独症儿童关爱促进行动实施方案（2024—2028年）》，株洲市在世界孤独症日开展孤独症儿童关爱主题活动，组织康复机构、志愿者和社会力量共同参与。", "u": "https://m.voc.com.cn/xhn/news/202504/28272282.html", "o": "新湖南", "d": "2025-04-03"},
    {"t": "四川省第十一届残运会暨第六届特奥会开幕", "s": "四川省第十一届残疾人运动会暨第六届特殊奥林匹克运动会在广安市开幕，成都代表团派出353名运动员参与21个大项，为智力残疾人等群体搭建展示自我的竞技舞台。", "u": "http://m.toutiao.com/group/7686461278559044138/", "o": "龙泉驿残联", "d": "2026-09-17"},
    {"t": "贵州举办第二十次全国特奥日活动", "s": "贵州特奥日活动结合智力残疾人身心特点设置亲子跳绳、乒乓球、定点投篮、拔河等趣味项目，孩子们在家长陪伴下踊跃参与，展现特奥少年阳光勇敢的精神风貌。", "u": "http://gz.people.com.cn/n2/2026/0728/c410739-41652610.html", "o": "人民网贵州", "d": "2026-07-28"},
    {"t": "陕西紫阳“运动无界，融合有爱”亲子趣味运动会", "s": "紫阳县在残疾人体育健身示范点举办亲子趣味运动会，设置套圈夺宝、弹跳乒乓球、亲子接力运球等项目，通过家属陪伴、志愿者协助、残健互动，引导智力残疾人走出家庭融入社区。", "u": "http://www.shx.chinanews.com.cn/news/2026/0723/111291.html", "o": "中国新闻网陕西", "d": "2026-07-23"},
    {"t": "乌鲁木齐天山区残健融合运动会", "s": "天山区残联举办残健融合运动会，既有拔河、同心协力大脚板等集体协作项目，也为智力残疾儿童设置保龄球、套圈、S弯障碍跑等趣味运动项目，促进残健共融。", "u": "https://www.xjdpf.org.cn/info/1106/34332.htm", "o": "新疆维吾尔自治区残疾人联合会", "d": "2026-05-21"},
    {"t": "天津第二十次全国特奥日活动启动", "s": "天津市特奥日主题为“运动无界，融合有爱”，近200名智力残疾人及亲友参加定点投篮、足球射门、飞镖球等趣味项目，并向18个特殊教育学校发放活动器材。", "u": "http://www.tjdpf.org.cn/system/2026/06/23/030100652.shtml", "o": "天津市残疾人联合会", "d": "2026-06-23"},
    {"t": "安阳特奥日活动暨融合趣味运动会", "s": "安阳市残联主办全国特奥日活动暨融合趣味运动会，设置多项亲子协作特色项目，兼顾趣味性、安全性与协作性，为特殊青少年提供奔跑协作、感受运动魅力的平台。", "u": "https://wap.anyang.gov.cn/2026/07-14/2514082.html", "o": "安阳市政府", "d": "2026-07-14"},
    {"t": "宜春“超越自我 融合有爱”特奥日亲子趣味运动会", "s": "宜春市残联与市智力残疾人及亲友协会联合主办特奥日亲子趣味运动会，弘扬“勇敢尝试 争取胜利”特奥精神，推动残健融合发展。", "u": "http://www.jxdpf.gov.cn/jxscjrlhh/sxdt/pc/content/content_2074391803497979904.html", "o": "江西省残疾人联合会", "d": "2026-07-07"},
    {"t": "福建第二十次全国特奥日活动：趣味运动促康复", "s": "福建省特奥日活动以“运动无界，融合有爱”为主题，将体育健身、康复训练与趣味互动深度结合，为智力残疾人搭建展示自我的平台。", "u": "http://fjnews.fjsen.com/wap/2026-07/30/content_32227871.htm", "o": "东南网", "d": "2026-07-30"},
]

def build():
    print('=== 行隅专栏爬虫 v3 ===')
    cols = {'social': [], 'doing': [], 'company': [], 'policy': [], 'teach': [], 'activity': []}

    # 1. 中国残联官网工作动态（主力，翻页）
    for it in crawl_cdpf():
        cols[classify(it['title'])].append(it)
    # 1b. 政策资料 / 就业培训
    for it in crawl_cdpf_list('https://www.cdpf.org.cn/ywpd/jyjy/jyjyzcwj/', '中国残联·政策资料', '政策资料'):
        cols[classify(it['title'])].append(it)
    for it in crawl_cdpf_list('https://www.cdpf.org.cn/fwpt1/jypx1/', '中国残联·就业培训', '就业培训'):
        cols[classify(it['title'])].append(it)
    # 1c. 中国残联更多栏目（宣传文化/体育/康复/维权/政策/公告）
    for name, base, maxp in CDPF_MORE_COLS:
        for it in crawl_paged(name, base, lambda p, b=base: b + ('index.htm' if p == 0 else f'index{p}.htm'), maxp, src_label=name):
            cols[classify(it['title'])].append(it)

    # 2. 残联就业服务平台接口（资讯/公告/法规）
    for api, src, pages in [('getHomeInformationList', '中国残联就业服务平台', 4),
                            ('getHomeNotice', '中国残联就业服务平台·公告', 4),
                            ('getHomeRegulations', '中国残联就业服务平台·政策', 4)]:
        for it in crawl_api(api, src, pages):
            cols[classify(it['title'])].append(it)

    # 3. 省级残联 + 中国残疾人网
    for name, base, page_fn, maxp in PROV_SOURCES:
        if page_fn:
            for it in crawl_paged(name, base, page_fn, maxp, src_label=name):
                cols[classify(it['title'])].append(it)
        else:
            t = fetch(base)
            for it in parse_list(base, t):
                it['source'] = name
                cols[classify(it['title'])].append(it)

    # 4. 手工核验的真实报道 seed
    for it in SEED_SOCIAL:
        cols['social'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})
    for it in SEED_DOING:
        cols['doing'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})
    for it in SEED_COMPANY:
        cols['company'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})
    for it in SEED_POLICY:
        cols['policy'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})
    for it in SEED_TEACH:
        cols['teach'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})
    for it in SEED_ACTIVITY:
        cols['activity'].append({'title': it['t'], 'summary': it['s'], 'source': it['o'], 'date': it['d'], 'url': it['u']})

    # 5. 历史累积：读取已有 articles.json 合并（内容只增不减）
    try:
        with open('articles.json', encoding='utf-8') as f:
            old = json.load(f)
        for k in cols:
            if old.get(k):
                cols[k].extend(old[k])
        print('  历史累积: 已合并旧数据', {k: len(old.get(k, [])) for k in cols})
    except Exception as e:
        print('  历史累积: 无旧数据或读取失败', str(e)[:40])

    # 6. 去重 + 按日期倒序
    for k in cols:
        seen = set()
        uniq = []
        for it in cols[k]:
            key = (it.get('url') or it.get('title', ''))
            if key in seen:
                continue
            seen.add(key)
            uniq.append(it)
        uniq.sort(key=lambda x: x.get('date', ''), reverse=True)
        # 每类最多保留 60 篇（保持"50 个左右"的自然浮动）
        cols[k] = uniq[:60]

    out = dict(cols)
    out['updated_at'] = time.strftime('%Y-%m-%d %H:%M:%S')
    with open('articles.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    print('=== 完成 ===')
    for k, v in cols.items():
        print(f'  {k}: {len(v)} 条')
    print('写入 articles.json')

if __name__ == '__main__':
    build()
