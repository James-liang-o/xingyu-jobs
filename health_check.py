#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 行隅站点健康检查：线上可访问性 + 数据新鲜度 + 本地生成健康度
# 发现问题 → 自动重新触发岗位/专栏更新流程；代码本身坏了 → 建 issue 告警
import datetime, json, os, re, subprocess, sys, urllib.request

URL = 'https://james-liang-o.github.io/xingyu-jobs/'
REPO = os.environ.get('GITHUB_REPOSITORY', 'James-liang-o/xingyu-jobs')
TOKEN = os.environ.get('GH_TOKEN', '') or os.environ.get('GITHUB_TOKEN', '')

def fetch(url, timeout=40):
    req = urllib.request.Request(url, headers={'User-Agent': 'xingyu-health/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.status, r.read().decode('utf-8', 'ignore')

def dispatch(wf):
    if not TOKEN:
        print('无 token，跳过重新触发', wf); return False
    body = json.dumps({'ref': 'main'}).encode()
    req = urllib.request.Request(
        'https://api.github.com/repos/%s/actions/workflows/%s/dispatches' % (REPO, wf),
        data=body, method='POST',
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json', 'User-Agent': 'xingyu-health'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            ok = r.status == 204
            print('重新触发', wf, '->', '成功' if ok else 'HTTP %s' % r.status)
            return ok
    except Exception as e:
        print('重新触发', wf, '失败:', e); return False

def open_issue(title, body):
    if not TOKEN:
        print('无 token，无法建 issue'); return
    payload = json.dumps({'title': title, 'body': body}).encode()
    req = urllib.request.Request('https://api.github.com/repos/%s/issues' % REPO, data=payload,
        headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
                 'Content-Type': 'application/json', 'User-Agent': 'xingyu-health'})
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            print('已创建告警 issue, HTTP', r.status)
    except Exception as e:
        print('创建 issue 失败:', e)

def main():
    problems = []
    st, html = 0, ''
    try:
        st, html = fetch(URL)
        print('线上状态: HTTP', st, '| 页面字节:', len(html))
    except Exception as e:
        problems.append('站点无法访问: %s' % e)

    if st == 200 and html:
        if '行隅' not in html:
            problems.append('页面未含站点标识"行隅"')
        m = re.search(r'数据更新[:：]\s*([0-9]{4})-([0-9]{2})-([0-9]{2})', html)
        if m:
            upd = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date()
            gap = (today - upd).days
            print('数据更新时间:', upd, '| 距今天数:', gap)
            if gap > 2:
                problems.append('岗位数据已 %d 天未更新（最新 %s），岗位更新流程疑似失效' % (gap, upd))
        else:
            problems.append('页面未找到"数据更新"时间戳')
        tm = re.search(r'id="stTotal">\s*([0-9]+)', html)
        if tm:
            n = int(tm.group(1))
            print('岗位总数:', n)
            if n < 4000:
                problems.append('岗位总数异常偏低: %d' % n)
        else:
            problems.append('未找到岗位总数标记')
        cj = re.search(r'专栏.*?([0-9]+)\s*篇', html)
        if cj and int(cj.group(1)) < 500:
            problems.append('专栏总篇数异常偏低: %s' % cj.group(1))

    try:
        import json as _json
        arts = _json.load(open('articles.json', encoding='utf-8'))
        total_arts = sum(len(v) for k, v in arts.items() if isinstance(v, list))
        print('专栏总篇数(本地):', total_arts)
        if total_arts < 550:
            problems.append('专栏总篇数异常偏低(本地): %d' % total_arts)
    except Exception as e:
        problems.append('articles.json 读取失败: %s' % e)

    try:
        r = subprocess.run(['python3', 'gen_page.py'], capture_output=True, text=True, timeout=900)
        tail = (r.stdout or r.stderr or '').strip().splitlines()
        print('本地生成:', 'OK' if r.returncode == 0 else 'FAIL', '|', tail[-1] if tail else '')
        if r.returncode != 0:
            problems.append('gen_page.py 生成失败: ' + ((r.stderr or r.stdout) or '')[-300:])
    except Exception as e:
        problems.append('gen_page.py 执行异常: %s' % e)

    if not problems:
        print('HEALTH_OK: 站点与数据一切正常')
        return

    print('发现 %d 个问题:' % len(problems))
    for p in problems:
        print(' -', p)
    for wf in ('update-jobs.yml', 'update-articles.yml'):
        dispatch(wf)
    if any('gen_page.py' in p for p in problems):
        open_issue('【行隅站点自检】代码生成异常，需人工查看', '\n'.join(problems))
    sys.exit(1)

if __name__ == '__main__':
    main()
