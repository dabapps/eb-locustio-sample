import re
import os
import smtpd
import asyncore
import logging
from slugify import slugify
from multiprocessing import Lock

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__file__)

SMTPD_DIR = os.getenv("SMTPD_DIR", "/tmp/smtpd/")
SMTPD_PORT = os.getenv('SMTPD_PORT', 2525)

NO_EMAIL_AVAILABLE = "n/a"


def get_last_message_for(email_address):
    filename = slugify(email_address)
    try:
        with open(os.path.join(SMTPD_DIR, filename), 'r') as fh:
            return fh.read()
    except IOError:
        pass
    return NO_EMAIL_AVAILABLE


team_member_acquisition_lock = Lock()
TEAM_MEMBER_EMAIL_IDENTIFIER = "send you the attached questionnaire"
TEAM_MEMBER_SURVEY_LINK_PATTERN = 'href="[^"]+/(questionnaire/[^"]+)"'
TEAM_MEMBER_NOT_AVAILABLE = "n/a"


def _find_team_member_email():
    for dir_name, subdir_names, filenames_list in os.walk(SMTPD_DIR):
        for filename in filenames_list:
            full_filename = os.path.join(dir_name, filename)
            # print(full_filename)
            with open(full_filename, "r") as file_handle:
                for line in file_handle:
                    if re.search(TEAM_MEMBER_EMAIL_IDENTIFIER, line):
                        # Extract URL
                        for line in file_handle:
                            # <a href="http://wethrive.ctf.sh:32768/questionnaire/42761994-ee94-47c3-825c-1daa6a48d800">here</a>
                            m = re.search(TEAM_MEMBER_SURVEY_LINK_PATTERN, line)
                            if m:
                                # Delete file
                                os.remove(full_filename)
                                return m.group(1)
    return TEAM_MEMBER_NOT_AVAILABLE


def get_next_team_member():
    # Try and make sure we don't hand out the same one multiple times
    # by using a lock.
    team_member_acquisition_lock.acquire()
    result = _find_team_member_email()
    team_member_acquisition_lock.release()
    return result


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
    try:
        os.mkdir(SMTPD_DIR)
    except OSError:
        pass
    s = PutLastestEmailInFilesystem(("0.0.0.0", SMTPD_PORT), None)
    asyncore.loop()
