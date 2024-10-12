import re,os,uuid,bs4,zhconv,subprocess,typing
from ebooklib import epub
from tqdm import trange


class resources:
    
    def __init__(self) -> None:
        self.init_ttf()
        self.init_css()
    def init_ttf(self) -> None:
        resls:typing.Iterable[str] = filter(lambda x:x.endswith("ttf"),os.listdir())
        self.ttf:list[tuple[str,bytes]] = []
        for ttfn in resls:
            with open(f"./Utils/{ttfn}",'rb') as f:
                self.ttf.append((ttfn,f.read(),))
    def init_css(self) -> None:
        pf="@font-face {\n    font-family: \"beetsoup_gntfts\";\n    src:{\n"
        for ttfname,_ in self.ttf:
            pf += f"        url(\"./{ttfname}\"),\n"
        pf = pf[:-2]+';\n    }\n}\n'
        with open(f"./Utils/style.css",'r',encoding='utf-8') as f:
            cssf = f.read()
        self.css = pf+cssf
    
    def epubXML_format(self,iStr:str,level:int=0) -> str:
        if level < 1:
            pbs4 = bs4.BeautifulSoup(iStr,"html.parser")
            for _ in pbs4.select("*"):
                if 'style' in _.attrs:
                    del _['style']
            for _ in pbs4.select("script"):
                _.extract()
            iStr = pbs4.prettify()
        if level < 2 :
            iStr = zhconv.convert(iStr, "zh-hans")\
                .replace('“', '「')\
                .replace('”', '」')\
                .replace('‘', '『')\
                .replace('’', '』')\
                .replace("&nbsp;", '')\
                .replace('\\n', '')
        if level < 3:
            iStr = iStr.replace("&", "&amp;")\
                .replace("<", "&lt;")\
                .replace(">", "&gt;")\
                .replace('"', "&quot;")\
                .replace('\'', "&#x27;")\
                .replace(' ',"&nbsp;")
        return re.sub(u"[\\x00-\\x08\\x0b\\x0e-\\x1f\\x7f]", '',iStr).strip()

    def PageGenerator(self,cid:int,sid:int,uid:int,title:str,pages:str|list[str],spliter:typing.Literal["CR","LF","CRLF"]="CRLF"):
        titleF  = self.epubXML_format(title.strip(),1)
        if isinstance(pages,str):
            _pls = pages.split(spliter.replace("CR",'\r').replace("LF",'\n'))
        elif isinstance(pages,list):
            _pls = pages
        restmp = ['<?xml version=\'1.0\' encoding=\'utf-8\'?>\n<!DOCTYPE html>\n<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/#" lang="cn" xml:lang="cn">\n',
            '<head>\n',
           f'  <title>{title.strip()}</title>\n',
            '</head>\n',
            '<body>\n',
            '  <div>\n'
           f'    <h3>{titleF}</h3>\n\n',
            *[ '' if len(frame.strip())==0 else f"    <p>{self.epubXML_format(frame.strip(),1)}</p>\n\n    <br/>\n\n" for frame in _pls],
            '  </div>\n</body>\n</html>']
        _res = (''.join(restmp)).encode("utf-8")
        # Build EpubH5Page
        _EH = epub.EpubHtml(
            f"U{uid:06d}.xhtml", 
            f"C{cid:03d}S{sid:06d}.xhtml",
            "application/xhtml+xml",
            _res,
            title.strip(),'zh-CN'
        )
        _EH.add_link(rel="stylesheet", href="../style.css", type="text/css")
        return _EH
        
gb_res = resources()

