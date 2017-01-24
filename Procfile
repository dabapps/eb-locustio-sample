locust-master: /bin/bash -c "exec /usr/local/bin/locust -f locustfile.py --port=9876 --master"
locust-follower: /bin/bash -c "exec /usr/local/bin/locust -f locustfile.py --port=9876 --slave --master-host=$(<.masterIP)"
slurping-smtpd: python slurping_smtpd.py
