import os,sys,re
from typing import Callable


def HansNum2int(numstr:str) -> int:
    pass

def allC2N(numstr:str) -> int:
            numstr = numstr.replace("俩","二")
            NL="一二三四五六七八九"
            ML=[ "十百千" , "万亿兆" ]
            NumDict={'':0,'零':0, '〇':0, '一':1, '二':2, '两':2, '三':3, '四':4, '五':5, '六':6, '七':7, '八':8, '九':9, '十':10, '百':100, '千':1000, '万':10000, '亿':100000000, '兆':1000000000000}
            if len(numstr)==1:
                return NumDict[numstr]
            if len(numstr)==2:
                if numstr[0]=="十" and numstr[1] in NL:
                    return 10+NumDict[numstr[1]]
            for ml1 in ML[1]:
                numstr=numstr.replace(ml1,' '+ml1+' ')
            numList = numstr.split()
            reply = [0,0]
            def fourC2N(numstr):
                NumDicts={'':'','零':'','':'〇', '一':'1', '二':'2', '两':'2', '三':'3', '四':'4', '五':'5', '六':'6', '七':'7', '八':'8', '九':'9', '十':'*10+', '百':'*100+', '千':'*1000+'}
                final=''
                for n in numstr:
                    final += str(NumDicts[n])
                if final[-1] == '+':
                    return eval(final[:-1])
                return eval(final)
            for s in numList:
                if s in ML[1]:
                    if reply[1] == 0:
                        reply = [reply[0]*NumDict[s] , 0]
                    else:
                        reply=[reply[1]*NumDict[s] , 0]
                else:
                    try:
                        reply[1]=fourC2N(s)
                    except:
                        return 1
            return reply[0]+reply[1]

unum = re.compile(r"^\D*(\d+)\D*")
cnum = re.compile("[^〇零一两二三四五六七八九十百千万亿兆]*([〇零一两二三四五六七八九十百千万亿兆]+)")
Pattls : list[tuple[re.Pattern,Callable[[str],int]]] = [(unum,int,),(cnum,allC2N,)]

def GetNumber(iMatStr:re.Match[str] | str) -> int:
    if isinstance(iMatStr,re.Match):
        if isinstance(iMatStr.group(1),str):
            iStr: str = iMatStr.group(1)
        else:
            iStr = iMatStr.group()
    else:
        iStr = iMatStr
    global Pattls
    for pat in Pattls:
        try:
            a = pat[0].match(iStr).group(1).strip()
            return pat[1](a)
        except BaseException:
            pass
    return 2147483647

def GetTree():
    from bs4 import BeautifulSoup
    with open("page.h5",'rb') as a:
        b = BeautifulSoup(a.read(),"lxml")
    tp1 = b.select_one("div#allCatalog")
    t1 = tp1.select("div.catalog-volume")
    t2: dict[str, str] = {}
    for _ in t1:

        try:
            _key = list(_.select_one("h3.volume-name").strings)[0].strip()
            _val= _.select_one("li").select_one("a").string.split(' ',1)[0]
        except BaseException as e:
            raise Exception(f"Error in {_.prettify()} with {e}")
        finally:
            t2[_key] = _val
    t3 = {}
    for k in t2.keys():
        print(t2[k],allC2N(t2[k][1:-1]))
        t3[f"第{allC2N(t2[k][1:-1])}章"] = f"VOL:: {k}"
    print(t3)
    return t3

def BuildChapter(ifile:list[str]) -> list[str]:
    t2 = GetTree()
    final = []
    for line in ifile:
        for k in t2.keys():
            if k in line:
                final .append(t2[k]+"\r\n")
                del t2[k]
                break
        final.append(line)
    return final
