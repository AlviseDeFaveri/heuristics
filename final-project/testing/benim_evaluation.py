from scipy import *
from math import *
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import sys
import pyclipper
from functools import *
import scipy as scp
import random as rdm
import pickle


# Figure de visualisation de la parcelle
fig = plt.figure()
canv = fig.add_subplot(1,1,1)
canv.set_xlim(0,500)
canv.set_ylim(0,500)

# ************ Paramètres de la métaheuristique ***PSO=10000 DE=1500*********NB indiv 20*
"""Nb_Cycles = 15
Nb_Indiv = 10"""
ntaboo = 30
nbNeigh = 30
iterMax = 1000
idemMax = iterMax/10

# ***********************************************************

# ***************** Paramètres du problème ******************
# Différentes propositions de parcelles :
polygone1 = ((10,10),(10,400),(400,400),(400,10))
polygone2 = ((10,10),(10,300),(250,300),(350,130),(200,10))
polygone3 = ((50,150),(200,50),(350,150),(350,300),(250,300),(200,250),(150,350),(100,250),(100,200))
polygone4 = ((50,50),(50,400),(220,310),(220,170),(330,170),(330,480),(450,480),(450,50))

def areasize(polygone):
    pola=list(polygone)
    p0=pola[0]
    p1=pola[1]
    p2=pola[2]
    p3=pola[3]
    return (distance(p0,p1)*distance(p0,p3))

def lostarea(polygone,rect):
    return (areasize(polygone)-areasize(rect))


# ***********************************************************

# Transforme le polygone en liste pour l'affichage.
def poly2list(polygone):
    polygonefig = list(polygone)
    polygonefig.append(polygonefig[0])
    return polygonefig

# Fenètre d'affichage
def dessine(polyfig,rectfig):
    global canv, codes
    canv.clear()
    canv.set_xlim(0,500)
    canv.set_ylim(0,500)
    # Dessin du polygone
    codes = [Path.MOVETO]
    for i in range(len(polyfig)-2):
      codes.append(Path.LINETO)
    codes.append(Path.CLOSEPOLY)
    path = Path(polyfig, codes)
    patch = patches.PathPatch(path, facecolor='orange', lw=2)
    canv.add_patch(patch)

    # Dessin du rectangle
    codes = [Path.MOVETO]
    for i in range(len(rectfig)-2):
      codes.append(Path.LINETO)
    codes.append(Path.CLOSEPOLY)
    path = Path(rectfig, codes)
    patch = patches.PathPatch(path, facecolor='grey', lw=2)
    canv.add_patch(patch)

    # Affichage du titre (aire du rectangle)
    plt.title("Aire : {}".format(round(aire(rectfig[:-1]),2)))

    plt.draw()
    plt.pause(0.1)

def permuteOne(path,i):
    nv = path[:]
    e = nv.pop(i)
    nv.append(e)
    return nv

Henergy = []      # Energy
Htime = []        # time
Hbest = []        # distance

ltaboo = []       # taboo list

def bestNeighbor(path, nbNeigh, ltaboo):
    global bestV, bestDist
    #list of indices to swap to generate Neighbors
    b = generateneigh(polygone,path)
    bestV = b['pos']
    bestDist = b['eval']

    for i in range(nbNeigh):
        Neigh = generateneigh(polygone,path)
        if Neigh['pos'] not in ltaboo[:10]: #aspirion criteria
            d = Neigh['eval']
            if (d > bestDist):
                bestV = Neigh['pos']
                bestDist = d
    return (bestV,bestDist)

# Récupère les bornes de la bounding box autour de la parcelle
def getBornes(polygone):
    lpoly = list(polygone) #tansformation en liste pour parcours avec reduce
    #return reduce(lambda (xmin,xmax,ymin,ymax),(xe,ye): (min(xe,xmin),max(xe,xmax),min(ye,ymin),max(ye,ymax)),lpoly[1:],(lpoly[0][0],lpoly[0][0],lpoly[0][1],lpoly[0][1]))
    return reduce(lambda acc,e: (min(e[0],acc[0]),max(e[0],acc[1]),min(e[1],acc[2]),max(e[1],acc[3])),lpoly[1:],(lpoly[0][0],lpoly[0][0],lpoly[0][1],lpoly[0][1]))
