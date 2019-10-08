import threading

import time

def fun1(a, b):
  #time.sleep(1)
  c = a + b
  print(c)

thread1 = threading.Thread(target = fun1, args = (12, 10))
thread1.start()
thread2 = threading.Thread(target = fun1, args = (10, 17))
thread2.start()
print('\nTotal number of threads', threading.activeCount())
print('List of threads: ', threading.enumerate())
