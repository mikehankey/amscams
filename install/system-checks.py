"""
system-checks.py

CHECK FIX ASTROMETRY.NET PROBLEMS (and other system problems)

"""
import subprocess
import os
def check_fix_astrometry(cmds = [], msgs = []):
    # is the latest version installed
    if os.path.exists("/usr/bin/solve-field") is False:
        print("Latest version of Astrometry.net not installed")
        print("Installing Astrometry.net")
        cmd = "sudo apt-get install astrometry.net"
        cmds.append(cmd)
    else:
        msgs.append("Latest version of Astrometry.net is installed")
        
    # are the indexes installed for the latest version
    index_files = os.listdir("/usr/share/astrometry")
    if len(index_files) < 4:
        print("Index files missing")
        cmd = "wget http://broiler.astrometry.net/~dstn/4100/index-4116.fits -O /usr/share/astrometry/index-4116.fits"
        cmds.append(cmd)
        cmd = "wget http://broiler.astrometry.net/~dstn/4100/index-4117.fits -O /usr/share/astrometry/index-4117.fits"
        cmds.append(cmd)
        cmd = "wget http://broiler.astrometry.net/~dstn/4100/index-4118.fits -O /usr/share/astrometry/index-4118.fits"
        cmds.append(cmd)
        cmd = "wget http://broiler.astrometry.net/~dstn/4100/index-4119.fits -O /usr/share/astrometry/index-4119.fits"
        cmds.append(cmd)
    else:
        msgs.append("Latest Astrometry.net index files are installed.")
    
    # is the old version disabled
    if os.path.exists("/usr/local/astrometry/") is True:
        cmd = "mv /usr/local/astrometry /usr/local/astrometry.old"
        cmds.append(cmd)
    else:
        msgs.append("Old Astrometry.net un-installed.")
        
    for cmd in cmds:
        print(cmd)
        #os.system(cmd)
    for msg in msgs:
        print(msg)
        #os.system(cmd)

check_fix_astrometry()
print("DONE")
