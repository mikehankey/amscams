#!/bin/sh

sudo cp crontab-ams /var/spool/cron/crontabs/ams
sudo cp crontab-root /var/spool/cron/crontabs/root
sudo chown ams /var/spool/cron/crontabs/ams
sudo chgrp crontab /var/spool/cron/crontabs/ams
sudo chmod 600 /var/spool/cron/crontabs/ams
sudo /etc/init.d/cron restart
