import copy


class Fragment:
    pass

class BottomSlash(Fragment):
    def __str__(self):
        return "◢"


class TopSlash(Fragment):
    def __str__(self):
        return "◤"


class BottomBackSlash(Fragment):
    def __str__(self):
        return "◣"


class TopBackSlash(Fragment):
    def __str__(self):
        return "◥"


SE = BottomSlash()
NW = TopSlash()
SW = BottomBackSlash()
NE = TopBackSlash()


class Block:
    def indexes(self, rows, columns):
        return ((r,c) for r in rows for c in columns)
    pass

class QI(Block):
    def indexes(self):
        return super().indexes([0,1],[0,1])
    

class QII(Block):
    def indexes(self):
        return super().indexes([0,1],[2,3])

class QIII(Block):
    def indexes(self):
        return super().indexes([2,3],[0,1])

class QIV(Block):
    def indexes(self):
        return super().indexes([2,3],[2,3])

I , II, III, IV = QI(), QII(), QIII(), QIV()

class GridPattern:
    pattern = [ [SE, SW, SE, SW]
        ,[NE, NW, NE, NW]
        ,[SE, SW, SE, SW]
        ,[NE, NW, NE, NW]]


class Grid:

    
    
    def h_axis_symmetry(self):
        return [self.h_specular[x] for x in self.grid[0]] == self.grid[3] \
               and [self.h_specular[x] for x in self.grid[1]] == self.grid[2]
    
    def v_axis_symmetry(self):
        for x in self.grid:
            if x[0:2] != [self.v_specular[y] for y in x[:-3:-1]]:
                return False
        return True
    
    def h_axis_color_symmetry(self):
        return [self.h_specular[self.c_specular[x]] for x in self.grid[0]] == self.grid[3] and [self.h_specular[self.c_specular[x]] for x in self.grid[1]] == self.grid[2]
    
    def v_axis_color_symmetry(self):
        for x in self.grid:
            if x[0:2] != [self.v_specular[self.c_specular[y]] for y in x[:-3:-1]]:
                return False
        return True
    
    def pi_symmetry(self):
        for r in range(0,2):
            for c in range(0,4):
                if self.c_specular[self.grid[r][c]] != self.grid[-(r+1)][-(c+1)]:
                    return False
        return True
    
    
    def pi_color_symmetry(self):
        for r in range(0,2):
            for c in range(0,4):
                if self.grid[r][c] != self.grid[-(r+1)][-(c+1)]:
                    return False
        return True
        
    
    def symmetries(self):
        syms = []
        for x in self.possible_symmetries:
            if x[1]():
                syms.append(x[0])
        return syms
    
    def __init__(self):
        self.grid = self.__shallow_copy_of_matrix(GridPattern.pattern)
        self.possible_symmetries = [("Horizontal", self.h_axis_symmetry),
            ("Horizontal color", self.h_axis_color_symmetry),
            ("Vertical", self.v_axis_symmetry),
            ("Vertical color", self.v_axis_color_symmetry),
            ("180 deg", self.pi_symmetry),
            ("180 deg color", self.pi_color_symmetry)]
        self.v_specular = {
            SW : SE,
            NE : NW,
            NW : NE,
            SE : SW,
        }
        
        self.h_specular = {
            SW : NW,
            NE : SE,
            NW : SW,
            SE : NE,
        }
        
        self.c_specular = {
            SW : NE,
            NE : SW,
            NW : SE,
            SE : NW,
        }
        
    def __copy__(self):
        cp = Grid()
        cp.grid = self.__shallow_copy_of_matrix(self.grid)
        return cp
        
    def __shallow_copy_of_matrix(self, matr):
        return [[el for el in row] for row in matr]
    
    def row(self, f, t):
        tmp = self.grid[f]
        self.grid[f] = self.grid[t]
        self.grid[t] = tmp
    
    def col(self, f, t):
        for r in self.grid:
            tmp = r[f]
            r[f] = r[t]
            r[t] = tmp
    
    def intToBlock(self, i):
        if i == 0:
            return I
        elif i == 1:
            return II
        elif i == 2:
            return III
        elif i == 3:
            return IV
        else:
            return None
    
    def block(self, f, t):
        if isinstance(f,int):
            f = self.intToBlock(f)
        if isinstance(t, int):
            t = self.intToBlock(t)
        # f and t are instances of block
        from_ = f.indexes()
        to_ = t.indexes()
        for (ir, ic) in from_:
            (jr, jc) = next(to_)
            tmp = self.grid[ir][ic]
            self.grid[ir][ic] = self.grid[jr][jc]
            self.grid[jr][jc] = tmp

    def __str__(self):
        buf = ""
        for r in self.grid:
            for c in r:
                buf+=str(c)
            buf+="\n"
        return buf
                

if __name__ == '__main__':
    g = Grid()
    print(g)
    g.row(1,2)
    print("moving rows")
    print(g)
    print("moving blocks")
    g.block(I, IV)
    print(g)