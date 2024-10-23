import urllib3,tqdm,re
from urllib import parse
from bs4 import BeautifulSoup,Tag
class Solution:
    def __init__(self,netloc:str) -> None:
        self.netloc = netloc
        #<scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        self.conn = urllib3.PoolManager(2,{"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11"})
        self.cache :list[tuple[str,BeautifulSoup]] = []
    def check(self,url:str) -> bool:
        self.checker = parse.urlparse(url)
        if self.checker.netloc == self.netloc:
            return True
        return False
    def GetPage(self,url:str,m:str="GET") -> BeautifulSoup :
        r = self.conn.request(m,url)
        d = BeautifulSoup(r.data,"html.parser")
        r.close()
        return d
    def Save(self):
        pass
    def urlgo(self,url:str,base:str=None) -> str:
        if base is None:
            base  = parse.urlunparse(self.checker)
        return parse.urljoin(base,url)
      
class Auto:
    def __init__(self,url:str=None,**argv):
        for _ in Solution.__subclasses__():
            s = _()
            if s.check(url):
                s(url,**argv)

class 独步小说网(Solution):
    def __init__(self) -> None:
        super().__init__("www.dbxsd.com")
    def __call__(self, url: str,part:slice=slice(None,None,1)):
        p = self.checker.path
        pid = re.match("/?book/(.*)/?",p).group(1)
        page = self.GetPage(f"http://www.dbxsd.com/book/{pid}")
        bkname = page.select_one("h1").string.strip()
        # GetBookLists
        # url, title
        targls:list[tuple[str,str]] = []
        for a in tqdm.tqdm( page.select_one("div#all-chapter").select("a")):
            targls.append((f"http://www.dbxsd.com{a['href']}",a["title"].strip(),))
        targls = targls[part]
        with open(f"{bkname}.txt",'a',encoding='utf-8') as f:
            for url,tit in tqdm.tqdm(targls):
                now = f"\n==={tit}===\n\n    "
                p = [self.GetPage(url)]
                try:
                    __id = 2
                    while "_" in p[-1].select_one("div.col-md-6.text-center").select(a)[2]["href"]:
                        p.append(self.GetPage(url[:-5]+f"_{__id}.html"))
                except:
                    pass
                for _ in p:
                    now+= '\n    '.join([ ps.string for ps in _.select_one("div#cont-body").select("p") ])
                f.write(now)
class 新天禧小说(Solution):
    def __init__(self) -> None:
        super().__init__("www.tianxibook.com")
    def seq(self, url: str,part:slice=slice(None,None,1)):
        del url
        del part
        p = self.checker.path
        pid = re.match("/book/(.*)/.*",p).group(1)
        page = self.GetPage(f"http://www.tianxibook.com/xiaoshuo/{pid}")
        bkname = page.select_one("h1").string.strip()
        _initpage =  page.select_one("#content_1").select_one("a")['href']
        targls:list[str] = []
        while True:
            try:
                page = self.GetPage("http://www.tianxibook.com" +_initpage)
            except:
                with open(f"{bkname}.txt",'w',encoding='utf-8') as f:
                    f.writelines(targls)
                return
            targls.append(
                '\n    '.join([ ps.string for ps in page.select_one("div#booktxt").select("p") ]) + "\n"
            )
            _initpage = page.select_one("div.bottem1").select("a")[2]["href"]
    def normal(self, url: str,part:slice=slice(None,None,1)):
        
        p = self.checker.path
        pid = re.match("/book/(.*)/.*",p).group(1)
        page = self.GetPage(f"http://www.tianxibook.com/xiaoshuo/{pid}")
        bkname = page.select_one("h1").string.strip()
        bkrange = [ "http://www.tianxibook.com" + _['value'] for _ in page.select_one("#indexselect").select("option")[1:] ]
        targls:list[tuple[str,str]] = []
        for a in tqdm.tqdm( page.select_one("div#content_1").select("a")):
            targls.append((f"http://www.tianxibook.com{a['href']}",a.string.strip(),))
        for u in bkrange:
            page = self.GetPage(u)
            for a in tqdm.tqdm( page.select_one("div#content_1").select("a")):
                targls.append((f"http://www.tianxibook.com{a['href']}",a.string.strip(),))
        targls = targls[part]
        with open(f"{bkname}.txt",'a',encoding='utf-8') as f:
            for url,tit in tqdm.tqdm(targls):
                now = f"\n==={tit}===\n\n    "
                p = [self.GetPage(url)]
                try:
                    while "_" in p[-1].select_one("div.bottem1").select("a")[2]["href"]:
                        p.append("http://www.tianxibook.com" + p[-1].select_one("div.bottem1").select(a)[2]["href"])
                except:
                    pass
                for _ in p:
                    try:
                        booktxt = _.select_one("div#booktxt")
                        paragraphs = booktxt.select("p")
                        if paragraphs is not None:
                            now+= '\n    '.join([ ps.string for ps in paragraphs ])
                    except:
                        pass
                f.write(now)

    def __call__(self, url: str,part:slice=slice(None,None,1),use_seq:bool=False):
        if use_seq:
            self.seq(url,part)
        else:
            self.normal(url,part)
