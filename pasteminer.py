import httplib
import random
from HTMLParser import HTMLParser
from datetime import datetime
import time
import hashlib
from threading import Thread, Lock
import mutex
import os
from Queue import Queue
import signal
import socket
import urllib2
import codecs
import socks
from socksipy import *
import sys
import json

def get_dict(d,key,default=None):
    try:
        return d[key]
    except KeyError:
        return default

class Worker(Thread):
    def __init__(self,name,id,queue):
        Thread.__init__(self)
        ## worker id
        self.id=name+"["+str(id)+"]"
        ## Instance of the queue
        self.queue=queue
        ## Set deamon to true
        self.deamon=True
        # start worker
        self.start()

    def run(self):
        while True:
            work, args, kargs = self.queue.get()
            try:
                work(*args,**kargs)
            except Exception, e:
                print ("Exception running task["+str(e)+"]: "+str(e.message)+" "+str(e.args))
            self.queue.task_done()

class ThreadPool():
    def __init__(self,name,num_threads,queue):
        ## Module id
        self.id=name
        ## Thread list
        self.threads=[]
        ## Number of threads
        self.num_threads=num_threads
        ## working queue
        self.queue=queue
        # Initialize threads
        for i in xrange(self.num_threads):
            t = Worker(self.id,i,self.queue)
            self.threads.append(t)

    def new_work(self, work, *args, **kargs):
        self.queue.put((work,args,kargs))
        if(self.queue.qsize()>15):
            print "Queue size: "+str(self.queue.qsize())

    def hard_kill(self):
        for t in self.threads:
            t._Thread__stop()

    def wait_for_workers(self):
        self.queue.join()

class URLReader():
    def __init__(self,name="default",ip=None,port=80,type="SOCKS5"):
        if(ip==None):
            self.proxy=False
            self.opener=urllib2.build_opener()
        else:
            self.proxy=True
            self.ip=ip
            self.port=port
            if(type.lower()=="socks5"):
                self.type=socks.PROXY_TYPE_SOCKS5
            elif(type.lower()=="socks4"):
                self.type=socks.PROXY_TYPE_SOCKS4
            else:
                self.type=socks.PROXY_TYPE_SOCKS5
            self.opener = urllib2.build_opener(SocksiPyHandler(self.type, self.ip, self.port))
        self.name=name
        print " = URL Reader %s created!" % (self.name,)

    def test_connection(self):
        try:
            conn=self.opener.open("http://www.google.com")
            data=conn.read()
            return True
        except Exception, e:
            self.opener = urllib2.build_opener(SocksiPyHandler(self.type, self.ip, self.port))
            return False

    def is_direct(self):
        return not self.proxy

    def is_proxy(self):
        return self.proxy

    def read(self,url):
        try:
            conn=self.opener.open(url)
            return conn.read()
        except Exception, e:
            self.test_connection()
            return None

