#!/usr/bin/env python3
'''Read data from WEB via `requests` [GET|POST] method
Usage of,
./webReader.py URL [JSON] [RTYPE] [METHOD]

Example,
#----- To read web data from FRED
./webReader.py 'https://api.stlouisfed.org/fred/series/observations?file_type=json&series_id=CPIAUCNS' $(cat ~/.fredapi.json)
#----- OR 
api_key=$(jq ".api_key" ~/.fredapi.json)
./webReader.py 'https://api.stlouisfed.org/fred/series/observations?' '{"api_key":'\"${api_key}\"',"file_type":"json","series_id":"CPIAUCNS","observation_start":"2022-07-01"}'
#----- OR to read web data from yahoo-finance
./webReader.py 'https://query1.finance.yahoo.com/v7/finance/spark?range=1d&interval=30m&indicators=close&includeTimestamps=false&includePrePost=false&corsDomain=finance.yahoo.com&.tsrc=finance' '{"symbols":"AAPL,IBM"}'
#----- OR 
./webReader.py 'https://query1.finance.yahoo.com/v7/finance/spark' '{"symbols":"AAPL","range":"1d","interval":"60m"}'
#----- OR to load a streaming file 
./webReader.py http://api1.beyondbond.com/downloads/grimm10-49_1.png {} stream get "${user},${pswd}"
#----- OR 
python3 -c "from webReader import yhReader;df=yhReader(['AAPL','AMD'],types='spark');print(df)"
#----- OR 
python3 -c "from webReader import yhReader;df=yhReader(['AAPL','AMD'],types='chart');print(df)"

Last Mod.,
Tue 11 Oct 2022 10:40:10 PM EDT
'''
import sys
import requests
from requests.auth import HTTPBasicAuth as HA
import pandas as pd

hds={'Content-Type': 'text/html', 'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}

def chart_json2df(res):
	jx=res["chart"]["result"][0]
	epoch=jx["timestamp"]
	close=jx["indicators"]["quote"][0]["close"]
	open=jx["indicators"]["quote"][0]["open"]
	high=jx["indicators"]["quote"][0]["high"]
	low=jx["indicators"]["quote"][0]["low"]
	volume=jx["indicators"]["quote"][0]["volume"]
	ticker=jx["meta"]["symbol"]
	if "adjclose" in jx["indicators"]:
		adjusted=jx["indicators"]["adjclose"][0]["adjclose"]
	else:
		adjusted=close
	dx=pd.DataFrame(data=dict(epoch=epoch,close=close,open=open,high=high,low=low,adjusted=adjusted,ticker=ticker))
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
	urx="https://query1.finance.yahoo.com/v8/finance/chart/{}"
	param=dict(interval='1d',range='7d')
	pLst=['interval','range','fields','period1','period2']
	data={k:v for k,v in opts.items() if k in pLst}
	param.update(data)
	df=pd.DataFrame()	
	for tx in tkLst:
		url=urx.format(tx)
		res=webReader(url,data=param,debugTF=debugTF,**opts)
		dx = chart_json2df(res)
		df = pd.concat([df,dx])
	df.index.name="DATE"
	df=df.drop(["epoch"],axis=1)
	df["pbdate"]=pd.Series((df.index)).apply(lambda x: pd.Timestamp.strftime(x,"%Y%m%d")).values
	return df

def yh_spark(tkLst=['AAPL'],debugTF=False,**opts):
	url="https://query1.finance.yahoo.com/v7/finance/spark?"
	param=dict(symbols=",".join(tkLst),interval='1d',range='7d')
	pLst=['symbols','interval','range','fields','period1','period2']
	data={k:v for k,v in opts.items() if k in pLst}
	param.update(data)
	res=webReader(url,data=param,debugTF=debugTF,**opts)
	df=spark_json2df(res)
	return df

def yh_quote(tkLst=['AAPL'],debugTF=False,**opts):
	url="https://query1.finance.yahoo.com/v7/finance/quote?"
	param=dict(symbols=",".join(tkLst))
	res=webReader(url,data=param,debugTF=debugTF,**opts)
	jlst=res["quoteResponse"]["result"]
	return pd.DataFrame(jlst)

def yhReader(tkLst=['AAPL'],types='spark',debugTF=False,**opts):
	typ=types.lower()
	if typ =='chart':
		return yh_chart(tkLst=tkLst,debugTF=debugTF,**opts)
	elif typ =='spark':
		return yh_spark(tkLst=tkLst,debugTF=debugTF,**opts)
	elif typ =='quote':
		return yh_quote(tkLst=tkLst,debugTF=debugTF,**opts)
	return {}

def webReader(url,data=None,rtype='json',method='get',headers=hds,sessionTF=True,user='',pswd='',**opts):
	if not url:
		return {}
	rq = requests.Session() if sessionTF else requests
	rqOpts={}
	if (user and pswd):
		rqOpts.update(auth=HA(user,pswd))
	if method.lower()=='post':
		ret = rq.post(url,data=data,headers=headers,**rqOpts)
	else:
		ret = rq.get(url,params=data,headers=headers,**rqOpts)
	res = ret.json() if rtype.lower()=='json' else ret.text
	return res
	
def streamReader(url,data=None,rtype='json',method='get',headers=hds,sessionTF=True,stream=True,filepath='',user='',pswd='',**opts):
	from urllib.parse import urlparse
	import shutil
	if not url:
		return {}
	if not filepath:
		o=urlparse(url)
		filepath=o.path.split('/')[-1]
	rq = requests.Session() if sessionTF else requests
	rqOpts={}
	if stream:
		rqOpts.update(stream=stream)
	if (user and pswd):
		rqOpts.update(auth=HA(user,pswd))
	if method.lower()=='post':
		ret = rq.post(url,data=data,headers=headers,**rqOpts)
	else:
		ret = rq.get(url,params=data,headers=headers,**rqOpts)
	if ret.status_code == 200:
		with open(filepath, 'wb') as f:
			ret.raw.decode_content = True
			shutil.copyfileobj(ret.raw, f)  
	else:
		print(ret.status_code,ret.raise_for_status(),file=sys.stderr)
	del ret
	return filepath
	
if __name__ == '__main__' :
	import json;
	argc=len(sys.argv)
	if argc>1:
		url = sys.argv[1]
	else:
		sys.stderr.write(__doc__)
		exit(1)
	try:
		print(sys.argv[2])
		data   = json.loads(sys.argv[2]) if argc>2 else None
	except Exception as e:
		sys.stderr.write("**ERROR: {}\n".format(e))
		data   = None
	rtype = sys.argv[3] if argc>3 else 'json'
	method = sys.argv[4] if argc>4 else 'get'
	user,pswd = (sys.argv[5] if argc>5 else ',').split(',')
	if rtype == 'stream':	
		res=streamReader(url,data=data,method=method,rtype=rtype,user=user,pswd=pswd)
	else:
		res=webReader(url,data=data,method=method,rtype=rtype,user=user,pswd=pswd)
		if 'spark' in url:
			df = spark_json2df(res)
			print(df)
	print(res,file=sys.stderr)
