#!/usr/bin/env python3
'''chatGPT API Quickstart
Usage of,
./chatgtpAPI.py JSON
/cgi-bin/chatgptapi?model=MODEL&prompt=PROMPT

#--From commandline
chatgptAPI.py '{"prompt":"plan me a 2-day aruba trip"}'

Example, 
#--From internet
/cgi-bin/chatgptapi?prompt=suggest 3 names of my cat
OR
/cgi-bin/chatgptapi?model=text-davinci-edit-001&input=when%20my%20birthday&instruction=fix%20sentence

List of model:
"text-davinci-003": # create completions
"text-davinci-edit-001": # edits
"text-embedding-ada-002": # create embddings
"images-generations": # create images
"images-edits": # edit images
"images-variations": # images variation
"list-files": # list files
"upload-files": # upload files
"delete-files": # delete files

Last Mod.,
Tue 17 Jan 2023 05:35:49 PM EST
'''
import sys,os
import cgi,cgitb
import json
import datetime

def evv(va):
	try:
		return eval(va)
	except:
		return va
		
def get_cgi(mth,**opts):
	import cgi,cgitb
	cgitb.enable(logdir="/apps/fafa/bb_site/cgi-bin/.log")
	cgitb.enable(format='text',display=False)
	mf = cgi.FieldStorage()
	sys.stdout.write(" --{}-Args: {}\n".format(mth,mf))
	for ky in mf:
		va=mf[ky].value
		if ky[-2:] == 'TF':
			va = True if va[:1].lower() in ['t','y','1'] else False
		else:
			va = evv(va)
		opts.update({ky:va})
	return opts

def ulopen(url,rtype="rb"):
	import urllib.request
	if url[:4].lower()=='http':
		req=urllib.request.Request(url)
		return urllib.request.urlopen(req)
	else:
		return open(url,rtype)