# Transformation d'une solution du pb (centre/coin/angle) en rectangle pour le clipping
# Retourne un rectangle (A(x1,y1), B(x2,y2), C(x3,y3), D(x4,y4))
def pos2rect(pos):
    # coin : point A
    xa, ya = pos[0], pos[1]
    # centre du rectangle : point O
    xo, yo = pos[2], pos[3]
    # angle  AÔD
    angle = pos[4]

    # point D : rotation de centre O, d'angle alpha
    alpha = pi * angle / 180 # degre en radian
    xd = cos(alpha)*(xa-xo) - sin(alpha)*(ya-yo) + xo
    yd = sin(alpha)*(xa-xo) + cos(alpha)*(ya-yo) + yo
    # point C : symétrique de A, de centre O
    xc, yc = 2*xo - xa, 2*yo - ya
    # point B : symétrique de D, de centre O
    xb, yb = 2*xo - xd, 2*yo - yd

    # round pour le clipping
    return ((round(xa),round(ya)),(round(xb),round(yb)),(round(xc),round(yc)),(round(xd),round(yd)))


# Distance entre deux points (x1,y1), (x2,y2)
def distance(p1,p2):
    return sqrt((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2)

# Aire du rectangle (A(x1,y1), B(x2,y2), C(x3,y3), D(x4,y4))
# 	= distance AB * distance BC
def aire(rect):
    p1=rect[0]
    p2=rect[1]
    p3=rect[2]
    p4=rect[3]
    return (distance(p1,p2)*distance(p1,p4))

    #distance(p1[0],p1[1])* distance(p2[0],p2[1])
#def aire((pa, pb, pc, pd)):
#	return distance(pa,pb)*distance(pb,pc)

# Clipping
# Prédicat qui vérifie que le rectangle est bien dans le polygone
# Teste si
# 	- il y a bien une intersection (!=[]) entre les figures et
#	- les deux listes ont la même taille et
# 	- tous les points du rectangle appartiennent au résultat du clipping
# Si erreur (~angle plat), retourne faux
def verifcontrainte(rect, polygone):
    try:
        # Config
        pc = pyclipper.Pyclipper()
        pc.AddPath(polygone, pyclipper.PT_SUBJECT, True)
        pc.AddPath(rect, pyclipper.PT_CLIP, True)
        # Clipping
        clip = pc.Execute(pyclipper.CT_INTERSECTION, pyclipper.PFT_EVENODD, pyclipper.PFT_EVENODD)
        #all(iterable) return True if all elements of the iterable are true (or if the iterable is empty)
        return (clip!=[]) and (len(clip[0])==len(rect)) and all(list(map(lambda e:list(e) in clip[0], rect)))
    except pyclipper.ClipperException:
        # print rect
        return False

# Crée un individu (centre/coin/angle) FAISABLE
# un individu est décrit par votre metaheuristique contenant au moins:
# 	- pos : solution (centre/coin/angle) liste des variables
#	- eval :  aire du rectangle
#	- ... : autres composantes de l'individu
def initUn(polygone):
    global xmin,xmax,ymin,ymax
    anglemin = 1
    anglemax = 89
    boolOK = False

    while not boolOK: # tant que non faisable
        xo=random.uniform(xmin,xmax)
        yo=random.uniform(ymin,ymax)

        xa=xo+pow(-1,random.randint(0,1))*random.uniform(10,min(xo-xmin,xmax-xo))
        ya=yo+pow(-1,random.randint(0,1))*random.uniform(10,min(yo-ymin,ymax-yo))

        angle = random.uniform(anglemin,anglemax)

        pos = [round(xa),round(ya),round(xo),round(yo),angle]
        rect = pos2rect(pos)
        # calcul du clipping
        boolOK = verifcontrainte(rect,polygone)
    ev = aire(pos2rect(pos))
    return {'pos':pos, 'eval':ev}


def generateneigh(polygone,rect):
    global xmin,xmax,ymin,ymax
    anglemin = 1
    anglemax = 89
    boolOK = False
    xinit=rect[2]
    yinit=rect[3]
    while not boolOK: # tant que non faisable
        xo=random.uniform(xinit-20,xinit+20) # distance from our rectangle +- 20
        yo=random.uniform(yinit-20,yinit+20) # distance from our rectangle +- 20

        xa=xo+pow(-1,random.randint(0,1))*random.uniform(10,min(xo-xmin,xmax-xo))
        ya=yo+pow(-1,random.randint(0,1))*random.uniform(10,min(yo-ymin,ymax-yo))

        angle = random.uniform(anglemin,anglemax)

        pos = [round(xa),round(ya),round(xo),round(yo),angle]
        rect = pos2rect(pos)
        # calcul du clipping
        boolOK = verifcontrainte(rect,polygone)
    ev = aire(pos2rect(pos))
    return {'pos':pos, 'eval':ev}

"""# Init de la population
def initPop(nb,polygone):
    return [initUn(polygone) for i in range(nb)]

# Retourne la meilleure particule entre deux : dépend de la métaheuristique
def bestPartic(p1,p2):
    return p1

# Retourne une copie de la meilleure particule de la population
def getBest(population):
    return dict(reduce(lambda acc, e: bestPartic(acc,e),population[1:],population[0]))"""

results = []

for polygone in [polygone1, polygone2, polygone3, polygone4]:
    # Constante polygone dessinable
    polygonefig = poly2list(polygone)

    bestlist =[]

    for n in range(30):
        print(n)

        # *************************************** ALGO D'OPTIM ***********************************
        # calcul des bornes pour l'initialisation
        xmin,xmax,ymin,ymax = getBornes(polygone)
        # initialisation de la population (de l'agent si recuit simulé) et du meilleur individu.
        """pop = initPop(Nb_Indiv,polygone)
        best = getBest(pop)"""
        best=initUn(polygone)
        Henergy = []      # Energy
        Htime = []        # time
        Hbest = []        # distance

        ltaboo = []       # taboo list

        initsol = initUn(polygone) # choose randomly the first rectangle

        route = initsol['pos']
        dist = initsol['eval']

        best_route = route
        best_dist = dist

        # boucle principale (à affiner selon la métaheuristique / le critère de convergence choisi)
        #for i in range(Nb_Cycles):
            # déplacement

            # Mise à jour de la meilleure solution et affichage

        i=0
        cptIdem = 0
        # initialization of the taboo list
        ltaboo.insert(0,best_route)

        # main loop of the taboo algorithm
        while i <= iterMax: # and cptIdem <= idemMax:
            # get the best Neighbor
            (Neighbor, dist) = bestNeighbor(route, nbNeigh, ltaboo) #this is the original
            #(Neighbor, dist) = bestNeighor2(route, nbNeigh, ltaboo)# this is to run with the aspiration criteria

            # comparison to the best, if it is better, save it and refresh the figure
            if dist > best_dist:
                cptIdem = 0
                best_dist = dist
                best_route = Neighbor
                #draw(best_route, best_dist, x, y)
                #dessine(polygonefig, poly2list(pos2rect(best_route)))

            # add to taboo list
            ltaboo.insert(0,Neighbor)
            if (len(ltaboo) > ntaboo):
                ltaboo.pop()

            cptIdem += 1

            # next iteration
            i += 1
            route = Neighbor
            # historization of data
            if i % 10 == 0:
                Henergy.append(dist)
                Htime.append(i)
                Hbest.append(best_dist)

            best={'pos': best_route,'eval': best_dist}

        # FIN : affichages
        bestlist.append(best)
        #print(best['eval'])
        #dessine(polygonefig, poly2list(pos2rect(best["pos"])))
        #plt.show()

    results.append(bestlist)

with open('ts_eval.data', 'wb') as filehandle:
    # store the data as binary data stream
    pickle.dump(results, filehandle)

dessine(polygonefig, poly2list(pos2rect(best["pos"])))
plt.show()