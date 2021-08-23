import subprocess
from lib.PipeUtil import cfe, load_json_file, save_json_file

class SystemHealth():
   def __init__(self):
      self.json_conf = load_json_file("../conf/as6.json")
      self.data_dirs = {}
      self.data_dirs["/mnt/ams2/HD"] = {}
      self.data_dirs["/mnt/ams2/HD"]['max_size'] = 400
      self.data_dirs["/mnt/ams2/SD/proc2"] = {}
      self.data_dirs["/mnt/ams2/SD/proc2"]['max_size'] = 350

   def make_report(self):
      print("SYSTEM HEALTH REPORT")
      df_data, mounts = self.run_df()
      print("DF DATA:", df_data)
      print("MOUNTS:", mounts)
      self.check_quotas()
      for dd in self.data_dirs:
         print("DD:", dd, self.data_dirs[dd])

   def check_quotas(self):
      for tdir in self.data_dirs:
         output = self.do_du(tdir) 
         if output is not None:
            used = output[0]
            used = used.replace("G", "")
            used = used.replace("M", "")
            used = used.replace("K", "")
            self.data_dirs[tdir]['used_size'] = int(float(used))
            


   def do_du(self,tdir):
      cmd = "du -h " + tdir
      print(cmd)
      output = subprocess.check_output(cmd, shell=True).decode("utf-8")
      lines = output.split("\n")
      match = None
      for line in lines:
         el = line.split("\t")
         if len(el) > 1:
            if el[1] == tdir:
               match = el

      return(match)

   def run_df(self):
      df_data = []
      mounts = {}
      if True:
         cmd = "df -h "
         output = subprocess.check_output(cmd, shell=True).decode("utf-8")
         #   Filesystem                 Size  Used Avail Use% Mounted on

         for line in output.split("\n"):
            #line = line.replace("  ", " ")
            temp = " ".join(line.split())
            disk_data = temp.split(" ")
            if len(disk_data) > 5:
               file_system = disk_data[0]
               size = disk_data[1]
               used  = disk_data[2]
               avail = disk_data[3]
               used_perc = disk_data[4]
               mount = disk_data[5]
               print(mount, used_perc)
               if mount == "/" or mount == "/mnt/ams2" or mount == "/mnt/archive.allsky.tv" or mount == "/home":
                  df_data.append((file_system, size, used, avail, used_perc, mount))
                  used_perc = used_perc.replace(" ", "")
                  mounts[mount] = int(used_perc.replace("%", ""))
      else:
         print("Failed du")

      return(df_data, mounts)
