class velocity:
    def __init__(self, permlist):
        self.permutations = permlist

    def __add__(self, v2):
        v = self.copy()
        v.append(v2)
        return v

    def __mul__(self, coeff):
        v = self.copy()
        n = len(self.permutations)

        while len(v.permutations) < coeff*n:
            v.permutations.expand(self)
        return v[:n]

def add(v1, v2):
    v = v1.copy()
    v.append(v2)
    return v

def times(v1, coeff):
    v = v1.copy()
    n = len(v1)

    while len(v.permutations) < coeff*n:
        v.permutations.expand(self)

    return v[:n]

def minus(p1, p2):
    p = p1.copy
    permlist = []

    # repeat until p1 has become p2
    while(p1 != p2):

        for i in range(len(p)):
            if(p[i] != p2[i]):
                permuteTwo(p, i, p.index(p2[i]))
                permlist.append([i, p.index(p2[i])])

    return permlist

