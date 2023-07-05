#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ALAN API 
Last mod.,
Thu Aug 25 19:19:30 EDT 2022
"""
import codecs,sys,os
os.environ['TZ']='America/New_York' # set New_York EST as default
from optparse import OptionParser
import numpy as np
import pandas as pd
import pandas_datareader.data as web
import datetime
import re
import json
import os,cgi,cgitb
from _alan_calc import get_start_end,subDict,subDF,renameDict,getKeyVal
from _alan_calc import  sqlQuery,conn2mgdb,conn2pgdb,pqint,saferun
from _alan_str import find_mdb,dtCvt
from _alan_date import next_date,s2dt
from glob import glob,iglob
import base64
import subprocess
from bson.objectid import ObjectId

import pprint
#%matplotlib inline 
#import matplotlib.pyplot as plt 
from hashlib import md5
if sys.version_info.major == 2:
	reload(sys)
	sys.setdefaultencoding('utf8')

# set pandas global display formula
#pd.set_option('display.max_colwidth', -1)
pd.options.display.float_format='{:,.2f}'.format

# set mongoDB database connection as globals()
mgDB=conn2mgdb(dbname='ara')
pgDB=conn2pgdb(dbname='ara')
currDate=datetime.datetime.now()

def verify_apikey(ak):
	if ak=='beyondbond_internal_testing_only':
		return 1
	ht=pd.read_csv("/apps/fafa/webDir/loginDir/.htpasswd.dat",sep="\t")
	aLst=list(ht['api_key'])
	return 1 if ak.lower() in aLst else 0

class myPrettyPrinter(pprint.PrettyPrinter):
	def format(self, object, context, maxlevels, level):
		if isinstance(object, unicode):
			#return (object.encode('utf8'), True, False)
			return (object, True, False)
		return pprint.PrettyPrinter.format(self, object, context, maxlevels, level)

def dft_tablename(search,instrument,tablename):
	if tablename is not None :
		return tablename
	if search == "search_list" :
		tablename='(select m.*,s.exch from spdr_list s, mapping_ticker_cik m where m.ticker=s.ticker and act_code=1 order by sector DESC,ticker) as m' if instrument=='stock' else 'mapping_series_label'
	elif search in ["search_history", "search_hist" ]:  
		tablename='prc_hist' if instrument=='stock' else 'ara_globalmacro_hist'
	#elif search == "search_quote" :
	#	tablename='yh_quote_curr' if instrument=='stock' else 'macro_hist_fred'
	#elif search == "search_comment" :
	#	tablename='ohlc_daily_comment_cn' if instrument=='stock' else 'ara_globalmacro_forecast_comment_cn'
	elif search == "search_factor" :
		tablename='ara_outlook_factor_temp' if instrument=='stock' else 'ara_globalmacro_forecast_comment_cn'
	else :
		tablename = None
	return tablename
	
def fmtSetting(x,pcsn=2,comma=','):
	from numpy import int64,int32
	if isinstance(x,float):
		return "{:{}.{}f}".format(x,comma,pcsn)
	elif isinstance(x,(int,int64,int32)):
		return "{:{}}".format(x,comma)
	else:
		return "{}".format(x)

def fmt0f(x):
	return fmtSetting(x,pcsn=0,comma='')

def fmt0a(x):
	return fmtSetting(x,pcsn=0,comma=',')

def fmt2a(x):
	return fmtSetting(x,pcsn=2,comma=',')

@saferun
def data_output(data,output='json',**optx):
	''' Convert dataFrame 'data' into type:'output' output
	'''
	if data is None or len(data)<1:
		ret=getKeyVal(optx,'ret',{})
		return ret
	elif '**ERROR' in data[:9] or not isinstance(data,pd.DataFrame):
		if  isinstance(data,(dict,list)):
			return json.dumps(data,default=dtCvt) #ensure_ascii=False
		return data
	elif output == 'dict' :
		orient=getKeyVal(optx,'orient','records')
		return data.to_dict(orient=orient)
	elif output == 'json' :
		orient=getKeyVal(optx,'orient','records')
		if sys.version_info.major == 2:
			return data.to_json(orient=orient,force_ascii=False).encode('utf8')
		return data.to_json(orient=orient,default_handler=dtCvt)
	elif output == 'json_by_column' :
		return data.to_json()
		#return json.loads(data.to_json())
		#return data.to_json(force_ascii=False).encode('utf8')
	elif output == 'html' : 
		float_fmt=getKeyVal(optx,'float_fmt','{:,.2f}')
		pd.options.display.float_format=float_fmt.format
		data = data.replace([np.nan, np.inf, -np.inf], '', regex=True)
		#return data.to_html(index=False)
		cfm = { 'pbdate':fmt0f,
			'closeDate':fmt0f,
			'epochs':fmt0f,
			'close':fmt2a,
			'marketCap':fmt0a,
			'dollarValue':fmt0a,
			'volume':fmt0a,
			'count':fmt0a}
		cfm=getKeyVal(optx,'cfm',cfm)
		return data.to_html(index=False,formatters=cfm)
	elif output == 'csv_by_comma' :
		index=getKeyVal(optx,'index',False)
		return data.to_csv(sep=",",index=index)
	elif output == 'tsv' :
		index=getKeyVal(optx,'index',False)
		return data.to_csv(sep="\t",index=index)
	elif output == 'csv' :
		sep=getKeyVal(optx,'sep','|')
		index=getKeyVal(optx,'index',False)
		return data.to_csv(sep=sep,index=index)
	elif output in ['DF','df','DataFrame','dataframe'] :
		return data
	else:
		sep=getKeyVal(optx,'sep','|')
		index=getKeyVal(optx,'index',False)
		return data.to_csv(sep=sep,index=index)

def xql_factor_comment(ticker,fdLst,factor='technical',lang='',subtopic='attr'):
	xlang = "_{}".format(lang) if lang=='cn' else ''
	if factor =='overall':
		if subtopic=='attr':
			tablename="ara_outlook_factor_temp"
		else:
			tablename="ara_outlook_factor_recommend{}".format(xlang)
	else:
		if subtopic=='attr':
			tablename="ara_outlook_attr_{}".format(factor)
		else:
			tablename="ara_outlook_attr_{}_comment{}".format(factor,xlang)
	
	if ticker=='*':
		xqr="SELECT {} FROM {} WHERE factor='{}'".format(fdLst,tablename,factor)
	else:
		xqr="SELECT {} FROM {} WHERE ticker='{}' AND factor='{}'".format(fdLst,tablename,ticker,factor)
	return xqr

def geteach_comment(ticker,fdLst,tablename=None,lang=None,dbname="ara",hostname='localhost',topic='factor',subtopic='',factor='',**optx):
	if tablename is None:
		return None
	colx='ticker'
	if factor in ['technical','valuation','quality','macro','overall']:
		xqr=xql_factor_comment(ticker,fdLst,factor=factor,lang=lang,subtopic=subtopic)
	elif ticker=='*':
		xqr="SELECT {} FROM {}".format(fdLst,tablename)
	else:
		xqr="SELECT {} FROM {} WHERE {}='{}' ".format(fdLst,tablename,colx,ticker)
	pqint( xqr ,file=sys.stderr)
	try:
		data=pd.read_sql(xqr,con=pgDB)
		if ticker=='*':
			xqr="SELECT ticker,ranking,ntotal from ara_ranking_list where category='AI' and subtype='SP500'".format(ticker)
		else:
			xqr="SELECT ticker,ranking,ntotal from ara_ranking_list where category='AI' and subtype='SP500' and ticker='{}'".format(ticker)
		rankX=pd.read_sql(xqr,con=pgDB)
		data = data.merge(rankX,on='ticker')
		#pqint(data.tail(2) ,file=sys.stderr)
	except Exception as e:
		pqint(str(e), 'failed to pull pricing data' ,file=sys.stderr)
		return None
	return data


def geteach_peers(tkLst,fdLst,subtopic='',output='csv',tablename=None,lang=None,dbname="ara",hostname='localhost',**optx):
	from iex_peers import iex_peers
	df,peerLst,peerInfo=iex_peers(tkLst)
	#if subtopic!='detailed':
	#	return peerLst
	if fdLst !='*':	
		field = list(set(fdLst.split(',')) & set(df.columns))
		
		df = df[field]
	data = df # data = data_output(df,output)
	pqint( df.tail(2) ,file=sys.stderr)
	return data

def peers_comment(tkLst,fdLst,**optx):
	return geteach_peers(tkLst,fdLst,**optx)

def rerun_dss(ticker=''):
	'''
	rerun daily_single_stock via forking subprocess
	'''
	data=''
	if len(ticker)<1:
		return json.dumps(dict(err="no ticker assigned",err_code=400))
	tkLst=sqlQuery("SELECT ticker from mapping_ticker_cik where ticker='{}'".format(ticker))
	if len(tkLst)<1:
		return json.dumps(dict(err="ticker not available",err_code=402))
	try:
		xcmd="cd /apps/fafa/pyx/alan/; python3 _alan_mp4.py daily_single_stock {} 1".format(ticker)
		sys.stderr.write("==RERUN: {}\n".format(xcmd))
		myproc = subprocess.Popen(xcmd,shell=True)
		if myproc.poll() != None:
			sys.stderr.write("**WARNING: {} not running\n".format(xcmd))
		else:
			sys.stderr.write("=={}: {} still running\n".format(ticker,xcmd))
		return json.dumps(dict(err="Analysis will be available shortly.",err_code=304))
	except Exception as e:
		sys.stderr.write("**WARNING: {} on {}\n".format(str(e),xcmd))
		return json.dumps(dict(err=str(e),err_code=403))

def report_comment(tkLst,fdLst,lang='cn',dbname='ara',hostname='localhost',limit=1,**optx):
	outTF=optx.pop('outTF',True)
	tablename='daily_single_stock'
	field=optx.get('field',{})
	if tkLst is not None and len(tkLst)>0:
		ticker=tkLst[0].upper()
		jobj={"ticker":ticker}
	else:
		ticker=''
		jobj={}
	zsrt={'pbdt'}
	data=[]
	try:
		#- for debugging as directly call mongodb
		#zsrt=[(x,-1) for x in zsrt]
		#host="{}:27017".format(hostname)
		#mgDB=MongoClient(host)[dbname]
		#data=list(mgDB[tablename].find(jobj,{'_id':0},sort=zsrt).limit(limit) )
		data,_,err=find_mdb(jobj,clientM=None,tablename=tablename,dbname=dbname,sortLst=zsrt,limit=1,dfTF=False)
		#if len(xtmp)>0:
		#	data = [{x:y for x,y in xtmp[0].items() if not isinstance(y,(dict))}]
	except Exception as e:
		sys.stderr.write("**ERROR: {},{} @{}\n".format(ticker,str(e),'report_comment'))
		data=[]

	if len(data)<1:
		ret=rerun_dss(ticker)
		sys.stderr.write("**WARNING: {} @{}\n".format(ret,'report_comment'))
		return ret

	# data = data_output(data,output)
	pqint( "===report_comment():\nFind:{},Field:{},Sort:{}\n".format(jobj,field,zsrt) ,file=sys.stderr)
	pqint( " --from tablename: {}".format(tablename) ,file=sys.stderr)
	pqint( " --DF[top]:\n{}".format(data) ,file=sys.stderr)
	return data

def news1_comment(tkLst,fdLst,**optx):
	from rssnews import rssnews
	outTF=optx.pop('outTF',True)
	opts={}
	for x,y in optx.items():
		if y is not None and x not in ['topic','dbname']:
			opts.update({x:y})
	if len(tkLst)>0:
		opts.update(tklst=tkLst)
	opts.update(outTF=False,nth=":")
	sys.stderr.write(" --OPTS:{} @{}\n".format(opts,"news_comment"))
	data=rssnews(**opts)
	if outTF and not isinstance(data,pd.DataFrame):
		data = pd.DataFrame(data)
	sys.stderr.write(" --data:{}\n".format(data)[:100]+"\n")
	return data

def pubdates_ob(pubdates='',key="pubDate"):
	from pandas import Timestamp as ts
	if not pubdates:
		return {}
	x1, x2 = pubdates.split(',')
	if all([x1,x2]):
		ob = {key:{"$gte":ts(x1),"$lte":ts(x2)}}
	elif  x1:
		ob = {key:{"$gte":ts(x1)}}
	elif  x2:
		ob = {key:{"$lte":ts(x2)}}
	else:
		ob = {}
	return ob

def get_news_query(queryObj,**opts):
	if 'source' in opts and opts['source']: # for multi-source selection
		queryObj.update({'source':{'$in':opts['source'].split(',')}})
	if 'url' in opts and opts['url']:
		queryObj.update({'url':opts['url']})
	if 'newstopic' in opts and opts['newstopic']:
		queryObj.update({'topic':opts['newstopic']})
	if 'title' in opts and opts['title']:
		queryObj.update({'title':{'$regex':opts['title'],'$options':'i'}})
	if 'title_cn' in opts and opts['title_cn']:
		queryObj.update({'title_cn':{'$regex':opts['title_cn'],'$options':'i'}})
	if 'summary' in opts and opts['summary']:
		queryObj.update({'summary':{'$regex':opts['summary'],'$options':'i'}})
	if 'pubdates' in opts and opts['pubdates']:
		ob = pubdates_ob(opts['pubdates'])
		queryObj.update(ob)
	return queryObj

def chatgpt_comment(tkLst,fdLst,**optx):
	from chatgptAPI import chatgptAPI;
	vx="dbname,debugTF,end,hostname,instrument,lang,outTF,output,src,start,subtopic,tablename,topic".split(',')
	for x in vx:
		del optx[x]

	res=chatgptAPI(**optx) 
	if 'choices' in res:
		return res['choices']
	else:
		return []

def news_comment(tkLst,fdLst,lang='cn',dbname='ara',hostname='localhost',output='html',limit=200,**optx):
	print("===@news_comment tkLst:{}, optx: {}".format(tkLst,optx),file=sys.stderr)
	from _alan_str import ssh2mg
	serverM,clientM=ssh2mg()
	sys.stderr.write(" --serverM:{},clientM:{}\n".format(serverM,clientM))
	from mongo_en2cn import mongo_en2cn as me
	outTF=optx.pop('outTF',True)
	tablename='rssNews'
	jobj={}
	transource=optx.pop('transource','google')
	#transource=optx.pop('transource','openai')
	subtopic=optx.get('subtopic','company')
	sortLst=['pubDate']
	data=[]
	if subtopic=='company' and len(tkLst)>0:
		ticker=tkLst[0]
		from rssCompany import run_rssCompany as rrc
		data = rrc(ticker)
		print("===Run Company News:{},\n --{}".format(ticker,data)[:100],file=sys.stderr)
	elif subtopic=='translate':
		link=optx.pop('link','')
		_id=optx.pop('_id','')
		src=optx.pop('fromLang','en')
		dest=optx.pop('toLang','zh-tw')
		tablename=optx.pop('tablenews','rssCompany')
		if link:
			jobj={'link':link}
		elif not _id:
			return []
		else:
			jobj={'_id':ObjectId(_id)}
		field={'title','title_cn','summary','summary_cn'}
		print("===Run Translation:",jobj,tablename,field,src,dest,file=sys.stderr)
		data = me(jobj,clientM=clientM,tablename=tablename,field=field,src=src,dest=dest,transource=transource)
	else:
		jobj = get_news_query(jobj,**optx)
		pqint(" --->news query jobj:\n",jobj,file=sys.stderr)

		field={'_id','ticker','title','title_cn','description','summary','summary_cn','pubDate','link','source'}
		data,_,_=find_mdb(jobj,clientM=clientM,tablename=tablename,dbname=dbname,field=field,sortLst=sortLst,limit=limit,dfTF=outTF)
		if isinstance(data,pd.DataFrame):
			data.drop_duplicates(subset =["pubDate","link"], keep = 'first', inplace = True)
	if fdLst not in ['*',''] and fdLst is not None:
		fields=fdLst.split(',')
		data = subDict(data,fields)
	if outTF and not isinstance(data,pd.DataFrame):
		data = pd.DataFrame(data)
	if serverM:
		clientM.close()
		serverM.stop()
	return data

def hourly_comment(tkLst,fdLst,tablename=None,lang=None,dbname="ara",hostname='localhost',output=None,start=None,end=None,topic=None,subtopic=None,**optx):
	from _alan_str import find_mdb
	if fdLst=='*':
		field = {}
	else:
		field = set(fdLst.split(','))
	limit=0
	instrument = getKeyVal(optx,'instrument','stock')
	rpt_hm = getKeyVal(optx,'rpt_hm',None)
	hhmm = getKeyVal(optx,'hhmm',None)
	pqint(tablename,optx,file=sys.stderr)
	#if subtopic.lower() == 'sector':
	tablename="mkt_briefing_media" # use if gtts-cli is working for audio/video
	#tablename="mkt_briefing_details" # otherwise
	if subtopic == 'sector':
		tablename="hourly_report"
		if len(tkLst)<1:
			jobj={"ticker":{"$in":["^GSPC","^DJI","^IXIC"]}}
		sortLst=['rpt_time']
		field={'ticker','comment','rpt_time','rpt_hm','rpt_status','title','label'}
		limit=3
	elif rpt_hm is not None or len(tkLst)>0:
		tablename="mkt_briefing_details"
		jobj={}
		if rpt_hm is not None:
			hmLst = [int(x) for x in rpt_hm.split(',')]
			jobj.update(rpt_hm={"$in":hmLst})
		if len(tkLst)>0 and tkLst[0]!='$' :
			jobj.update(ticker={"$in":tkLst})
		if len(field)<1:
			field = {"ticker","label","rpt_hm","rpt_time","cprice","xprice","comment","rpt_date","pngname"}
		sortLst=['rpt_time']
	elif hhmm is not None:
		hmLst = [int(x) for x in hhmm.split(',')]
		jobj={"hhmm":{"$in":hmLst}}
		sortLst=['pbdt']
	else:
		jobj={}
		sortLst=['pbdt']
		limit=1
	outTF = getKeyVal(optx,'outTF',True)
	df,_,_=find_mdb(jobj,tablename=tablename,dbname=dbname,field=field,sortLst=sortLst,limit=limit,dfTF=outTF)
	data = df # data = data_output(df,output)
	pqint( "===hourly_comment():\nFind:{},Field:{},Sort:{}\n".format(jobj,field,sortLst) ,file=sys.stderr)
	pqint( " --tkLst: {},fdLst: {}".format(tkLst,fdLst) ,file=sys.stderr)
	pqint( " --from tablename: {}".format(tablename) ,file=sys.stderr)
	pqint( " --DF keys:\n{}".format(df[0].keys())+"\n" ,file=sys.stderr)
	pqint( " --DF:\n{}".format(df)[:200]+"\n" ,file=sys.stderr)
	return data

def theme_comment(tkLst,fdLst,subtopic='ipo',**opts):
	from _alan_rmc import run_topic_theme
	outTF=opts.pop('outTF',True)
	if subtopic.lower() in ['majorplayer','media','ipo','etffund']:
		funcName= "topic_{}_{}".format("theme",subtopic)
		sys.stderr.write("===RUNNING {} with OPTS:{}\n".format(funcName,opts))
		df=run_topic_theme(funcName=funcName,subtopic=subtopic,outTF=outTF,**opts)
	if len(df)<0:
		return {}
	if fdLst not in ['*',''] and fdLst is not None:
		fields=fdLst.split(',')
		df = subDict(df,fields)
	if len(df)<0:
		return []
	if isinstance(df,pd.DataFrame):
		sys.stderr.write("==OPTS:{},FIELDS:{}, DATA:\n{}".format(opts,fdLst,df.tail(2)))
	data = df # data = data_output(df,**opts)
	return data

def industry_comment(tkLst,fdLst,dbname='ara',output=None,**opts):
	tablename='record_hilo'
	try:
		field=['category_cn','ticker','close','pchg','pbdate','label_cn','comment']
		data,_,err=find_mdb({}, dbname=dbname,tablename=tablename,field=field,sortLst={"category":-1},dfTF=True)
	except Exception as e:
		sys.stderr.write("**ERROR: {},{} @{}\n".format(ticker,str(e),'industry_comment'))
		data=[]
	return data

def industry_commentOLD(tkLst,fdLst,output=None,**opts):
	df = getlist_filter(fdLst=fdLst,subtopic='industry')
	if not (tkLst is None or len(tkLst)<1 or tkLst[0] in ['','*']):
		df = df[df['ticker'].isin(tkLst)]
	if len(df)<1:
		return None
	data = df # data = data_output(df,output)
	return data

def search_comment(tkLst,fdLst,**opts):
	topicLst='hourly|news|report|theme|peers|industry|MFRM|news1|chatgpt'.split('|')
	topic=getKeyVal(opts,'topic','MFRM')
	if topic not in topicLst:
		return None
	argName="{}_comment".format(topic)
	if topic in topicLst and argName in globals():
		pqint("==RUNNING {}() Inputs:{}".format(argName,opts),file=sys.stderr)
		try:
			data=globals()[argName](tkLst,fdLst,**opts)
		except Exception as e:
			pqint("**ERROR:{} to run {}".format(str(e),argName),file=sys.stderr)
			data={}
		return data
	output=opts.pop('output',None)
	data=pd.DataFrame()
	optx=subDict(opts,['tablename','lang','dbname','hostname','topic','subtopic','factor'])
	if tkLst[0]=='*':
		data=geteach_comment('*',fdLst,**optx)
		# data = data_output(data,output)
		return data
	for ticker in tkLst:
		ret=geteach_comment(ticker,fdLst,**optx)
		if ret is not None and len(ret)>0:
			data=data.append(ret,ignore_index=True)
		else:
			continue
	# data = data_output(data,output)
	if len(data)<1:
		return None
	return data

def search_factor(tkLst,fdLst,**opts):
	opts.update(subtopic='attr')
	return search_comment(tkLst,fdLst,**opts)

def geteach_quote(ticker,fdLst,tablename=None,lang=None,dbname="ara",hostname='localhost',colx='ticker'):
	if tablename is None:
		return None
	xtmp="select {} from {} WHERE {}='{}' order by pbdate DESC limit 2"
	xqr=xtmp.format(fdLst,tablename,colx,ticker)
	sys.stderr.write(" --geteach_quote from pgDB::{}\n".format(tablename))
	sys.stderr.write(" --SQL:\n{}\n".format(xqr))
	try:
		data=pd.read_sql(xqr,con=pgDB)
		data=renameDict(data,{"series":"ticker","value":"close"})
		colv = 'close'
		if data.shape[0]>1 and 'change' not in data.columns:
			chg = data[colv].iloc[0]-data[colv].iloc[1]
			pchg = data[colv].iloc[0]/data[colv].iloc[1]-1
			data = data.iloc[0]
			data['change']=chg
			data['changePercent']=pchg
		sys.stderr.write(" --DATA[{}]:\n{}\n".format(len(data),data))
	except Exception as e:
		sys.stderr.write("**ERROR:{} @ {}\n".format(str(e),'geteach_quote'))
		return None
	return data

def getlist_quotes(tkLst,fdLst,tablename="iex_sector_quote",lang=None,dbname="ara",hostname='localhost',colx='symbol'):
	from _alan_str import find_mdb
	dd = []
	pqint( tkLst ,file=sys.stderr)
	for ticker in tkLst:
		ret,_,_=find_mdb({colx:ticker},tablename=tablename,dbname=dbname)
		pqint( ret,ticker,tablename,dbname ,file=sys.stderr)
		dd = dd + ret
	df = pd.DataFrame(dd)
	if fdLst != '*':
		field = set(fdLst.split(','))
		newcol = list(field & set(df.columns))
		df = df[newcol]
	return df

def geteach_financials_history(ticker,fdLst,**opts):
	debugTF = getKeyVal(opts,'debugTF',False)
	subtopic = getKeyVal(opts,'subtopic','')
	src = getKeyVal(opts,'src','zacks')
	jobj={'ticker':ticker}	
	if subtopic == 'eps': # and src=='zacks':
		tablename='earnings_zacks'
		jd=list(mgDB[tablename].find(jobj,{'_id':0},sort=[("pbdate",-1)]))
		if len(jd)<1:
			return []
		datax = pd.DataFrame(jd)
		datax = renameDict(datax,{'pChg':'epsSuprise%','ESP':'epsSuprise'})
	elif subtopic == 'eps' and src=='yh': # No longer used
		tablename='earnings_yh'
		jobj.update({'actualEPS':{'$ne':np.nan}})
		jd=list(mgDB[tablename].find(jobj,{'_id':0},sort=[("pbdate",-1)]))
		if len(jd)<1:
			return []
		for j,xd in enumerate(jd):
			jd[j]['EPSReportDate']="{}{}{}{}-{}{}-{}{}".format(*list(str(jd[j]['pbdate'])))
		datax = pd.DataFrame(jd)
	elif subtopic == 'roe':
		freq = getKeyVal(opts,'freq','Q')
		tablename='qS_IS_{}'.format('A' if freq=='A' else 'Q')
		jd=list(mgDB[tablename].find(jobj,{'_id':0}))
		if len(jd)<1:
			return []
		datax = pd.DataFrame(jd) if len(jd)>0 else []

		tablename='qS_BS_{}'.format('A' if freq=='A' else 'Q')
		jd=list(mgDB[tablename].find(jobj,{'_id':0}))
		if len(jd)>0:
			for j,xd in enumerate(jd):
				a=jd[j]['pbdate']
				jd[j]['reportDate']='{:04d}-{:02d}-{:02d}'.format(int(a/10000),int(a/100)%100,a%100)
				jd[j]['freq']=freq
			d2 = pd.DataFrame(jd)
			datax = datax.merge(d2,on=['ticker','pbdate','endDate'],how='inner')
			if debugTF:
				sys.stderr.write("=====geteach_financials_history() d2:{}".format(d2))
		if 'netIncome' in datax.columns and 'totalStockholderEquity' in datax.columns:
			datax['roe'] = datax['netIncome']/datax['totalStockholderEquity']
		if debugTF:
			sys.stderr.write("=====geteach_financials_history() datax:{}".format(datax))
		datax=subDF(datax,['ticker','roe','pbdate','reportDate','freq','endDate','netIncome','totalStockholderEquity'])
		sys.stderr.write(" ---datax:{}\n{}\n".format(ticker,datax))
	else:
		return []
	return datax

def geteach_financials_historyOLD(ticker,fdLst,**opts):
	colx='ticker'
	if 'subtopic' in opts and opts['subtopic'] == 'eps':
		tablename='earnings_hist_yh'
		xqTmp = "select {} from {} where {}='{}' order by pbdate"
		xqr=xqTmp.format(fdLst,tablename,colx,ticker)
	elif 'subtopic' in opts and opts['subtopic'] == 'roe':
		freq = opts['freq'] if 'freq' in opts else 'Q'
		tablename='iex_financials_hist'
		xqTmp = "select (\"netIncome\"::float/\"shareholderEquity\"*100.) as roe, {} from {} where {}='{}' and freq='{}' order by pbdate"
		xqr=xqTmp.format(fdLst,tablename,colx,ticker,freq)
	sys.stderr.write(" --{} SQL:\n{}\n".format('geteach_financials_history',xqr))
	datax=pd.read_sql(xqr,con=pgDB)
	return datax

def geteach_minute_web(ticker,fdLst,**opts):
	''' pull minute data from web 
	'''
	from _alan_calc import get_minute_iex 
	# get_minute_yh DEPRECATED, yh_spark_hist is used
	from yh_chart import yh_spark_hist as ysh, runOTF;
	src = opts.pop('src','iex')
	src= "yh" if '^' in ticker or '=' in ticker else src
	sys.stderr.write("---Get minute data {} from WEB::{}\n".format(ticker,src.upper()))
	if src=='yh':
		#datax = get_minute_yh(ticker,ranged='1d',tsTF=True,debugTF=False)
		#d=ysh([ticker],saveDB=False,range='1d',types='chart',interval='5m',debugTF=True)
		d=runOTF(ticker,ysh,deltaTolerance=900,types='chart',tablename='yh_chart_hist',zpk=['ticker','pbdt'],range='15m',interval='5m',debugTF=True,dbname='ara')
		if len(d)>0:
			datax=pd.DataFrame(d)
		else:
			return []
	else:
		datax = get_minute_iex(ticker,ranged='1d',date=None,tsTF=True,debugTF=False)
	return datax

def geteach_minute_db(ticker,fdLst,**opts):
	''' pull minute data from database 
	'''
	subtopic=getKeyVal(opts,'subtopic','')
	src = opts.pop('src','iex')
	src= "yh" if '^' in ticker or '=' in ticker else src
	tablename="{}_spark_hist".format(src)
	sys.stderr.write("---Get minute data {} from MDB::{}\n".format(ticker,tablename))
	try:
		jobj={"ticker":ticker}
		# Get latest pbdate
		xd = mgDB[tablename].find_one({"$query":jobj,"$orderby":{"epochs":-1}},{"pbdate":1,"_id":0})
		jobj.update(xd)
		if subtopic in ['sparkline','spark']:
			d = mgDB[tablename].find(jobj,{"_id":0},sort=[("epochs",-1)]).limit(20)
		else:
			d = mgDB[tablename].find(jobj,{"_id":0})
		if d is None:
			return {}
		data=list(d)
		if len(data)<1:
			sys.stderr.write(" --No data found from {}\n".format(tablename))
			return {}
		datax = pd.DataFrame(data)
		#datax,_,_ = find_mdb({"ticker":ticker},clientM=mgDB,tablename=tablename,sortLst={"epochs"},dfTF=True)
	except Exception as e:
		sys.stderr.write("**ERROR:{} @ {}\n".format(str(e),'geteach_minute_db'))
		datax={}
	return datax

def geteach_minute_history(ticker,fdLst,**opts):
	''' pull minute data from database (default)
	OR web if 'webTF' is True
	'''
	webTF=subtopic=getKeyVal(opts,'webTF',False)
	if webTF:
		opts.update(src='yh')
		return geteach_minute_web(ticker,fdLst,**opts)
	data=geteach_minute_db(ticker,fdLst,**opts)
	if data is None or len(data)<1:
		sys.stderr.write("**WARNING:{}\n".format("data not found in DB, live pulling"))
		opts.update(src='yh')
		return geteach_minute_web(ticker,fdLst,**opts)
	return data

def geteach_daily_history(ticker,fdLst,**opts):
	from _alan_calc import pullStockHistory
	from yh_chart import yh_spark_hist as ysh, runOTF
	datax = []
	try:
		datax = pullStockHistory(ticker,pgDB=pgDB,**opts)
		if datax is None or len(datax)<1:
			sys.stderr.write("**WARNING:{}\n".format("data not found in DB, live pulling"))
			datax=runOTF(ticker,ysh,deltaTolerance=86400,types='chart',tablename='yh_daily_hist',zpk=['ticker','pbdt'],range='1y',interval='1d',debugTF=True,dbname='ara')
			datax=pd.DataFrame(datax)
	except Exception as e:
		pqint("**ERROR:{} @ {}, opts:\n{}".format(str(e),'geteach_daily_history',opts) ,file=sys.stderr)
	return datax

def geteach_history(ticker,fdLst,**opts):
	# for topic list 'financial','daily','minute'
	topic = getKeyVal(opts,'topic','daily') 
	argName = "geteach_{}_history".format(topic)
	try:
		if argName not in globals():
			argName="geteach_daily_history"
		sys.stderr.write(" RUNNING Ticker:{}[fdLst:{}]:topic:{} of {}()\n".format(ticker,fdLst,topic,argName) )
		argFunc = globals()[argName]
		df = argFunc(ticker,fdLst,**opts)
	except Exception as e:
		sys.stderr.write("**ERROR: {} @{}()".format(str(e),argName) )
		df = ''
	return df

def get_sector_etfname(tkLst,**opts):
	if 'topic' in opts and 'subtopic' in opts:
		if opts['topic']=='market' and opts['subtopic']=='sector':
			tkLst = list(pd.read_sql("select etfname from spdr_sector",con=pgDB)['etfname'].values)
	return tkLst

def get_valid_DB_quote(ticker='AAPL',tablename="yh_quote_curr",deltaTolerance=86400):
	jobj={"ticker":ticker}
	ret = list(mgDB[tablename].find(jobj,{"_id":0},sort=[("epochs",-1)]).limit(1))
	#ret,_,_=find_mdb(jobj,tablename=tablename,dbname="ara")
	if len(ret)<1:
		return []
	pbdtMod=ret[0]['pbdt']
	pbdtCurr=pd.Timestamp(pd.Timestamp.now())
	deltaPassed=pd.Timedelta(pbdtCurr - pbdtMod).total_seconds()
	if deltaPassed>deltaTolerance:
		return []
	pqint( "==DB[{}] quote {}:\n{}".format(tablename,ticker,ret) ,file=sys.stderr)
	return ret

def search_quote(tkLst,fdLst,**opts):
	from yh_chart import yh_spark_hist as ysh;
	tkLst=get_sector_etfname(tkLst,**opts)
	instrument = getKeyVal(opts,'instrument','stock')
	outTF = getKeyVal(opts,'outTF',True)
	hostname,dbname,tablename,lang = getKeyVal(opts,['hostname','dbname','tablename','lang'],['localhost','ara',None,None])
	colx='ticker' if instrument=='stock' else 'series'
	data=[]
	opts.pop('ticker',None)
	for ticker in tkLst:
		sys.stderr.write("---Get {} @ search_quote\n".format(ticker))
		try:
			# get quotes from MDB::"yh_quote_curr" for yahoo source indices setup in the PGDB::'mapping_series_label'
			if instrument=='stock' or re.search(r'[=^.]',ticker):
				mktLst =['^GSPC','^DJI','^IXIC','^SOX']
				if ticker.upper() in mktLst:
					tablename="market_indicator_quote"
				else:
					tablename="yh_quote_curr"
				ret=get_valid_DB_quote(ticker,tablename=tablename)
			else: # get quotes for all fields from pgDB
				ret=geteach_quote(ticker,fdLst='*',tablename=tablename,lang=lang,dbname=dbname,hostname=hostname,colx=colx)
			if instrument=='stock' and len(ret)<1: # get live quote
				pqint( "==Get live quote:{} @ {}".format(ticker,'yh_spark_hist()') ,file=sys.stderr)
				ret = ysh(ticker,types='quote',dfTF=False,**opts)
				pqint( "==Live quote {}:\n{}".format(ticker,ret) ,file=sys.stderr)
			if ret is not None and len(ret)>0:
				#data=data.append(ret,ignore_index=True)
				data.extend(ret)
			else:
				continue
		except Exception as e:
			pqint( "**ERROR:{} @ {}".format(str(e),search_quote) ,file=sys.stderr)
			continue
	if len(data)<1:
		return None
	data=pd.DataFrame(data)
	data=renameDict(data,{'pchg':'changePercent','xclose':'prevClose'})
	colx=['ticker','epochs','open','high','low','close','volume','xclose','change','pchg','pbdt','hhmm','pbdate','changePercent','prevClose','marketCap']
	if fdLst is not None:
		if fdLst.lower()=='all':
			return data
		elif fdLst.lower()=='':
			pass
		else:
			fieldLst = list(set(fdLst.split(',')) & set(data.columns))
			colx = fieldLst if len(fieldLst)>0 else colx
	data=subDF(data,colx)
	#if outTF:
	#	output = opts.pop('output','json')
	#	data = data_output(data,output)
	return data

def search_hist(tkLst,fdLst,**opts):
	output=getKeyVal(opts,'output','json')
	topic=getKeyVal(opts,'topic','daily')
	opts.pop('ticker',None)
	data=pd.DataFrame()
	dd=[]
	for ticker in tkLst:
		df=geteach_history(ticker,fdLst,**opts)
		sys.stderr.write(" --DF: {}\n{}\n".format(ticker,type(df)))
		if isinstance(df,pd.DataFrame) and len(df)>0:
			data=data.append(df,ignore_index=True)
		elif isinstance(df,list) and len(df)>0:
			dd=dd.extend(df)
		else:
			continue
	if len(dd)>0:
		data=pd.DataFrame(dd)
	sys.stderr.write(" --DATA[{}] tail:\n{}\n".format(len(data),data.tail()))
	if topic not in ['daily','minute']:
		return data # data_output(data,output)
	data=renameDict(data,{"name":"ticker"})
	colx=['ticker','epochs','open','high','low','close','volume','xclose','change','pchg','pbdt','hhmm','pbdate']
	data=subDF(data,colx)
	return data # data_output(data,output)

def search_history(tkLst,fdLst='',**opts):
	return search_hist(tkLst,fdLst=fdLst,**opts)

# DEPRECATED
def getlist_filterOLD(fdLst='',subtopic='mostvalue',start=None,id=None):
	from _alan_str import stock_screener as bbpre
	scrDct={'mostactive':'most_actives', 'mostvalue':'most_values',
		'gainers':'day_gainers', 'losers':'day_losers', 'industry':'sector_gainers',
		'5%':'5%','-5%':'-5%','+5%':'+5%',
		'day_gainers':'day_gainers', 'day_losers':'day_losers', 'sector_gainers':'sector_gainers',
		'sector_losers':'sector_losers', 'most_actives':'most_actives', 'most_values':'most_values'}
	s=subtopic.lower()
	sID=scrDct.pop(s,'most_values')
	df=bbpre(sID)
	if 'close' not in df and 'price' in df:
		df['close']=df['price']
	return df

def getlist_filter(fdLst='',subtopic='mostvalue',start=None,id=None):
	from _alan_str import stock_screener as bbpre
	if subtopic.lower()=='mostactive': # 爆量
		df=bbpre('most_actives',addiFilter=1)
	elif subtopic.lower()=='mostvalue': # 金額爆量
		df=bbpre('most_values',addiFilter=1)
	elif subtopic.lower()=='gainers': # 牛方
		df=bbpre('day_gainers',addiFilter='abs(changePercent)>1&price>4.99')
	elif subtopic.lower()=='losers': # 熊方
		df=bbpre('day_losers',addiFilter='abs(changePercent)>1&price>4.99')
	elif subtopic in ['5%','+5%']:
		df=bbpre('day_gainers',addiFilter=2)
	elif subtopic == '-5%':
		df=bbpre('day_losers',addiFilter=2)
	elif subtopic.lower() == 'industry':
		df=bbpre('sector_gainers')
	else: # most_active as default
		df=bbpre('most_actives',addiFilter=1)
	if 'close' not in df and 'price' in df:
		df['close']=df['price']
	if 'ranking' not in df:
		df['ranking'] = [int(x)+1 for x in df.index.values]
	return df

def getlist_market(fdLst,subtopic='sector',start=None,id=None):
	if subtopic=='theme':
		xqr = "SELECT theme FROM theme_list group by theme"
		if id is not None:
			xqTmp = "SELECT {} FROM theme_list where theme='{}'"
			xqr = xqTmp.format(fdLst,id)
	else:
		if id is not None:
			xqTmp = "SELECT {} FROM mapping_ticker_cik WHERE sector='{}'"
			xqr = xqTmp.format(fdLst,id)
		else:
			xqTmp = "SELECT {} FROM spdr_sector WHERE sector not like '%%Index'"
			xqr = xqTmp.format(fdLst)
	sys.stderr.write(" --SQL:{}\n".format(xqr))
	data=pd.read_sql(xqr,con=pgDB)
	return data

def getlist_recommend(fdLst,subtopic='AI',start=None,id=None):
	return getlist_AI(fdLst,subtopic=subtopic,start=start,id=id)

def getlist_AI(fdLst,subtopic='AI',start=None,id=None):
	"""
	subtopic list [ai|industry|value|growth]
	"""
	subtopic = subtopic.lower()
	if start is None:
		start="2018-10-24"
	if fdLst == '*':
		fieldLst = fdLst
	else:
		fieldLst = '"{}"'.format('","'.join(fdLst.split(',')))
	
	if subtopic=='growth': # for z=0.225 for 60% uptrend
		xqTmp = """SELECT {} FROM ara_outlook_factor_temp WHERE sector not like '%%Index' and factor='overall' and zscore>=0.255 ORDER BY zscore DESC limit 10"""
		xqr = xqTmp.format(fieldLst)
	elif subtopic=='value':
		xqTmp = """SELECT {} FROM ara_outlook_factor_temp WHERE sector not like '%%Index' and factor='valuation' and zscore>=0.255 ORDER BY zscore DESC limit 10"""
		xqr = xqTmp.format(fieldLst)
	elif subtopic=='watchlist':
		xqTmp = """SELECT {} FROM ara_outlook_factor_temp WHERE sector not like '%%Index' and factor='valuation' and zscore<=-0.0 ORDER BY zscore DESC limit 10"""
		xqr = xqTmp.format(fieldLst)
	elif subtopic=='alert':
		xqTmp = """SELECT {} FROM ara_outlook_factor_temp WHERE sector not like '%%Index' and factor='valuation' and zscore<=-0.255 ORDER BY zscore limit 10"""
		xqr = xqTmp.format(fieldLst)
	elif subtopic=='industry':
		xqTmp = """SELECT {} FROM ara_outlook_factor_recommend_cn WHERE length(recommend)>0 and sector like '%%Index' ORDER BY confidence DESC"""
		xqr = xqTmp.format(fieldLst)
	elif subtopic=='alert':
		xqTmp = """SELECT {} FROM ara_outlook_factor_recommend_cn WHERE length(recommend)>0 and sector not like '%%Index' ORDER BY confidence DESC limit 10"""
		xqr = xqTmp.format(fieldLst)
	else:
		return None

	pqint(xqr ,file=sys.stderr)
	data=pd.read_sql(xqr,con=pgDB)
	#data['ranking'] = [int(x)+1 for x in data.index.values]
	return data

import getpass
def geteach_list(tkLst,fieldLst,tablename=None,lang=None,dbname="ara",hostname='localhost'):
	if tablename is None:
		return None
	if fieldLst is None:
		fieldLst='*'
	xqr="SELECT {1} FROM {0}".format(tablename,fieldLst)
	if tablename == 'mapping_series_label':
		xqr = xqr + " WHERE mkt_list=1 ORDER BY category_seq,category_label_seq"
	elif tkLst[0]!='*':
		inLst=json.dumps(tkLst)[1:-1].replace('"','\'')
		xqr = xqr + " WHERE ticker in ({}) ORDER BY ticker".format(inLst)
	pqint( xqr ,file=sys.stderr)
	try:
		data=pd.read_sql(xqr,con=pgDB)
		pqint(data.tail(2) ,file=sys.stderr)
	except Exception as e:
		pqint("***ERROR: {} @ {}()".format(str(e),"geteach_list") ,file=sys.stderr)
		return "***ERROR: {} @ {}()".format(str(e),"geteach_list")
		#return None
	return data

def search_list(tkLst,fdLst,**opts):
	topic,start,subtopic,output,id = getKeyVal(opts,['topic','start','subtopic','output','id'],[None,None,None,None,None])
	hostname,dbname,tablename,lang = getKeyVal(opts,['hostname','dbname','tablename','lang'],['localhost','ara',None,None])
	pqint("==>{}::topic:{},subtopic:{},field:{}".format('search_list',topic,subtopic,fdLst) ,file=sys.stderr)
	if hasattr(subtopic,'__len__') is not True:
		subtopic = ''
	if topic in ['filter','recommend','AI','market']: # select either [getlist_filter|getlist_recommend]
		funcName = "getlist_{}".format(topic)
		if funcName in globals():
			searchListFunc = globals()[funcName]
			pqint( "Applying {}: {}".format(funcName,searchListFunc) ,file=sys.stderr)
			data = searchListFunc(fdLst,subtopic=subtopic,start=start,id=id)
			# data = data_output(df,output)
			return data
	elif topic in ['ytdRtn','sp500','cdr','ipo']:
		#from ytdRtn_calc import ytdRtn_calc,ytdOTF
		from ytdRtn_cdr import ytdRtn_calc
		if subtopic is None or len(subtopic)<1: 
			subtopic='sector'
		if start is None or len(start)<1: 
			start=20210101
		pqint("---{}::topic:{},subtopic:{},start:{}".format('ytdRtn_calc',topic,subtopic,start) ,file=sys.stderr)
		data = ytdRtn_calc(topic=topic,start=start,group=subtopic)[0]
		return data
		#tablename='ytdRtn_{}'.format(subtopic)
		#data=ytdOTF(ytdRtn_calc,start=start,deltaTolerance=900,tablename=tablename,zpkChk=['group'],zpk=[subtopic],group=subtopic,debugTF=True,dbname='ara')
		#sys.stderr.write(" --ytdRtn_calc data:{}\n{}\n".format(type(data),data))
		#outTF=opts.pop('outTF',True)
		#if outTF:
		#	data=pd.DataFrame(data)
		#return data
	elif topic in ['peers']:
			data = geteach_peers(tkLst,fdLst,subtopic=subtopic,output=output)
			return data
		
	if tablename is None:
		tablename='spdr_list'
	data=geteach_list(tkLst,fdLst,tablename=tablename,lang=lang,dbname=dbname,hostname=hostname)
	# data = data_output(data,output)
	return data

def search_allocation(tkLst,fdLst,**opts):
	output = getKeyVal(opts,'output',None)
	from bl_portopt2 import bl_example
	try:
		data = bl_example(tkLst)
		data['mktCapWeigh'] = data['mktCapWeigh']*100.0
		data['weight'] = data['weight']*100.0
		data['rrt'] = data['rrt']*100.0
		pd.options.display.float_format = '{:.2f}'.format
		# data = data_output(data,output)
	except Exception as e:
		data = None
	return data

def search_mp3(tkLst,fdLst,**opts):
	tagContent='''
	<audio class="audioClass" controls>
	  <source src="{}" type="audio/mpeg">
	  Your browser does not support the audio tag.
	</audio>
	'''
	attrType=getKeyVal(opts,'attrType','src') # tag|src|content for tag_setup|src_filename|content
	tagContent=getKeyVal(opts,'tagContent',tagContent)
	limit=getKeyVal(opts,'limit',30) 
	aliasDir=getKeyVal(opts,'aliasDir','/apps/fafa/pyx/alan/US/mp3_hourly')
	routeDir=getKeyVal(opts,'routeDir','/US/mp3_hourly')
	filename=getKeyVal(opts,'filename','*.mp3')
	fpath="{}/{}".format(aliasDir,filename)
	fpLst = sorted(iglob(fpath), key=os.path.getmtime, reverse=True)
	sys.stderr.write("===Search {}\n".format(attrType))
	sys.stderr.write(" --searching:{}, found:{}\n".format(fpath,fpLst))
	data=[]
	for fname in fpLst[:limit]:
		fp=fname.replace(aliasDir,routeDir)
		if attrType=='tag':
			data=tagContent.format(fp)
			return data
		elif attrType=='content':
			fp=open(fname,'rb')
			data=fp.read()
			fp.close()
			return data
		else:
			data=fp
			return data
			#data.append(fp)
	#sys.stderr.write(" --Ret Data:\n{}\n".format(data))
	return data

def search_mp4(tkLst,fdLst,**opts):
	tagContent='''
	<video class="videoClass" controls>
	  <source src="{}" type="video/mp4">
	  Your browser does not support the video tag.
	</video>
	'''
	opts.pop('tagContent',None)
	return search_mp3(tkLst,fdLst,tagContent=tagContent,**opts)

def search_img(tkLst,fdLst,**opts):
	tagContent='''<img class="imgClass" src="{}" >'''
	opts.pop('tagContent',None)
	return search_mp3(tkLst,fdLst,tagContent=tagContent,**opts)

def search_txt(tkLst,fdLst,**opts):
	attrType=getKeyVal(opts,'attrType','src') # tag|src|content for tag_setup|src_filename|content
	opts.pop('attrType',None)
	data= search_mp3(tkLst,fdLst,attrType=attrType,**opts)
	return data

def cgi_api(optx={'pprint':'N','api_key':''}):
	import os 
	curdir = os.path.dirname(os.path.realpath(__file__))
	helpfile =  "{}/{}".format(curdir,'alanapi_help.html')
	xf, _ = opt_alanapi()
	xf.update(optx)
	cgitb.enable(display=0,logdir="/apps/fafa/https/html/log/",format="text")
	cssStyle='''<style>)
	table {border-collapse: collapse;font-size:11pt}
	thead {background:lightgray;font-size:14pt;}
	table tr {border:1px solid black}
	tbody tr:nth-child(even){background:lightgray;}
	</style>
	'''
	mf = cgi.FieldStorage()
	sys.stderr.write("===== START CGI arguments:{}:{}\n{}\n".format(s2dt(),list(mf),mf))
	for ky in mf:
		va=mf[ky].value
		if ky[-2:] == 'TF':
			va = True if va[:1].lower() in ['t','y','1'] else False
		xf[ky]=va
	search,output,attrType=getKeyVal(xf,['search','output','attrType'],['list',None,'src'])
	### No action and show help
	if xf['search'] is None:	
		print("Content-type:text/html;charset=utf-8\r\n\r\n")
		print(open(helpfile).read())
		return None

	### No api_key match
	if verify_apikey(xf['api_key']) < 1:
		print("Content-type:text/html;charset=utf-8\r\n\r\n")
		print("<H2 style='color:red;'>{}</H2>".format("203: Non-Authoritative Information due to invalid api_key"))
		print(open(helpfile).read())
		return None

	### Start setup cgi parameters xf
	if 'ticker' in xf: 
		symLst=xf['ticker'].split(',')
	else:
		symLst=None
	### Run model
	try:
		fdLst = xf['field']
		xf.pop('field',None)
		sys.stderr.write("===START run_alanapi {}\n".format(s2dt()))
		sys.stderr.write(" --tkLst: {}\n".format(symLst))
		sys.stderr.write(" --fdLst: {}\n".format(fdLst))
		sys.stderr.write(" --OPTS: {}\n".format(xf))
		sys.stderr.write(" --OUT OPTS:{}:{}:{}\n".format(search,output,attrType))
		data=run_alanapi(symLst,fdLst,**xf)
	except Exception as e:
		sys.stderr.write("**ERROR: {} @ {}()\n".format(str(e),"cgi_api"))
		sys.stderr.write(" --OPTS: {}\n".format(xf))
	### START CGI OUTPUT 
	if data is None or (type(data) == 'str' and len(data.strip())<1):
		print("Content-type:text/html;charset=utf-8\r\n\r\n")
		print("<H2 style='color:red;'>{}</H2>".format("204: No Content"))
		print(open(helpfile).read())
	elif output=='json':
		print("Content-type:application/json;charset=utf-8\r\n\r\n")
		print(data)
	elif output=='dict':
		sys.stdout.write("Content-type:text/plain;charset=utf-8\r\n\r\n")
		pprint.pprint(data)
	elif search=='mp3' and attrType=='content': # streaming data
		try:
			data=base64.b64encode(data).decode()
			data="data:audio/mpeg;base64,"+data
		except Exception as e:
			sys.stderr.write("**ERROR mp3:{}\n{}\n".format(str(e),type(data)))
		#OR
		print("Content-type:text/html;\r\n\r\n")
		data='<embed class=audioClass src="'+data+'" hidden="false" autostart="false" loop="false"/>'
		print(data)
		sys.stderr.write("{}\n".format(data[:100]))
	elif search=='mp4' and attrType=='content': # streaming data
		#print("Content-type:video/mp4;charset=base64\r\n\r\n")
		data=base64.b64encode(data).decode()
		data="data:video/mp4;base64,"+data
		print("Content-type:text/html;\r\n\r\n")
		data='<embed class=videoClass src="'+data+'" hidden="false" autostart="false" loop="false"/>'
		print(data)
	elif search=='img' and attrType=='content': # streaming data
		#print("Content-type:image/svg+xml;\r\n\r\n")
		data=base64.b64encode(data).decode()
		data="data:image/svg+xml;base64,"+data
		print("Content-type:text/html;\r\n\r\n")
		data='<embed class=imgClass src="'+data+'" hidden="false" loop="false"/>'
		print(data)
	elif output=='html':
		print("Content-type:text/html;charset=utf-8\r\n\r\n")
		print(cssStyle)
		tblStyle=getKeyVal(xf,'tblStyle',cssStyle)
		print(data)
	else:
		if output in ['csv','tsv']:
			sys.stdout.write("Content-type:text/plain;charset=utf-8\r\n\r\n")
		else:
			print("Content-type:text/html;charset=utf-8\r\n\r\n")
			pageHeader=getKeyVal(xf,'pageHeader','ALAN API Page')
			if pageHeader is not None:
				print("<header><title>{}</title></header>\r\n".format(pageHeader))
		print(data)
	sys.stderr.write("===END cgi_api @ {}\n".format(s2dt()))
	return data

from pymongo import MongoClient
from bson import json_util
import json
def search_ohlc(tkLst,fdLst,tablename=None,lang=None,dbname="ara",hostname='localhost',output=None,start=None,end=None,topic=None,subtopic=None):
	host="localhost:27017";dbname="ara";tablename="ohlc_pattern"
	dbM=MongoClient(host)[dbname]
	name="morning_star"
	data=[]
	for ticker in tkLst:
		#pData=dbM[tablename].find({"ticker":ticker,"name":name})
		if ticker=='*':
			pData=dbM[tablename].find()
		else:
			pData=dbM[tablename].find({"ticker":ticker})
		mobj= json.loads(json_util.dumps(pData))
		data.append(mobj)
	return data

def run_alanapi(symLst,fdLst,**opts):
	'''
	list of keys:
	['lang', 'subtopic', 'search', 'end', 'start', 'debugTF', 'hostname', 'tablename', 'topic', 'field', 'instrument', 'output', 'dbname']
	'''
	search, instrument, hostname, dbname, tablename = opts['search'],opts['instrument'],opts['hostname'],opts['dbname'],opts['tablename']
	if search == None:
		search='search_list'
	elif search[:7] != 'search_':
		search = 'search_{}'.format(search)
	if symLst is None or len(symLst)<1:
		symLst=['*'] if search[-5:] == '_list' else []
	try:
		opts['tablename']=dft_tablename(search,instrument,tablename)
		pqint(" --- {} {}, instrument:{}, tablename:{}\n".format(search,symLst,instrument,tablename) ,file=sys.stderr)
		searchFunc=globals()[search]
		opts.pop('search',None)
		data=searchFunc(symLst,fdLst,**opts)
	except Exception as e:
		pqint('**ERROR: failed to run {}: {}'.format(searchFunc,str(e)) ,file=sys.stderr)
		return None
	outTF = opts.pop('outTF',True)
	if outTF:
		output = opts.pop('output','json')
		data = data_output(data,output)
	return data
	

def opt_alanapi():
	parser = OptionParser(usage="usage: %prog [option] SYMBOL ...", version="%prog 0.7",
		description="API for ALAN")
	parser.add_option("-s","--start",action="store",dest="start",
		help="start YYYY-MM-DD (default: 3-year-ago)")
	parser.add_option("-e","--end",action="store",dest="end",
		help="end YYYY-MM-DD (default: today)")
	parser.add_option("","--src",action="store",dest="src",default="iex",
		help="source [fred|yh|iex](default: iex)")
	parser.add_option("","--host",action="store",dest="hostname",default="localhost",
		help="db host (default: localhost)")
	parser.add_option("","--database",action="store",dest="dbname",default="ara",
		help="database (default: eSTAR_2)")
	parser.add_option("-t","--table",action="store",dest="tablename",
		help="db tablename (default: None)")
	parser.add_option("","--field",action="store",dest="field",default="*",
		help="database column field (default: *)")
	parser.add_option("","--instrument",action="store",dest="instrument",default="stock",
		help="instrument type [stock|macro] (default: None)")
	parser.add_option("-o","--output",action="store",dest="output",
		help="output type [json|csv|html] (default: None)")
	parser.add_option("-l","--lang",action="store",dest="lang",default="en",
		help="language (default: en)")
	parser.add_option("","--search",action="store",dest="search",
		help="SEARCH action (default: None)")
	parser.add_option("","--topic",action="store",dest="topic",
		help="TOPIC to search  (default: None)")
	parser.add_option("","--subtopic",action="store",dest="subtopic",
		help="SUBTOPIC (default: None)")
	parser.add_option("","--extra_js",action="store",dest="extraJS",
		help="extra JSON in DICT format.")
	parser.add_option("","--extra_xs",action="store",dest="extraXS",
		help="extra excutable string in k1=v1;k2=v2; format")
	parser.add_option("","--debug",action="store_true",dest="debugTF",default=False,
		help="debugging (default: False)")
	(options, args) = parser.parse_args()
	try:
		opts = vars(options)
		from _alan_str import extra_opts
		extra_opts(opts,xkey='extraJS',method='JS',updTF=True)
		extra_opts(opts,xkey='extraXS',method='XS',updTF=True)
		opts.pop('extraXS',None)
		opts.pop('extraJS',None)
	except Exception as e:
		sys.stderr.write("**ERROR:{} @{}\n".format(str(e),'opt_csv2plot'))
	return opts, args

def main():
	""" API for ALAN
		Usage: alanapi.py [option] SYMBOL ...
	"""
	pp = myPrettyPrinter(indent=4,width=20)
	xreq=os.getenv('REQUEST_METHOD')
	data=''
	if xreq in ('GET','POST') : # WEB MODE
			data=cgi_api()
	else:
		(opts, args)=opt_alanapi()
		pqint( (opts, args) ,file=sys.stderr)
		symLst = args if len(args)>0 else None
		fdLst = opts['field']
		opts.pop('field',None)
		sys.stderr.write("===START: {}:{}:{}\n".format(symLst,fdLst,opts))
		data=run_alanapi(symLst,fdLst,**opts)
		print(data)
	return data

if __name__ == '__main__':
	try:
		data = main()
	except Exception as e:
		sys.stderr.write("**ERROR:{} @ {}\n".format(str(e),'main'))
