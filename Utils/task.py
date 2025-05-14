__all__ = ["EpubBulider"]

import zipfile
from time import strftime, localtime
from typing import NamedTuple
from pathlib import Path
from subprocess import Popen
import pickle
import base64
import re


from ebooklib import epub
from uuid import uuid4 as GUID
from zhconv import convert as Conv


from env import TUI, Config, ApplyResult

def BuildCssWithFont(
        fontPromise:ApplyResult[bytes]|None) -> list[epub.EpubItem]:
    default_fontfamily = ["LXGW WenKai GB Screen R"]
    naming = {
        'familyName': 'AutoFamily01',
        'filename': 'CompressFont.woff2',
    }

    def ls2str(l: list[str]) -> str:
        return ','.join([f"\"{_}\"" for _ in l])
    if fontPromise is not None:
        default_fontfamily = [naming['familyName'], *default_fontfamily]
    CSS = f'''body,p {{    font-family:{ls2str(default_fontfamily)};}}
h1,h2,h3,h4,h5,h6 {{    text-align: center    }}'''
    if fontPromise is None:
        return [epub.EpubItem(uid="style.css", file_name="style.css",
                              media_type="text/css", content=CSS.encode("utf-8"))]
    CSS = f'''@font-face {{
font-family: \"{naming["familyName"]}\";
src: url(\"./{naming["filename"]}\") format(\"woff2\")}}\n''' + CSS
    itemcss = epub.EpubItem(uid="style.css", file_name="style.css",
                            media_type="text/css", content=CSS.encode("utf-8"))
    itemfont = epub.EpubItem(
        naming["filename"], naming["filename"], "font/ttf", fontPromise.get())
    return [itemcss, itemfont]


class TextAttributes(NamedTuple):
    class FormatError(Exception): pass
    name: str
    author: str
    abstract: str
    markby: list[str]

    @classmethod
    def _build(cls, name: str, author: str, abstract: str,
               markby: list[str]) -> "TextAttributes":
        return cls(
            name.strip(),
            author.strip(),
            abstract.strip(),
            [_.strip() for _ in markby if not _.isspace() and _]
        )

    @classmethod
    def Loads1(cls, keys: list[str]) -> "TextAttributes":
        return cls._build(
            keys[2],
            keys[3],
            keys[4],
            [keys[1], keys[0]]
        )

    @classmethod
    def Loads2(cls, keys: list[str]) -> "TextAttributes":
        KeyTag = keys[0].strip()
        # 'b::KeyB64 = KeyTag.removeprefix('<Book-Infos.data=b\'').removesuffix('\'/>')
        KeyB64 = KeyTag.removeprefix('<Book-Infos.data="').removesuffix('"/>')
        MarkBK, NameBK, AtorBK, BrifBK = pickle.loads(base64.b64decode(KeyB64))
        return cls._build(
            NameBK,
            AtorBK,
            BrifBK,
            MarkBK)

    def Dumps1(self) -> str:
        if len(self.markby) != 2:
            raise Exception("Unsupported markers.")
        return f":: BeetSoup doc Rev 1\n{self.markby[1]}\n{self.markby[0]}\n{self.name}\n{self.author}\n{self.abstract}\n\n"

    def Dumps2(self) -> str:
        return f":: PubDoc rev 2\n<Book-Infos.data=\"{base64.b64encode(pickle.dumps((self.markby, self.name, self.author, self.abstract))).decode('utf-8')}\"/>\n\n"

    @classmethod
    def _Auto(cls, Check: list[bytes]) -> tuple[int, "TextAttributes"]:
        TargetLine = Check[0].decode("utf-8").strip()
        match TargetLine:
            case ":: BeetSoup doc Rev 1":
                return 6, cls.Loads1([_.decode("utf-8") for _ in Check[1:6]])
            case ":: PubDoc rev 2":
                return 2, cls.Loads2([_.decode("utf-8") for _ in Check[1:2]])
            case _:
                raise cls.FormatError()


