import sys; sys.path.insert(0, '.')
import test_registry_base as tr
for k in open('keys.txt').read().split():
    n = tr.normalize(k); print(tr.classify(n), "\t", n)
