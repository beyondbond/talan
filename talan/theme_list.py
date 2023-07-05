#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
#- Description:
Update sp500_component table in pgDB
Update dow_component table in pgDB
Update nasdaq_ipos table in MDB
Update madmoney_hist table in MDB
#- Available methods:
  sp500_component dow_component madmoney_hist nasdaq_ipos
#- Usage of:
python3 theme_list.py sp500_component
python3 theme_list.py dow_component
python3 theme_list.py nasdaq_ipos
python3 theme_list.py madmoney_hist --extra_xs='airdate="07"'
#- OR
python3 theme_list.py nasdaq_ipos --extra_xs='month="2020-07"'
OR check ipo for the current month
python3 theme_list.py nasdaq_ipos 
#- OR
python3 theme_list.py madmoney_hist --extra_xs='airdate="2020-02-15"'
#- OR for the last 180 days
python3 theme_list.py madmoney_hist --extra_xs='airdate="180"'
#- OR for the last 7 days
python3 theme_list.py madmoney_hist --extra_xs='airdate="07"'
#- OR for ALL history
python3 theme_list.py madmoney_hist --extra_xs='airdate="%"'

#- Methods available :
def sp500_component
def dow_component
def madmoney_hist
def nasdaq_ipos
def madmoney_screener (DEPRECATED)
def spy_component (DEPRECATED)
def nasdaq_spos (DEPRECATED)
def spy_component (DEPRECATED)

#- Ref Sites:
https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
https://madmoney.thestreet.com/screener/index.cfm?stocks&showrows=2000
https://us.spdrs.com/site-content/xls/SPY_All_Holdings.xls?fund=SPY&docname=All+Holdings&onyx_code1=&onyx_code2=
https://www.nasdaq.com/markets/ipos/activity.aspx?tab=filings&month=2019-07
https://api.nasdaq.com/api/ipo/calendar?date=2019-10

