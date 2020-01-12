#!/usr/bin/python
# Author: Alvise de'Faveri Tron
from scipy import *
from math import *
import matplotlib.pyplot as plt
from matplotlib.path import Path
import matplotlib.patches as patches
import sys
import pyclipper
from functools import *

# Figure de visualisation de la parcelle
fig = plt.figure()
canv = fig.add_subplot(1,1,1)
canv.set_xlim(0,500)
canv.set_ylim(0,500)

# ************ Paramètres de la métaheuristique ************
Nb_Cycles = 2000
Nb_Indiv = 15
# ***********************************************************

# ***************** Paramètres du problème ******************
# Différentes propositions de parcelles :
#polygone = ((10,10),(10,400),(400,400),(400,10))
#polygone = ((10,10),(10,300),(250,300),(350,130),(200,10))
polygone = ((50,150),(200,50),(350,150),(350,300),(250,300),(200,250),(150,350),(100,250),(100,200))
#polygone = ((50,50),(50,400),(220,310),(220,170),(330,170),(330,480),(450,480),(450,50))

psi,cmax = (0.7, 1.47)

# ******************* Previously implemented ******************

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


##
## Draw the whole "swarm" of rectangles
##
def dessineAll(polyfig,pop):
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
    for r in pop:
        rectfig = poly2list(pos2rect(r['pos']))
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
#   = distance AB * distance BC
def aire(rect):
    # AC
    l1 = distance(rect[0], rect[1])
    # AD
    l2 = distance(rect[0], rect[3])
    return l1*l2
#def aire((pa, pb, pc, pd)):
#   return distance(pa,pb)*distance(pb,pc)

# Clipping
# Prédicat qui vérifie que le rectangle est bien dans le polygone
# Teste si
#   - il y a bien une intersection (!=[]) entre les figures et
#   - les deux listes ont la même taille et
#   - tous les points du rectangle appartiennent au résultat du clipping
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
#   - pos : solution (centre/coin/angle) liste des variables
#   - eval :  aire du rectangle
#   - ... : autres composantes de l'individu
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

    ev = aire(rect)
    return {'vit':[0,0,0,0,0], 'pos':pos, 'eval':ev, 'bestpos':pos, 'besteval':ev, 'bestvois':[]}

# Init de la population
def initPop(nb,polygone):
    return [initUn(polygone) for i in range(nb)]


#********************** PSO Displacement Functions *****************************
##
## Add two velocities (sum element by element)
##
def add(v1, v2):
    res = [v1[i] + v2[i] for i in range(len(v1))]
    res[4] = abs(res[4])%180    # angle must be between 0 and 180 deg
    return res

##
## Multiply a velocity (multiply each element)
##
def times(v1, coeff):
    res = [coeff*v for v in v1]
    res[4] = abs(res[4])%180    # angle must be between 0 and 180 deg
    return res

##
## Subtract two velocities (subtract element by element)
##
def minus(p1, p2):
    res = [p1[i] - p2[i] for i in range(len(p1))]
    res[4] = abs(res[4])%180    # angle must be between 0 and 180 deg
    return res

##
## Calculate the velocity and move the particle
##
def move(particle):
    global psi,cmax
    nv = dict(particle)

    # calculate the velocity according to PSO parameters
    bp = minus(particle["bestpos"], particle["pos"])
    bv = minus(particle["bestvois"], particle["pos"])

    rbp = times(bp, cmax*random.uniform())
    rbv = times(bv, cmax*random.uniform())
    ps = times(particle["vit"],psi)

    a = add(ps, rbp)
    a = add(a, rbv)

    velocity = a

    # apply the velocity to the particle and calculate the new rectangle
    pos = particle["pos"]
    newpos = [pos[i] + velocity[i] for i in range(len(pos))]

    # if the new rectangle is inside the polygon, accept it
    if verifcontrainte(pos2rect(newpos), polygone):
        nv['vit'] = velocity
        nv['pos'] = newpos
        nv['eval'] = aire(pos2rect(newpos))
    # else generate a new particle (but keep the bestpos history)
    else:
        new = initUn(polygone)
        nv['vit'] = new['vit']
        nv['pos'] = new['pos']
        nv['eval'] = new['eval']

    return nv

#********************** PSO evaluation *****************************

# Retourne la meilleure particule entre deux : dépend de la métaheuristique
def bestPartic(p1,p2):
    if(p1['eval'] > p2['eval']):
        return p1
    else:
        return p2

# Retourne une copie de la meilleure particule de la population
def getBest(population):
    return dict(reduce(lambda acc, e: bestPartic(acc,e),population[1:],population[0]))

#********************** PSO update *****************************

# Update information for the particles of the population
def update(particle,bestParticle):
    nv = dict(particle)
    if(particle["eval"] > particle["besteval"]):
        nv['bestpos'] = particle["pos"]
        nv['besteval'] = particle["eval"]
    nv['bestvois'] = bestParticle["bestpos"]
    return nv


# Constante polygone dessinable
polygonefig = poly2list(polygone)


##
## Return the nbn nearest particles in the swarm list
##
def getNeighborhood(particle, swarm, nbn):
    neighbors = []
    tot = (int)(nbn/2)
    initIndex = swarm.index(particle)

    # get successors
    for i in range(initIndex+1, initIndex + tot +1):
        if i < len(swarm):
            neighbors.append(swarm[i])
            tot -= 1
        else:
            break

    # get predecessors
    for i in range(initIndex-tot-1, initIndex):
        if i >= 0:
            neighbors.append(swarm[i])
            tot -= 1
        else:
            break

    return neighbors

##
## Update information for the particles
##
def localUpdate(particle,swarm,nbn):
    # get best between neighbors instead of in the whole swarm
    bestParticle = getBest(getNeighborhood(particle,swarm,nbn))

    # update
    nv = dict(particle)
    if(particle["eval"] < particle["besteval"]):
        nv['bestpos'] = particle["pos"][:]
        nv['besteval'] = particle["eval"]
    nv['bestvois'] = bestParticle["bestpos"][:]
    return nv


# ****************************** ALGO D'OPTIM **********************
# calcul des bornes pour l'initialisation
xmin,xmax,ymin,ymax = getBornes(polygone)

# initialisation de la population (de l'agent si recuit simulé) et du meilleur individu.
pop = initPop(Nb_Indiv,polygone)
best = getBest(pop)
best_cycle = best

# boucle principale (à affiner selon la métaheuristique / le critère de convergence choisi)
for i in range(Nb_Cycles):

    # Update informations of each particle
    pop = [update(e,best_cycle) for e in pop] # global best
    #pop = [localUpdate(e,pop, 4) for e in pop] # local best

    # Move each particle according to the element
    pop = [move(e) for e in pop]

    # Update of the best solution
    best_cycle = getBest(pop)
    if (best_cycle["eval"] > best["eval"]):
        best = best_cycle

    dessine(polygonefig, poly2list(pos2rect(best["pos"])))
    #dessineAll(polygonefig, pop)

dessine(polygonefig, poly2list(pos2rect(best["pos"])))
plt.show()
