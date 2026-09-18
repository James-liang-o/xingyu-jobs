# -*- coding: utf-8 -*-
"""
行隅·岗位数据质检脚本
功能：
  1. 查重：按 code 去重（保留信息最全的一条），重复条数写入报告
  2. 失效更新：截止日期已过但 status 仍为 active 的岗位 → expired（页面自动显示"已失效"）
  3. 链接检查：抽样 HEAD/GET 探测详情链接可访问性，坏链接统计域名级报告
  4. 自动修复：去重与失效标记直接写回 jobs_national.json，并重跑 gen_page.py 重新生成页面
用法：python3 quality_check.py [--skip-links]   （--skip-links 跳过链接检查，仅做查重与失效修复）
"""
import json, re, io, os, sys, ssl, datetime, random, socket
import urllib.request, urllib.parse

BASE = os.path.dirname(os.path.abspath(__file__))
JSON = os.path.join(BASE, 'jobs_national.json')
LINK_SAMPLE = 120          # 每次抽样的链接数量
LINK_TIMEOUT = 12          # 单个链接超时秒数
REPORT = []

def log(msg):
    print(msg, flush=True)
    REPORT.append(msg)

def load_jobs():
    with io.open(JSON, encoding='utf-8') as f:
        return json.load(f)

def save_jobs(data):
    with io.open(JSON, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False)

def today():
    return datetime.date.today()

def deadline_past(j):
    m = re.match(r'(\d{4})-(\d{2})-(\d{2})', j.get('deadline', '') or '')
    if not m:
        return False
    try:
        return datetime.date(*map(int, m.groups())) < today()
    except Exception:
        return False

def dedup(jobs):
    """按 code 去重：保留字段最全的一条（字段非空数量最多），其余丢弃"""
    by_code = {}
    for j in jobs:
        code = j.get('code', '')
        if not code:
            code = 'ncode-' + str(abs(hash((j.get('name',''), j.get('org',''), j.get('loc','')))))
            j['code'] = code
        cur = by_code.get(code)
        if cur is None:
            by_code[code] = j
            continue
        def score(x):
            return sum(1 for v in x.values() if v not in (None, '', []))
        if score(j) > score(cur):
            by_code[code] = j
    return list(by_code.values())

def refresh_status(jobs):
    """deadline 已过 → expired；expired 但 deadline 未过且原接口 job_status=1 → active（保守：不改回）"""
    fixed = 0
    for j in jobs:
        if j.get('status') != 'expired' and deadline_past(j):
            j['status'] = 'expired'
            fixed += 1
    return fixed

def check_link(url):
    """返回 (ok, detail)；ok=True 表示链接可访问（2xx/3xx），404/410/拒绝等视为坏"""
    if not url:
        return True, 'no-url'
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0 Safari/537.36'})
    try:
        with urllib.request.urlopen(req, timeout=LINK_TIMEOUT, context=ctx) as r:
            code = getattr(r, 'status', 200) or 200
        if code < 400:
            return True, 'HTTP %d' % code
        return False, 'HTTP %d' % code
    except urllib.error.HTTPError as e:
        return e.code in (401, 403, 429, 503), 'HTTP %d' % e.code   # 需要登录/限流/临时故障不算坏
    except Exception as e:
        return False, str(e)[:60]

def sample_links(jobs, n=LINK_SAMPLE):
    random.seed(today().toordinal())
    pool = [j for j in jobs if j.get('url')]
    picked = random.sample(pool, min(n, len(pool)))
    bad = []
    checked = 0
    for j in picked:
        ok, detail = check_link(j['url'])
        checked += 1
        if not ok:
            bad.append((j.get('code'), j.get('name',''), j.get('org',''), j.get('url',''), detail))
    return checked, bad

