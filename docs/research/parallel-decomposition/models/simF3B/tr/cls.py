import sys; sys.path.insert(0, __import__("os").path.dirname(__file__))
import importlib.util,sys,json,subprocess
spec=importlib.util.spec_from_file_location("tr",sys.argv[1]);m=importlib.util.module_from_spec(spec);sys.modules["tr"]=m;spec.loader.exec_module(m)
ex=json.load(open(sys.argv[2]))["exceptions"]
for l in sys.argv[3:]:
    k=m.normalize(l); print(m.classify(k,ex), k)
