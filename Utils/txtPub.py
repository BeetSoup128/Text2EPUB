import re,os,uuid,bs4,zhconv,subprocess,typing
from ebooklib import epub
from tqdm import trange

class Style:
    def __init__(self,txtpath:str,ttf:str,b:bytes,csst:str,us:bool,zs:bool) -> None:
        self.ttf = (ttf,b,)
        self.conf = (us,zs,)
        if us :
            self.css = ("@font-face {\n    font-family: \"beetsoup_gntfts\";\n    src:\n", ";\n    \n}\n"+ csst,)
            if zs :
                self.ctx = subprocess.Popen(f"pyftsubset ./Utils/{ttf} --text-file={txtpath} --flavor=woff2 --output-file=./tmp.woff2")
        else :
            self.css = ("",csst,)
    def _get_css(self) -> str:
        if self.conf[1]:
            self.ctx.wait()
            return self.css[0] + f"url(\"./{self.ttf[0][:-4]}.woff2\")  format(\"woff2\") , local(\"{self.ttf[0]}\")" + self.css[1]
        return self.css[0] + f"url(\"{self.ttf[0]}\"),local(\"{self.ttf[0]}\")" + self.css[1]
    def get_css(self) -> bytes:
        return self._get_css().encode()
    def get_ttf(self) -> tuple[str,bytes] :
        if self.conf[1]:
            self.ctx.wait()
            with open(f"./tmp.woff2",'rb') as f:
                _ret=(self.ttf[0][:-4]+".woff2",f.read(),)
            os.remove("./tmp.woff2")
            return _ret
        return self.ttf
    def use_ttf(self) -> bool:
        return self.conf[0]

class WorkSpace:
    def __init__(self) -> None:
        self.Local_Font:str = "LXGW WenKai GB"
        with open(f"./Utils/style.css",'r',encoding='utf-8') as f:
            self.css = f.read()
        self.init_ttf()
    def init_ttf(self) -> None:
        self.ttf:tuple[str,bytes] =()
        for ttfn in filter(lambda x:x.endswith("ttf"),os.listdir("Utils")):
            with open(f"./Utils/{ttfn}",'rb') as f:
                self.ttf=(ttfn,f.read(),)
                return
    def style(self,path:str,using_style:bool,zip_style:bool) -> Style:
        return Style(path,self.ttf[0],self.ttf[1],self.css,using_style,zip_style)
    @staticmethod
    def FmtStrXhtml(iStr:str,level:int=1) -> str:
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
    @staticmethod
    def GenEpubPage(cid:int,sid:int,uid:int,title:str,pages:str|list[str],spliter:typing.Literal["CR","LF","CRLF"]="CRLF"):
        titleF  = WorkSpace.FmtStrXhtml(title)
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
            *[ '' if len(frame.strip())==0 else f"    <p>{WorkSpace.FmtStrXhtml(frame)}</p>\n\n    <br/>\n\n" for frame in _pls],
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
        _EH.add_link(rel="stylesheet", href="./style.css", type="text/css")
        return _EH
    @staticmethod
    def __call__():
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
                    TextBook(f,True,True)
    print("Now ending")

main = WorkSpace()

