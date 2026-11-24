"""Проверка модели B: что даёт pipe на послойном графе, если стек разрешён
только по контрактным рёбрам (правило B 4/§7.7), а на послойном графе их нет.
Импортирует simB/sim.py как есть, меняя только условие старта преемника."""
import sys, random, statistics as st, importlib.util, types
spec=importlib.util.spec_from_file_location('simb', sys.argv[1])
src=open(sys.argv[1]).read().split("for name,g in(('layered'")[0]
m=types.ModuleType('simb'); exec(src, m.__dict__)
# вариант: слот свободен при сдаче, но преемник ждёт вливания (рёбра «поведение/данные»)
src2=src.replace("else: okt=[handed.get(d) for d in g[x]]","else: okt=[(handed if STACK else fin).get(d) for d in g[x]]")
m2=types.ModuleType('simb2'); m2.__dict__['STACK']=False; exec(src2, m2.__dict__)
random.seed(1)
for name,g in (('layered',m.layered()),('planned',m.planned())):
    for K in (4,):
        a=st.mean(m.run(g,'serial',K=K,R=K)[0] for _ in range(2000))
        b=st.mean(m.run(g,'pipe',K=K,R=K)[0] for _ in range(2000))
        c=st.mean(m2.run(g,'pipe',K=K,R=K)[0] for _ in range(2000))
        print(f'{name:8} K={K} serial={a:5.0f}  pipe(стек по всем рёбрам)={b:5.0f}  pipe(слот свободен, преемник ждёт вливания)={c:5.0f}')
