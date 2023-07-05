#!/usr/bin/env python3
# -*- coding: utf-8 -*-
'''
DEPRECATED, use ticker2cik.py for sec.gov edgar related info
Get [CIK,SIC,Company] info from [TICKER] via
http://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&Find=Search&owner=exclude&action=getcompany&output=atom
Get GIC [Sector] via
https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=summaryProfile'
Convert chinese [company_cn] via tencent site: http://qt.gtimg.cn/q=usAAPL
http://qt.gtimg.cn/q=us{ticker}

Using feedparser
[feed] keys:
['addresses', 'links', 'address', 'updated', 'assigned-sic', 'id', 'updated_parsed', 'city', 'zip', 'author', 'title_detail', 'state', 'state-of-incorporation', 'conformed-name', 'state-location-href', 'street1', 'assigned-sic-desc', 'phone', 'assigned-sic-href', 'link', 'authors', 'author_detail', 'ticker_sec', 'cik-href', 'fiscal-year-end', 'cik', 'title', 'guidislink', 'company-info', 'assitant-director', 'state-location']

Last mod., Wed Jul 17 10:07:29 EDT 2019
by Ted
'''

import sys
import requests
import feedparser
import pandas as pd
from sqlalchemy import create_engine
if sys.version_info.major == 2:
	reload(sys)
	sys.setdefaultencoding('utf8')
headers={'Content-Type': 'text/html', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}


def subDict(M,K=[],reverseTF=False):
	"""
	return a subset of M that matches K keys
	OR
	if reverse is True
	a subset of M that does not match K keys
	"""
	if reverseTF is True: # invert-match, select non-matching [kyLst] keys
		return { ky:va for ky,va in M.items() if ky not in K }
	else:
		return { ky:va for ky,va in M.items() if ky in K }

# ticker to get [CIK,SIC,Company] info via sec-edgar site
def get_company_info(ticker):
	'''
	Get [CIK,SIC,Company] info from [TICKER] via
	http://www.sec.gov/cgi-bin/browse-edgar?CIK={ticker}&Find=Search&owner=exclude&action=getcompany&output=atom
	'''
	tkX=ticker.upper().replace('-','').replace('.','')
	urx = 'http://www.sec.gov/cgi-bin/browse-edgar?CIK={}&Find=Search&owner=exclude&action=getcompany&output=atom'
	url = urx.format(tkX)
	d = feedparser.parse(url)
	if 'cik' in d.feed:
		d.feed['ticker_sec'] = tkX
		d.feed['ticker'] = ticker
	return d

def parse_feed(f):
	vky=dict(ticker="ticker",ticker_sec="ticker_sec",cik="cik",
		company="conformed-name",sic="assigned-sic",yymm="fiscal-year-end")
	a={}
	for (j,(xk,xv)) in enumerate(vky.items()) :
		if f.has_key(xv):
			a[xk]=f[xv]
		else:
			a[xk]=''
		if xk in ["cik","sic","yymm"]:
			a[xk]=int(a[xk]) if len(a[xk])>0 else None
		elif xk in ["company"]:
			a[xk]=a[xk].upper()
	return a

def ticker2cik(ticker):
	tkX=ticker.upper()
	d = get_company_info(tkX)
	if d.feed.has_key('cik') is False :
		return {}
	f = parse_feed(d.feed)
	return f

def ticker_mapping_batch(tkLst,debugTF=False):
	vf=[]
	for tkX in tkLst:
		f=fst=fcn={}
		# GET cik, sic info
		try:
			f = ticker2cik(tkX)
			if not f:
				f.update(cik=-999999,sic=-999,yymm=1231,ticker_sec=tkX)	
		except Exception as e:
			errmsg="**ERROR: {} of {} @ {}\n".format(str(e),tkX,'ticker_mapping_batch')
			sys.stderr.write(errmsg)
			f.update(cik=-999999,sic=-999,yymm=1231,ticker_sec=tkX)	
			#continue
		# GET sector info
		try:
			fst = ticker2sector(tkX)
			if fst:
				fst['sector_alias'] = fst['sector']
				f.update(subDict(fst,['sector_alias','industry']))
			else:
				f['sector_alias'] = f['industry'] = ''
		except Exception as e:
			errmsg="**ERROR: {} of {} @ {}\n".format(str(e),tkX,'running ticker2sector')
			sys.stderr.write(errmsg)
		# GET company_cn info
		try:
			fcn = ticker2cn(tkX)
			if fcn:
				f.update(fcn)
			else:
				f['company_cn'] = txt2tw(f['company'])
		except Exception as e:
			errmsg="**ERROR: {} of {} @ {}\n".format(str(e),tkX,'running ticker2cn')
			sys.stderr.write(errmsg)
			continue
		if f:
			sys.stderr.write("{}\n".format(f))
			vf.append(f)
		
	return vf

