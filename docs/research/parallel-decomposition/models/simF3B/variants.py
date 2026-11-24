import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import f3b_r2 as M, statistics as st
MODE=os.environ.get("MODE","r2pull"); OV=bool(os.environ.get("OV"))
def V(name,mod):
    T,MA=M.graph(MODE); T=dict(T); MA={k:list(v) for k,v in MA.items()}
    mod(T,MA); w=M.mk(T); W=sum(w(k) for k in T); S,_=M.span(T,w)
    out=[]
    for p in (0,0.3,0.43):
        rs=[M.run(T,MA,4,3,p,s,overflow=OV) for s in range(400)]
        out.append(f'{st.median(r[0] for r in rs):.0f}/{st.median(r[1] for r in rs):.0f}')
    occ=st.mean(r[2] for r in [M.run(T,MA,4,3,0.3,s,overflow=OV) for s in range(200)])
    print(f'{name:38} W={W:.0f} S={S:.0f} P={W/S:.2f}  H/конец p=0:{out[0]} p=.3:{out[1]} p=.43:{out[2]} зан {occ:.2f}')
def base(T,MA): pass
def cj_stack_rd(T,MA): pass
def cj_no_stack(T,MA):
    v=T['CJ']; T['CJ']=(v[0],v[1],v[2],['KB','RD'],['J'],v[5])
def ks_with_rd(T,MA):
    # чтение внутри KS
    del T['RD']
    for k,v in list(T.items()):
        T[k]=(v[0],v[1],v[2],[d for d in v[3] if d!='RD'],[d for d in v[4] if d!='RD'],v[5])
    MA.pop('RD',None); MA['KS']=['TJ']
def ks_rd_L(T,MA):
    ks_with_rd(T,MA); v=T['KS']; T['KS']=(v[0],v[1],v[2],v[3],v[4],34)
def ws_split(T,MA):
    # WS: GET отдельно (от RD,KB) и POST (от CJ) deep S
    cj_stack_rd(T,MA)
    T['WG']=('V',1,'S',['KB','RD'],[],None); v=T['WS']; T['WS']=('V',1,'S',v[3],v[4],None)
    MA['WG']=['TW','REF']; MA['WS']=['TW','REF','WG']; h=T['H']; T['H']=(h[0],h[1],h[2],h[3]+['WG'],h[4],h[5])
if __name__=="__main__": V('r2 '+MODE,base)
if __name__=="__main__": V('CJ (стек) только от J, RD влитым',cj_no_stack)
if __name__=="__main__": V('чтение внутри KS (M, вес 24)',ks_with_rd)
if __name__=="__main__": V('чтение внутри KS (честно L, 34)',ks_rd_L)
if __name__=="__main__": V('CJ стек + WS на GET/POST',ws_split)
