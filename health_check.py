#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 行隅站点健康检查：线上可访问性 + 数据新鲜度 + 本地生成健康度
# 发现问题 → 自动重新触发岗位/专栏更新流程；代码本身坏了 → 建 issue 告警
import datetime, json, os, re, subprocess, sys, urllib.request

URL = 'https://james-liang-o.github.io/xingyu-jobs/'
REPO = os.environ.get('GITHUB_REPOSITORY', 'James-liang-o/xingyu-jobs')
TOKEN = os.environ.get('GH_TOKEN', '') or os.environ.get('GITHUB_TOKEN', '')

def fetch(url, timeout=40):
    # Cache-Control: no-cache 强制绕过 GitHub Pages CDN 缓存，避免读到旧版页面误报
    req = urllib.request.Request(url, headers={'User-Agent': 'xingyu-health/1.0', 'Cache-Control': 'no-cache', 'Pragma': 'no-cache'})
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

def pages_build_status():
    """查 GitHub Pages 最近一次部署状态：能发现"仓库已更新但线上没部署成功"的情况。
    不读线上页面内容——raw/github.io 都有 CDN 缓存，读内容会误报（曾把 16 天前的缓存版当成线上版本）。"""
    if not TOKEN:
        return None
    try:
        req = urllib.request.Request('https://api.github.com/repos/%s/pages/builds/latest' % REPO,
            headers={'Authorization': 'Bearer ' + TOKEN, 'Accept': 'application/vnd.github+json',
                     'User-Agent': 'xingyu-health'})
        with urllib.request.urlopen(req, timeout=30) as r:
            d = json.load(r)
        return d.get('status'), (d.get('error') or {}).get('message'), d.get('created_at')
    except Exception as e:
        print('Pages 部署状态查询失败:', e)
        return None

def main():
    problems = []
    # 1) 线上可访问性（只判状态码，不解析内容——内容有 CDN 缓存）
    st, html = 0, ''
    try:
        st, html = fetch(URL)
        print('线上状态: HTTP', st, '| 页面字节:', len(html))
    except Exception as e:
        problems.append('站点无法访问: %s' % e)
    if st and st != 200:
        problems.append('线上返回异常状态码: HTTP %s' % st)

    # 2) 数据新鲜度：读仓库本地 checkout 文件（与 main 分支一致，完全无 CDN 缓存干扰）
    check_html = ''
    for fn in ('行隅_全国岗位导航.html', 'index.html'):
        if os.path.exists(fn):
            check_html = open(fn, encoding='utf-8').read()
            print('仓库页面文件:', fn, '| 字节:', len(check_html))
            break
    if not check_html:
        problems.append('未找到仓库页面文件（行隅_全国岗位导航.html）')

    # 3) Pages 部署状态（仓库新但线上部署失败的情况）
    pb = pages_build_status()
    if pb:
        pstatus, perr, pcreated = pb
        print('Pages 最近部署:', pstatus, '|', pcreated)
        if pstatus == 'errored':
            problems.append('GitHub Pages 最近一次部署失败: %s' % (perr or '未知原因'))

    if check_html:
        # 所有权指纹校验：页面必须保留唯一性标识（被篡改/替换会丢）
        if 'xingyu-origin' not in check_html:
            problems.append('页面丢失所有权指纹 xingyu-origin，疑似被篡改或替换')
        vm = re.search(r'class="ver">v?([0-9.]+)<', check_html)
        if vm:
            print('页面版本:', vm.group(1))
        else:
            problems.append('页面未找到版本号标记')
        m = re.search(r'数据更新[:：]\s*([0-9]{4})-([0-9]{2})-([0-9]{2})', check_html)
        if m:
            upd = datetime.date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
            today = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=8)).date()
            gap = (today - upd).days
            print('数据更新时间(仓库):', upd, '| 距今天数:', gap)
            # 数据陈旧超过 7 天才告警（1~2 天内的偶发源不可达不打扰；连续 7 天未更新说明流程真的失效）
            if gap > 7:
                problems.append('岗位数据已 %d 天未更新（最新 %s），岗位更新流程疑似失效' % (gap, upd))
        else:
            problems.append('页面未找到"数据更新"时间戳')
        tm = re.search(r'id="stTotal">\s*([0-9]+)', check_html)
        if tm:
            n = int(tm.group(1))
            print('岗位总数:', n)
            if n < 4000:
                problems.append('岗位总数异常偏低: %d' % n)
        else:
            problems.append('未找到岗位总数标记')
        cj = re.search(r'专栏.*?([0-9]+)\s*篇', check_html)
        if cj and int(cj.group(1)) < 450:
            problems.append('专栏总篇数异常偏低: %s' % cj.group(1))
    try:
        import json as _json
        arts = _json.load(open('articles.json', encoding='utf-8'))
        total_arts = sum(len(v) for k, v in arts.items() if isinstance(v, list))
        print('专栏总篇数(本地):', total_arts)
        if total_arts < 450:
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
    for wf in ('update.yml', 'articles.yml'):
        dispatch(wf)
    if any('gen_page.py' in p for p in problems):
        open_issue('【行隅站点自检】代码生成异常，需人工查看', '\n'.join(problems))
    sys.exit(1)

if __name__ == '__main__':
    main()