class Loader:
    def __init__(self, pathstr: str | Path):
        if isinstance(pathstr, Path):
            self._Path = pathstr
        else:
            self._Path = Path(pathstr)
        self._name = self._Path.name.rsplit(".", 1)[0]
        self._raw = self._Path.read_bytes()
        self.TextLine = None

    def Dump(self, pfx: str = '', sfx: str = ''):
        if self.TextLine is None:
            raise Exception("No TextLine.")
        with open(self._Path, "w", encoding="utf-8") as f:
            f.write(pfx)
            f.write("\n".join(self.TextLine))
            f.write(sfx)

    def BuildPhase(self) -> tuple[TextAttributes | None, "EpubBulider.Phase"]:
        try:
            ignore, attr = TextAttributes._Auto(self._raw.splitlines()[:6])
            text = [_.decode("utf-8") for _ in self._raw.splitlines()[ignore:]]
        except (UnicodeError, TextAttributes.FormatError):
            attr = None
            text = None
            codecs = ["utf-8", "utf-16", "gb18030"]
            for codec in codecs:
                try:
                    text = self._raw.decode(codec).splitlines()
                except UnicodeError:
                    continue
                break
            if text is None:
                raise Exception("Unsupported encoding.")
        self.TextLine = [_.rstrip() for _ in text if not _.isspace() and _]
        return (attr, EpubBulider.Phase(self.TextLine, [self.strFMT(
            _) for _ in self.TextLine], [self.strXMLFMT(_) for _ in self.TextLine]),)

    @staticmethod
    def strFMT(iStr: str) -> str:
        return Conv(iStr, "zh-hans").replace('“', '「').replace('”', '」')\
            .replace('‘','『').replace('’', '』').replace("&nbsp;", '').replace('\\n', '')

    @staticmethod
    def strXMLFMT(iStr: str) -> str:
        return Loader.strFMT(iStr).replace("<", "&lt;")\
            .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&#x27;")