def main():
    skip_links = '--skip-links' in sys.argv
    data = load_jobs()
    jobs = data.get('jobs', [])
    before = len(jobs)
    log('质检开始：原始 %d 条' % before)

    # 1) 查重
    after_dedup = dedup(jobs)
    log('查重：%d 条 → %d 条（清理重复 %d 条）' % (before, len(after_dedup), before - len(after_dedup)))

    # 2) 失效更新
    fixed = refresh_status(after_dedup)
    expired = sum(1 for j in after_dedup if j.get('status') == 'expired')
    log('失效更新：本次标记失效 %d 条，当前失效共 %d 条' % (fixed, expired))

    # 3) 链接抽样
    if skip_links:
        log('链接检查：已跳过（--skip-links）')
        bad = []
    else:
        checked, bad = sample_links(after_dedup)
        log('链接检查：抽样 %d 条，坏链接 %d 条' % (checked, len(bad)))
        for b in bad[:15]:
            log('  坏链接: [%s] %s / %s → %s' % (b[0], b[1][:20], b[2][:16], b[4]))
        if len(bad) > 15:
            log('  ……共 %d 条坏链接（报告仅列前15）' % len(bad))

    # 4) 写回
    data['jobs'] = after_dedup
    data['total'] = len(after_dedup)
    if isinstance(data.get('total_mh'), int):
        data['total_mh'] = len(after_dedup)
    # by_letter 重建（若存在）
    if isinstance(data.get('by_letter'), dict) and data['by_letter']:
        by = {}
        for j in after_dedup:
            c = j.get('city') or j.get('prov') or '其他'
            for ch in c:
                m = {'北':'B','上':'S','广':'G','深':'S','天':'T','重':'C','成':'C','杭':'H','南':'N','武':'W','西':'X','苏':'S','郑':'Z','长':'C','沈':'S','济':'J','哈':'H','石':'S','太':'T','昆':'K','贵':'G','兰':'L','拉':'L','乌':'W','银':'Y','呼':'H','宁':'N','海':'H','福':'F','厦':'X','青':'Q','大':'D','连':'L','无':'W','东':'D','烟':'Y','潍':'W','洛':'L','开':'K','佛':'F','温':'W','嘉':'J','绍':'S','湖':'H','徐':'X','常':'C','镇':'Z','扬':'Y','泰':'T','盐':'Y','淮':'H','合':'H','芜':'W','安':'A','马':'M','泉':'Q','漳':'Z','赣':'G','九':'J','昌':'C','宜':'Y','岳':'Y','株':'Z','湘':'X','衡':'H','桂':'G','柳':'L','南':'N','宁':'N','海':'H','口':'K','三':'S','亚':'Y','长':'C','春':'C','吉':'J','松':'S','白':'B','通':'T','延':'Y','四':'S','辽':'L','盘':'P','营':'Y','阜':'F','丹':'D','锦':'J','朝':'C','辽':'L','阳':'Y','沈':'S','鞍':'A','抚':'F','本':'B','大':'D','连':'L','丹':'D','锦':'J','营':'Y','阜':'F','辽':'L','盘':'P','铁':'T','朝':'C','葫':'H','兴':'X','沧':'C','廊':'L','保':'B','承':'C','张':'Z','唐':'T','秦':'Q','邢':'X','邯':'H','衡':'H','台':'T','沧':'C','石':'S','张':'Z','承':'C','廊':'L','保':'B','唐':'T','秦':'Q','邢':'X','邯':'H','衡':'H'}.get(ch)
                if m:
                    by.setdefault(m, {}).setdefault(c, []).append(j)
                    break
        data['by_letter'] = by
    save_jobs(data)
    log('已写回 jobs_national.json：%d 条' % len(after_dedup))

    # 5) 重新生成页面
    log('重新生成页面…')
    os.chdir(BASE)
    ret = os.system('python3 gen_page.py')
    log('gen_page.py 退出码 %d' % (ret >> 8 if ret > 255 else ret))

    log('质检完成')

if __name__ == '__main__':
    main()
