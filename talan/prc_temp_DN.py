#!/usr/bin/env python3
""" Program: prc_temp_DN.py
    Description: Script to download Yahoo history
    Usage of:
	# from a list of SYMBOLS
		python prc_temp_DN.py SYMBOL1 SYMBOL2 ...
	OR
	# from stdin
		printf "SELECT ticker FROM mapping_ticker_cik where act_code=1"| psql.sh -d ara -At | python prc_temp_DN.py 
	to get [SYMBOL1,SYMBOL2,...] history
	and save them into [dbname]:prc_temp_yh
	then run prc_yh2hist.sql to insert additional to [prc_hist] (optional)
	OR
		printf "SELECT series FROM mapping_series_label"| psql.sh -d ara -At | python prc_temp_DN.py --table=macro_temp_fred
	then run fred2hist.sql to insert additional to [macro_hist_fred] (optional)
	OR
		cat currency.list | python prc_temp_DN.py -d ara --no_database_save
	to view history
    Note:
	To consolidate version for prc_temp_cn_DN.py & prc_temp_cn_DN.py.deprecated.
	This program will retire the following programs:
	prc_temp_av_DNLD.py
	prc_temp_batch.py
	prc_temp_cn.tradego.py
	prc_temp_DNLD.py
	prc_temp_yh_DNLD.py
	prc_temp_yh.py
    add '-' for SYMBOL1 as input from stdin
    direct use _alan_calc.data_from_web function 
    Last mod., Tue Apr 16 09:18:04 EDT 2019
    Last mod., Mon Oct 11 13:05:32 EDT 2021
	change `days` to string to allow ['1d','1mo','1y'] options
    Last mod., Tue 04 Jul 2023 04:02:56 PM EDT
"""
import sys
from optparse import OptionParser
import datetime
import pandas as pd
from sqlalchemy import create_engine
#from _alan_calc import data_from_web

def yh_download(symbol,ranged='1d',period1=None,period2=None,**optx):
	debugTF=optx.pop('debugTF',False)
	if debugTF:
		sys.stderr.write("===yh_download inputs: {}\n".format(locals()))
	urx="https://query2.finance.yahoo.com/v7/finance/download/{}"
	url=urx.format(symbol)
	
	if not any([period1,period2]) and ranged:
		url+='?range={}'.format(ranged)
	elif period1 and not period2:
		period2=pd.Timestamp.now().strftime("%F")

	if all([period1,period2]):
		period1=pd.Timestamp(period1+" 00:00:00EDT").strftime("%s")
		period2=pd.Timestamp(period2+" 23:59:59EDT").strftime("%s")
		url+='?period1={}'.format(period1)
		url+='&period2={}'.format(period2)

	if debugTF:
		sys.stderr.write(" --URL: {}\n".format(url))

	df=pd.read_csv(url)
	clx=[x.lower().replace('adj close','adjusted') for x in df.columns]
	df.columns=clx
	df['date']=[int(x.replace('-','')) for x in df['date']]
	df['ticker']=symbol
	if debugTF:
		sys.stderr.write(" --DF:\n{}\n".format(df.tail(3)))
	df.rename(columns={'date':'pbdate','ticker':'name'},inplace=True)
	clx=['open','high','low','close','volume','adjusted','pbdate','name']
	return df[clx]