Last mod., 
Fri Jul 10 11:58:36 EDT 2020
'''
import sys
import pandas as pd
from optparse import OptionParser
from sqlalchemy import create_engine
import datetime
import requests
import json
import re
from pymongo import MongoClient
from bs4 import BeautifulSoup, element as bs4Element
from _alan_calc import save2pgdb,conn2mgdb,renameDict
from _alan_str import write2mdb,insert_mdb,upsert_mdb

# to deal with ç u'\xe7' character
if sys.version_info.major == 2:
	reload(sys)
	sys.setdefaultencoding('utf8')
	from urlparse import parse_qs
else:
	from urllib.parse import parse_qs


def epoch2ymd(x,s=1000,fmt='%Y%m%d'):
	'''
	convert datetime from Unix epoch to YYYYMMDD 
	'''
	return datetime.datetime.fromtimestamp(int(x/s)).strftime(fmt)

def getKeyVal(opts={},key='',val=None):
	'''
	Get value from dict 'opts' default to 'val'
	Example:
	  saveDB=getKeyVal(opts,key='saveDB',val=True)
	'''
	if not all([key,opts]):
		return None
	return opts[key] if key in opts else val

def dow_component(hostname='localhost',dbname='ara',tablename='dow_component',debugTF=False,**kwargs): 
	'''
	Update pgDB Table: dow_component
	Get DOW30 list from wiki
	and save to both mongoDB and postgreSQL
	DB Table: dow_component
	ref site: https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average
	'''
	url='https://en.wikipedia.org/wiki/Dow_Jones_Industrial_Average'
	saveDB=getKeyVal(kwargs,key='saveDB',val=True)
	if debugTF:
		sys.stderr.write('URL:{url}\n'.format(url=url))
	try:
		df = pd.read_html(url,attrs={'id':'constituents'},index_col=False,header=0)[0]
		if len(df)<30:
			return {}
		df['ticker'] = [s.replace('.','-') for s in df['Symbol']]
		df.columns = [re.sub('[(), ]', '',x) for x in df.columns]
	except Exception as e:
		sys.stderr.write("**ERROR: dow_component:{}\n".format(str(e)))
		return {}
	if saveDB:
		save2pgdb(df,db=dbname,tablename=tablename)
		mobj,_,_ = insert_mdb(df,clientM=None,dbname=dbname,tablename=tablename,wmode='replace')
	return df

def sp500_component(hostname='localhost',dbname='ara',tablename='sp500_component',debugTF=False,**kwargs): 
	'''
	Update pgDB Table: sp500_component
	Get Sp500 list from wiki
	and save to both mongoDB and postgreSQL
	ref site: https://en.wikipedia.org/wiki/List_of_S%26P_500_companies
	'''
	saveDB=getKeyVal(kwargs,key='saveDB',val=True)
	url='https://en.wikipedia.org/wiki/List_of_S%26P_500_companies'
	if debugTF:
		sys.stderr.write('URL:{url}\n'.format(url=url))
	try:
		df = pd.read_html(url,attrs={'id':'constituents'},index_col=False,header=0)[0]
		if len(df)<500:
			return {}
		df['ticker'] = [s.replace('.','-') for s in df['Symbol']]
		save2pgdb(df,db=dbname,tablename=tablename)
	except Exception as e:
		sys.stderr.write('**ERROR: sp500_component:{}\n'.format(str(e)))
		return {}
	if saveDB:
		save2pgdb(df,db=dbname,tablename=tablename)
		mobj,_,_ = insert_mdb(df,clientM=None,dbname=dbname,tablename=tablename,wmode='replace')
	return df

# DEPRECATED
def spy_component(hostname='localhost',dbname='ara',tablename='spy_component',debugTF=False,**kwargs): 
	'''
	Update pgDB Table: spy_list
	get SPY list in daily basis
	ref table: spy_list
	ref site: https://us.spdrs.com/site-content/xls/SPY_All_Holdings.xls?fund=SPY&docname=All+Holdings&onyx_code1=&onyx_code2=
	'''
	url='https://us.spdrs.com/site-content/xls/SPY_All_Holdings.xls?fund=SPY&docname=All+Holdings&onyx_code1=&onyx_code2='
	if debugTF:
		sys.stderr.write('URL:{url}\n'.format(url=url))
	try:
		df = pd.read_excel(url,index_col=False,header=3)
		if len(df)<500:
			return {}
		df.dropna(subset=['Sector'],inplace=True)
		df = df.drop(df[df['Identifier']=='CASH_USD'].index)
		df = df.reset_index(drop=True)
		df['ticker'] = [s.replace('.','-') for s in df['Identifier']]
		df.at[df['ticker']=='CCL-U','ticker'] = 'CCL'
	except Exception as e:
		sys.stderr.write('**ERROR: spy_component:{}\n'.format(str(e)))
		return {}
	mobj,_,_ = write2mdb(df,clientM=None,dbname=dbname,tablename=tablename,zpk={'*'})
	return df

def add_sector_industry(df=[]):
	from yh_chart import runOTF
	from _alan_calc import subDict
	if len(df)<1:
		return []
	tkLst=df['ticker'].values
	datax=runOTF(list(df['ticker'].values),'yh_financials',modules="summaryProfile",dbname='ara',tablename="yh_summaryProfile",zpk={'ticker'},deltaTolerance=8640000)
	if len(datax)<1:
		return df
	dg =  subDict(pd.DataFrame(datax),['ticker','sector','industry'])
	df = df.merge(dg,on='ticker',how='left')
	return df

def nasdaq_ipos(hostname='localhost',dbname='ara',tablename='nasdaq_ipos',tab='filing',month='',debugTF=False,**kwargs): 
	'''
	Update MDB Table: nasdaq_ipos
	get recent IPOs
	ref table: nasdaq_ipos
	ref site: https://api.nasdaq.com/api/ipo/calendar?date=2019-10
	'''
	if len(month)<1:
		month = datetime.datetime.now().strftime('%Y-%m')
	urx='https://api.nasdaq.com/api/ipo/calendar?date={month}'
	url = urx.format(month=month)
	sys.stderr.write(' --URL:{}\n'.format(url))
	headers={'Content-Type': 'application/json', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
	try:
		#ret =requests.get(url,timeout=5)
		ret=requests.Session().get(url,headers=headers)
		jsx=ret.json()
		actions=getKeyVal(kwargs,key='actions',val='priced')
		data = jsx['data'][actions]['rows']
		if not data:
			actions='filed'
			data = jsx['data'][actions]['rows']
			if not data:
				return {}
		colX=jsx['data'][actions]['headers']
		df = pd.DataFrame(data)
		df = renameDict(df,colX)
		if debugTF:
			sys.stderr.write(' --DATA:\n{}\n'.format(data))
			sys.stderr.write(' --df:\n{}\n'.format(df))
		if "Exchange/ Market" in df:
			df=df.rename(columns={"Exchange/ Market":"Market"})
		if debugTF:
			sys.stderr.write('COLUMNS:{}\n'.format(df.columns))
		df.dropna(subset=['Symbol'],inplace=True)
		if len(df)<1:
			return {}
		df['ticker'] = [s.replace('.','-') for s in df['Symbol']]
		if 'Offer Amount' in df:
			df['offer'] = [float(s.replace('$','').replace(',','')) for s in df['Offer Amount']]
			df = df.drop(['Offer Amount'], axis=1)
		if 'Date' in df:
			df['pbdate'] = [int(datetime.datetime.strptime(s,'%m/%d/%Y').strftime('%Y%m%d')) for s in df['Date']]
		elif 'Date Filed' in df:
			df['pbdate'] = [int(datetime.datetime.strptime(s,'%m/%d/%Y').strftime('%Y%m%d')) for s in df['Date Filed']]
		elif 'Date Priced' in df:
			df['pbdate'] = [int(datetime.datetime.strptime(s,'%m/%d/%Y').strftime('%Y%m%d')) for s in df['Date Priced']]

	except Exception as e:
		sys.stderr.write('**ERROR: nasdaq_ipos:{}\n'.format(str(e)))
		return {}
	df.columns = [x.replace(' ','').lower() for x in df.columns]
	df = add_sector_industry(df)
	mobj,_,_ = upsert_mdb(df,clientM=None,dbname=dbname,tablename=tablename,zpk={'ticker','pbdate','actions'})
	return df

def nasdaq_spos(hostname='localhost',dbname='ara',tablename='nasdaq_spos',debugTF=False,**kwargs): 
	return nasdaq_ipos(hostname=hostname,dbname=dbname,tablename=tablename,debugTF=debugTF,**kwargs)

def madmoney_hist(hostname='localhost',dbname='ara',tablename='madmoney_hist',airdate='180',pricehigh=1000,pricelow=0,sortby='airdate',showrows=2000,rawTF=False,saveDB=True,debugTF=False,**kwargs):
	return madmoney_screener(hostname=hostname,dbname=dbname,tablename=tablename,airdate=airdate,pricehigh=pricehigh,pricelow=pricelow,sortby=sortby,showrows=showrows,rawTF=rawTF,saveDB=saveDB,debugTF=debugTF,**kwargs)

def madmoney_screener(hostname='localhost',dbname='ara',tablename='madmoney_hist',airdate='180',pricehigh=1000,pricelow=0,sortby='airdate',showrows=2000,rawTF=False,saveDB=True,debugTF=False,**kwargs):
	'''
	Update MDB Table: madmoney_hist
	get madmoney list in daily basis
	ref table: madmoney_hist
	ref site: https://madmoney.thestreet.com/screener/index.cfm?showview=stocks&showrows=500
	'''
	sys.stderr.write('{}\n'.format(locals()))
	urx='https://madmoney.thestreet.com/screener/index.cfm?showview=stocks&showrows={showrows}&airdate={airdate}'
	CallD={'5':'buy','4':'positive','3':'hold','2':'negative','1':'sell'}
	SegmentD=dict(F='Featured Stock',D='Discussed Stock ',C='Callers Stock',I='Guest Interview',L='Lighting Round',M='Mail Bag',G='Game Plan',S='Sudden Death')
	url= urx.format(showrows=showrows,airdate=airdate)
	jd = dict(symbol='',airdate=airdate,called='%',industry='%',sector='%',segment='%',pricelow=pricelow,pricehigh=pricehigh,sortby=sortby)
		
	sys.stderr.write('URL:\n{}\nPOST:{}\n'.format(url,jd))
	try:
		#res = requests.get(url,timeout=10)
		res = requests.post(url,data=json.dumps(jd),timeout=10)
		if res.status_code!=200:
			sys.stderr.write('**HTTP: {} @ {}\n'.format(res.status_code,url))
			return {}
		xstr=res.content
		df = pd.read_html(xstr,attrs={'id':'stockTable'},index_col=False,header=0)[0]
		if len(df)<1 or pd.isnull(df.loc[0,'Company']):
			sys.stderr.write('**{} @ {}\n'.format("No sotcks were found...",url))
			return {}
		s = BeautifulSoup(xstr,'lxml')
		trLst=s.find_all('table')[0].find_all('tr')
		dd=[]
		for j,rwx in enumerate(trLst):
			if j<1:
				tagX='th' 
				tdLst = rwx.find_all(tagX)
				vHdr = [x.text for x in tdLst]
				continue
			else:
				tagX='td' 
			tdLst = rwx.find_all(tagX)
			vLst=[]
			if len(tdLst)<len(vHdr):
				continue
			for k,xTd in enumerate(tdLst):
				if isinstance(xTd.next,bs4Element.Tag) and xTd.next.has_attr('alt'):
					xv = xTd.next['alt']
				elif isinstance(xTd.next,bs4Element.Tag) and xTd.next.has_attr('href'):
					xv =  parse_qs(xTd.next['href'])['symbol'][0]
				else:
					xv = xTd.text
				vLst.append(xv)

			dx = dict(zip(vHdr,vLst))
			dd.append(dx)
		df=pd.DataFrame(dd)
	except Exception as e:
		sys.stderr.write('**ERROR: {} @{}\n'.format(str(e),'madmoney_screener()'))
		return {}
	if rawTF:
		return df
	try:
		df['CallDscript']=[CallD[x] for x in df['Call']]
		df['SegmentDscript']=[SegmentD[x] for x in df['Segment']]
		df['Price'] = df['Price'].apply(lambda x:float(x.strip('$')))
		mmdd = [int("".join(x.split('/'))) for x in df['Date']]
		tdate=datetime.datetime.today()
		cmmdd = int(tdate.strftime("%m%d"))
		cYr = tdate.year
		xYr = tdate.year -1
		pbdate = [(cYr if cmmdd>x else xYr)*10000 + x for x in mmdd]
		df['pbdate'] = pbdate
		df['Portfolio'] = df['Portfolio'].apply(lambda x: x.strip())
		df['ticker'] = [s.replace('.','-') for s in df['Portfolio']]
		df = add_sector_industry(df)
	except Exception as e:
		sys.stderr.write('**ERROR: {} @ PULLING {}\n'.format(str(e),url))
		return {}
		
	if saveDB:
		mobj,_,msg = upsert_mdb(df,clientM=None,dbname=dbname,tablename=tablename,zpk={'ticker','pbdate'})
		sys.stderr.write('==Save to: MDB:{}: {}\n'.format(tablename,msg))

	return df

def opt_theme_list(argv,retParser=False):
	""" command-line options initial setup
	    Arguments:
		argv:	list arguments, usually passed from sys.argv
		retParser:	OptionParser class return flag, default to False
	    Return: (options, args) tuple if retParser is False else OptionParser class 
	"""
	parser = OptionParser(usage="usage: %prog [option] METHOD", version="%prog 0.7",
		description="get sp500_component and save to MDB::sp500_component")
	parser.add_option("","--no_database_save",action="store_false",dest="saveDB",default=True,
		help="no save to database (default: save)")
	parser.add_option("","--extra_js",action="store",dest="extraJS",
		help="extra JSON in DICT format.")
	parser.add_option("","--extra_xs",action="store",dest="extraXS",
		help="extra excutable string in k1=v1;k2=v2; format")
	parser.add_option("","--debug",action="store_true",dest="debugTF",default=False,
		help="debugging (default: False)")
	(options, args) = parser.parse_args(argv[1:])
	if retParser is True:
		return parser
	opts = vars(options)
	try:
		from _alan_str import extra_opts
		extra_opts(opts,xkey='extraJS',method='JS',updTF=True)
		extra_opts(opts,xkey='extraXS',method='XS',updTF=True)
	except Exception as e:
		sys.stderr.write("**ERROR: {}\n".format(str(e)))
	return (opts, args)

##### MAIN PROGRAM #####
if __name__ == '__main__':
	opts, args = opt_theme_list(sys.argv,retParser=False)
	if len(args)>0 and args[0] in globals():
		funcName = args[0]
	else:
		funcName = 'sp500_component'

	if funcName in globals():
		funcArg=globals()[funcName]
		sys.stderr.write("==RUN: {}\n".format(funcArg))
		df = funcArg(**opts)
	else:
		exit(-1)
	if isinstance(df,pd.DataFrame):
		if len(df)<30:
			sys.stderr.write("{}\n".format(df.to_csv(index=False,sep="|")))
		else:
			sys.stderr.write("{}\n".format(df.head(2).to_csv(index=False,sep="|")))
			sys.stderr.write("{}\n".format(df.tail(2).to_csv(index=False,sep="|")))
			sys.stderr.write("Total rows:{}\n".format(len(df)))
