# -*- coding: utf-8 -*-
"""
行隅·全国残疾人岗位爬虫 v2
来源（全部为公开页面/公开接口，仅供信息导航，数据版权归原发布方）：
  1. 中国残联就业服务平台 - 动态接口（全国岗位，公开数据，低频访问）
  2. 上海市人社局 - 事业单位面向残疾人专项招聘公告（含岗位简章 xls）
  3. 上海市残联 - 就业服务中心工作动态
  4. 虹口区残联 - 助残就业活动公告
  5. 广东省残疾人就业服务网 - 站点入口（SPA，接口未公开，保留入口）
输出：jobs_national.json（全量+按城市分组） / jobs_national.csv
"""
import json, re, csv, urllib.request, ssl, time

HDR = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36'}
CTX = ssl.create_default_context()
CTX.check_hostname = False
CTX.verify_mode = ssl.CERT_NONE

def fetch(url, timeout=30, retries=2):
    for i in range(retries):
        try:
            req = urllib.request.Request(url, headers=HDR)
            with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
                return r.read()
        except Exception as e:
            if i == retries - 1:
                print('FETCH FAIL', url, e)
                return None
            time.sleep(1)
    return None

CENTRAL_KEYS = ['中国联通','中国移动','中国电信','国家电网','南方电网','中国石油','中国石化','中国海油','中石油','中石化',
'中国建筑','中国中铁','中国铁建','中国交建','中国邮政','中国银行','工商银行','农业银行','建设银行','交通银行','邮储银行',
'中国人寿','中国人保','中国烟草','中粮集团','国投','华润','中核','航天科技','航天科工','航空工业','中国船舶','兵器工业',
'中国电子','中国中车','中国能建','中国电建','中国化学','中国五矿','中广核','国家能源集团','中国华能','中国大唐','中国华电',
'国家电投','中国三峡','中国宝武','鞍钢集团','中国铝业','中远海运','中国中化','招商局','中信集团','光大集团','中国国新',
'中国诚通','中国航发','中国融通','国家开发银行','进出口银行','农业发展银行','中国一汽','东风汽车','中国商飞','中国旅游集团',
'中国黄金','中国盐业','中国通用','新兴际华','中国节能','中国建材','中国有色','中国钢研','中国中冶','中国航空油料']
STATE_KEYS = ['集团有限公司','集团股份公司','省电力','市电力','水务集团','燃气集团','公交集团','地铁集团','轨道交通',
'城投','城建集团','交通投资','交投集团','铁路投资','国有资本','国资委','烟草公司','烟草专卖','供电公司','发电集团',
'能源集团','建设投资集团','开发投资','港口集团','机场集团','粮油集团','供销社','粮食集团','盐业公司','盐业集团',
'自来水公司','热力公司','供热公司','供水集团','高速公路集团']
GOV_KEYS = ['人民政府','街道办事处','机关事务','委员会','残疾人联合会','研究院','科学院','大学','学院','博物馆','图书馆',
'人民医院','中医院','中心医院','妇幼保健院','体育职业学院','人才服务中心','就业服务中心','劳动保障']

def classify_nature(pr, name):
    """识别单位性质：pr 字段优先，名称关键词兜底。返回 '' / 央企 / 国企 / 事业单位"""
    if pr in ('央企', '国企', '事业单位', '机关'):
        return pr
    n = name or ''
    if not n:
        return ''
    if any(k in n for k in CENTRAL_KEYS):
        return '央企'
    if any(k in n for k in GOV_KEYS):
        return '事业单位'
    if any(k in n for k in STATE_KEYS):
        return '国企'
    m = re.match(r'^([一-龥]{2,4})(省|市|县|自治州|自治县)', n)
    if m and any(k in n for k in ['集团', '电力', '供水', '燃气', '热力', '公交', '地铁', '供热', '自来水']):
        return '国企'
    return ''

def html_text(b):
    if not b:
        return ''
    s = b.decode('utf-8', errors='ignore')
    s = re.sub(r'<script[\s\S]*?</script>', ' ', s)
    s = re.sub(r'<style[\s\S]*?</style>', ' ', s)
    s = re.sub(r'<[^>]+>', ' ', s)
    s = re.sub(r'&nbsp;?', ' ', s)
    s = re.sub(r'&ldquo;|&rdquo;', '"', s)
    s = re.sub(r'&mdash;', '-', s)
    s = re.sub(r'\s+', ' ', s)
    return s.strip()

