import sys; sys.path.insert(0, sys.argv[1])
import test_registry_base as tr
for line in open('names.txt'):
    t,k=line.split(); n=tr.normalize(k); print(t, tr.classify(n), k, sep='\t')
