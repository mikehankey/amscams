#!/usr/bin/python3
from tkinter import *
import tkinter.messagebox as tkMessageBox
from tkinter import ttk
import os

#window = Tk()

if os.path.isfile("/home/ams/amscams/install_complete.txt") == 0:
   

   tkMessageBox.showwarning("REBOOT SYSTEM", "The system needs to reboot to complete the ALLSKY SOFTWARE install. \nEnter the system password in the terminal and press enter or reboot from the desktop icon in the top right corner." )
   os.system("sudo touch /home/ams/amscams/install_complete.txt && shutdown -r now")

#ttk.Button(window, text="Hello").grid()
#window.mainloop()
#root.withdraw()
#tkMessageBox.showwarning('ALLSKY7 SETUP', 'We see this is the first time you have booted with ALLSKY7 software. We need to register your system and update your configuration.')
