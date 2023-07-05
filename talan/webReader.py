#!/usr/bin/env python3
'''Read data from WEB via `requests` [GET|POST] method
Usage of,
./webReader.py URL [JSON]
OR
./webReader.py AAPL 'dict(funcName="yhReader")'

Where:
JSON default value:
{ "funcName":"webReader",
  "opts": { "rtype":"json", "method":"get" }
}

Example,
#----- To read web data from FRED
./webReader.py 'https://api.stlouisfed.org/fred/series/observations?file_type=json&series_id=CPIAUCNS' $(cat ~/.fredapi.json)
#----- OR 
api_key=$(jq ".api_key" ~/.fredapi.json)
./webReader.py 'https://api.stlouisfed.org/fred/series/observations?' '{"api_key":'\"${api_key}\"',"file_type":"json","series_id":"CPIAUCNS","observation_start":"2022-07-01"}'
#----- OR to read web data from yahoo-finance
./webReader.py 'https://query2.finance.yahoo.com/v7/finance/spark?range=1d&interval=30m&indicators=close&includeTimestamps=false&includePrePost=false&corsDomain=finance.yahoo.com&.tsrc=finance' '{"symbols":"AAPL,IBM"}'
#----- OR 
./webReader.py 'https://query2.finance.yahoo.com/v7/finance/spark' '{"symbols":"AAPL","range":"1d","interval":"60m"}'
#----- OR to load a streaming file 
./webReader.py http://api1.beyondbond.com/downloads/grimm10-49_1.png {} stream get "${user},${pswd}"
#----- OR to load stock spark prices 
./webReader.py AAPL,TSM 'dict(funcName="yhReader")'
#----- OR 
python3 -c "from webReader import yhReader;df=yhReader(['AAPL','AMD'],types='spark');print(df)"
#----- OR 
python3 -c "from webReader import yhReader;df=yhReader(['AAPL','AMD'],types='chart');print(df)"
#----- OR 
python3 -c "from webReader import yhReader;df=yhReader(['AAPL','AMD'],types='quote');print(df)"

Last Mod.,
Sun 02 Jul 2023 06:52:03 PM EDT
'''
__usage__='\n'.join(__doc__.split('\n')[:11])
import sys
import requests
from requests.auth import HTTPBasicAuth as HA
import pandas as pd

headers={'Content-Type': 'text/html', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}

credentials={}

apiBase = 'https://query2.finance.yahoo.com'

def getCredentials(cookieUrl='https://fc.yahoo.com', crumbUrl=apiBase+'/v1/test/getcrumb'):
	cookies = requests.get(cookieUrl).cookies
	crumb = requests.get(url=crumbUrl, cookies=cookies, headers=headers).text
	return {'cookies': cookies, 'crumb': crumb}

def chart_json2df(res):
	jx=res["chart"]["result"][0]
	ticker=jx["meta"]["symbol"]
	epoch=jx["timestamp"]
	dlst=jx["indicators"]["quote"][0]
	dlst.update(epoch=jx["timestamp"])
	if "adjclose" in jx["indicators"]:
		adjusted=jx["indicators"]["adjclose"][0]["adjclose"]
	else:
		adjusted=dlst["close"]
	dlst.update(epoch=epoch,adjusted=adjusted)
	dx=pd.DataFrame(data=dlst)
	dx['ticker']=ticker
	dx.set_index(pd.DatetimeIndex(dx['epoch'].apply(pd.Timestamp.fromtimestamp)),inplace=True)
	return dx

def spark_json2df(res):
	jlst=res["spark"]["result"]
	df=pd.DataFrame()	
	for jx in jlst:
		epoch=jx["response"][0]["timestamp"]
		close=jx["response"][0]["indicators"]["quote"][0]["close"]
		ticker=jx["symbol"]
		dx=pd.DataFrame(data=dict(epoch=epoch,close=close,ticker=ticker))
		dx.set_index(pd.DatetimeIndex(dx['epoch'].apply(pd.Timestamp.fromtimestamp)),inplace=True)
		df = pd.concat([df,dx])
	df.index.name="DATE"
	df=df.drop(["epoch"],axis=1)
	df["pbdate"]=pd.Series((df.index)).apply(lambda x: pd.Timestamp.strftime(x,"%Y%m%d")).values
	return df

def yh_chart(tkLst=['AAPL'],debugTF=False,**opts):
	if debugTF:
		sys.stderr.write("==yh_chart inputs:{}\n".format(locals()))
	urx="https://query2.finance.yahoo.com/v8/finance/chart/{}"
	parat=dict(interval='1d',range='7d')
	pLst=['interval','range','fields','period1','period2','includeAdjustedClose']
	parax={k:v for k,v in opts.items() if k in pLst}
	parat.update(parax)
	df=pd.DataFrame()	
	for tx in tkLst:
		url=urx.format(tx)
		res=webReader(url,pjson=parat,debugTF=debugTF,**opts)
		dx = chart_json2df(res)
		df = pd.concat([df,dx])
	df.index.name="DATE"
	df=df.drop(["epoch"],axis=1)
	df["pbdate"]=pd.Series((df.index)).apply(lambda x: pd.Timestamp.strftime(x,"%Y%m%d")).values
	if parat.get('interval','')[-1:]=="m":
		df["epochs"]=pd.Series((df.index)).apply(lambda x: pd.Timestamp.strftime(x,"%s000")).values
	if not opts.get('dfTF',False):
		return df.to_dict(orient='records')
	return df

