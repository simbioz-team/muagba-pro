import sys,os,json,re,importlib.util
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
spec=importlib.util.spec_from_file_location("tr","test_registry_base.py");m=importlib.util.module_from_spec(spec);sys.modules["tr"]=m;spec.loader.exec_module(m)
ex=json.load(open("reg.json"))["exceptions"]
old=dict(m._COMPILED)
add=sys.argv[1]
newc=[(n,(m._boundary(p+"|"+add) if n=="banks" else m._boundary(p))) for n,p in m.GROUP_RULES]
def cl(k,comp):
    if k in ex: return ex[k]
    for n,r in comp:
        if r.search(k): return n
    return "core"
keys=[m.normalize(l.strip()) for l in open("all.txt")]+[m.normalize(x) for x in sys.argv[2:]]
for k in keys:
    a=cl(k,list(m._COMPILED)); b=cl(k,newc)
    if a!=b: print(a,"->",b,k)
print("core after:", sum(cl(k,newc)=="core" for k in keys))
for x in sys.argv[2:]:
    k=m.normalize(x); print(cl(k,newc),k)
