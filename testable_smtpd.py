import os
import smtpd
import asyncore
import requests
import logging
from slugify import slugify

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

SMTPD_DIR = os.getenv("SMTPD_DIR", "/tmp/smtpd/")
SMTPD_PORT = os.getenv('SMTPD_PORT', 2525)
SMTPD_HOSTNAME = os.getenv('SMTPD_HOSTNAME', None)

if SMTPD_HOSTNAME is None:
    logger.info("Asking AWS meta-data server for our public name...")
    SMTPD_HOSTNAME = requests.get("http://169.254.169.254/latest/meta-data/public-hostname", timeout=10).content


def get_last_message_for(email_address):
    filename = slugify(email_address)
    try:
        with open(os.path.join(SMTPD_DIR, filename), 'r') as fh:
            return fh.read()
    except FileNotFoundError:
        pass


class PutLastestEmailInFilesystem(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        for email_address in rcpttos:
            filename = os.path.join(SMTPD_DIR, slugify(email_address))
            with open(filename, 'w+') as fh:
                fh.write(data)
                logger.info("Writing email to: {}".format(filename))
                # print(data)

if __name__ == "__main__":
    logger.info("Starting SMTPD...")
    s = PutLastestEmailInFilesystem(("0.0.0.0", SMTPD_PORT), None)
    asyncore.loop()
