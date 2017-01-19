import os
import smtpd
import asyncore
import requests

SMTPD_PORT = os.getenv('SMTPD_PORT', 2525)
SMTPD_HOSTNAME = os.getenv('SMTPD_HOSTNAME', requests.get("http://169.254.169.254/latest/meta-data/public-hostname").content)


class PutLastestEmailInFilesystem(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print(peer)
        print(mailfrom)
        print(rcpttos)
        print(data)
        print(kwargs)

if __name__ == "__main__":
    s = PutLastestEmailInFilesystem(("0.0.0.0", SMTPD_PORT), None)
    asyncore.loop()
