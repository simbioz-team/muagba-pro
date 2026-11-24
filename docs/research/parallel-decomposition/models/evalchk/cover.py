import re,sys
def files_of(md, expand):
    out={}
    cur=None
    for line in open(md):
        m=re.match(r'- \[ \] (T\d+)',line)
        if m: cur=m.group(1); out[cur]=set(); continue
        m=re.match(r'\|\s*(T0\d\d)\s*\|\s*(.+?)\s*\|',line)
        if m and cur and m.group(1)>='T043' and 'Зона' not in line:
            out[m.group(1)]=set(re.findall(r'`([^`]+)`',m.group(2)))|set(re.findall(r'[\w/{},\.\-\[\]\(\)]+\.py',m.group(2)))
        if cur and line.strip().startswith('Файлы:'):
            out[cur]|=set(x.strip() for x in line.split(':',1)[1].split(','))
    return out
def norm(p,expand):
    for a,b in expand: p=p.replace(a,b)
    p=p.split('#')[0].split(' ')[0]
    return p
BE='services/django-api/courses/'
A=files_of('f1-A-r1.md',None); B=files_of('f1-B-r1.md',None)
def allpaths(d):
    s=[]
    for t,fs in d.items():
        for f in fs:
            f=norm(f,[('BE/',BE)])
            # expand {a,b}
            m=re.match(r'(.*)\{(.+?)\}(.*)',f)
            if m:
                for x in m.group(2).split(','): s.append((t,m.group(1)+x.strip()+m.group(3)))
            else: s.append((t,f))
    return s
cons=[l.strip() for l in open(sys.argv[1]) if l.strip()]
for name,d in (('A',A),('B',B)):
    ps=allpaths(d); miss=[]
    for c in cons:
        short=c.replace(BE,'')
        hit=[t for t,p in ps if p and (c.startswith(p.rstrip('/')) or p.endswith(short) or short.endswith(p.replace(BE,'').rstrip('/')) and p.replace(BE,'').rstrip('/'))]
        if not hit: miss.append(short)
    print(name,'missing',len(miss),'of',len(cons)); print('  ','\n   '.join(miss))
