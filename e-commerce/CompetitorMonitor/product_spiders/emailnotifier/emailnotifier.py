import smtplib
import email
import os
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.mime.audio import MIMEAudio
from email.mime.image import MIMEImage
from email.encoders import encode_base64
from mimetypes import guess_type
from os.path import basename

class EmailNotifierException(Exception):
    pass

class EmailNotifier(object):
    def __init__(self, username, password, from_, host, port):
        self.username = username
        self.password = password
        self.from_ = from_
        self.host = host
        self.port = port

    def getAttachment(self, path, charset='ASCII'):
        contentType, encoding = guess_type(path)

        if contentType is None or encoding is not None:
            contentType = 'application/octet-stream'

        mainType, subType = contentType.split('/', 1)
        _file = open(path, 'rb')

        if mainType == 'text':
            attachment = MIMEText(_file.read(), subType, charset)
        elif mainType == 'message':
            attachment = email.message_from_file(_file)
        elif mainType == 'image':
            attachment = MIMEImage(_file.read(), _subType=subType)
        elif mainType == 'audio':
            attachment = MIMEAudio(_file.read(), _subType=subType)
        else:
            attachment = MIMEBase(mainType, subType)
            attachment.set_payload(_file.read())
            encode_base64(attachment)

        _file.close()

        attachment.add_header('Content-Disposition', 'attachment',
            filename=basename(path))

        return attachment

    def send_notification(self, recipients, subject, body, attachments=None, bcc=[]):
        plain_part = MIMEText(body)

        if attachments:
            msg = MIMEMultipart()
            msg.preamble = 'This is a multi-part message in MIME format.'
            msg.epilogue = ''
            msg.attach(plain_part)
            for path in attachments:
                msg.attach(self.getAttachment(path))
        else:
             msg = plain_part

        msg['From'] = self.from_
        msg['Subject'] = subject
        msg['To'] = ','.join(recipients)
        if type(bcc) in [str, unicode]:
            bcc = [bcc]
        try:
            server = smtplib.SMTP(self.host, self.port)
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(self.username, self.password)
            server.sendmail(self.from_, recipients + bcc, msg.as_string())
            server.quit()
        except smtplib.SMTPException, e:
            raise EmailNotifierException(e.message)


if __name__ == '__main__':
    notifier = EmailNotifier('adrian@inovica.com',
                             'yamaha197',
                             'reporting@competitormonitor.com',
                             'smtpcorp.com', 465)

    '''
    notifier.send_notification(['emr.frei@gmail.com'],
                               'Test attachment',
                               'This is a test',
                               attachments=['/home/merfrei/Downloads/cablevision_fibertel_factura.pdf'])
    '''
    subject = 'Spider deployed (spider)'
    text = 'The following spider has been deployed:\n'
    text += 'Account: %s\n' % 'account'
    text += 'Spider: %s\n' % 'spider'

    text += 'Notes: %s' % 'notes'

    notifier.send_notification(['stephen.sharp@intelligenteye.com', 'lucas.moauro@intelligenteye.com'], subject, text)