def write2db(df,engine=None,dbname='ara',tablename='',rmode='replace'):
	if not tablename:
		return df
	if not engine:
		engine = create_engine('postgresql://sfdbo@localhost:5432/'+dbname)
	df.to_sql(tablename,engine,index=False,schema='public',if_exists=rmode)
	engine.dispose()
	return df

def txt2twOLD(s,dest='zh-tw'):
	from googletrans import Translator
	tranx=Translator().translate
	return tranx(s,dest=dest).text

def txt2tw(dscr='',src='en',dest='zh-TW'):
	from google_trans_new import google_translator as Translator
	import html
	dscr =html.unescape(dscr)
	dscr = str(dscr.strip()+"\n")
	if len(dscr)<1:
		return dscr
	try:
		newd = Translator().translate(dscr,lang_src=src,lang_tgt=dest)
		return newd
	except Exception as e:
		sys.stderr.write("**ERROR: @{} of {}\nINPUT:\n{}\n".format("txt2tw",str(e),dscr))
		return ''

# ticker to get chinese 'company_cn' via http://qt.gtimg.cn
def ticker2cn(ticker,urx='http://qt.gtimg.cn/q=us{}',debugTF=False):
	''' 
	To get company name in chinese based on ticker 'ticker'
	Return dict {ticker,company,company_cn}
	'''
	r=requests.get(urx.format(ticker.upper()))
	d = r.text.split('~')
	if len(d)<2:
		return {}
	company_cn = d[1]
	company = d[46]
	if debugTF:
		sys.stderr.write("{}|{}\n".format(ticker,company_cn))
	try:
		company_cn = txt2tw(company_cn)
	except Exception as e:
		sys.stderr.write("**ERROR: {} @ {}\n".format(str(e),"ticker2cn"))
	da = dict(zip(("ticker","company_cn","company"),(ticker,company_cn,company)))
	return da

# ticker to get 'sector' via yahoo finance site
def ticker2sector(ticker,urx='',debugTF=False):
	'''
	Get GIC [Sector] via
	https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=summaryProfile'
	'''
	if not urx:
		urx='https://query2.finance.yahoo.com/v11/finance/quoteSummary/{ticker}?modules=summaryProfile'
	try:
		r = requests.Session().get(urx.format(ticker=ticker),headers=headers)
		js = r.json()
		jd = js["quoteSummary"]["result"][0]['summaryProfile']
	except Exception as e:
		sys.stderr.write("**ERROR: {} @ {}\n".format(str(e),'ticker2sector'))
		return {}
	return jd

def ticker_mapping(tkLst,saveDB=False):
	try:
		dd = ticker_mapping_batch(tkLst)
		if len(dd)<1:
			return {}
		df = pd.DataFrame(dd)
		write2db(df,tablename='ticker_mapping_temp')
	except Exception as e:
		sys.stderr.write("**ERROR: {}\n".format(str(e)))
		return {}
	return df

if __name__ == '__main__':
	args=sys.argv[1:]
	if len(args)<1 or args[0]=='-':
		tkLst = sys.stdin.read().split()
		saveDB=True
	else:
		tkLst=args
		saveDB=False
	dd = ticker_mapping(tkLst,saveDB=saveDB)
	if len(dd)>0:
		sys.stdout.write("{}\n".format(dd.to_csv(index=False,sep='|')))
