from pathlib import Path
import sys,runpy

script=Path(__file__).with_name('probe_nature_xpbd21.py')
for amount in (0.,.5,1.):
    sys.argv=[str(script),'--',str(amount)]
    runpy.run_path(str(script),run_name='__main__')