def yh_spark(tkLst=['AAPL'],debugTF=False,**opts):
	if debugTF:
		sys.stderr.write("==yh_spark inputs:{}\n".format(locals()))
	url="https://query2.finance.yahoo.com/v7/finance/spark?"
	parat=dict(symbols=",".join(tkLst),interval='1d',range='7d')
	pLst=['symbols','interval','range','fields','indicators','period1','period2']
	parax={k:v for k,v in opts.items() if k in pLst}
	parat.update(parax)
	res=webReader(url,pjson=parat,debugTF=debugTF,**opts)
	df=spark_json2df(res)
	if parat.get('interval','')[-1:]=="m":
		df["epochs"]=pd.Series((df.index)).apply(lambda x: pd.Timestamp.strftime(x,"%s000")).values
	return df

def yh_quote(tkLst=['AAPL'],debugTF=False,**opts):
	if debugTF:
		sys.stderr.write("==yh_quote inputs:{}\n".format(locals()))
	url="https://query2.finance.yahoo.com/v7/finance/quote?"
	parat=dict(symbols=",".join(tkLst))
	pLst=['symbols','fields','formatted']
	parax={k:v for k,v in opts.items() if k in pLst}
	parat.update(parax)
	res=webReader(url,pjson=parat,debugTF=debugTF,**opts)
	jlst=res["quoteResponse"]["result"]
	if opts.get('dfTF',False):
		return pd.DataFrame(jlst)
	else:
		return jlst

def yhReader(tkLst,types='spark',debugTF=False,**opts):
	if isinstance(tkLst,str):
		tkLst=tkLst.split(',')
	typ=types.lower()
	if typ =='chart':
		return yh_chart(tkLst=tkLst,debugTF=debugTF,**opts)
	elif typ =='spark':
		return yh_spark(tkLst=tkLst,debugTF=debugTF,**opts)
	elif typ =='quote':
		return yh_quote(tkLst=tkLst,debugTF=debugTF,**opts)
	return {}

def webReader(url,pjson={},rtype='json',method='get',sessionTF=True,debugTF=False,**opts):
	global credentials
	if not url:
		return {}
	user, pswd = [opts.pop(x,'') for x in ['user','pswd'] ]
	if debugTF:
		sys.stderr.write("==webReader inputs:{}\n".format(locals()))
	rq = requests.Session() if sessionTF else requests
	rqOpts={}
	if 'quote' in url and 'quoteS' not in url:
		if not credentials:
			credentials=getCredentials()
		crumb,cookies = (credentials['crumb'],credentials['cookies'])
		pjson.update(crumb=crumb)
		rqOpts.update(cookies=cookies)
	if (user and pswd):
		rqOpts.update(auth=HA(user,pswd))
	if debugTF:
		sys.stderr.write(" --requests URL:{}\n --params:{}\n --rqOpts:{}\n".format(url,pjson,rqOpts))
	if method.lower()=='post':
		ret = rq.post(url,data=pjson,headers=headers,**rqOpts)
	else:
		ret = rq.get(url,params=pjson,headers=headers,**rqOpts)
	res = ret.json() if rtype.lower()=='json' else ret.text
	return res
	
def streamReader(url,pjson={},rtype='json',method='get',sessionTF=True,debugTF=False,**opts):
	from urllib.parse import urlparse
	import shutil
	if not url:
		return {}
	stream = opts.pop('stream',True)
	user, pswd,filepath = [opts.pop(x,'') for x in ['user','pswd','filepath'] ]
	if debugTF:
		sys.stderr.write("==streamReader inputs:{}\n".format(locals()))
	if not filepath:
		o=urlparse(url)
		filepath=o.path.split('/')[-1]
	rq = requests.Session() if sessionTF else requests
	rqOpts={}
	if stream:
		rqOpts.update(stream=stream)
	if (user and pswd):
		rqOpts.update(auth=HA(user,pswd))
	if debugTF:
		sys.stderr.write(" --requests URL:{}\n --params:{}\n --rqOpts:{}\n".format(url,pjson,rqOpts))
	if method.lower()=='post':
		ret = rq.post(url,data=pjson,headers=headers,**rqOpts)
	else:
		ret = rq.get(url,params=pjson,headers=headers,**rqOpts)
	if ret.status_code == 200:
		with open(filepath, 'wb') as f:
			ret.raw.decode_content = True
			shutil.copyfileobj(ret.raw, f)  
	else:
		print(ret.status_code,ret.raise_for_status(),file=sys.stderr)
	del ret
	return filepath
	
def mainTst():
	pjson={}
	argc=len(sys.argv)
	if argc>1:
		url = sys.argv[1]
	else:
		sys.exit(__usage__)
	try:
		pjson=eval(sys.argv[2]) if sys.argv[2:] else {}
	except Exception as e:
		sys.stderr.write("**ERROR: Invalid JSON, {}\n".format(e))
	opts = pjson.pop('opts',{})
	funcName = pjson.pop('funcName','webReader')
	if funcName in globals() and hasattr(globals()[funcName],'__call__'):
		funcArg=globals()[funcName]
	else:
		sys.stderr.write("**WARNINGS: Invalid function:{}\n".format(funcName))
		sys.exit(__usage__)

	if funcArg in [streamReader,webReader]:
		res=funcArg(url,pjson=pjson,**opts)
		if 'spark' in url:
			res = spark_json2df(res)
		elif 'chart' in url:
			res = chart_json2df(res)
	else:
		if opts:
			pjson.update(opts)
		res=funcArg(url,**pjson)
	return res

if __name__ == '__main__' :
	try:
		sys.exit(mainTst())
	except Exception as e:
		sys.stderr.write("**ERROR: mainTst {}\n".format(e))
		sys.exit(__usage__)

