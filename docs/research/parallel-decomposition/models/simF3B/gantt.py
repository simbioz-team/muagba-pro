import heapq, f3b2
T=f3b2.T; w=f3b2.w; MA=f3b2.MA
def sched(N,R,rev=8,mrg=2):
    succ={k:[x for x in T if k in T[x][3]+T[x][4]] for k in T}; rank={}
    def r(k):
        if k not in rank: rank[k]=w(k)+max([r(x) for x in succ[k]],default=0)
        return rank[k]
    for k in T: r(k)
    t=0;ev=[];slots=[None]*N;frev=R;ready=[];revq=[];handed=set();merged={};started=set();approved=set();log={}
    def can(k): return all(d in merged for d in T[k][3]) and all(d in handed for d in T[k][4])
    def tm():
        ch=True
        while ch:
            ch=False
            for k in list(approved):
                if k in merged: continue
                need=MA.get(k,[])+T[k][4]
                if all((d in merged) or (d in approved and k in MA.get(d,[])) for d in need): merged[k]=t;ch=True
    def disp():
        nonlocal frev
        for k in T:
            if k not in started and can(k): started.add(k);ready.append(k)
        ready.sort(key=lambda k:-rank[k])
        for i in range(N):
            if slots[i] is None and ready:
                k=ready.pop(0);slots[i]=k;log[k]=[i+1,t];heapq.heappush(ev,(t+w(k),'hand',k))
        revq.sort(key=lambda k:-rank[k])
        while frev and revq:
            k=revq.pop(0);frev-=1;heapq.heappush(ev,(t+rev,'rev',k))
    disp()
    while ev:
        t,e,k=heapq.heappop(ev)
        if e=='hand': slots[slots.index(k)]=None;handed.add(k);revq.append(k);log[k].append(t)
        elif e=='rev': frev+=1;approved.add(k);heapq.heappush(ev,(t+mrg,'mrg',k))
        elif e=='mrg': tm()
        disp()
    for k,(s,a,b) in sorted(log.items(),key=lambda x:(x[1][0],x[1][1])):
        print(f'слот {s}: {k:4} {a:5.0f}–{b:5.0f}  влита {merged[k]:5.0f}  ранг {rank[k]:.0f}')
    print('H влита', merged['H'])
sched(4,3)
