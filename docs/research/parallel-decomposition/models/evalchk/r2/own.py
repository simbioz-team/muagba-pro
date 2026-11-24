import re, sys
P = '../../'
def files_A():
    txt = open(P+'f1-A-r2.md').read()
    own = {}
    for m in re.finditer(r"^- \[ \] (T\d+).*?(?=^- \[ \] T|\Z|^## )", txt, re.S|re.M):
        t = m.group(1); block = m.group(0)
        f = re.search(r"Файлы: (.*)", block)
        if not f: continue
        for x in f.group(1).split(','):
            x = x.strip().split('#')[0]
            x = x.replace('BE/', 'services/django-api/courses/')
            own.setdefault(t, []).append(x)
    return own
def files_B():
    # crude: all backtick paths in rows/lines per task id
    txt = open(P+'f1-B-r2.md').read()
    own = {}
    cur = None
    for line in txt.splitlines():
        m = re.match(r"^\| \*{0,2}(T\d+)", line) or re.match(r"^- \[ \] \*\*(T\d+)", line)
        if m: cur = m.group(1)
        elif not line.startswith('  '): cur = None if not line.startswith('|') else cur
        if not cur: continue
        for b in re.findall(r"`([^`]+)`", line):
            # expand {a,b}
            mm = re.match(r"(.*)\{([^}]*)\}(.*)", b)
            items = [mm.group(1)+x+mm.group(3) for x in mm.group(2).split(',')] if mm else [b]
            for it in items:
                it = it.replace('BE/', '')
                own.setdefault(cur, []).append(it)
    return own
def owners(path, own, prefix):
    res = []
    for t, fs in own.items():
        for f in fs:
            f2 = f
            if prefix and not f2.startswith('services/'): f2 = prefix + f2
            if f2.endswith('/') and path.startswith(f2): res.append(t)
            elif '*' in f2 and re.fullmatch(f2.replace('.', r'\.').replace('*', '.*'), path): res.append(t)
            elif f2 == path: res.append(t)
    return sorted(set(res))
A = files_A(); B = files_B()
lists = {
 'r1_create39': [l.strip() for l in open('../f1_lt_create_tests.txt') if l.strip()],
 'B59': ['services/django-api/courses/' + l.split()[-1] for l in open('../../f1B/lt_tests.txt') if l.strip()],
}
for nm, L in lists.items():
    for plan, own, pre in (('A', A, ''), ('B', B, 'services/django-api/courses/')):
        miss = [p for p in L if not owners(p, own, pre)]
        print(nm, plan, 'unowned', len(miss), '/', len(L))
        for p in miss: print('   ', p.replace('services/django-api/courses/', ''))
