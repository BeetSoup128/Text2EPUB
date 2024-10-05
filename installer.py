import urllib3,tqdm,re,bs4
from urllib import parse

class Solution:
    def __init__(self,netloc:str) -> None:
        self.netloc = netloc
        #<scheme>://<netloc>/<path>;<params>?<query>#<fragment>
        self.conn = urllib3.PoolManager(2,{"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11"})
    def __call__(self,url:str):
        pass
    def check(self,url:str) -> bool:
        self.checker = parse.urlparse(url)
        if self.checker.netloc == self.netloc:
            return True
        return False
    def GetPage(self,url:str,m:str="GET") -> bs4.BeautifulSoup :
        r = self.conn.request(m,url)
        d = bs4.BeautifulSoup(r.data,"html.parser")
        r.close()
        return d
Solutions:list[Solution] = []
class Auto:
    global Solutions
    def __init__(self,url:str=None):
        for s in Solutions:
            if s.check(url):
                s(url)
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
Solutions.append(独步小说网())





if __name__ == "__main__":
    Auto("https://www.dbxsd.com/book/p2481/")