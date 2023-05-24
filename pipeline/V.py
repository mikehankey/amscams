from vpython import *

sphere(pos=vector(0,0,0), radius = .5, color=color.green, idx=1)
sphere(pos=vector(-10,-10,10), radius = .5, color=color.green, idx=1)

ground = box (pos=vector(0, 0, 0), size=vector(100, .1, 100 ),  color = color.blue)
ground = box (pos=vector(0, 20, 0), size=vector(100, .1, 100 ),  color = color.blue, opacity=.3)
ground = box (pos=vector(0, 40, 0), size=vector(100, .1, 100),  color = color.blue, opacity=.3)
ground = box (pos=vector(0, 60, 0), size=vector(100, .1, 100),  color = color.blue, opacity=.3)
ground = box (pos=vector(0, 80, 0), size=vector(100, .1, 100),  color = color.blue, opacity=.3)
ground = box (pos=vector(0, 100, 0), size=vector(100,.1, 100),  color = color.blue, opacity=.3)

L=100
R = L/100
d = L-2
xaxis = cylinder(pos=vec(0,0,0), axis=vec(0,0,d/2), radius=R, color=color.yellow)
yaxis = cylinder(pos=vec(0,0,0), axis=vec(d/2,0,0), radius=R, color=color.yellow)
zaxis = cylinder(pos=vec(0,0,0), axis=vec(0,d,0), radius=R, color=color.yellow)
k = 1.02
h = 0.05*L
text(pos=xaxis.pos+k*xaxis.axis/2, text='x', height=h, align='center', billboard=True, emissive=True)
text(pos=yaxis.pos+k*yaxis.axis/2, text='y', height=h, align='center', billboard=True, emissive=True)
text(pos=zaxis.pos+k*zaxis.axis, text='z', height=h, align='center', billboard=True, emissive=True)

arrow(pos = vector(-50, 100, -50),
      axis = vector(1, -1, -1),
      color = vector(1, 1, 1),
      up = vector(-1, -1, -1),
      length=50
      )

povexport.export("test.jpg")