def batch_prc_temp(tkLst,dbname='ara',output=None,tablename='prc_temp_yh',
	src='yh',days='1d',end=None,hostname='localhost',wmode='replace',
	tsTF=True,sep='|',indexTF=False,debugTF=False,saveDB=False,start=None):
	""" Get yahoo price history via [pandas_datareader.data] 
		from a list of tickers:[tkLst]
		and save them into table:[tablename] and database URL: [dbURL]
	"""
	if debugTF:
		sys.stderr.write("===batch_prc_temp inputs: {}".format( locals())+'\n')
	engine = None
	btime = datetime.datetime.now()
	sys.stderr.write("BEGIN----- @ {} -----BEGIN".format(btime)+'\n')
	rmode= wmode
	dm=pd.DataFrame()
	for i,ticker in enumerate(tkLst,1):
		sys.stderr.write(" --{}. {} ...".format(i,ticker)+'\n')
		try:
			symbol=ticker.upper()
			#df=data_from_web(symbol,start=start,end=end,days=days,src=src,debugTF=debugTF)
			df=yh_download(symbol,period1=start,period2=end,ranged=days,debugTF=debugTF)
			if df is None or len(df)<1:
				continue
			dm = pd.concat([dm,df])
			if not engine and all([saveDB,hostname,dbname]):
				dbURL='postgresql://sfdbo@{}:5432/{}'.format(hostname,dbname)
				engine = create_engine(dbURL) 
			if saveDB and engine:
				df.to_sql(tablename,engine,schema='public',index=False,if_exists=rmode)
				rmode= "append"
			sys.stderr.write(" --{}. {} DF({}) Done\n".format(i,ticker,len(df)))
			if debugTF:
				sys.stderr.write("\n{}".format( df.columns.values)+'\n')
				sys.stderr.write("{} {}".format( df.values[0],0)+'\n')
				if len(df)>1:
					sys.stderr.write("{} {}".format( df.values[-1],len(df)-1)+'\n')
		except Exception as e:
			sys.stderr.write( "***ERROR {}:{} @ prc_temp_DN.batch_prc_temp():{}".format(i,symbol,str(e))+'\n')
			continue

	etime = datetime.datetime.now()
	sys.stderr.write(" --Run time: {}".format(etime-btime)+'\n')
	sys.stderr.write("END------- @ {} -------END".format(etime)+'\n')
	if(engine is not None) :
		engine.dispose()
	if output=='csv' and len(dm)>0:
		sys.stdout.write("{}".format(dm.to_csv(index=indexTF,sep=sep))) 
	elif output=='dict' and len(dm)>0:
		sys.stdout.write("{}\n".format(dm.to_dict(orient='records'))) 
	elif output=='json' and len(dm)>0:
		sys.stdout.write("{}\n".format(dm.to_json(orient='records'))) 
	elif output=='html' and len(dm)>0:
		sys.stdout.write("{}\n".format(dm.to_html(index=indexTF))) 
	elif output=='string' and len(dm)>0:
		sys.stdout.write("{}\n".format(dm.to_string(index=indexTF))) 
	return dm

def opt_prc_temp_DN(argv,retParser=False):
	""" command-line options initial setup
	    Arguments:
		argv:   list arguments, usually passed from sys.argv
		retParser:      OptionParser class return flag, default to False
	    Return: (options, args) tuple if retParser is False else OptionParser class
	"""
	parser = OptionParser(usage="usage: %prog [option] SYMBOL1 ...", version="%prog 0.65",
		description="Script to download Yahoo/FRED history")
	parser.add_option("","--days",action="store",dest="days",default='1d',
		help="number of days from endDate (default: 1d)")
	parser.add_option("-s","--start",action="store",dest="start",
		help="start YYYY-MM-DD (default: None)")
	parser.add_option("-e","--end",action="store",dest="end",
		help="end YYYY-MM-DD (default: None)")
	parser.add_option("","--src",action="store",dest="src",default="yh",
		help="source [fred|iex|yahoo](default: yh)")
	parser.add_option("-d","--database",action="store",dest="dbname",default="ara",
		help="database (default: ara)")
	parser.add_option("","--host",action="store",dest="hostname",default="localhost",
		help="db host (default: localhost)")
	parser.add_option("-t","--table",action="store",dest="tablename",default="prc_temp_yh",
		help="db tablename (default: prc_temp_yh)")
	parser.add_option("-w","--wmode",action="store",dest="wmode",default="replace",
		help="db table write-mode [replace|append] (default: replace)")
	parser.add_option("","--no_database_save",action="store_false",dest="saveDB",default=True,
		help="no save to database (default: save to database)")
	parser.add_option("-o","--output",action="store",dest="output",
		help="OUTPUT type [csv|html|json] (default: no output)")
	parser.add_option("","--no_datetimeindex",action="store_false",dest="tsTF",default=True,
		help="no datetime index (default: use datetime)")
	parser.add_option("","--show_index",action="store_true",dest="indexTF",default=False,
		help="show index (default: False) Note, OUTPUT ONLY")
	parser.add_option("","--sep",action="store",dest="sep",default="|",
		help="output field separator (default: |) Note, OUTPUT ONLY")
	parser.add_option("","--debug",action="store_true",dest="debugTF",default=False,
		help="debugging (default: False)")
	(options, args) = parser.parse_args(argv[1:])
	if retParser is True:
		return parser
	return (vars(options), args)

if __name__ == '__main__':
	(options, args)=opt_prc_temp_DN(sys.argv)
	if len(args)==0 or (len(args)==1 and args[0]=='-'):
		sys.stderr.write("\nRead from pipe\n"+'\n')
		tkLst = sys.stdin.read().strip().split()
	elif len(args)==1 and ',' in args[0]:
		tkLst = args[0].strip().split(',')
	else:
		tkLst = args
		options['saveDB']=False
	r = batch_prc_temp(tkLst,**options)