def parse_xls_roles(data):
    """解析人社局岗位简章 xls"""
    try:
        import xlrd
        wb = xlrd.open_workbook(file_contents=data)
    except Exception as e:
        print('XLS ERR', e)
        return []
    sh = wb.sheet_by_index(0)
    head_row = None
    for r in range(min(6, sh.nrows)):
        vals = [str(sh.cell_value(r, c)).strip() for c in range(sh.ncols)]
        joined = '|'.join(vals)
        if (('岗位编号' in joined or '岗位名称' in joined) and '单位' in joined
                and any('主管' in v or '用人' in v or '招聘人数' in v for v in vals)):
            head_row = r
            break
    if head_row is None:
        return []
    head = [str(sh.cell_value(head_row, c)).strip() for c in range(sh.ncols)]
    def col(*names):
        for i, h in enumerate(head):
            for n in names:
                if n in h:
                    return i
        return -1
    ci = {
        'code': col('岗位编号'), 'owner': col('主管单位'), 'org': col('用人单位'),
        'name': col('岗位名称'), 'type': col('岗位类别'), 'duty': col('岗位职责'),
        'num': col('招聘人数'), 'edu': col('学历'), 'major': col('专业'),
        'loc': col('工作地点'), 'contact': col('联系人'),
    }
    roles = []
    for r in range(head_row + 1, sh.nrows):
        def g(k):
            i = ci[k]
            return str(sh.cell_value(r, i)).strip() if i >= 0 else ''
        name = g('name')
        if not name:
            continue
        roles.append({
            'code': g('code'), 'owner': g('owner'), 'org': g('org'), 'name': name,
            'type': g('type'), 'duty': g('duty'), 'num': g('num'),
            'edu': g('edu'), 'major': g('major'), 'loc': g('loc'),
            'contact': re.sub(r'\s+', ' ', g('contact')),
            'source': '上海市人社局-残疾人专项招聘',
            'url': 'https://rsj.sh.gov.cn/tgsgg_17341/20251031/t0035_1436498.html',
            'published': '2025-10-31',
        })
    return roles

def fetch_hubei_api(pages=3):
    """爬湖北省残疾人求职招聘信息平台（官方公开接口）"""
    jobs = []
    for p in range(1, pages + 1):
        try:
            q = urllib.parse.urlencode({'pageNum': p, 'size': 50})
            url = 'https://www.hbcjrjy.cn/prod-api/open/Jobhb/getLatestPositionList?' + q
            req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://www.hbcjrjy.cn/'})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                body = json.loads(r.read().decode('utf-8', errors='ignore'))
        except Exception as e:
            print('  湖北API ERR page %d: %s' % (p, e))
            time.sleep(2)
            continue
        recs = body.get('data') or []
        if not recs:
            break
        for rec in recs:
            # 湖北接口返回字段：job 岗位名 / companyName / createTime / jobInfo(HTML职责)
            duty = re.sub(r'<[^>]+>', ' ', rec.get('jobInfo', '') or '')
            duty = re.sub(r'\s+', ' ', duty).strip()
            jobs.append({
                'code': str(rec.get('jobId', '')), 'owner': classify_nature('', rec.get('companyName', '')), 'org': rec.get('companyName', ''),
                'name': rec.get('job', ''), 'type': '',
                'duty': duty[:200],
                'num': '', 'edu': '',
                'major': '', 'loc': '湖北省', 'prov': '湖北省', 'city': '', 'dist': '',
                'contact': '见原平台', 'source': '湖北省残疾人求职招聘信息平台',
                'url': 'https://www.hbcjrjy.cn/jobDetail/' + str(rec.get('jobId', '')),
                'published': rec.get('createTime', ''), 'updated': rec.get('updateTime', ''),
                'deadline': '',
                'dis_types': [], 'dis_str': '', 'is_mh': False,
            })
        time.sleep(0.8)
    return jobs

