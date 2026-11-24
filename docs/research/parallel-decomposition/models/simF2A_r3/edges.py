"""Проверка П-8 (цикл) и П-9 (ярус) для новых рёбер плана на графе базового коммита 053602900."""
import json, sys
g = json.load(open('module-graph-base.json')); t = json.load(open('module-tiers-base.json'))
tier = {n: int(k) for k, v in t['tiers'].items() for n in v}
core = set(t['core_tier0'])
def tier_of(u):
    if u.startswith('root:'): return 0 if u[5:] in core else 4
    return tier.get(u)
def check(name, new, rt_tier):
    tier['rung_theory'] = rt_tier
    E = {(e['from'], e['to']) for e in g['edges']} | set(new)
    adj = {}
    for a, b in E: adj.setdefault(a, set()).add(b)
    def reach(a, b, seen=None):
        seen = seen or set(); st = [a]
        while st:
            x = st.pop()
            if x == b: return True
            if x in seen: continue
            seen.add(x); st += adj.get(x, ())
        return False
    bad = [(a, b, 'П-8 цикл') for a, b in new if reach(b, a)]
    bad += [(a, b, 'П-9 ярус') for a, b in new if not a.startswith('root:') and tier_of(b) is not None and tier_of(a) is not None and tier_of(b) > tier_of(a)]
    print(f'{name}: новых рёбер {len(new)}, нарушений {len(bad)}')
    for x in bad: print('   ', *x)
r2 = [('rung_theory', 'topic_content'), ('rung_theory', 'ksa_graph'), ('rung_theory', 'root:models'),
      ('topic_content', 'rung_theory'), ('course_pipeline', 'rung_theory'), ('lesson', 'rung_theory'),
      ('dialogue', 'rung_theory'), ('track_manage', 'rung_theory'), ('diagnostic_bank', 'rung_theory'),
      ('topic_content', 'course_pipeline')]   # r2: T025 rung_rollback (topic_content) правит gating.py
r3 = [('rung_theory', 'ksa_graph'), ('rung_theory', 'course_structure'), ('rung_theory', 'root:models'),
      ('rung_theory', 'helpers'), ('rung_theory', 'domain_errors'),
      ('topic_content', 'rung_theory'), ('course_pipeline', 'rung_theory'), ('lesson', 'rung_theory'),
      ('dialogue', 'rung_theory'), ('track_manage', 'rung_theory'), ('diagnostic_bank', 'rung_theory'),
      ('task_classes', 'rung_theory'), ('course_graph_editor', 'rung_theory'),
      ('root:apps', 'course_pipeline'), ('root:apps', 'topic_content')]  # окно отката: регистрация в CoursesConfig.ready
check('r2 (rung_theory ярус 3)', r2, 3)
check('r3 (rung_theory ярус 2)', r3, 2)
# запрет для рёбер вниз: кто из того, что rung_theory достигает, не должен импортировать rung_theory
adj = {}
for e in g['edges']: adj.setdefault(e['from'], set()).add(e['to'])
seen, st = set(), ['ksa_graph', 'course_structure', 'helpers', 'domain_errors']
while st:
    x = st.pop()
    if x in seen or x.startswith('root:'): continue
    seen.add(x); st += adj.get(x, ())
print('не импортируют rung_theory (иначе цикл):', ' '.join(sorted(seen)))
