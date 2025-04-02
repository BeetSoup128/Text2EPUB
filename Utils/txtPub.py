import os,typing,subprocess,re,io,zipfile,multiprocessing,pickle,base64,shutil,time,signal

from fontTools import subset,ttLib
from ebooklib import epub
from zhconv import convert as Chconv
from weakref import ref
from rich.console import Console as RConsole
from uuid import uuid1

__Project_Name__ = """BeetSoup128/PyS_txt2epub3"""

class Utils:
    class Cfg(typing.NamedTuple):
        targ:str = "."
        cache:str= "./!!!Backups"
        utils:str= "./Utils"
        sync:str = ""
    class TUI:
        class __Display:
            def __init__(self,rTUI:ref):
                self.r:ref[Utils.TUI] = rTUI
            @property
            def __TUI(self):
                if (__t := self.r() )is None:
                    raise RuntimeError("No TUI inst")
                return __t
            def All(self):
                t = self.__TUI
                for obj in t.RegdObjects:
                    t.c.print(obj)
            def __call__(self):
                t = self.__TUI
                t.c.clear()
                for obj in t.RegdObjects:
                    t.c.print(obj)
            def Tmp(self,*objs):
                for o in objs:
                    self.__TUI.c.print(o)
        def __init__(self):
            self.c = RConsole(markup=True)
            self.RegdObjects:list = []
            self.Display = self.__Display(ref(self))
        def RegObj(self, *obj) -> None:
            self.RegdObjects.extend([o for o in obj])
        def clear(self):
            self.RegdObjects.clear()
        def input(self,prompt:str)->str:
            return self.c.input(prompt)
    class QuickMarker:
        def __init__(self,LevelName:str,QuickChoices:list[str]=None):
            self.LVn = LevelName
            self.choices = QuickChoices if QuickChoices is not None else []
        @classmethod
        def All(cls):
            Parmers :list[tuple] = [("Section",[]),("Chapter",[])]
            return [Utils.QuickMarker(*P) for P in Parmers]
    _T = typing.TypeVar("_T")
    @staticmethod
    def Check(d:dict,_k,_default:_T) -> _T:
        r = d.get(_k,_default)
        if not isinstance(r,type(_default)):
            raise Exception("ParmerError")
        return r
    @staticmethod
    def _Gcss(regls:list[dict[str,str]],names:list[str]) -> str:
        css = ""
        regfont = ' '.join([f"@font-face{{font-family:{_['font-family']};{_['at']}}}" for _ in regls])
        familys = ','.join([f"\"{_}\"" for _ in names])
        css += regfont
        css += f"@page{{margin-top:0px;margin-bottom:0px}}body{{font-family:{familys};font-size:100%;padding:0;margin-left:0px;margin-right:0px;orphans:0;widows:0;}}p{{font-family:{familys};font-size:1em;line-height:150%;text-indent:2em;margin-top:1.5em;margin-bottom:0;margin-left:0;margin-right:0;orphans:0;widows:0;}}"
        css += "h1,h2,h3,h4,h5,h6{text-align:center}h1{font-size:2.5em}h2{font-size:1.85em}h3{font-size:1.35em}h4{font-size:1.00em}h5{font-size:0.75em}h6{font-size:0.55em}.a{text-indent:0em}div.centeredimage{text-align:center;display:block;margin-top:0.5em;margin-bottom:0.5em}img.attpic{border:1px solid;max-width:100%;margin:0}.booktitle{margin-top:30%;margin-bottom:0;border-style:none solid none none;border-width:50px;font-size:3em;line-height:120%;text-align:right}.bookauthor{margin-top:0;border-style:none solid none none;border-width:50px;page-break-after:always;font-size:large;line-height:120%;text-align:right}.titletoc,.titlel1top,.titlel1std,.titlel2top,.titlel2std,.titlel3top,.titlel3std,.titlel4std{margin-top:0;border-style:none double none solid;border-width:0px 5px 0px 20px;padding:45px 5px 5px 5px;font-size:x-large;line-height:115%;text-align:justify}.titlel1single,.titlel2single,.titlel3single{margin-top:35%;border-style:none solid none none;border-width:30px;padding:30px 5px 5px 5px;font-size:x-large;line-height:125%;text-align:right}"
        return css
    @classmethod
    def css(cls,fonfFamily:str,fontUrl:str,fontFormat:str="ttf") -> str:
        """Optional More url in one str, but just kep `fontFormat` is None"""
        if fontFormat is None:
            fontReg = [{"font-family":fonfFamily,"at":f"url(\"{fontUrl}\")"}]
        else:
            fontReg = [{"font-family":fonfFamily,"at":f"url(\"{fontUrl}\") format(\"{fontFormat}\")"}]
        fontExtra = [_["font-family"] for _ in fontReg] + ["LXGW WenKai GB"]
        return cls._Gcss(fontReg,fontExtra)
    @classmethod
    def cssl(cls,fontadds:list[dict[str,str]]) -> str:
        for _ in fontadds:
            for p in ["font-family","at"]:
                if p not in _:
                    raise Exception("ParmerError!!!\nNo font family found")
        fontReg = [{"font-family":_["font-family"],"at":_["at"]} for _ in fontadds]
        fontExtra = [_["font-family"] for _ in fontReg] + ["LXGW WenKai GB"]
        return cls._Gcss(fontReg,fontExtra)
    @staticmethod
    def __CmpFontWith(fontfile,target_str:str) -> bytes:
        ft = ttLib.TTFont(fontfile)
        sr = subset.Subsetter()
        sr.populate(text=target_str)
        sr.subset(ft)
        ft.flavor = "woff2"
        with io.BytesIO() as tmp:
            ft.save(tmp,False)
            tmp.seek(0)
            target = tmp.read()
        return target
    @staticmethod
    def GenFonttoQ(strLS:list[str],Q:multiprocessing.Queue):
        signal.signal(signal.SIG_IGN,signal.SIG_IGN)
        set_text = { u for k in strLS for u in k}
        fb = io.BytesIO(Q.get())
        ft = ttLib.TTFont(fb)
        sr = subset.Subsetter()
        sr.populate(text=''.join(set_text))
        sr.subset(ft)
        ft.flavor = "woff2"
        _qio = io.BytesIO()
        ft.save(_qio,False)
        Q.put_nowait(_qio.getvalue())
    @staticmethod
    def __check(strls:list[str],at:slice) -> bool:
        for line in strls[at]:
            if not line[at].isspace():
                return True
        return False
    @staticmethod
    def loadu8f(fileat:str) -> list[str]:
        codecs = ['utf-8','utf-16','gb18030']
        for cd in codecs:
            try:
                with open(fileat,'a+t',encoding=cd,errors='strict') as targ:
                    targ.seek(0)
                    result = targ.readlines()
                    result = [_.rstrip()+"\n" for _ in result]
                    targ.truncate(0)
                    targ.seek(0)
                    targ.writelines(result)
                    return result
            except UnicodeDecodeError:
                continue
            except FileNotFoundError:
                raise Exception(f"FileNotFound:{fileat} at {os.getcwd()}")
            except PermissionError:
                raise Exception(f"PermissionNotAllowed:{fileat} at {os.getcwd()}")
        raise Exception("No codecs found")
    @staticmethod
    def bookPath(name:str,path:str) -> str:
        return os.path.join(path,name)
    @staticmethod
    def FmtStrXhtml(iStr:str) -> str:
        return Chconv(iStr, "zh-hans").replace('“', '「').replace('”', '」').replace('‘', '『').replace('’', '』').replace("&nbsp;", '').replace('\\n', '').strip()
    @classmethod
    def FmtStrXhtmlH(cls,iStr:str) -> str:
        return cls.FmtStrXhtml(iStr).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;").replace('\'', "&#x27;").replace(' ',"&nbsp;").strip()
    @classmethod
    def SafeGEP(cls,b:int,e:int,title:str,pages:str|list[str],spliter:typing.Literal["CR","LF","CRLF"]="CRLF"):
        if cls.__check(pages if isinstance(pages,list) else [pages],slice(None,None,1)):
            return cls.GenEpubPage(b,e,title,pages,spliter)
    @classmethod
    def GenEpubPage(cls,b:int,e:int,title:str,pages:str|list[str],spliter:typing.Literal["CR","LF","CRLF"]="CRLF"):
        titleF  = cls.FmtStrXhtml(title)
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
            *[ '' if len(frame.strip())==0 else f"    <p>{cls.FmtStrXhtml(frame)}</p>\n\n    <br/>\n\n" for frame in _pls],
            '  </div>\n</body>\n</html>']
        _res = (''.join(restmp)).encode("utf-8")
        # Build EpubH5Page
        _EH = epub.EpubHtml(
            f"U{b:06d}.xhtml", 
            f"R{b}_{e}.xhtml",
            "application/xhtml+xml",
            _res,
            title.strip(),
            'zh-CN'
        )
        _EH.add_link(rel="stylesheet", href="./style.css", type="text/css")
        return _EH
    @classmethod
    def GenEpubSubC(cls,data:list[str], lvmap:list[tuple[int,int]], namemap:list[dict|None]) -> tuple[list[epub.EpubHtml], list[tuple[epub.Link, list]]]:
        entries= lvmap
        if not entries:
            return [], []
        nodes = []
        stack = []
        for i, (current_id, current_level) in enumerate(entries):
            # 计算内容范围
            next_id = entries[i+1][0] if i < len(entries)-1 else len(data)
            content_start = current_id + 1
            content_end = next_id - 1 if i < len(entries)-1 else len(data) - 1
            # 寻找父节点（最近且级别更小的节点）
            parent = None
            for node in reversed(stack):
                if node['level'] < current_level:
                    parent = node
                    break
            # 创建新节点
            new_node = {
                'id': current_id,
                'level': current_level,
                'title': cls.FmtStrXhtmlH(data[current_id]) if namemap[current_level] is None else namemap[current_level][current_id] ,
                'content_start': content_start,
                'content_end': content_end,
                'children': []
            }
            if parent is None:
                stack.append(new_node)
            else:
                parent['children'].append(new_node)
                stack.append(new_node)
            nodes.append(new_node)
        spine:list[epub.EpubHtml] = []
        # 生成TOC结构
        def build_toc(node) -> tuple[epub.Link, list] | epub.EpubHtml | None:
            children = node['children']
            if children:
                return [epub.Link("####",node['title'],f"U{node['id']}"),
                    [c for c in [build_toc(child) for child in children] if c is not None]]
            else: # 处理内容可能为空的情况
                content_lines = []
                if node['content_start'] <= node['content_end']:
                    content_lines = data[node['content_start'] : node['content_end'] + 1]
                __cache = cls.SafeGEP(node['content_start'], node['content_end'], node['title'], content_lines, spliter="CRLF")
                if __cache is not None:
                    spine.append(__cache)
                return __cache  # 返回生成的epub.EpubHtml对象
        toc = build_toc(nodes[0])
        spine.sort(key=lambda x: x.get_id())  # 确保spine按id排序
        return spine, toc
    @staticmethod
    def BacUp(name:str,Backup:str) -> None:
        try:
            os.remove(f"{Backup}/{name}.ePub")
        except:
            pass
        try:
            os.remove(f"{Backup}/{name}.txt")
        except:
            pass
        shutil.move(f"{name}.txt",Backup)
        shutil.move(f"{name}.ePub",Backup)
    @staticmethod
    def SycUp(name:str,Syncup:str) -> None:
        try:
            os.remove(f"{Syncup}/{name}.ePub")
        except:
            pass
        try:
            shutil.copy(f"{name}.ePub",Syncup)
        except:
            pass