def chatgptAPI(**opts):
	import requests
	import json

	rqOpts = opts.pop("rqOpts",{})
	pathname=opts.pop('pathname',None)
	debugTF=opts.pop('debugTF',False)
	xtra=evv(opts.pop('xtra',''))
	if isinstance(xtra,dict):
		opts.update(xtra)

	hds={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/59.0.3071.115 Safari/537.36'}
	if not any([True for x in ["image","prompt","input","instruction"] if x in opts]):
		return dict(err="**WARNINGS:required `prompt` in opts:{}".format(opts))
	model = opts.get("model","text-davinci-003")
	if debugTF:
		sys.stderr.write("INPUT opts:{}\n".format(opts))
	if model in ["text-davinci-003","text"]: # create completions
		if not any([True for x in ["prompt"] if x in opts]):
			return {}
		url = opts.pop("url","https://api.openai.com/v1/completions")
		data={"model": model,"top_p": 0.1,"max_tokens": 4000}
	elif model=="text-davinci-edit-001": # edits
		if 'instruction' not in opts: 
			opts.update(instruction="correct it")
		if 'prompt' in opts: 
			input=opts.pop('prompt','')
			if 'input' not in opts:
				opts.update(input=input)
		url = opts.pop("url","https://api.openai.com/v1/edits")
		data={"model": model,"top_p": 0.1}
	elif model=="text-embedding-ada-002": # create embddings
		if 'prompt' in opts: 
			input=opts.pop('prompt','')
			if 'input' not in opts:
				opts.update(input=input)
		if not any([True for x in ["input"] if x in opts]):
			return dict(err="**WARNINGS:[{}] required `input` in opts:{}".format(model,opts))
		url = opts.pop("url","https://api.openai.com/v1/embeddings")
		data={"model": model,"top_p": 0.1}
	elif model in ["images-generations","image","images","create-image","create-images"]: # create images
		if not any([True for x in ["prompt"] if x in opts]):
			return {}
		url = opts.pop("url","https://api.openai.com/v1/images/generations")
		data={"n":1,"size": "512x512"}
	elif model in ["images-edits","edit-images","edit-image"]: # edit images
		if not all([True for x in ["image","prompt"] if x in opts]):
			return {}
		url = opts.pop("url","https://api.openai.com/v1/images/edits")
		data={"n":1,"size": "512x512"}
		#hds.update({'Content-Type': 'multipart/form-data'})
		hds.pop('Content-Type',None)
		files=dict(image=ulopen(opts.pop('image'),"rb"))
		rqOpts.update(files=files)
	elif model=="images-variations": # images variation
		if not all([True for x in ["image"] if x in opts]):
			return {}
		if 'prompt' in opts: 
			image=opts.pop('prompt','')
			if 'image' not in opts:
				opts.update(image=image)
		url = opts.pop("url","https://api.openai.com/v1/images/variations")
		data={"n":1,"size": "512x512"}
		#hds.update({'Content-Type': 'multipart/form-data'})
		hds.pop('Content-Type',None)
		files=dict(image=ulopen(opts.pop('image'),"rb"))
		rqOpts.update(files=files)
	elif model=="list-files": # list files
		url = opts.pop("url","https://api.openai.com/v1/files")
		data={}
	elif model=="upload-files": # upload files
		if not all([True for x in ["file","purpose"] if x in opts]):
			return {}
		url = opts.pop("url","https://api.openai.com/v1/files")
		data={}
	elif model=="delete-files": # delete files
		if not all([True for x in ["file_id"] if x in opts]):
			return {}
		url = opts.pop("url","https://api.openai.com/v1/files")
		url = "{}/{}".format(url,opts["file_id"])
		data={"object":"file","deleted":True}
	else:
		return {}
		
	headers = opts.pop("headers",hds)
	sessionTF = opts.pop("sessionTF",False)
	if "OPENAI_API_KEY" in os.environ:
		auth='Bearer {}'.format(os.environ["OPENAI_API_KEY"])
	else:
		auth='Bearer {}'.format(open('/home/rstudio/.OPENAI_API_KEY','r').read().strip())
	headers.update(Authorization=auth) 
	
	if opts:
		for x,y in opts.items():
			if x not in ['model','pathname','submit','xtra']:
				data[x]=evv(y)

		if "temperature" in data:
			data.pop("top_p",None)
			
	rq = requests.Session() if sessionTF else requests
	if debugTF:
		sys.stderr.write("+++url:{}\ndata:{}\nheaders:{}\nrqOpts:{}".format(url,data,headers,rqOpts))
	if model=="delete-files": # delete files
		ret = rq.delete(url,headers=headers,**rqOpts)
	else:
		if 'Content-Type' in headers and headers['Content-Type']=='application/json':
			ret = rq.post(url,data=json.dumps(data),headers=headers,**rqOpts)
		else:
			ret = rq.post(url,data=data,headers=headers,**rqOpts)
	res = ret.json()
	data.update(model=model)
	res['input_param']=data
	return res
	
if __name__ == '__main__' :
	xreq=os.getenv('REQUEST_METHOD')
	if xreq in ('GET','POST'):
		pst=sys.stdin.read()
		optx=get_cgi(xreq)
		try:
			if pst:
				optx.update(eval(pst))
		except Exception as e:
			optx.update(err=str(e))
		ctype=optx.pop('ctype','json')
		if ctype=='html':
			print("Content-type:text/html;charset=utf-8\r\n\r\n")
		elif ctype=='plain':
			print("Content-type:text/plain;charset=utf-8\r\n\r\n")
		elif ctype=='multipart':
			print("Content-type:multipart/form-data\r\n\r\n")
		else:
			print("Content-type:application/json;charset=utf-8\r\n\r\n")
	else:
		optx=eval(sys.argv[1]) if sys.argv[1:] else {}
		ctype=optx.pop('ctype','json')
	debugTF=optx.get('debugTF',False)
	if not optx:
		if xreq in ('GET','POST'):
			print(json.dumps(dict(err=__doc__)) if ctype=='json' else __doc__)
		sys.exit(__doc__)
	if debugTF:
		sys.stderr.write("optx:{}\n".format(optx))
	res=chatgptAPI(**optx)

	if ctype=='json':
		if debugTF:
			print(json.dumps([optx,res]))
		else:
			print(json.dumps(res))
		try:
			remoteAddr=os.getenv('HTTP_X_REAL_IP')
			if not remoteAddr:
				remoteAddr=os.getenv('REMOTE_ADDR')
			pbdt=datetime.datetime.now()
			fp=open("/apps/fafa/bb_site/cgi-bin/.log/chatgptapi.log","a")
			fp.write("++ from {} @ {}\n{}\n".format(remoteAddr,pbdt,json.dumps(res)))
		except Exception as e:
			sys.stderr.write("**ERROR on logfile:{}\n".format(e))
	else:
		if 'choices' in res and 'text' in res['choices'][0]:
			print(res['choices'][0]['text'])
		elif 'data' in res and 'url' in res['data'][0]:
			print(res['data'][0]['url'])
		else:
			print("N/A")
