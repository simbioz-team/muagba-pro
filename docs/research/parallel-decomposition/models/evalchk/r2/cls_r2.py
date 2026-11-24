import sys, re, json
sys.path.insert(0, '..')
import test_registry_base as tr
tree = open('tree.txt').read().split()
reg = json.load(open('reg.json'))
exc = reg.get('exceptions', {})
units = []
for env in tr.ENVIRONMENTS:
    base = '' if env.root == '.' else env.root + '/'
    for p in tree:
        if not p.startswith(base): continue
        rel = p[len(base):]
        if not any(rel.startswith(r + '/') for r in env.test_roots): continue
        parts = rel.split('/')
        if tr._SKIP_PARTS & set(parts): continue
        name = parts[-1]
        if not tr._is_test(name, env.runner): continue
        if len(parts) >= 3 and parts[-3:-1] == ['management', 'commands']: continue
        units.append((env.key, rel, tr.normalize(rel)))
def mk(rules):
    comp = [(n, tr._boundary(p)) for n, p in rules]
    def c(k):
        if k in exc: return exc[k]
        for n, pat in comp:
            if pat.search(k): return n
        return 'core'
    return c
base = list(tr.GROUP_RULES)
# A: banks rule second, structure(course_goal) right after saga
A = list(base)
A.insert(1, ("banks", r"course_bank|learning_process|step6|exam_trainer"))
i = [n for n,_ in A].index('saga')
A.insert(i+1, ("structure", r"course_goal"))
# B: alternatives appended to existing structure and banks rules
B = []
for n, p in base:
    if n == 'structure': p = p + r"|learning_process|course_goal|step6"
    if n == 'banks': p = p + r"|exam_trainer"
    B.append((n, p))
cb, ca, cB = mk(base), mk(A), mk(B)
print('units', len(units), 'django', sum(1 for u in units if u[0]=='django-api'))
print('core base', sum(1 for u in units if cb(u[2])=='core'))
for nm, c in (('A', ca), ('B', cB)):
    ch = [(u[1], cb(u[2]), c(u[2])) for u in units if cb(u[2]) != c(u[2])]
    print(nm, 'changed', len(ch))
    for x in ch: print('  ', *x)
# new modules
newA = sys.argv[1:] 

import os
def newmods(md, prefix_map):
    txt = open(md).read()
    paths = set(re.findall(r"[A-Za-z_/\[\]\{\}\.,0-9-]*test[A-Za-z_0-9]*\.(?:py|tsx?|spec\.ts)", txt))
    return paths
if os.environ.get('NEW'):
    for md, c in (('../../f1-A-r2.md', ca), ('../../f1-B-r2.md', cB)):
        core = []
        for p in sorted(newmods(md, None)):
            name = p.split('/')[-1]
            if not (re.match(r"^tests?_", name) or '.test.' in name or '.spec.' in name): continue
            k = tr.normalize('courses/' + p if not p.startswith(('scripts','FEA','services','JT')) else p)
            g = c(k)
            if g == 'core': core.append(p)
        print(md, 'core:', core)