class oneBook:
    global gb_res
    def __init__(self,path:str,inner_style:bool=False) -> None:
        self.dbg = False
        self.rawText :list[str]= []
        self.GroupBy:tuple[str]= ()
        self.BookTree:list[tuple[str,list[tuple[str,list[str]]]]] = []
        self.quickGB:list[str] = ["!Count100","VOL::","^第[零一二三四五六七八九十百千万0123456789 ]+卷"]
        self.quickSB:list[str] = ["^(:?番外|第[零一二三四五六七八九十百千万0123456789 ]+章)","^===.*==="]
        self.iStyle = inner_style
        self.ttf=gb_res.ttf

        self.__call__(path)
        

    def openText(self,path:str) -> bool:
        if not os.path.exists(path):
            return False
        with open(path,'r',encoding='utf-8') as f:
            self.rawText = f.readlines()
        return True
    def regGroupBy(self,Groupby:str,_DEFAULT = "!Count100") -> bool:
        if not Groupby:
            Groupby = _DEFAULT
        try:
            Groupby = self.quickGB[int(Groupby)]
        except:
            pass
        if Groupby.startswith("!Count"):
            try:
                sectionSplit = int(Groupby[6:])
                self.GroupBy:tuple[str,int]= ('num',sectionSplit,)
                return True
            except:
                return False
        if Groupby.startswith("rg[") and Groupby.endswith("]"):
            try:
                sectionSplitls = Groupby[3:-1].split(',')
                self.GroupBy = ('ls',[re.compile(_) for _ in sectionSplitls],)
                return True
            except:
                return False
        try:
            self.GroupBy = ('re',re.compile(Groupby),)
            return True
        except:
            return False
    def regSection(self,Sect:str,_DEFAULT = r"^(:?番外|第[零一二三四五六七八九十百千万0123456789 ]+章)") -> bool:
        if not Sect:
            Sect = _DEFAULT
        try:
            Sect = self.quickSB[int(Sect)]
        except:
            pass
        _PattSec =  re.compile(Sect)
        match self.GroupBy[0]:
            case "num":
                SectMax: int = self.GroupBy[1]
                _SectionCount :int = 0
                self.BookTree = [ (f"Chapter>>{_SectionCount:06d}~{_SectionCount+SectMax:06d}<<",
                                   [("DefaultSection",["Init Section Here"])]) ]
                for line in self.rawText:
                    if not _PattSec.match(line):
                        self.BookTree[-1][1][-1][1].append(line)
                    elif ( (_SectionCount % SectMax) == 0) and (_SectionCount != 0):
                        _SectionCount = _SectionCount+1
                        self.BookTree.append((f"Chapter>>{_SectionCount:06d}~{_SectionCount+SectMax:06d}<<",
                                              [(line,[])]))
                    else:
                        _SectionCount = _SectionCount +1
                        self.BookTree[-1][1].append((line,[]))
                    continue
            case "ls":
                self.BookTree = []
                _PatLS:list[re.Pattern] = self.GroupBy[1]
                _INITB = True
                _INITC = True
                for line in self.rawText:
                    if _INITB:
                        if _PatLS[0].match(line):
                            self.BookTree.append((line,[]))
                            _PatLS.pop(0)
                            _INITB = False
                        else:
                            continue
                    else:
                        if _PatLS!=[]:
                            if _PatLS[0].match(line):
                                self.BookTree.append((line,[]))
                                _PatLS.pop(0)
                                _INITC = True
                        if _INITC:
                            if _PattSec.match(line): # match Section
                                self.BookTree[-1][1].append((line,[]))
                                _INITC = False
                            else:
                                continue
                        else:
                            if _PattSec.match(line): # match Section
                                self.BookTree[-1][1].append((line,[]))
                            else:
                                self.BookTree[-1][1][-1][1].append(line)
            case "re":
                self.BookTree = []
                _PatChap : re.Pattern = self.GroupBy[1]
                _INITB = True
                _INITC = True
                for line in self.rawText:
                    if _INITB:
                        if _PatChap.match(line): # match Chapter
                            self.BookTree.append((line,[]))
                            _INITB = False
                        else:
                            continue
                    else:
                        if _PatChap.match(line):
                            self.BookTree.append((line,[]))
                            _INITC = True
                        if _INITC:
                            if _PattSec.match(line): # match Section
                                self.BookTree[-1][1].append((line,[]))
                                _INITC = False
                            else:
                                continue
                        else:
                            if _PattSec.match(line): # match Section
                                self.BookTree[-1][1].append((line,[]))
                            else:
                                self.BookTree[-1][1][-1][1].append(line)
            case _:
                return False
        return True
    def regBook(self,name:str,author:str,brief:str="Default Brief",uid:bytearray=None)->None:
        self._name = name
        bk = epub.EpubBook()
        bk.set_language('zh')
        bk.set_title(name)
        bk.set_identifier(str(uid if uid is not None else uuid.uuid1()))
        bk.add_author(author)
        bk.add_metadata("DC", "description", brief )
        if self.iStyle:
            for fontid,(font,data) in enumerate(self.ttf):
                bk.add_item(epub.EpubItem(f"F{fontid:06d}.ttf",f"{font}","font/ttf",data))        
        bk.add_item(epub.EpubItem("style.css","style.css","text/css",gb_res.css))
        spine_tmp = ["nav"]
        SectionCount = sum([ len(ils[1])  for ils in self.BookTree ])
        with trange(1,SectionCount+1) as TBAR:
            UT = iter(TBAR)
            SectionBuild:list[list[epub.EpubHtml]] = []
            ChapterBuild:list[tuple[epub.Link,list[epub.EpubHtml]]] = []
            for cid,(ChapterName, innerLS) in enumerate(self.BookTree,1):

                SectionBuild.append([])
                for sid,(SectionName, PageLsStr) in enumerate(innerLS,1):
                    TBAR.set_description_str(f"C{cid:03d}S{sid:06d}")
                    _pagenow = gb_res.PageGenerator(
                        cid,sid,next(UT),SectionName,PageLsStr
                    )
                    bk.add_item(_pagenow)
                    spine_tmp.append(_pagenow)
                    SectionBuild[-1].append(_pagenow)
                ChapterBuild.append((epub.Link("javascript:void(0)",ChapterName,f"Chap{cid:03d}"),SectionBuild[-1],))
            
        print(f"Total Chap{cid:03d}, SecPage{SectionCount:06d}")

        bk.toc = ChapterBuild
        bk.add_item(epub.EpubNcx())
        bk.add_item(epub.EpubNav())
        bk.spine = spine_tmp
        self.bk = bk
    def Generate(self,path:str)-> None:
        epub.write_epub(path,self.bk)
    def __call__(self,path:str):
        os.system("cls")
        print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n")
        print(f" Opening file in `{path               :^25}`.     ")
        if self.openText(path):
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n")
            print(f" Find File `{path               :^25}`,...Done.")
        else:
            print(f" unable to open file{path}!!!")
            return
        _NOK = True
        _NP3 = subprocess.Popen("notepad.exe "+f)
        while(_NOK):
            while input(">Update File?\nYes/[N]o > ").strip() not in ['','n','N','no','NO']:
                self.openText(path)
                os.system("cls")
                print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n")
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.\n",
                  " Confirm the text file,...                Done.")
            while not self.regGroupBy( input(">Group By your Section, {}\n".format('\n'.join([":: "+str(_[0]) + " is `{}`".format(_[1]) for _ in zip(range(len(self.quickGB)),self.quickGB) ]))).strip()):
                print("Parmer ERROR, please re input")
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.\n",
                  " Confirm the text file,...                Done.\n",
                  " Set `GroupBy`,...                        Done.")
            while not self.regSection( input(">Set your Section, {}\n".format('\n'.join([ ":: "+str(_[0])+ " is `{}`".format(_[1]) for _ in zip(range(len(self.quickSB)),self.quickSB) ]))).strip()):
                print("Parmer ERROR, please re input")
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.\n",
                  " Confirm the text file,...                Done.\n",
                  " Set `GroupBy`,...                        Done.\n",
                  " Set `regSection`,...                     Done.")
            n = input(">Name   Here").strip()
            a = input(">Author Here").strip()
            b = input(">Brief  Here").strip()
            print("All is done, Now Working!!!")
            self.regBook(path[:-4]if '' == n else n,a,"Default Brief Here" if not b else b)
            print("Now Saving!")
            self.Generate(path.rsplit('.')[0]+".ePub")
            a = input("OK?[Y]es/No").strip().lower()
            if a in "yes":
                _NOK = False
        _NP3.kill()

if __name__ =='__main__':
    print("Now running")
    l = os.listdir()
    for f in l:
        if f.endswith('.txt'):
            if f.startswith((
                "!",
                "NovelSeries"
            )):
                continue
            if f[:-4]+'.ePub' not in l:
                oneBook(f,True)
    print("Now ending")