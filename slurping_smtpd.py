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
SMTPD_DIR_TEAM_MEMBERS = os.path.join(SMTPD_DIR, 'team_members')
SMTPD_PORT = os.getenv('SMTPD_PORT', 2525)

NO_EMAIL_AVAILABLE = "n/a"


def get_smtpd_status_info():
    return "Team Member Emails backlog: {}".format(get_team_member_backlog_count())


def get_team_member_backlog_count():
    return len([name for name in os.listdir(SMTPD_DIR_TEAM_MEMBERS) if os.path.isfile(name)])


def get_last_message_for(email_address):
    filename = slugify(email_address)
    try:
        with open(os.path.join(SMTPD_DIR, filename), 'r') as fh:
            return fh.read()
    except IOError:
        pass
    return NO_EMAIL_AVAILABLE


team_member_acquisition_lock = Lock()
TEAM_MEMBER_EMAIL_IDENTIFIER = 'href="[^"]+/questionnaire/[^"]+"'
TEAM_MEMBER_SURVEY_LINK_PATTERN = 'href="[^"]+/(questionnaire/[^"]+)"'
TEAM_MEMBER_NOT_AVAILABLE = "n/a"


def _extract_activation_link(content):
    m = re.search(TEAM_MEMBER_SURVEY_LINK_PATTERN, content, re.MULTILINE)
    if m:
        return m.group(1)


def _find_team_member_email():
    """
    You don't need to tell me this is awful and could be sped up :)
    It's just not quite awful enough for me to care just yet.

    Caching some may work, but I'm not sure if this is run in threads.
    The right answer is probably to stick all the emails into Redis
    instead of the filesystem.  Clients could then pull them straight
    from redis on the master.
    """
    try:
        first_filename = os.path.join(SMTPD_DIR_TEAM_MEMBERS, os.listdir(SMTPD_DIR_TEAM_MEMBERS)[0])
        with open(first_filename, 'r') as filehandle:
            url = filehandle.read()  # it only contains the activation link
        os.remove(first_filename)
        return url
    except IndexError:
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
        write_into_dir = SMTPD_DIR
        if re.search(TEAM_MEMBER_EMAIL_IDENTIFIER, data):
            write_into_dir = SMTPD_DIR_TEAM_MEMBERS
            # reduce contents to just the activation link
            data = _extract_activation_link(data)
        for email_address in rcpttos:
            filename = os.path.join(write_into_dir, slugify(email_address))
            with open(filename, 'w+') as fh:
                fh.write(data)
                logger.info("Writing email to: {}".format(filename))
                # print(data)


def create_tmp_dirs():
    for dirpath in [SMTPD_DIR, SMTPD_DIR_TEAM_MEMBERS]:
        try:
            os.mkdir(dirpath)
        except OSError as e:
            print(e)

if __name__ == "__main__":
    logger.info("Starting SMTPD...")
    create_tmp_dirs()
    s = PutLastestEmailInFilesystem(("0.0.0.0", SMTPD_PORT), None)
    asyncore.loop()
