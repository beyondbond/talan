import sys,os
sys.path.append(os.path.dirname(__file__))
from _alan_calc import *
from _alan_date import *
from _alan_str import *
from _alan_pppscf import batch_pppscf,vertex_locator,vertex_mnmx
from yh_chart import *
from yh_hist_batch import *
from yh_predefined import bb_predefined
from find_recent_eps import find_recent_eps
from headline_calc import find_hiloRecord,headline_calc
from headline_sts import headline_hist
from iex_peers import iex_peers,peers_performance,ticker2sectorRanking
from macro_event_yh import run_macro_event_yh
from plot_templates import plot_templates
from record_hilo import get_titlehead
from ticker2label import ticker2label,t2l
import types
unLst=['popen','Call','OLD','TBD','_DEPRECATED','Popen','__']
talan_vars = {k:v for (k,v) in globals().items() if callable(v) and not any(map(k.__contains__,unLst)) and isinstance(v,types.FunctionType) and v.__doc__} 
for k in ['unLst']:
	globals().pop(k,None)
