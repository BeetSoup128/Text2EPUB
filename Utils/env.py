__all__ = ["ApplyResult","Config", "TUI"]

import os
import shutil
import time
from io import BytesIO
from weakref import ref
from pathlib import Path
from multiprocessing import Process,SimpleQueue
from typing import (
    NamedTuple,
    Iterable,
    Callable,
    TypeVar,
    Generic
)
from signal import signal, SIGINT, SIG_IGN


from rich.console import Console as RConsole
from fontTools import ttLib, subset


def ConvertFont2Q(iFontBytes:bytes, _LimitTexts:list[str]) -> bytes:
    iFont = ttLib.TTFont(BytesIO(iFontBytes),recalcBBoxes=False, recalcTimestamp=False)
    setter = subset.Subsetter()
    setter.populate(text=''.join({c for t in _LimitTexts for c in t}))
    setter.subset(iFont)
    iFont.flavor = "woff2"
    _qio = BytesIO()
    iFont.save(_qio, False)
    return _qio.getvalue()


Result_t = TypeVar('Result_t')


class ApplyResult(Generic[Result_t]):
    result:Result_t|None
    @staticmethod
    def FuncWarper(func:Callable[..., Result_t],
                oQueue:SimpleQueue,
                args:tuple,
                kwds:dict):
        signal(SIGINT,SIG_IGN)
        try:
            reply_var = func(*args,**kwds)
        except BaseException as e:
            raise e
        oQueue.put(reply_var)


    def __init__(self,func:Callable[..., Result_t], args=(), kwds={}):
        self.oQ = SimpleQueue()
        self.runningProcess = Process(target=self.FuncWarper,args=(func,self.oQ,args,kwds))
        self.runningProcess.start()
        self.result = None
        self.resultOK=False
    def get(self) -> Result_t:
        if not self.resultOK:
            self.resultOK = True
            self.result = self.oQ.get()
        assert self.result is not None, "No Result_t type found"
        return self.result


class Config(NamedTuple):
    targ: str = "."
    cache: str = "./!!!Backups"
    utils: str = "./Utils"
    sync: str = "NoSync!!!"

    def findall(self) -> list[Path]:
        result = []
        for k in os.listdir(self.targ):
            tmp = Path(k)
            if tmp.is_file() and tmp.suffix.lower() == ".txt":
                result.append(tmp)
        return result

    @staticmethod
    def MoveA(srcs: list[Path], dst: Path) -> None:
        if not os.path.exists(dst):
            os.makedirs(dst)
        for k in srcs:
            if (targ := Path(dst).joinpath(k)).exists():
                os.remove(targ)
            shutil.move(k, dst)

    @staticmethod
    def CopyA(srcs: list[Path], dst: Path) -> None:
        if not os.path.exists(dst):
            os.makedirs(dst)
        for k in srcs:
            shutil.copy2(k, dst)

    def Backup(self, result: list[Path]) -> None:
        self.MoveA(result + [_.with_suffix(".ePub")
                   for _ in result], Path(self.cache))

    def isSync(self) -> bool:
        if self.sync == "NoSync!!!":
            return False
        if not self.sync:
            return False
        return True

    def Sync(self, result: list[Path]) -> None:
        self.CopyA([_.with_suffix(".ePub") for _ in result], Path(self.sync))

    def GenFontPromise(self, LimitTexts: list[str]) -> ApplyResult[bytes] | None:
        for k in os.listdir(self.utils):
            if k.endswith(".ttf"):
                with open(os.path.join(self.utils, k), 'rb') as f:
                    return ApplyResult(ConvertFont2Q, (f.read(), LimitTexts.copy()))
        return None


class TUI:
    def __init__(self) -> None:
        self.console = RConsole()
        self.Objects = []
        self.Display = self._Display(ref(self))

    class _Display:
        def __init__(self, refobj: ref) -> None:
            self.ref: ref[TUI] = refobj

        @property
        def c(self):
            if (t := self.ref()) is None:
                raise RuntimeError("No TUI object referenced")
            return t

        def Temp(self, *objs, **argv):
            self.c.console.print(*objs, **argv)

        def __call__(self):
            c = self.c
            c.console.clear()
            for obj in c.Objects:
                c.console.print(obj)

    def reg(self, *objs):
        self.Objects.extend([*objs])

    def add(self, *objs):
        self.Objects.extend([*objs])
        self.Display()

    def input(self, prompt: str) -> str:
        return self.console.input(prompt)

    def inputUntilExit(self, prompt, sfx=None) -> list[str]:
        result = []
        self.Display.Temp(sfx)
        while True:
            try:
                result.append(self.input(prompt))
            except KeyboardInterrupt:
                return result
            except BaseException as e:
                raise e

    def inputUntilExitWithHint(self, prompts: Iterable,
                               _finally: str = ":/") -> list[str]:
        result = []
        for p in prompts:
            try:
                result.append(self.input(p))
            except KeyboardInterrupt:
                return result
            except BaseException as e:
                raise e
        return result + self.inputUntilExit(_finally)

    def exitWithin3S(self) -> None:
        self.Display.Temp("Waiting 3 seconds to exit...")
        time.sleep(3)
        os._exit(0)

    def clearAll(self) -> "TUI":
        self.console.clear()
        self.Objects.clear()
        return self