class Filter():
    def __init__(self,fdict):
        import re
        self.type=get_dict(fdict,"type","keyword")
        if(self.type.lower() in ["reg","re","regular_expression"]):
            self.type="reg"
            self.re=get_dict(fdict,"re")
            self.flags=get_dict(fdict,"flags")
            self.flag=0
            if("I" in self.flags):
                self.flag = self.flag | re.I
            if("L" in self.flags):
                self.flag = self.flag | re.L
            if("M" in self.flags):
                self.flag = self.flag | re.M
            if("S" in self.flags):
                self.flag = self.flag | re.S
            if("U" in self.flags):
                self.flag = self.flag | re.U
            if("X" in self.flags):
                self.flag = self.flag | re.X
        elif(self.type.lower() in ["word_list","wordlist"]):
            self.type="word_list"
            self.case=get_dict(fdict,"case","sensitive")
            self.comp=get_dict(fdict,"compare","in")
            self.wl=get_dict(fdict,"list",[])
        else:
            #keyword
            self.kw=get_dict(fdict,"key_string")
            self.case=get_dict(fdict,"case","sensitive")
            self.comp=get_dict(fdict,"compare","in")
            self.type="keyword"
        print " = Filter of the type %s loaded!" % (self.type)

    def keyword_match(self,string):
        if(self.kw!=None and string!=None):
            a=self.kw
            b=string
            if(self.case!="sensitive"):
                a=a.lower()
                b=b.lower()
            a=a.decode('utf-8')
            b=b.decode('utf-8')
            if(self.comp=="in"):
                return (a in b)
            else:
                return (a == b)
        return False

    def word_list_match(self,string):
        for word in self.wl:
            if(word!=None and string!=None):
                a=word
                b=string
                if(self.case!="sensitive"):
                    a=a.lower()
                    b=b.lower()
                a=a.decode('utf-8')
                b=b.decode('utf-8')
                if(self.comp=="in"):
                    res = (a in b)
                else:
                    res = (a == b)
                if(res):
                    return True
        return False

    def re_match(self,string):
        import re
        if(self.re!=None and string!=None):
            mObj = re.match( self.re, string, self.flag)
            if(mObj):
                return True
            else:
                return False
        return False

    def match(self,string):
        if(self.type=="keyword"):
            return self.keyword_match(string)
        elif(self.type=="word_list"):
            return self.word_list_match(string)
        else:
            return self.re_match(string)

class PasteSource():

    def __init__(self,options={}):
        self.name=get_dict(options,"name","pastebin")
        self.host=get_dict(options,"host","www.pastebin.com")
        self.raw_link=get_dict(options,"raw_link","/raw.php?i=")
        self.link_validate_re=get_dict(options,"link_validate_re")
        self.invalid_content=get_dict(options,"invalid_content")
        self.update_link=get_dict(options,"update_link","/ajax/realtime_data.php?q=2&randval=")
        print " = Source %s loaded!" % (self.name,)

    def feed(self,u_reader):
        link="http://"+str(self.host)+str(self.update_link)+str(random.random())
        return u_reader.read(link)

    def validate_urls(self,lst):
        import re
        res=[]
        if(self.link_validate_re!=None):
            for link in lst:
                mObj = re.match( self.link_validate_re , link,0)
                if(mObj):
                    res.append(link)
        return res

    def validate_content(self,content):
        if(content==None):
            return False
        if(self.invalid_content==None or self.invalid_content==""):
            return True
        if(self.invalid_content in content):
            return False
        else:
            return True

class MyHTMLParser(HTMLParser):
    def __init__(self):
        HTMLParser.__init__(self)
        self.links=[]

    def getLinks(self):
        return self.links

    def handle_starttag(self, tag, attrs):
        #print "Encountered a start tag:", tag
        if(tag=="a"):
            for attr in attrs:
                for i in xrange(len(attr)):
                    if(attr[i]=="href"):
                        self.links.append(attr[i+1])

