import sys,os; sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
import f3b_r2 as M
T,MA=M.graph('r2pull')
H,end,log,merged,acc,rank=M.run(T,MA,4,3,0,-1,trace=True,overflow=True)
ID={'C0':'T001','K1':'T001','KS':'T002','KB':'T003','KC':'T004','RD':'T005','J':'T006','CJ':'T007','MIG':'T008','REF':'T009','QS':'T010','QC':'T011','WS':'T012','FC':'T013','UC':'T014','RP':'T015','RU':'T016','TJ':'T017','TM':'T018','TR':'T019','TQ':'T020','TQC':'T021','TW':'T022','TF':'T023','TK':'T024','TRU':'T025','E1':'T026','E2':'T027','H':'T028'}
iv=sorted([(a,b,k) for k,ls in log.items() for kind,a,b in ls],key=lambda x:(x[0], x[2]!='K1'))
slots=[]; out={}
for a,b,k in iv:
    if k=='K1': i=out['C0'][0]; slots[i]=b; out[k]=(i,a,b); continue
    for i,e in enumerate(slots):
        if e<=a+1e-9: slots[i]=b; break
    else: slots.append(b); i=len(slots)-1
    out[k]=(i,a,b)
rows={}
for k,(i,a,b) in sorted(out.items(),key=lambda x:x[1][1]):
    rows.setdefault(i,[]).append(f"{ID[k]} {a:.0f}–{b:.0f} ({merged[k]:.0f})")
for i in sorted(rows): print(f'| {i+1} | '+' → '.join(rows[i])+' |')
print('H влита',H,'приёмки',acc,'конец',end)