class EpubBulider:
    __Project_Name__ = "BeetSoup128/PyS_txt2epub3"

    class QuickMarkers:
        class choice(NamedTuple):
            name: str
            choices: list[str]

        def __init__(self, *opt):
            self._listchoices = [_ for _ in opt if isinstance(_, self.choice)]

        def add(self, choice: choice) -> "EpubBulider.QuickMarkers":
            self._listchoices.append(choice)
            return self

        def GetHints(self, lv: int) -> list[str]:
            if lv < len(self._listchoices):
                return [f"[red]{lv:03d}::{self._listchoices[lv].name}\n", *[
                    f"[green]Quick{idx:03d} [blue]{prompt}\n" for idx, prompt in enumerate(self._listchoices[lv].choices)]]
            else:
                return [f"Now try to mark level{lv:03d}"]

        def GetPatten(self, lv: int, result: str) -> str:
            if lv < len(self._listchoices):
                if result.isspace() or not result:
                    return self._listchoices[lv].choices[0]
                try:
                    residx = int(result[0])
                    return self._listchoices[lv].choices[residx]
                except ValueError:
                    return result.strip()
            else:
                return result.strip()

        @classmethod
        def From(cls, a: TextAttributes | None,
                 _default: "EpubBulider.QuickMarkers|None" = None) -> "EpubBulider.QuickMarkers":
            if a is not None:
                return cls(
                    *[cls.choice(f"DefaultLv{lv}", [expr]) for lv, expr in enumerate(a.markby)])
            elif _default is not None:
                return _default
            else:
                return cls().add(cls.choice("简单快速分章节", ["^(:?番外|终章|序章|第[〇零一两二三四五六七八九十百千万0123456789 ]+章)", "^===.*===", "^Chap\\d+"]))\
                    .add(cls.choice("简单快速分卷", ["!Count100", "^VOL::.*", "^第[〇零一两二三四五六七八九十百千万0123456789 ]+卷"]))

    class Phase:
        raw: list[str]
        FMT: list[str]
        XMLFMT: list[str]

        def __init__(self, r: list[str], f: list[str], x: list[str]):
            self.raw = [""] + r
            self.FMT = [""] + f
            self.XMLFMT = [""] + x
            self.listMatchedLines: list[list[int]] = []
            self.lsdictMarkerName: list[dict[int, str]] = []


        @staticmethod
        def _GenCount(iStr: str) -> slice | None:
            p_Count = re.compile(r"^!Count[,\d]+$")
            if p_Count.match(iStr):
                varcounts = [
                    int(_) if _ else None for _ in iStr[6:].split(",")]
                if len(varcounts) < 3:
                    varcount = varcounts[0]
                    return slice(None, None, varcount)
                else:
                    return slice(*varcounts[:3])
            else:
                return None

        def Match(self, patternStr: str):
            if varslice := self._GenCount(patternStr):
                self.listMatchedLines.insert(
                    0, self.listMatchedLines[0][varslice])
                step = varslice.step or 1
                self.lsdictMarkerName.insert(
                    0, {lidx: f"Count{idx * step + 1}~{idx * step + step}" for idx, lidx in enumerate(self.listMatchedLines[0])})
            else:
                patten = re.compile(patternStr)
                self.listMatchedLines.insert(
                    0, [idx for idx, words in enumerate(self.raw) if re.match(patten, words)])
                self.lsdictMarkerName.insert(
                    0, {idx: self.XMLFMT[idx] for idx in self.listMatchedLines[0]})

        def BuildNodes(self, TitlePage=True,
                       VolumeName: str = "MAIN") -> list["EpubBulider.Node"]:
            LvMap = [(__MLine, __Level) for __Level, __MLines in enumerate(
                self.listMatchedLines, 1) for __MLine in __MLines]
            LvMap.append((0, 0))
            self.lsdictMarkerName.insert(0, {0: VolumeName})
            if TitlePage:
                LvMap.append((0, len(self.listMatchedLines)))
                self.lsdictMarkerName[-1][0] = "|==扉页==|"
            nodes: list[EpubBulider.Node] = []
            stack: list[EpubBulider.Node] = []
            LvMap.sort()
            for i, (current_id, current_level) in enumerate(LvMap):
                # 计算内容范围
                next_id = LvMap[i +
                                1][0] if i < len(LvMap) - 1 else len(self.raw)
                content_start = current_id + 1
                content_end = next_id - 1\
                    if i < len(LvMap) - 1 else len(self.raw) - 1
                # 寻找父节点（最近且级别更小的节点）
                parent = None
                for node in reversed(stack):
                    if node.level < current_level:
                        parent = node
                        break
                # 创建新节点
                new_node = EpubBulider.Node(
                    seq_id=i,
                    level=current_level,
                    title=self.lsdictMarkerName[current_level].get(
                        current_id, ""),
                    content= self.FMT[content_start : content_end + 1],#[self.FMT[j] for j in range(content_start, content_end + 1)],
                    children=[],
                )
                if parent is None:
                    stack.append(new_node)
                else:
                    parent.children.append(new_node)
                    stack.append(new_node)
                nodes.append(new_node)
            return nodes

    class Node:
        seq_id: int
        level: int
        title: str
        content: list[str]
        children: list["EpubBulider.Node"]

        def __init__(self, seq_id: int, level: int, title: str,
                     content: list[str], children: list["EpubBulider.Node"]):
            self.seq_id = seq_id
            self.level = level
            self.title = title
            self.content = content
            self.children = children

        def _BuildContent(self) -> bytes:
            return '''<?xml version=\'1.0\' encoding=\'utf-8\'?>
<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops" epub:prefix="z3998: http://www.daisy.org/z3998/2012/vocab/structure/#" lang="cn" xml:lang="cn">
<head>
  <title>{Title}</title>
</head>
<body>
  <div>
    <h3>{Title}</h3>
{Body}
  </div>
</body>
</html>'''.format_map({
                "Title": self.title,
                "Body": "\n".join([f"<p>{c.strip()}</p><br/>" for c in self.content])
            }).encode("utf-8")

        def Build(
                self, pageCollection: list) -> tuple[epub.Link, list] | epub.EpubHtml | None:
            if self.children:
                return (epub.Link("####", self.title, f"U{self.seq_id}"),
                        [c for c in [child.Build(pageCollection) for child in self.children] if c is not None],)
            elif self.content:
                page = epub.EpubHtml(
                    f"U{self.seq_id:06d}.xhtml",
                    f"U{self.seq_id:06d}.xhtml",
                    "application/xhtml+xml",
                    self._BuildContent(),
                    self.title,
                    'zh-CN')
                page.add_link(rel="stylesheet",
                              href="./style.css", type="text/css")
                pageCollection.append(page)
                return page
            else:
                return None

    def __init__(self, filepath: str | Path, config: Config,
                 t: TUI , QuickMarkers:QuickMarkers|None=None):
        self.t = Loader(filepath)
        self.conf = config
        self.ui = t.clearAll()
        self.q = QuickMarkers

    def run(self, Auto: bool = True, reWrite: int = 2, usingTitltPage: bool = True,
            usingVolumeLevel: bool = True) -> "EpubBulider":
        self.ui.reg(f"[red]Now Building the Book {self.t._name}")
        self.book = epub.EpubBook()
        self.book.set_identifier(str(GUID()))
        attr, self.ph = self.t.BuildPhase()
        self.Font = self.conf.GenFontPromise(self.ph.FMT)
        if attr is None or not Auto:
            with Popen(f"notepad4.exe \"{self.t._Path.absolute().as_posix()}\"") as g:
                attr = self._InvokeAttrs(self.QuickMarkers.From(attr, self.q))
                g.kill()
        else:
            self.ui.add("[blue]Auto Running")
            self._ApplyAttrs(attr)
        self._Build(usingTitltPage, usingVolumeLevel)
        match reWrite:
            case 1:
                self.t.Dump(attr.Dumps1())
            case 2:
                self.t.Dump(attr.Dumps2())
            case 0:
                self.t.Dump()
            case _:
                pass
        return self

    def _SetAttrs(self, attribute: TextAttributes) -> TextAttributes:
        self.book.add_item(epub.EpubNcx())
        self.book.add_item(epub.EpubNav())
        self.book.set_language("zh-CN")
        self.book.set_unique_metadata(
            'DC', "date", strftime("%Y-%m-%d", localtime()))
        self.book.set_unique_metadata('OPF', 'generator', '',
                                      {'name': 'generator', 'content': self.__Project_Name__})
        self.book.set_unique_metadata(
            'DC', "publisher", self.__Project_Name__ + " Build")
        self.book.set_title(attribute.name)
        self.book.add_author(attribute.author)
        self.book.add_metadata("DC", "description", attribute.abstract)
        return attribute

    def _InvokeAttrs(self, default: QuickMarkers) -> TextAttributes:
        self.ui.Display.Temp("[red]Now Invoking the Book Markers.")
        g_patstrls: list[str] = []

        def Loop():
            lv = len(self.ph.listMatchedLines)
            self.ui.Display.Temp(
                "type \\d for Quick chioce(optional),!Count\\d+[:\\d+:\\d+] to match CountBy, and any to match RegExp.\n", *default.GetHints(lv))
            patstr = default.GetPatten(lv, self.ui.input(">>>"))
            self.ph.Match(patstr)
            g_patstrls.append(patstr)
            self.ui.add(
                f"[blue]Match {patstr}::{lv:03d} with {len(self.ph.listMatchedLines[0])} lines.")
        while True:
            try:
                Loop()
            except KeyboardInterrupt:
                break
            except BaseException as e:
                self.ui.Display.Temp(f"[red]Error: {e}")
        self.ui.Display()
        self.ui.Display.Temp("[red]Now Invoking the BookAttributes.")
        bookname = self.ui.input(
            f"[blue]Bookname\n [yellow]>>>[blue]{self.t._name}").strip() or self.t._name
        bookauthor = self.ui.input("[blue]Author\n [yellow]>>>").strip()
        tmp_bookabstractls = self.ui.inputUntilExit(
            "[yellow]>>>", "[blue]Brief,Ctrl+C to exit")
        bookabstractls = [_.strip()
                          for _ in tmp_bookabstractls if not _.isspace() and _]
        self.ui.add(
            f"[blue]Bookname:[green]{bookname}\n[blue]Author:[green]{bookauthor}\n[blue]Brief:[green]{'\n'.join(bookabstractls).strip()}")
        return self._SetAttrs(TextAttributes(
            bookname,
            bookauthor,
            "<br/>".join(bookabstractls).strip(),
            g_patstrls.copy()
        ))

    def _ApplyAttrs(self, a: TextAttributes):
        for expr in a.markby:
            self.ph.Match(expr)
            lv = len(self.ph.listMatchedLines)
            self.ui.add(
                f"[blue]Match {expr}::{lv:03d} with {len(self.ph.listMatchedLines[0])} lines.")
        self._SetAttrs(a)
        self.ui.add(
            f"[blue]Bookname:{a.name}\n[blue]Author:{a.author}\n[blue]Brief:{a.abstract}")

    def _Build(self, usingTitltPage: bool = True,
               usingVolumeLevel: bool = True) -> None:
        self.ui.add("[blue]Now Building the Book.")
        nodelist = self.ph.BuildNodes(usingTitltPage,
                                      self.t._name)
        unOrderedSpine: list[epub.EpubHtml] = []
        if usingVolumeLevel:
            ToC = [nodelist[0].Build(unOrderedSpine)]
        else:
            ToC = nodelist[0].Build(unOrderedSpine)
            assert isinstance(ToC,tuple)
            ToC = ToC[1]
        unOrderedSpine.sort(key=lambda x: str(x.get_id()))
        for item in unOrderedSpine:
            self.book.add_item(item)
        spine = ["nav"] + unOrderedSpine
        self.book.spine = spine
        self.book.toc = ToC
        for item in BuildCssWithFont(self.Font):
            self.book.add_item(item)
        # Setting the Cover
        if False:
            self.book.set_cover("defaultcover", '', False)
        ####
        FinalName = self.t._name + ".epub"
        writer = epub.EpubWriter(FinalName, self.book)
        writer.out = zipfile.ZipFile(writer.file_name,
                                     'w',
                                     zipfile.ZIP_DEFLATED,
                                     True,
                                     9)
        writer.out.writestr('mimetype', 'application/epub+zip',
                            compress_type=zipfile.ZIP_STORED)
        writer._write_container()
        writer._write_opf()
        writer._write_items()
        writer.out.close()
        return
