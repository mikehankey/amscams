fp = open("pip.conf")
PYTHON_EXE = "python3"
for line in fp:
   line = line.replace("\n", "")
   cmd = PYTHON_EXE + " -m pip install " + line
   print(cmd)
