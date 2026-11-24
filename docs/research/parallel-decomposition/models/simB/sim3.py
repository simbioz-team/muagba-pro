"""Равная работа: 22 полных среза против 13 срезов x3 (srv .6, cli .6, flow .5 = 22.1 ед.).
Ревью частично фиксировано: REVIEW*(0.5+0.5*w) - запуск, чтение задачи и check.sh не уменьшаются с размером.
Доля отказов у мелких задач по сторонам: p_split (расхождение сторон даже при контракте)."""
import sim2, statistics as st
base=sim2.run
def dur_patch():
    pass
import random
def run(G,N,R,p,mode,q,seed,fixed=True):
    g,deep,w,ce=G
    w2=dict(w)
    return sim2.run((g,deep,w2,ce),N,R,p,mode,q,seed)
# patch review duration via monkeypatch of REVIEW using size: emulate fixed part by raising w floor for review only
import types
src=open('sim2.py').read().replace("push(t+dur(k,REVIEW),'rev',k)","push(t+REVIEW*(0.5+0.5*w.get(k,1))*rnd.uniform(.7,1.4),'rev',k)")
ns={}; exec(compile(src.split("if __name__")[0],'s','exec'),ns)
def m(G,N,p,mode,q=0,R=4,n=400):
    rs=[ns['run'](G,N,R,p,mode,q,s) for s in range(n)]; return st.mean(r[0] for r in rs)
for N in (4,5):
  for p in (0.3,0.43):
    print(f'N={N} p={p}: fan22 pipe {m(ns["fan"](22),N,p,"pipe"):.0f} | split13x3 pipe {m(ns["split"](13),N,p,"pipe"):.0f} stack q.5 {m(ns["split"](13),N,p,"stack",.5):.0f} | fan22 block {m(ns["fan"](22),N,p,"block"):.0f}')
print('fan22 p=.15 pipe N=4', round(m(ns['fan'](22),4,.15,'pipe')))
print('число ревью-запусков: fan22 ~', round(22*1.43), ' split13x3 ~', round(39*1.43))
