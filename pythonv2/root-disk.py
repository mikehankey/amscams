#!/bin/bash
import os
import requests

def send_mail(name, email, subject, message):

    # Construct the payload as a dictionary
    payload = {
        "name": name,
        "email": email,
        "subject": subject,
        "message": message
    }

    # URL of the Lambda function
    url = "https://dvvrmz03kd.execute-api.us-east-1.amazonaws.com/"

    # Send the POST request
    response = requests.post(url, json=payload)

    if response.status_code == 200:
        # Parse the response if needed (assuming JSON response)
        response_data = response.json()
        print(response_data)  # Log the successful response
        return True
    else:
        return response.status_code


#send_mail("Mike", "mike.hankey@gmail.com", "test", "testing")

# Clean up apt cache
os.system("apt-get clean")

# Remove old kernels (except the current one)
os.system("apt-get autoremove -y")

# Clean up system journal logs
os.system("journalctl --vacuum-time=1d")

# Remove orphaned packages (Debian/Ubuntu)
os.system("deborphan | xargs apt-get -y remove --purge")

# Remove temporary files older than 10 days
os.system("find /tmp -type f -atime +2 -delete")


if os.path.exists("/home/ams/REFIT_METEOR_FRAMES") is True:
    os.system("rm -rf /home/ams/REFIT_METEOR_FRAMES")
    
# Send an email or alert if disk usage is high
#CURRENT=$(df / | grep / | awk '{ print $5}' | sed 's/%//g')
#THRESHOLD=90

os.system("touch diskcheck.txt")
os.system("sudo -u ams -i cp /home/ams/amscams/conf/as6.json /home/ams/amscams/conf/as6.json.back") 
