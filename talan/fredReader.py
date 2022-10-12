#!/usr/bin/env python3
''' Get series/observations from FRED site
Usage of,
fredSeries.py SERIES [ADDI] [OB_START] [UNITS] 

example,
fredReader.py CPIAUCNS
OR
fredReader.py CPIAUCNS observations 2022-01-02 
OR direct-function-call
python3 -c 'from fredReader import fredReader;df=fredReader("CPIAUCNS",units="pc1",observation_start="2022-01-01");print(df);'

Ref site:
    fred/series - Get an economic data series.
    fred/series/categories - Get the categories for an economic data series.
    fred/series/observations - Get the observations or data values for an economic data series.
    fred/series/release - Get the release for an economic data series.
    fred/series/search - Get economic data series that match keywords.
    fred/series/search/tags - Get the tags for a series search.
    fred/series/search/related_tags - Get the related tags for a series search.
    fred/series/tags - Get the tags for an economic data series.
    fred/series/updates - Get economic data series sorted by when observations were updated on the FRED® server.
    fred/series/vintagedates - Get the latest dates of the series were revised or new data values were released.

'''
import sys
import requests, datetime
import pandas as pd
import numpy as np
import json

def fredReader(series_id,**optx):
	try:
		dropnaTF=optx.pop('dropnaTF',True)
		series_id=series_id.upper()
		d=fredSeries(series_id,**optx)
		df=pd.DataFrame(d["observations"],columns=['date','value'])
		df.set_index(pd.DatetimeIndex(df['date']),inplace=True)
		df.index.name='DATE'
		df['pbdate']=[int(x.strftime("%Y%m%d")) for x in df.index]
		df['series']=series_id
		df['value']=pd.to_numeric(df['value'],errors='coerce')
		df=df[['series','value','pbdate']]
		if dropnaTF:
			df.dropna(inplace=True)
	except Exception as e:
		sys.stderr.write("**ERROR:{}: {}\n".format(series_id,e))
		df = {}
	return df
	
def fredSeries(series_id,addi='observations',file_type='json',api_key=None,debugTF=False,**optx):
	''' Get series from FRED site
		jdata=fredSeries('DGS10')
	    args:
		 series_id:  string as FRED series ID, e.g., "DEXCHUS", "DGS30"
		 addi:  various inquery of data info
		optional args `optx`:
		 units, observation_start
	    return:
		 series observations in json format
	'''
	if not api_key:
		api_key = '{api_key}'.format(**json.load(open('/home/rstudio/.fredapi.json')))
	addi='/'+addi if len(addi) else addi
	#urx='https://api.stlouisfed.org/fred/series{addi}?series_id={series_id}&api_key={api_key}&file_type={file_type}'
	urx='https://api.stlouisfed.org/fred/series{addi}?series_id={series_id}&file_type={file_type}'
	data=dict(api_key=api_key)
	url=urx.format(**locals())
	for k,v in optx.items():
		if not v:
			continue
		url=url+"&{}={}".format(k,v)
	if debugTF:
		sys.stderr.write(url+"\n")
	r=requests.get(url,params=data)
	r.json()
	return r.json()

if __name__ == '__main__':
	args=sys.argv[1:]
	if not args:
		print(__doc__)
		exit(1)
	series= args[0]
	addLst=['categories','observations','release','search','search/tags',
		'search/related_tags','tags','updates','vintagedates']
	addi= 'observations' 
	if len(args)>1 and args[1].lower() in addLst:
		addi=args[1].lower()
	cosd = args[2] if len(args)>2 and len(args[2])==10 else "2022-01-01"
	units = args[3] if len(args)>3 and len(args[3])>2 else ""
	d=fredSeries(series,addi=addi,units=units,observation_start=cosd,debugTF=True)
	if "observations" in d:
		df=pd.DataFrame(d["observations"])
		print(df.tail())
	elif "seriess" in d:
		print(d["seriess"])
	else:
		print(d)