class 书吧(Solution):
    def __init__(self) -> None:
        super().__init__("www.mshu8.com")
    def normal(self,url:str,part:slice=slice(None,None,1)):
        p = self.checker.path
        pid = re.match("/book/(\\d)(_1)?",p).group(1)
        page = self.GetPage(f"http://www.mshu8.com/book/587237{pid}_1/")
        bkname = page.select_one("div.info").select_one("h1").string.strip()
        bkrange = [ "http://www.mshu8.com" + _['value'] for _ in page.select_one("div.listpage").select("option")[1:] ]
        targls:list[tuple[str,str]] = []
        for a in tqdm.tqdm( page.select("div.section-box")[1].select("a")):
            targls.append((f"http://www.mshu8.com{a['href']}",a.string.strip(),))
        for u in bkrange:
            page = self.GetPage(u)
            for a in tqdm.tqdm( page.select("div.section-box")[1].select("a")):
                targls.append((f"http://www.mshu8.com{a['href']}",a.string.strip(),))
        targls = targls[part]
        with open(f"{bkname}.txt",'a',encoding='utf-8') as f:
            for url,tit in tqdm.tqdm(targls):
                now = f"\n==={tit}===\n\n    "
                p = [self.GetPage(url)]
                try:
                    while True:
                        nxt = p[-1].select_one("div.section-opt").select("a")[2]["href"]
                        if "_" in nxt:
                            break
                        p.append(f"http://www.mshu8.com{nxt}")
                except:
                    pass
                for _ in p:
                    now+= '\n    '.join([ ps.string for ps in _.select_one("div#content").select("p") ])
                f.write(now)
    def __call__(self, url:str,part:slice=slice(None,None,1)):
        return self.normal(url=url,part=part)
class 我的书城网(Solution):
    def __init__(self) -> None:
        super().__init__("www.qushucheng.com")
    def __call__(self, url: str,part:slice=slice(None,None,1)):
        p = self.checker.path
        res=re.compile(".*www.qushucheng.com(/book_\\d+).*").match(url)
        if res is not None:
            pid = res.group(1)
        page = self.GetPage(self.urlgo(pid))
        bkname = page.select_one("div.info").select_one("h1").string.strip()
        # GetBookLists
        def GetTuple(i_page:BeautifulSoup) -> list[tuple[str,str]]:
            i_res = []
            box = i_page.select("div.section-box")[1]
            for a in tqdm.tqdm(box.select('a')):
                i_res.append( ( a['href'], a.string.strip() ) )
            return i_res
        targls:list[tuple[str,str]] = GetTuple(page)
        for a in page.select_one("#indexselect").select("option"):
            targls.extend(GetTuple(self.GetPage(self.urlgo(a['value']))))
        # url, title
        targls = targls[part]
        with open(f"{bkname}.txt",'a',encoding='utf-8') as f:
            for _url,tit in tqdm.tqdm(targls):
                url = self.urlgo(_url)
                now = f"\n==={tit}===\n\n    "
                p = [self.GetPage(url)]
                try:
                    while True:
                        nowPage = p[-1]
                        nxtpage = nowPage.select_one("a#next_url")['href']
                        if nxtpage is not None:
                            nxturlp = parse.urlparse(str(nxtpage))
                        if '_' in nxturlp.path.split("/")[-1]:
                            p.append(self.GetPage(self.urlgo(nxtpage)))
                        else:
                            break
                except:
                    pass
                for _ in p:
                    now+= '\n    '.join([ ps.string for ps in _.select_one("div#content").select("p") ])
                f.write(now)

class Fetch:
    def __init__(self,homepage:str) -> None:
        self._home = parse.urlparse(homepage)
        #<scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        self.netloc = self._home.netloc
        self.conn = urllib3.PoolManager(2,{"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11"})
        self.cache :list[tuple[str,BeautifulSoup]] = []
    def check(self,url:str) -> bool:
        self.checker = parse.urlparse(url)
        if self.checker.netloc == self.netloc:
            self.checked = True
            return True
        return False
    def GetPage(self,url:str,m:str="GET") -> BeautifulSoup :
        r = self.conn.request(m,url)
        d = BeautifulSoup(r.data,"lxml")
        r.close()
        return d
    def Save(self):
        pass
    def urlgo(self,url:str,base:str=None) -> str:
        if base is None:
            base  = parse.urlunparse(self.checker)
        return parse.urljoin(base,url)
    @staticmethod
    def GetBook(page:BeautifulSoup,querySelector:str|list[str]|slice)->Tag:
        if not isinstance(querySelector,(str,list,slice)):
            raise Exception("selector error")
        if isinstance(querySelector,str):
            querySelector = [querySelector]
        tmp = [page.select_one('body')]
        for idx,s in enumerate(querySelector,1):
            if isinstance(s,str):
                tmp.append(tmp[-1].select_one(s))
            elif isinstance(s,slice):
                tmp.append(tmp[-1][s])
            else:
                raise Exception("Unreged selector")
            if tmp[-1] is None:
                raise Exception(f"Error while select{idx} in {tmp[-2]}")
        return tmp
    def GetIndexPage(self) -> list[Tag]:
        pass
    



if __name__ == "__main__":
    #Auto("https://www.dbxsd.com/book/p2481/")
    #Auto("https://www.tianxibook.com/book/94713664/",use_seq=True)
    #Auto("http://www.mshu8.com/book/587237/")
    #Auto("https://www.tianxibook.com/book/94027479/",use_seq=False)
    Auto("https://www.qushucheng.com/book_94528627/")
    #idx = iter(range(65535))
    #[ _ if re.match("^第(\d+)章(.*)",_) == None else f"第{next(idx):06d}章" +  re.match("^第(\d+)章(.*)",_).group(2) for _ in w ]