def fetch_prov_api(host, pages=3):
    """爬省级残联就业平台（cdpee 同源系统，getHomeJob 接口）"""
    jobs = []
    base = host + '/api/app-jycy-job/getHomeJob'
    for p in range(1, pages + 1):
        try:
            q = urllib.parse.urlencode({'pageNum': p, 'pageSize': 50})
            req = urllib.request.Request(base + '?' + q, headers={'User-Agent': 'Mozilla/5.0', 'Referer': host + '/'})
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                body = json.loads(r.read().decode('utf-8', errors='ignore'))
        except Exception as e:
            print('  省级API ERR %s page %d: %s' % (host, p, e))
            time.sleep(2)
            continue
        data = body.get('data') or {}
        recs = data.get('records', [])
        if not recs:
            break
        for rec in recs:
            ci = rec.get('companyInfo') or {}
            prov = rec.get('provinceid', '') or ''
            city = rec.get('cityid', '') or ''
            dist = rec.get('threeCityid', '') or ''
            loc = (prov + '·' + city + ('·' + dist if dist and dist not in (prov, city) else '')).strip('·')
            dis_list = rec.get('distype') or []
            dis_types = [d.get('disType', '') for d in dis_list if isinstance(d, dict)]
            dis_str = rec.get('distypeStr', '') or ''
            is_mh = ('智力残疾' in dis_str or '精神残疾' in dis_str or '智力残疾' in dis_types or '精神残疾' in dis_types)
            is_mental = ('精神残疾' in dis_str or '精神残疾' in dis_types)
            is_physical = any(k in dis_str or k in dis_types for k in ['肢体残疾', '视力残疾', '听力残疾', '言语残疾'])
            jobs.append({
                'code': rec.get('id', ''), 'owner': classify_nature(ci.get('pr', ''), ci.get('companyName', '')), 'org': ci.get('companyName', ''),
                'name': rec.get('jobName', ''), 'type': rec.get('jobType', ''),
                'duty': ' | '.join([x for x in [rec.get('jobTop', ''), rec.get('jobNext', ''), rec.get('jobPost', '')] if x]),
                'num': rec.get('jobNumber', ''), 'edu': rec.get('edu', ''),
                'major': '', 'loc': loc, 'prov': prov, 'city': city, 'dist': dist,
                'contact': '见原平台', 'source': host.replace('https://', '') + '（省级残联平台）',
                'url': host + '/job/jobDetail?id=' + str(rec.get('id', '')),
                'published': rec.get('createTime', ''), 'updated': rec.get('updateTime', ''),
                'deadline': rec.get('endTime', ''),
                'dis_types': dis_types, 'dis_str': dis_str, 'is_mh': is_mh, 'is_mental': is_mental, 'is_physical': is_physical,
            })
        time.sleep(0.8)
    return jobs

