import csv,collections,re,sys
R=lambda p,s: re.search(p,s,re.I)
RISK=r'гонк|race|конкур|lock|блокир|транзак|миграц|migration|alembic|ядр|\bcore\b|сервер|server|выкат|deploy|\bCI\b|импорт|import|tariff|тариф|billing|оплат|деньг|auth|вход|security|безопас|flaky|нестаб|причин|debug|инцидент|merge|слиян|интеграц|Гант|gantt'
def step(t,d):
    if t=='Explore': return 'search','haiku'
    if re.search(r'check\.sh|Run full|Full check|Run check',d,re.I): return 'run-check','script'
    if t in('muagba-base:reviewer','spec-reviewer') or R(r'^(Ревью|Review|Рецензия)|Red team|Audit|аудит|Critique|критик',d): return 'review','opus'
    if R(r'ответы владельца|owner answers|внести ответы|ссылки на ответы|CHANGELOG|Обновить текст',d): return 'mech-edit','sonnet'
    if R(r'Имитаци|Tester|Тестировщик|UX-тестер|Сверщик|persona',d): return 'tester','sonnet'
    if R(r'Приёмк|приемк|e2e|E2E|Перепровер|живьём|Verify|Independent check|check of|Purgatory check|browser',d): return 'acceptance','sonnet'
    if R(r'Спек|спек|Spec|План|plan|tasks|Продакт|Методолог|Судья|Арбитр|judge|Дизайнер|architect|teamlead|Развилк|концеп|замыс|Канон|Weight|вес |Досье|следстви|Групп|Команд|Discussant|скил|правил процесса|продуктов',d) and t!='muagba-base:implementer' and t!='implementer-high': return 'architect','opus'
    if t=='muagba-base:researcher' or R(r'Research|Исследов|Анализ|Состояни|Статус|Status|survey|Study|разведк|факты|facts|Market|История|Статистик|Summarize|Как устроен|Что в |Describe|Find ',d): return 'research','sonnet'
    if R(RISK,d): return 'impl-deep','opus'
    return 'impl','sonnet'
F={('opus','sonnet'):.5,('opus','haiku'):.05,('opus','opus'):1,('sonnet','sonnet'):1,('sonnet','opus'):2,('opus','script'):.05,('sonnet','script'):.1,('sonnet','haiku'):.1}
REV_ROUND=2.8; COORD=3.0
def sim(x):
    t,d=x['type'],x['desc']; s,m=step(t,d); cur='sonnet' if x['model']=='sonnet' else 'opus'
    c=float(x['cost']); new=c*F[(cur,m)]
    if s=='impl' and cur=='opus': new+=0.14*new+0.18*REV_ROUND+0.08*COORD
    if s in('acceptance','tester') and cur=='opus': new*=1.10
    return s,m,c,new
if __name__=='__main__':
    r=[x for x in csv.DictReader(open('subs.csv')) if x['proj'].startswith(('narta','nastavnik'))]
    since=sys.argv[1] if len(sys.argv)>1 else ''
    r=[x for x in r if x['start']>=since]
    agg=collections.defaultdict(lambda:[0,0.,0.])
    for x in r:
        s,m,c,n=sim(x); a=agg[(s,m)]; a[0]+=1;a[1]+=c;a[2]+=n
    T=sum(a[1] for a in agg.values()); N=sum(a[2] for a in agg.values())
    for k,a in sorted(agg.items(),key=lambda z:-z[1][1]): print(f'{k[0]:11}{k[1]:7}{a[0]:5}{a[1]:8.0f}{a[2]:8.0f}{(a[2]-a[1]):8.0f}')
    print(f'total {T:.0f} -> {N:.0f}  saving {T-N:.0f} ({(T-N)/T:.0%})')
