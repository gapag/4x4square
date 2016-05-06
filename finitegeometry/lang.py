from finitegeometry.model import Grid, SE, SW, NE, NW
import re

class Interpreter:
    
    def __init__(self):
        digits = "(1|2|3|4)"
        src = "(?P<src>"+digits+")"
        dst = "(?P<dst>"+digits+")"
        self.pattern = re.compile("(?P<cmd>(r|c|b))"+"\s*"+src+"\s*"+dst)
    
    def interpret(self, command):
        mo = self.pattern.fullmatch(command)
        if not mo:
            return None
        cmd = mo.group('cmd')
        src = int(mo.group('src'))-1
        dst = int(mo.group('dst'))-1
        if  cmd == 'b':
            c = Grid.block
            src = Grid.intToBlock(None, src)
            dst = Grid.intToBlock(None, dst)
        elif cmd == 'c':
            c = Grid.col
        elif cmd == 'r':
            c = Grid.row
            
        return lambda x: c(x, src, dst)
    
    

class Command:
    def __init__(self, f, t):
        self.coordinates=(f,t)
    pass


if __name__ == '__main__':
    inte = Interpreter()
    g = Grid()
    while(True):
        np = input()
        mo = inte.interpret(np)
        if mo:
            mo(g)
            print(g)