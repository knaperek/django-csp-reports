# STANDARD LIB
import logging
import json

# LIBRARIES
from django.conf import settings
from django.core.mail import mail_admins
from django.utils.importlib import import_module

# CSP REPORTS
from cspreports.models import CSPReport


logger = logging.getLogger(getattr(settings, "CSP_REPORTS_LOGGER_NAME", "CSP Reports"))


def process_report(request):
    """ Given the HTTP request of a CSP violation report, log it in the required ways. """
    if config.EMAIL_ADMINS:
        email_admins(request)
    if config.LOG:
        log_report(request)
    if config.SAVE:
        save_report(request)
    if config.ADDITIONAL_HANDLERS:
        run_additional_handlers(request)

def format_report(jsn):
    """ Given a JSON report, return a nicely formatted (i.e. with indentation) string.
        This should handle invalid JSON (as the JSON comes from the browser/user).
        We trust that Python's json library is secure, but if the JSON is invalid then we still
        want to be able to display it, rather than tripping up on a ValueError.
    """
    try:
        return json.dumps(json.loads(jsn), indent=4, sort_keys=True, separators=(',', ': '))
    except ValueError:
        return "Invalid JSON. Raw dump is below.\n\n" + jsn


def email_admins(request):
    user_agent = request.META.get('HTTP_USER_AGENT', '')
    report = format_report(request.body)
    message = "User agent:\n%s\n\nReport:\n%s" % (user_agent, report)
    mail_admins("CSP Violation Report", message)


def log_report(request):
    func = getattr(logger, config.LOG_LEVEL)
    func("Content Security Policy violation: %s", format_report(request.body))


def save_report(request):
    CSPReport.objects.create(json=request.body)


def run_additional_handlers(request):
    for handler in get_additional_handlers():
        handler(request)


class Config(object):
    """ Configuration with defaults, each of which is overrideable in django settings. """

    # Defaults, these are overridden using "CSP_REPORTS_"-prefixed versions in settings.py
    EMAIL_ADMINS = True
    LOG = True
    LOG_LEVEL = 'warning'
    SAVE = True
    ADDITIONAL_HANDLERS = []

    def __getattribute__(self, name):
        try:
            return getattr(settings, "%s%s" % ("CSP_REPORTS_", name))
        except AttributeError:
            return super(Config, self).__getattribute__(name)


config = Config()
_additional_handlers = None


def get_additional_handlers():
    """ Returns the actual functions from the dotted paths specified in ADDITIONAL_HANDLERS. """
    global _additional_handlers
    if not isinstance(_additional_handlers, list):
        handlers = []
        for name in config.ADDITIONAL_HANDLERS:
            module_name, function_name = name.rsplit('.', 1)
            function = getattr(import_module(module_name), function_name)
            handlers.append(function)
        _additional_handlers = handlers
    return _additional_handlers

