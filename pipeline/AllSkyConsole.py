#!/usr/bin/python3
import os
import sys
from termcolor import colored, cprint



class AllSkyConsole():

   def __init__(self):
      self.retro()


   def retro(self):
      self.header = """
  ____  _      _      _____ __  _  __ __
 /    || |    | |    / ___/|  |/ ]|  |  |
|  o  || |    | |   (   \_ |  ' / |  |  |
|     || |___ | |___ \__  ||    \ |  ~  |
|  _  ||     ||     |/  \ ||     ||___, |
|  |  ||     ||     |\    ||  .  ||     |
|__|__||_____||_____| \___||__|\_||____/
** O B S E R V I N G   S O F T W A R E **

AllSky.com/ALLSKY7 - (C) Mike Hankey 2016-2022 
Licensed use permitted. Restrictions apply.

Type "help" for a list of commands
      """

if __name__ == "__main__":
   os.system("clear")
   Console = AllSkyConsole()   
   print(Console.header)
   #cprint('\rWelcome...', 'red', attrs=['dark'], end='')
   #esc = chr(27)
   #print(f'a{esc}[5m_\u2592b\u2588{esc}[m_c')
   cmd = None
   while cmd != "quit":
      cmd = input("allsky>")
      print("you entered:", cmd)

