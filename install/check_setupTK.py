#!/usr/bin/python3
from tkinter import *
import tkinter.messagebox as tkMessageBox
from tkinter import ttk


class

window = Tk()
window.title("ALLSKY7 SOFTWARE INSTALLER")
window.geometry("600x400")
window.configure()

#a = Label(window, text = "Use this form to complete the one time station and software registration.").grid(row=0,column=0) 

        #For new stations this will complete the install process. For existing stations it will collect the information to enable the systems NETWORK functionality and ensure future updates. ").grid(row=0, column=0)

T = Text(window, height=3, width=75)
T.grid(row=0,column=0,columnspan=2)
T.insert(END, "Use this form to complete the \nsystem registration and software configuration." )

a = Label(window, text = "Your Full Name").grid(row=1, column=0)
a1 = Entry(window).grid(row=1,column=1)

b = Label(window, text = "Your Email").grid(row=2, column=0)
b1 = Entry(window).grid(row=2,column=1)

c = Label(window, text = "Cell Phone starting with + country code").grid(row=3, column=0)
c1 = Entry(window).grid(row=3,column=1)

d = Label(window, text = "ALLSKY Username").grid(row=4, column=0)
d1 = Entry(window).grid(row=4,column=1)

e = Label(window, text = "ALLSKY Password").grid(row=5, column=0)
e1 = Entry(window).grid(row=5,column=1)

f = Label(window, text = "This Station ID").grid(row=6, column=0)
f1 = Entry(window).grid(row=6,column=1)

g = Label(window, text = "Registration PIN Code").grid(row=7, column=0)
g1 = Entry(window).grid(row=7,column=1)

#b = Label(window, text = "Your Email").grid(row=2, column=0)
#b1 = Entry(window).grid(row=2,column=1)

def submit_register():
   tkMessageBox.showwarning("Sending Registration Data.", "ok" )

btn = ttk.Button(window, text="submit", command=submit_register).grid(row=8,column=0)

#ttk.Button(window, text="Hello").grid()
window.mainloop()
#root.withdraw()
#tkMessageBox.showwarning('ALLSKY7 SETUP', 'We see this is the first time you have booted with ALLSKY7 software. We need to register your system and update your configuration.')
