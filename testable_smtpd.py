import smtpd
import asyncore


class PutLastestEmailInFilesystem(smtpd.SMTPServer):
    def process_message(self, peer, mailfrom, rcpttos, data, **kwargs):
        print(peer)
        print(mailfrom)
        print(rcpttos)
        print(data)
        print(kwargs)

if __name__ == "__main__":
    s = PutLastestEmailInFilesystem(("0.0.0.0", 2525), None)
    asyncore.loop()