class PasteMiner():

    def __init__(self,proxy_list=[],source_list=[],filter={},miners=1,use_direct=True):
        self.url_readers=[]
        if(use_direct):
            print "Using direct connection."
            self.url_readers.append(URLReader())
        for pdict in proxy_list:
            self.url_readers.append(
                URLReader(
                    get_dict(pdict,"name","default"),
                    get_dict(pdict,"ip"),
                    int(get_dict(pdict,"port",8080))
                )
            )
        print "Loaded %s proxy(s)!" % (len(self.url_readers),)
        
        self.sources=[]
        for sdict in source_list:
            self.sources.append(PasteSource(sdict))
        print "Loaded %s source(s)!" % (len(self.sources),)

        self.filter_base=get_dict(filter,"base",True)
        if(self.filter_base):
            print "Setting filter to black list mode"
        else:
            print "Setting filter to white list mode"

        flist=get_dict(filter,"filters")
        self.filters=[]
        for dfilter in flist:
            self.filters.append(Filter(dfilter))
        print "Loaded %s filters(s)!" % (len(self.filters),)

        self.mining_q=Queue(0)
        self.cleaners=ThreadPool("cleaners",10,self.mining_q)
        self.miners=[]
        self.dict={}
        for i in xrange(miners):
            t=Thread(target=self.mining, args=());
            self.miners.append(t)
            t.start()
        print "%s miners started!" % (len(self.miners),)

    def destroy(self):
        print "Killing cleaners and miners..."
        self.cleaners.hard_kill()
        for t in self.miners:
            t._Thread__stop()
        print "Done."

    def parse(self,src,data):
        parser = MyHTMLParser()
        if(data!=None):
            parser.feed(data)
            return src.validate_urls(parser.getLinks())
        else:
            return []

    def visit(self,link):
        self.dict[link]=link

    def visited(self,link):
        v=get_dict(self.dict,link)
        if(v==None):
            return False
        else:
            return True

    def mining(self):
        while(True):
            for src in self.sources:
                u_reader=random.choice(self.url_readers)
                data=src.feed(u_reader)
                while(data==None):
                    u_reader=random.choice(self.url_readers)
                    data=src.feed(u_reader)
                lst=self.parse(src,data)
                for link in lst:
                    if(not self.visited(link)):
                        self.cleaners.new_work(self.clean,src,link)
                        if(len(self.dict)>10000):
                            self.dict={}
                        self.visit(link)
            time.sleep(1)

    def clean(self,src,link):
        try:
            max=10
            link="http://"+str(src.host)+str(src.raw_link)+link[1:]
            u_reader=random.choice(self.url_readers)
            text=u_reader.read(link)
            turn=1

            while(not src.validate_content(text)):
                #print "Pastebin is blocking! waiting..."
                if(turn==max):
                    break
                print "SOMETHING IS BLOCKING ME!"
                time.sleep(60)
                u_reader=random.choice(self.url_readers)
                text=u_reader.read(link)
                turn=turn+1

            if(src.validate_content(text)):
                if(self.filter_base):
                    add=True
                    #blacklist - if a condition hits true its blocked
                    for f in self.filters:
                        if(f.match(text)):
                            add=False
                            break
                    if(add):
                        self.save_file(text)
                else:
                    add=False
                    #whitelist - must have a true condition
                    for f in self.filters:
                        if(f.match(text)):
                            add=True
                            break
                    if(add):
                        self.save_file(text)
        except Exception, e:
            print "Exception on cleaner! link -> %s" % (link,)
            print e

    def save_file(self,content):
        hash=hashlib.sha1(content+str(time.time())).hexdigest()
        f = open("dump/"+str(hash)+".txt","w")
        print " === File saved "+str(hash)+" content: "+content[:20]
        f.write(content)
        f.close()

def catchSignals(signr, stack):
    miner.destroy()
    sys.exit(signr)

if __name__ == "__main__":
    try:
    f = open('settings.json', 'r')
        data=f.read()
	settings=json.loads(data)
    except Exception, e:
	print "Problem loading settings file!"
        print e
	print "Quitting..."
	exit(0)

    plist=get_dict(settings,"proxy_list",[])
    slist=get_dict(settings,"sources_list",[])
    fdict=get_dict(settings,"filters_dict",{})

    try:
        os.mkdir("dump")
    except Exception, e:
        pass

    miner = PasteMiner(plist,slist,fdict)

    signal.signal(signal.SIGABRT, catchSignals)
    signal.signal(signal.SIGFPE, catchSignals)
    signal.signal(signal.SIGTERM, catchSignals)
    signal.signal(signal.SIGILL, catchSignals)
    signal.signal(signal.SIGINT, catchSignals)
    signal.signal(signal.SIGSEGV, catchSignals)

    cmd=""
    #d=False
    while(True):
        cmd=raw_input("prompt> ")
	if(cmd=="exit"):
            break


    miner.destroy()