def fetch_national_api(pages=60, page_size=500):
    """爬中国残联就业服务平台动态接口（公开数据）：全国岗位，全量翻页"""
    jobs = []
    base = 'https://www.cdpee.org.cn/api/app-jycy-job/querySearchJobInfo'
    seen_ids = set()
    for p in range(1, pages + 1):
        try:
            q = urllib.parse.urlencode({'pageNum': p, 'pageSize': page_size})
            req = urllib.request.Request(base + '?' + q, headers=HDR)
            with urllib.request.urlopen(req, timeout=30, context=CTX) as r:
                body = json.loads(r.read().decode('utf-8', errors='ignore'))
        except Exception as e:
            print('  API ERR page %d: %s' % (p, e))
            time.sleep(2)
            continue
        data = body.get('data') or {}
        recs = data.get('records', [])
        if not recs:
            break
        new_cnt = 0
        for rec in recs:
            rid = str(rec.get('id', ''))
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            new_cnt += 1
            ci = rec.get('companyInfo') or {}
            prov = rec.get('provinceid', '') or ''
            city = rec.get('cityid', '') or ''
            dist = rec.get('threeCityid', '') or ''
            loc = (prov + '·' + city + ('·' + dist if dist and dist not in (prov, city) else '')).strip('·')
            # 残疾类型要求（心智障碍相关：智力残疾 / 精神残疾）
            dis_list = rec.get('distype') or []
            dis_types = [d.get('disType', '') for d in dis_list if isinstance(d, dict)]
            dis_str = rec.get('distypeStr', '') or ''
            is_mh = ('智力残疾' in dis_str or '精神残疾' in dis_str or '智力残疾' in dis_types or '精神残疾' in dis_types)
            is_mental = ('精神残疾' in dis_str or '精神残疾' in dis_types)
            is_physical = any(k in dis_str or k in dis_types for k in ['肢体残疾', '视力残疾', '听力残疾', '言语残疾'])
            # 时效字段：createTime 发布时间 / updateTime 更新时间 / endTime 招聘截止
            jobs.append({
                'code': rec.get('id', ''), 'owner': classify_nature(ci.get('pr', ''), ci.get('companyName', '')), 'org': ci.get('companyName', ''),
                'name': rec.get('jobName', ''), 'type': rec.get('jobType', ''),
                'duty': ' | '.join([x for x in [rec.get('jobTop', ''), rec.get('jobNext', ''), rec.get('jobPost', '')] if x]),
                'num': rec.get('jobNumber', ''), 'edu': rec.get('edu', ''),
                'major': '', 'loc': loc, 'prov': prov, 'city': city, 'dist': dist,
                'contact': '见原平台', 'source': '中国残联就业服务平台（动态接口）',
                'url': 'https://www.cdpee.org.cn/job/jobDetail?id=' + str(rec.get('id', '')),
                'published': rec.get('createTime', ''),
                'updated': rec.get('updateTime', ''), 'deadline': rec.get('endTime', ''),
                'status': 'active' if str(rec.get('jobStatus', '1')) == '1' else 'expired',
                'job_status': rec.get('jobStatus', '1'),
                'dis_types': dis_types, 'dis_str': dis_str, 'is_mh': is_mh, 'is_mental': is_mental, 'is_physical': is_physical,
            })
        time.sleep(0.8)
    return jobs

def pinyin_first_letter(s):
    """取城市名拼音首字母（A-Z），用于城市索引"""
    if not s:
        return '#'
    # 简单映射常用城市；兜底用汉字 unicode 粗略映射到拼音首字母表
    table = {}
    for line in """A阿 B八巴 C擦 D大 E额 F发 G嘎 H哈 I J机 K卡 L拉 M妈 N拿 O哦 P怕 Q七 R日 S撒 T他 U V W挖 X西 Y压 Z扎""".split():
        pass
    # 使用首汉字匹配常用拼音表（覆盖常见城市即可，兜底返回首个汉字）
    mapping = {
        '北': 'B', '上': 'S', '广': 'G', '深': 'S', '天': 'T', '重': 'C', '成': 'C', '杭': 'H',
        '南': 'N', '武': 'W', '西': 'X', '苏': 'S', '郑': 'Z', '长': 'C', '沈': 'S', '济': 'J',
        '哈': 'H', '石': 'S', '太': 'T', '昆': 'K', '贵': 'G', '兰': 'L', '拉': 'L', '乌': 'W',
        '银': 'Y', '呼': 'H', '西': 'X', '宁': 'N', '海': 'H', '福': 'F', '厦': 'X', '青': 'Q',
        '大': 'D', '连': 'L', '无': 'W', '东': 'D', '烟': 'Y', '潍': 'W', '洛': 'L', '开': 'K',
        '洛': 'L', '佛': 'F', '东': 'D', '温': 'W', '嘉': 'J', '绍': 'S', '湖': 'H', '徐': 'X',
        '常': 'C', '镇': 'Z', '扬': 'Y', '泰': 'T', '盐': 'Y', '淮': 'H', '合': 'H', '芜': 'W',
        '安': 'A', '马': 'M', '南': 'N', '泉': 'Q', '漳': 'Z', '泉': 'Q', '赣': 'G', '九': 'J',
        '上': 'S', '昌': 'C', '宜': 'Y', '岳': 'Y', '株': 'Z', '湘': 'X', '衡': 'H', '长': 'C',
    }
    first = s[0]
    return mapping.get(first, '#')