class WorkProcess:
    HavTitPage = True
    HavBookLevel = True
    def run(self,Auto:bool=True,SavRev:int=None):
        self.ConsoleUI.Display()
        if self.font_tasK is not None:
            self.font_tasK.start()
        if self.listStr[0].strip() == ":: BeetSoup doc Rev 1":
            self.ConsoleUI.Display.Tmp("[blue] Auto doc file format rev 1 found")
            self.listStr.pop(0)
            ChapBy = self.listStr.pop(0).strip()
            SectBy = self.listStr.pop(0).strip()
            NameBK = self.listStr.pop(0).strip()
            AtorBK = self.listStr.pop(0).strip()
            BrifBK = self.listStr.pop(0).strip()
            MarkBK = [SectBy,ChapBy]
        elif self.listStr[0].strip() == ":: PubDoc rev 2":
            self.ConsoleUI.Display.Tmp("[blue] Auto doc file format rev 2 found")
            self.listStr.pop(0)
            KeyTag = self.listStr.pop(0).strip()
            if KeyTag.startswith("<Book-Infos.data="):
                if KeyTag.endswith("/>"):
                    KeyB64 = KeyTag[19:-3]
            MarkBK,NameBK,AtorBK,BrifBK= pickle.loads(base64.b64decode(KeyB64))
        else:
            Auto =False
        self.listStr = [""] + self.listStr
        if Auto:
            self.Auto(MarkBK,NameBK,AtorBK,BrifBK)
            if SavRev is not None:
                self.listStr.pop(0)
                self.reWrite(SavRev,MarkBK,NameBK,AtorBK,BrifBK)
        else:
            self.WithTUI()
            if SavRev is not None:
                self.listStr.pop(0)
                self.reWrite(SavRev,self.list_marker,*self.list_book_data)
    def __init__(self,textfp:str,**args):
        self.cfg = Utils.Check(args,'cfg',Utils.Cfg())
        self.HintMarker = Utils.Check(args,"Marker",Utils.QuickMarker.All())
        self.ConsoleUI = Utils.Check(args,"UI",Utils.TUI())
        self.book = epub.EpubBook()
        self.strFileName = textfp
        self.strFilePath = Utils.bookPath(textfp,self.cfg.targ)
        self.listStr = Utils.loadu8f(self.strFilePath)
        self.listMatchedLines:list[list[int]] = []
        self.ConsoleUI.RegObj(f"[red]=Now Working with `{textfp}`=")
        self.list_marker = []
        self.list_book_data :list[str] = []
        self.tasQ = multiprocessing.Queue(1)
        self.lsdictMarkerName:list[dict|None] = []
        __TTFtarg = [Utils.bookPath(p,self.cfg.utils) for p in os.listdir(self.cfg.utils) if p.endswith(".ttf")]
        if len(__TTFtarg) == 0:
            self.ConsoleUI.RegObj(f"[blue] No TTF file found")
            self.font_tasK = None
        else:
            with open(__TTFtarg[0],'rb') as g:
                self.tasQ.put(g.read())
            __ctx = multiprocessing.get_context()
            self.font_tasK = __ctx.Process(target=Utils.GenFonttoQ,args=(self.listStr,self.tasQ), daemon=False)
    def __CountBy(self,count:slice | int,level:int=0) -> None:
        self.listMatchedLines.insert(0, self.listMatchedLines[level][count] if isinstance(count,slice) else self.listMatchedLines[level][::count])
        step:int = count.step if isinstance(count,slice) else count
        self.lsdictMarkerName.insert(0,{ lidx:f"Count{idx*step+1}~{idx*step+step}" for idx,lidx in enumerate(self.listMatchedLines[0])})
    def __REBy(self,reP:re.Pattern) -> None:
        self.listMatchedLines.insert(0, [idx  for idx,words in enumerate(self.listStr) if re.match(reP,words)])
        self.lsdictMarkerName.insert(0,None)
    def mark(self,Auto:str|None=None)-> None:
        self.ConsoleUI.Display()
        if Auto is None:
            self.ConsoleUI.Display.Tmp(
                "type \\d for Quick chioce(optional),!Count\\d+[:\\d+:\\d+] to match CountBy, and any to match RegExp.",
                f"Now try to mark{self.HintMarker[len(self.listMatchedLines)].LVn}" if len(self.HintMarker) < len(self.listMatchedLines) else f"Now try to mark ::level{len(self.listMatchedLines)}")
            if len(self.listMatchedLines) < len(self.HintMarker):
                Hints = self.HintMarker[len(self.listMatchedLines)]
                self.ConsoleUI.Display.Tmp(*[f"  Quick::{idx:03d}>>`{k}`"for idx,k in enumerate(Hints.choices)])
                rep = self.ConsoleUI.input(" >>> ").strip()
                if not rep:
                    return self.mark(Hints.choices[0])
                if re.match("^\\d+$",rep) and int(rep) < len(Hints.choices) :
                    return self.mark(Hints.choices[int(rep)])
            else:
                rep = self.ConsoleUI.input(" >>> ").strip()
        else:
            rep = Auto
        if re.match("^!Count\\d+:\\d+:\\d+$",rep):
            self.__CountBy(slice(*[ int(i) for i in rep[6:].split(':',3)]))
        elif re.match("^!Count\\d+$",rep):
            self.__CountBy(int(rep[6:]))
        else:
            self.__REBy(re.compile(rep))
        self.list_marker.append(rep)
        self.ConsoleUI.RegObj(f"[green]Split::{rep} done. Total{len(self.listMatchedLines[0])} matches")
    def build_book(self) -> None:
        LvMap = [ (__MLine,__Level) for __Level,__MLines in enumerate(self.listMatchedLines,1) for __MLine in __MLines]
        LvMap.append((0,len(self.listMatchedLines)))
        LvMap.append((0,0))
        self.lsdictMarkerName.insert(0,{0:self.strFileName[:-4]})
        if self.HavTitPage:
            self.listStr[0] = "|==扉页==|\n"
        LvMap.sort()
        Spine,ToC = Utils.GenEpubSubC(self.listStr, LvMap,self.lsdictMarkerName )
        for s in Spine:
            self.book.add_item(s)
        Spine.insert(0,"nav")
        if self.HavTitPage:
            self.listStr[0] = ""
        if self.HavBookLevel:
            self.book.toc = [ToC]
        else:
            self.book.toc = ToC[1]
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        self.book.set_language("zh-cn")
        self.book.set_unique_metadata('DC',"date",time.strftime("%Y-%m-%d", time.localtime()))
        self.book.set_unique_metadata('OPF', 'generator', '', {
            'name': 'generator', 'content':__Project_Name__})
        self.book.set_unique_metadata('DC',"publisher",__Project_Name__+" Build")
        self.book.spine = Spine
    def save_book(self)-> None:
        self.ConsoleUI.RegObj("[blue] Now Saving the Book.")
        self.ConsoleUI.Display()
        return epub.write_epub(self.strFilePath.replace(".txt",'.ePub',1),self.book)
    def WithTUI(self):
        self.ConsoleUI.RegObj("[blue]Using Terminal to build this book to EPUB.")
        with subprocess.Popen(f"notepad4 {self.strFilePath}") as p:
            Marking = True
            while(Marking):
                try:
                    self.mark()
                except KeyboardInterrupt as _:
                    Marking = False
                except BaseException as b:
                    raise Exception(b)
                finally:
                    continue
            self.ConsoleUI.Display()
            self.ConsoleUI.Display.Tmp("Now mark the book infomation")
            BKname = self.strFileName.replace(".txt",'',1)
            self.list_book_data.append(self.ConsoleUI.input(f"书名::>{BKname}").strip() or BKname)
            self.list_book_data.append(self.ConsoleUI.input("作者::>").strip())
            self.list_book_data.append(self.ConsoleUI.input("简介::>").strip())
            self.ConsoleUI.RegObj(f"[green]{self.list_book_data[0]}:{self.list_book_data[1]}","[green]"+self.list_book_data[2])
            self.ConsoleUI.Display()
            self.book.set_title(self.list_book_data[0])
            self.book.add_author(self.list_book_data[1])
            self.book.add_metadata('DC', "description", self.list_book_data[2].replace("\\n",'\n') )
            self.book.set_identifier(str(uuid1()))
            p.kill()
        if self.font_tasK is not None:
            self.book.add_item(epub.EpubItem("FontWOFF2","Compressed.ttf","font/ttf",self.tasQ.get()))
            self.book.add_item(epub.EpubItem("StyleCSS","style.css","text/css",Utils.css("CpTTF","./Compressed.ttf","woff2")))
        else:
            self.book.add_item(epub.EpubItem("StyleCSS","style.css","text/css",Utils.cssl()))
        self.build_book()
        self.save_book()
    def Auto(self,markers:list[str],name:str,author:str,brief:str):
        self.ConsoleUI.RegObj("[blue]Auto building this book to EPUB.")
        self.ConsoleUI.Display()
        for m in markers:
            self.mark(m)
        self.ConsoleUI.RegObj(f"[green]<{name}>:<{author}>","[green]<<<"+brief+">>>")
        self.ConsoleUI.Display()
        self.book.add_author(author)
        self.book.set_title(title=name)
        self.book.add_metadata('DC', "description", brief.replace('\n','<br/>'))
        self.book.set_identifier(str(uuid1()))
        self.build_book()
        if self.font_tasK is not None:
            self.book.add_item(epub.EpubItem("FontWOFF2","Compressed.ttf","font/ttf",self.tasQ.get()))
            self.book.add_item(epub.EpubItem("StyleCSS","style.css","text/css",Utils.css("CpTTF","./Compressed.ttf","woff2")))
        else:
            self.book.add_item(epub.EpubItem("StyleCSS","style.css","text/css",Utils.cssl()))
        self.save_book()
    def reWrite(self,rev:int,markers:list[str],name:str,author:str,brief:str):
        if rev == 1:
            with open(self.strFilePath,'w',encoding="utf-8") as f:
                f.write(":: BeetSoup doc Rev 1\n")
                f.write('\n'.join([markers[0],markers[1],name,author,brief.replace("\n","\\n")]))
                f.writelines(self.listStr)
            return
        if rev == 2:
            with open(self.strFilePath,'w',encoding="utf-8") as f:
                f.write(":: PubDoc rev 2\n")
                data_b64_pickle = base64.b64encode(pickle.dumps((markers,name,author,brief)))
                f.write(f"<Book-Infos.data={data_b64_pickle}/>\n\n")
                f.writelines(self.listStr)
