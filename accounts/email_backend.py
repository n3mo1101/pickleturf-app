import resend
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend


class ResendEmailBackend(BaseEmailBackend):
    """
    Custom Django email backend using Resend API.
    Drop-in replacement for SMTP backend.
    """

    def open(self):
        resend.api_key = settings.RESEND_API_KEY
        return True

    def close(self):
        pass

    def send_messages(self, email_messages):
        resend.api_key = settings.RESEND_API_KEY
        sent = 0

        for message in email_messages:
            try:
                # Build the payload
                params = {
                    'from':    message.from_email or settings.DEFAULT_FROM_EMAIL,
                    'to':      message.to,
                    'subject': message.subject,
                }

                # Handle HTML vs plain text
                if hasattr(message, 'alternatives'):
                    for content, mimetype in message.alternatives:
                        if mimetype == 'text/html':
                            params['html'] = content
                            break
                    # Include plain text as fallback
                    if message.body:
                        params['text'] = message.body
                else:
                    params['text'] = message.body

                resend.Emails.send(params)
                sent += 1

            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f'Resend failed for {message.to}: {e}')
                if not self.fail_silently:
                    raise

        return sent