def CkChapter(p:list[str],SplitBy:str) -> list[str]:
    mcr = re.compile(SplitBy)
    lines:list[re.Match[str]] = []
    for l in p:
        if tmp:=mcr.match(l):
            lines.append(tmp)
    numls = [ GetNumber(_.group(1)) for _ in lines]
    result:list[str] = []
    for i in range(len(numls)):
        if numls[i] == 0 or numls[i] == 1:
            continue
        if numls[i] - numls[i-1] == 1:
            continue
        result.append(lines[i-1].group(0).strip())
    return result
def CheckChapter():
    DEFAULT_S = "^(:?番外|第.+章)"
    for f in os.listdir("."):
        try:
            if f.endswith(".txt"):
                iFile = f
            else:
                continue
        except IndexError:
            raise Exception("IndexError"+str(sys.argv))
        with open(iFile,'r',encoding='utf-8') as f:
            NovelLS = f.readlines()
        os.system("cls")
        a = input("input rg spliter, default {"+DEFAULT_S+"}")
        if a.strip() != "":
            DEFAULT_S = a.strip()
        mcr = re.compile(DEFAULT_S)
        lines:list[re.Match[str]] = []
        for l in NovelLS:
            if tmp:=mcr.match(l):
                lines.append(tmp)
                #lines.append(l)
        numls = [ GetNumber(_) for _ in lines]
        result:list[str] = []
        for i in range(len(numls)):
            if numls[i] == 0 or numls[i] == 1:
                continue
            if numls[i] - numls[i-1] == 1:
                continue
            result.append(lines[i-1].group().strip())
        print('\n'.join(result))
        input("\nComplete? [Y/n]").strip() in ("Y",'y')
        os.system("cls")
def ReChapter(p:str,SplitBy:str,Optional:Callable[[int,re.Match[str]],str]=None) -> list[str]:
    if os.path.exists(p):
        with open(p,'r',encoding='utf-8') as f:
            final = f.readlines()
    else:
        raise Exception("NoFileFound")
    CpBy = re.compile(SplitBy)
    result = []
    chapidx = 0
    if Optional is None:
        for l in final:
            if CpBy.match(l):
                result.append(f"Chap{chapidx:04d}>{l.strip()}<\r\n")
                chapidx += 1
            else:
                result.append(l)
        return result
    print("Using user function")
    for l in final:
        if targ:=CpBy.match(l):
            result.append(Optional(chapidx,targ))
            chapidx += 1
        else:
            result.append(l)
    return result
class rmder:
    def __init__(self):
        self.r :set[str] = set()
    def __call__(self, idx:int,rgp:re.Match[str]) -> str:
        ChapName =rgp.group(1).strip()
        SectName =rgp.group(2).strip()
        if ChapName not in self.r:
            self.r.add(ChapName)
            return f"Vol:: {ChapName}\n\n>={SectName}=<\n\n"
        else:
            return f">={SectName}=<\n\n"
class reint:
    def __init__(self):
        pass
    def __call__(self, idx:int,rgp:re.Match[str]) -> str:
        chapname = rgp.group(1).strip()
        if isinstance(chapname,str):
            return f"Chap{idx+1:06d}>{chapname}<\r\n"
        raise Exception("Error")
def AutoCheck(path:str='.',SplitBy:str=r"^第([零一二三四五六七八九十百千万0123456789 ]+)章(.*)") -> bool:
    for f in os.listdir(path):
        if f.endswith(".txt"):
            with open(f,'r',encoding='utf-8') as g:
                res = CkChapter(g.readlines(),SplitBy)
                for r in res:
                    print(r)
            return True
        else:
            continue
    return True
if __name__ == '__main__':
    AutoCheck()
    exit(0)
    with open("Final.txt",'w',encoding='utf-8') as g:
        g.writelines(
            ReChapter("当方块人成群出现时601.txt",
                    r"^(.*) : (第\d+章.*)",rmder()
                )
            )
    exit(0)

    with open("当方块人成群出现时601.txt",'r',encoding='utf-8') as f:
        res = CkChapter(f.readlines(),r"^chapter\.(\d+).*")
        for r in res:
            print(r)
    exit(0)
    