class TextBook:
    global main
    def __init__(self,path:str,inner_style:bool=False,replace:bool=True) -> None:
        if not os.path.exists(path):
            #raise Exception("No File Found")
            return
        self.rawText :list[str]= []
        self.ChapterBy = ()
        self.BookTree:list[tuple[str,list[tuple[str,list[str]]]]] = []
        self.quickCB:list[str] = ["!Count100","VOL::","^第[零一两二三四五六七八九十百千万0123456789 ]+卷"]
        self.quickSB:list[str] = ["^(:?番外|第[零一两二三四五六七八九十百千万0123456789 ]+章)","^===.*==="]
        self.style = main.style(path,inner_style,True)
        try:
            self.AUTO(path)
        except BaseException :
            self.CLI(path)
            if replace:
                with open(path,'w',encoding='utf-8') as f:
                    ls = [":: BeetSoup doc Rev 1",self.c_ChapBy,self.c_SectBy,*self.c_Data]
                    f.write('\n'.join(ls)+'\n\n')
                    f.writelines(self.rawText)
        
    def openText(self,path:str) -> bool:
        for enc in ['utf-8','utf-16','gb18030']:
            try:
                with open(path,'r',encoding=enc) as f:
                    self.rawText = f.readlines()
                if enc == 'utf-8':
                    break
                with open(path,'w',encoding='utf-8') as g:
                    g.writelines(self.rawText)
                break
            except:
                pass
        if len(self.rawText) == 0:
            return False
        return True
    def regChapterBy(self,ChapBy:str,_DEFAULT = "!Count100") -> bool:
        if not ChapBy:
            ChapBy = _DEFAULT
        try:
            ChapBy = self.quickCB[int(ChapBy)]
        except:
            pass
        self.c_ChapBy = ChapBy
        if ChapBy.startswith("!Count"):
            try:
                sectionSplit = int(ChapBy[6:])
                self.ChapterBy:tuple[str,int]= ('num',sectionSplit,)
                return True
            except:
                return False
        if ChapBy.startswith("rg[") and ChapBy.endswith("]"):
            try:
                sectionSplitls = ChapBy[3:-1].split(',')
                self.ChapterBy = ('ls',[re.compile(_) for _ in sectionSplitls],)
                return True
            except:
                return False
        try:
            self.ChapterBy = ('re',re.compile(ChapBy),)
            return True
        except:
            return False
    def regSectionBy(self,SectBy:str,_DEFAULT = r"^(:?番外|第[零一二三四五六七八九十百千万0123456789 ]+章)") -> bool:
        if not SectBy:
            SectBy = _DEFAULT
        try:
            SectBy = self.quickSB[int(SectBy)]
        except:
            pass
        self.c_SectBy = SectBy
        _PattSec =  re.compile(SectBy)
        match self.ChapterBy[0]:
            case "num":
                SectMax: int = self.ChapterBy[1]
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
                _PatLS:list[re.Pattern] = self.ChapterBy[1]
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
                _PatChap : re.Pattern = self.ChapterBy[1]
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
        self.c_Data = (name,author,brief.replace("\n",'\\n'))
        bk = epub.EpubBook()
        bk.set_language('zh')
        bk.set_title(name)
        bk.set_identifier(str(uid if uid is not None else uuid.uuid1()))
        bk.add_author(author)
        bk.add_metadata("DC", "description", brief )
        if self.style.use_ttf():
            ttf,fb = self.style.get_ttf()
            bk.add_item(epub.EpubItem("FONT001.font",ttf,"font/ttf",fb))
        bk.add_item(epub.EpubItem("style.css","style.css","text/css",self.style.get_css()))
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
                    _pagenow = WorkSpace.GenEpubPage(
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
    def SaveBook(self,path:str)-> None:
        epub.write_epub(path,self.bk)
    def AUTO(self,path:str):
        os.system("cls")
        print(f"AUTO RUNNING:{path}")
        with open(path,'r',encoding='utf-8') as f:
            a = f.readline().strip()
            if a == ":: BeetSoup doc Rev 1":
                ChapBy = f.readline().strip()
                SectBy = f.readline().strip()
                name   = f.readline().strip()
                ah     = f.readline().strip()
                brief  = f.readline().replace("\\n",'\n')
        if self.openText(path):
            print('\n'.join([ChapBy,SectBy,name,ah,brief]))
            if self.openText(path):
                if self.regChapterBy(ChapBy) :
                    if self.regSectionBy(SectBy):
                        self.regBook(name,ah,brief)
                        self.SaveBook(path.rsplit('.')[0]+".ePub")
                        return
        raise Exception("SomeError!")
                


    def CLI(self,path:str):
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
        _NP3 = subprocess.Popen(f"notepad.exe \"./{path}\"")
        while(_NOK):
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.")
            while input(">Update File?\nYes/[N]o > ").strip() not in ['','n','N','no','NO']:
                self.openText(path)
                os.system("cls")
                print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n")
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.\n",
                  " Confirm the text file,...                Done.")
            while not self.regChapterBy( input(">Group By your Section, \n{}\n".format('\n'.join([":: "+str(_[0]) + " is `{}`".format(_[1]) for _ in zip(range(len(self.quickCB)),self.quickCB) ]))).strip()):
                print("Parmer ERROR, please re input")
            os.system("cls")
            print(">>>       YOU ARE RUNNING oneBook NOW       <<<\n\n\n",
                 f" Find File `{path               :^25}`,...Done.\n",
                  " Confirm the text file,...                Done.\n",
                  " Set `GroupBy`,...                        Done.")
            while not self.regSectionBy( input(">Set your Section, \n{}\n".format('\n'.join([ ":: "+str(_[0])+ " is `{}`".format(_[1]) for _ in zip(range(len(self.quickSB)),self.quickSB) ]))).strip()):
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
            self.SaveBook(path.rsplit('.')[0]+".ePub")
            a = input("OK?[Y]es/No").strip().lower()
            if a in "yes":
                _NOK = False
        _NP3.kill()

if __name__ =='__main__':
    main()