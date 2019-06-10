
from lib.UtilLib import calc_dist

def setup_metframes(mfd):
   # establish initial first x,y last x,y
   fx = mfd[0][2]
   fy = mfd[0][3]
   lx = mfd[-1][2]
   ly = mfd[-1][3]

   dir_x = fx - lx
   dir_y = fy - ly
   if dir_x < 0:
      x_dir_mod = 1
   else:
      x_dir_mod = -1
   if dir_y < 0:
      y_dir_mod = 1
   else:
      y_dir_mod = -1


   # establish first frame number, last frame number and total frames
   ff = mfd[0][1]
   lf = mfd[-1][1]
   tf = lf - ff
   tf = tf + 1

   # establish initial line distance and x_incr
   line_dist = calc_dist((fx,fy),(lx,ly))
   x_incr = int(line_dist / (tf ))

   metframes = {}
   etime = 0
   for i in range(0,tf):
      fi = i + ff
      metframes[fi] = {}
      if i > 0:
         etime = i / 25
      else:
         etime = 0
      metframes[fi]['etime'] = etime
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = 0
      metframes[fi]['hd_x'] = 0
      metframes[fi]['hd_y'] = 0
      metframes[fi]['w'] = 0
      metframes[fi]['h'] = 0
      metframes[fi]['max_px'] = 0
      metframes[fi]['ra'] = 0
      metframes[fi]['dec'] = 0
      metframes[fi]['az'] = 0
      metframes[fi]['el'] = 0
      metframes[fi]['len_from_last'] = 0
      metframes[fi]['len_from_start'] = 0
   xs = []
   ys = []
   for fd in mfd:
      frame_time, fn, hd_x,hd_y,w,h,max_px,ra,dec,az,el = fd
      fi = fn
      xs.append(hd_x)
      ys.append(hd_y)
      metframes[fi]['fn'] = fi
      metframes[fi]['ft'] = frame_time
      metframes[fi]['hd_x'] = hd_x
      metframes[fi]['hd_y'] = hd_y
      metframes[fi]['w'] = w
      metframes[fi]['h'] = h
      metframes[fi]['max_px'] = max_px
      metframes[fi]['ra'] = ra
      metframes[fi]['dec'] = dec
      metframes[fi]['az'] = az
      metframes[fi]['el'] = el
   metconf = {}
   metconf['xs'] = xs
   metconf['ys'] = ys
   metconf['fx'] = fx
   metconf['fy'] = fy
   metconf['lx'] = lx
   metconf['ly'] = ly
   metconf['tf'] = tf
   metconf['runs'] = 0
   metconf['line_dist'] = line_dist
   metconf['x_incr'] = x_incr
   metconf['x_dir_mod'] = x_dir_mod
   metconf['y_dir_mod'] = y_dir_mod

   return(metframes, metconf)