def main():
    jobs = []
    # ===== 读取上一轮数据（用于增量归档失效岗位） =====
    prev = {}
    try:
        with open('jobs_national.json', encoding='utf-8') as f:
            prev_data = json.load(f)
        for j in prev_data.get('jobs', []):
            if j.get('code'):
                prev[str(j['code'])] = j
        print('上一轮岗位:', len(prev))
    except Exception as e:
        print('无上一轮数据（首次运行）:', e)

    # ===== 来源1：中国残联动态接口（全国） =====
    print('[1/6] 中国残联动态接口（全国，全量翻页，保留全部残疾类型）...')
    api_jobs = fetch_national_api(pages=200, page_size=500)
    for j in api_jobs:
        j.setdefault('is_mental', '精神残疾' in (j.get('dis_str') or ''))
        j.setdefault('is_physical', any(k in (j.get('dis_str') or '') for k in ['肢体残疾', '视力残疾', '听力残疾', '言语残疾']))
    jobs.extend(api_jobs)
    print('  全国动态岗位数:', len(api_jobs), '| 心智可投:', sum(1 for j in api_jobs if j.get('is_mh')), '| 精神可投:', sum(1 for j in api_jobs if j.get('is_mental')), '| 身体类:', sum(1 for j in api_jobs if j.get('is_physical')))

    # ===== 来源2：甘肃省残疾人就业创业网络服务平台 =====
    print('[2/6] 甘肃省残疾人就业创业网络服务平台...')
    gs_jobs = fetch_prov_api('https://gansu.cdpee.org.cn', pages=15)
    jobs.extend(gs_jobs)
    print('  甘肃岗位数:', len(gs_jobs))

    # ===== 来源3：湖北省残疾人求职招聘信息平台 =====
    print('[3/6] 湖北省残疾人求职招聘信息平台...')
    hb_jobs = fetch_hubei_api(pages=15)
    jobs.extend(hb_jobs)
    print('  湖北岗位数:', len(hb_jobs))

    # ===== 来源4：上海市人社局 =====
    print('[4/6] 上海市人社局专项招聘...')
    xls_url = 'https://rsj.sh.gov.cn/cmsres/33/33dc8ddf11834ea5af10a2496173e0d7/bd21cf6e2876cf371e56f44a317f4f1e.xls'
    data = fetch(xls_url)
    if data:
        roles = parse_xls_roles(data)
        for r in roles:
            r.setdefault('prov', '上海市'); r.setdefault('city', '上海市'); r.setdefault('dist', '')
        jobs.extend(roles)
        print('  岗位数:', len(roles))

    # ===== 来源5：市残联动态 =====
    print('[5/6] 市残联就业动态...')
    news_url = 'https://www.shdpf.org.cn/clwz/clwz/jyfwzx/gzdt/index.html'
    b = fetch(news_url)
    if b:
        for m in re.finditer(r'<a[^>]+href="([^"]+)"[^>]*>([^<]*职为你来[^<]*|[^<]*招聘[^<]*)</a>', b.decode('utf-8', errors='ignore')):
            url, title = m.group(1).strip(), m.group(2).strip()
            if not url.startswith('http'):
                url = 'https://www.shdpf.org.cn' + url
            nb = fetch(url)
            if nb:
                txt = html_text(nb)
                jobs.append({
                    'code': '', 'owner': '', 'org': '（招聘会）', 'name': title,
                    'type': '招聘会', 'duty': txt[:300], 'num': '', 'edu': '', 'major': '',
                    'loc': '上海', 'prov': '上海市', 'city': '上海市', 'dist': '',
                    'contact': '见原公告', 'source': '上海市残联-就业服务中心',
                    'url': url, 'published': '',
                })
            time.sleep(0.5)

    # ===== 来源6：虹口残联 =====
    print('[6/6] 虹口区残联...')
    hk_url = 'https://www.shhk.gov.cn/xwzx/002014/20260507/b3557243-c46d-4e33-bd87-562077b8aaa5.html'
    hb = fetch(hk_url)
    if hb:
        txt = html_text(hb)
        jobs.append({
            'code': '', 'owner': '', 'org': '（区残联活动）', 'name': '虹口区助残周就业服务活动',
            'type': '招聘活动', 'duty': txt[:300], 'num': '', 'edu': '', 'major': '',
            'loc': '上海·虹口', 'prov': '上海市', 'city': '上海市', 'dist': '虹口区',
            'contact': '见原公告', 'source': '虹口区残联',
            'url': hk_url, 'published': '2026-05-07',
        })

    # ===== 来源7：广东平台入口 =====
    print('[7/7] 广东省残疾人就业服务网（站点入口）...')
    gb = fetch('https://www.jyfw.org.cn/')
    if gb:
        jobs.append({
            'code': '', 'owner': '', 'org': '（广东省平台）', 'name': '广东省残疾人就业服务网',
            'type': '站点入口', 'duty': '广东省残疾人就业岗位平台，岗位实时更新（含薪资），详见原站。',
            'num': '', 'edu': '', 'major': '', 'loc': '广东',
            'prov': '广东省', 'city': '', 'dist': '',
            'contact': '业务咨询 020-83196226', 'source': '广东省残疾人就业服务网',
            'url': 'https://www.jyfw.org.cn/', 'published': '',
        })

    # ===== 增量归档：上一轮有、本轮未出现的岗位标记失效并保留 =====
    fresh = set()
    for j in jobs:
        if j.get('code'):
            fresh.add(str(j['code']))
    expired = 0
    for code, old in prev.items():
        if code not in fresh:
            old = dict(old)
            old['status'] = 'expired'
            old['name'] = (old.get('name') or '') + ('【已失效】' if '【已失效】' not in (old.get('name') or '') else '')
            jobs.append(old)
            expired += 1
    if expired:
        print('归档失效岗位:', expired, '条')

    # 按城市分组（拼音首字母索引）
    city_map = {}
    for j in jobs:
        city = j.get('city') or j.get('prov') or '其他'
        if city not in city_map:
            city_map[city] = []
        city_map[city].append(j)

    # 每城市内按发布时间倒序（新的在前）；发布时间无法解析的排后面
    import datetime
    def sort_key(j):
        s = j.get('published') or ''
        m = re.search(r'(\d{4})[年/-](\d{1,2})[月/-](\d{1,2})', s)
        if m:
            return datetime.datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        return datetime.datetime(1970, 1, 1)
    for city in city_map:
        city_map[city].sort(key=sort_key, reverse=True)

    grouped = {}
    for city, lst in sorted(city_map.items()):
        letter = pinyin_first_letter(city)
        grouped.setdefault(letter, {})
        grouped[letter][city] = lst

    # 静态来源岗位默认标记 is_mh=False，dis_str 为空（人社局等未标明残疾类型）
    for j in jobs:
        j.setdefault('is_mh', False)
        j.setdefault('dis_str', '')
        j.setdefault('dis_types', [])

    out = {
        'updated_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'disclaimer': '本页面岗位信息均采集自各公开渠道（中国残联就业服务平台、各地残联与人社部门官网等），仅供求职者信息参考。信息版权归原发布方所有，岗位真实性与时效性以原发布方为准，请自行核实后联系。本平台仅为信息导航，不代投、不代招、不收取任何费用。',
        'total': len(jobs),
        'total_mh': sum(1 for j in jobs if j.get('is_mh')),
        'cities': len(city_map),
        'by_letter': grouped,
        'jobs': jobs,
    }
    with open('jobs_national.json', 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    with open('jobs_national.csv', 'w', encoding='utf-8-sig', newline='') as f:
        w = csv.writer(f)
        w.writerow(['省份', '城市', '岗位名称', '单位', '地点', '学历', '招聘人数', '适合残疾类型', '心智障碍可投', '联系方式', '来源', '原链接', '发布日期'])
        for j in jobs:
            w.writerow([j.get('prov', ''), j.get('city', ''), j['name'], j['org'], j['loc'], j['edu'], j['num'], j.get('dis_str', ''), '是' if j.get('is_mh') else '', j['contact'], j['source'], j['url'], j['published']])
    active = sum(1 for j in jobs if j.get('status') != 'expired')
    print('总计:', len(jobs), '条 | 覆盖城市:', len(city_map), '个 | 心智障碍可投:', out['total_mh'], '| 有效:', active, '失效:', len(jobs)-active, '-> jobs_national.json / jobs_national.csv')

if __name__ == '__main__':
    main()
