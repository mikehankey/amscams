from multiprocessing import Process

def calc_planes(x):
   print("FUNC!")
   for x in my_numbers:
      print('%s cube is %s' % (x, x**3))

if __name__ == '__main__':
   my_numbers = [3, 4, 5, 6, 7, 8]
   p = Process(target=calc_planes, args=('x',))
   p.start()
p.join
print ("Done")