EZMarker = [
        Utils.QuickMarker("简单快速分章节",
            ["^(:?番外|终章|序章|第[零一两二三四五六七八九十百千万0123456789 ]+章)",
                "^===.*===",
                "^Chap\\d+"]),
        Utils.QuickMarker("简单快速分卷",
            ["!Count100",
                "^VOL::.*",
                "^第[零一两二三四五六七八九十百千万0123456789 ]+卷"])
    ]
class MainProcess:
    def __init__(self,cfg:Utils.Cfg|None=None,checks=(".txt"),ignores = ("!")):
        self.Window = Utils.TUI()
        self.Config = cfg if cfg is not None else Utils.Cfg()
        a = [p for p in os.listdir(self.Config.targ) if p.endswith(checks) and not p.startswith(ignores)]
        b = []
        for i in a:
            tmp = i
            for j in checks:
                tmp = tmp.replace(j,'')
            b.append(tmp)
        self.books:list[str] = b
    def run(self,marker:list[Utils.QuickMarker],somebook:str=None,rev:int=2):
        for n in self.books:
            if f"{n}.ePub" not in os.listdir(self.Config.targ):
                WorkProcess(f"{n}.txt",conf = self.Config,
                    UI = self.Window,
                    Marker = marker ).run(SavRev=rev)
        if somebook is not None:
            try:
                WorkProcess(somebook,conf = self.Config,
                    UI = self.Window,
                    Marker = marker).run(SavRev=rev)
                self.books.append[somebook[:-4]]
            except:
                pass
        return self
    def Finally(self,SyncDir:str=''):
        BacDir = self.Config.cache
        SycDir = self.Config.sync or SyncDir
        Window = self.Window
        Window.clear()
        Window.RegObj("[red] =All works has done=",
                    f"[blue]Books[green]{self.books}[blue]try to backup or sync.",
                    f"[blue]target SyncForder is>[green]{SycDir}",
                    f"[blue]target Backup Dir is>[green]{BacDir}",
                    )
        Window.Display()
        if Window.input("[white]press [green]y[white]/n to continue this work\n[green]>>>").strip().lower() in "yes":
            if SycDir != '':
                for p in self.books:
                    Utils.SycUp(p,SycDir)
            for p in self.books:
                Utils.BacUp(p,BacDir)
        Window.Display.Tmp("[red] wait 3s to exit")
        time.sleep(3)

if __name__ =='__main__':
    main = MainProcess()
    main.run(EZMarker).Finally("C:/Users/BeetSoup/OneDrive/!Novel")
