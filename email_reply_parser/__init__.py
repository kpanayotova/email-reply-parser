import re

"""
    email_reply_parser is a python library port of GitHub's Email Reply Parser.
    This fork adds support for:
        - detecting forwarded message
        - multilingual reply header formats

    For more information, visit https://github.com/kpanayotova/email-reply-parser
    (forked from https://github.com/zapier/email-reply-parser)
"""


class EmailReplyParser(object):
    """ Represents a email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            text - A string email body

            Returns an EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            text - A string email body

            Returns reply body message
        """
        return EmailReplyParser.read(text).reply


class EmailMessage(object):
    """ An email message represents a parsed email body.
    """
    SIG_REGEX = r'(--|__|-\w)|(^Sent from my (\w+\s*){1,3})'

    QUOTE_HDR_REGEXS = [
        r'^:etorw.*nO',
        r'^:.*beirhcs.*mA',            # de
        r'^:\s*tirc\xa9\xc3.*eL',      # fr
                                       # TODO es
    ]
    MULTI_QUOTE_HDR_REGEXS = [
        r'((-+\s*)?On\s.*?wrote:)',
        r'((-+\s*)?Am\s.*?schrieb.*:)',        # de
        r'((-+\s*)?Le\s.*?\xc3\xa9crit\s*:)',  # fr
                                               # TODO es
    ]
    QUOTED_REGEX = r'(>+)'
    FORWARD_MESSAGES = [
        # apple mail forward
        'Begin forwarded message',

        # gmail/evolution forward
        'Forwarded [mM]essage',

        # outlook
        'Original [mM]essage',

        #TODO add translations
    ]
    FORWARD_REGEXS = ['^---+ ?%s.* ?---+$' % p for p in FORWARD_MESSAGES] \
                   + ['^%s:$' % p for p in FORWARD_MESSAGES]

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        is_multi_quote_header, regex = self.has_quote_header(self.text)
        if is_multi_quote_header:
            expr = re.compile(regex, flags=re.DOTALL)
            self.text = expr.sub(
                is_multi_quote_header.groups()[0].replace('\n', ''),
                self.text)

        self.lines = self.text.split('\n')
        self.lines.reverse()

        for line in self.lines:
            self._scan_line(line)

        self._finish_fragment()

        self.fragments.reverse()

        return self

    @property
    def reply(self):
        """ Captures reply message within email
        """
        reply = []
        for f in self.fragments:
            if not (f.hidden or f.quoted or f.forwarded):
                reply.append(f.content)
        return '\n'.join(reply)

    def _scan_line(self, line):
        """ Reviews each line in email message and determines fragment type

            line - a row of text from an email message
        """

        line = line.strip()

        is_forward = self.is_forward_header(line) is not None
        if is_forward:
            self._finish_fragment()
            for fragment in self.fragments:
                fragment.forwarded = True
            return

        if re.match(self.SIG_REGEX, line):
            line.lstrip()

        is_quoted = re.match(self.QUOTED_REGEX, line) != None

        if self.fragment and len(line) == 0:
            if re.match(self.SIG_REGEX, self.fragment.lines[-1]):
                self.fragment.signature = True
                self._finish_fragment()

        if self.fragment and ((self.fragment.quoted == is_quoted)
            or (self.fragment.quoted and (self.is_quote_header(line) or len(line.strip()) == 0))):

            self.fragment.lines.append(line)

        else:
            self._finish_fragment()
            self.fragment = Fragment(is_quoted, is_forward, line)

    def is_quote_header(self, line):
        return self._match_any(self.QUOTE_HDR_REGEXS, line[::-1])[0] != None

    def has_quote_header(self, text):
        """ Check if message contains reply header
        """
        return self._match_any(self.MULTI_QUOTE_HDR_REGEXS, text, re.MULTILINE | re.DOTALL, True)

    def is_forward_header(self, line):
        """ Check if this line is a forward header
        """
        return self._match_any(self.FORWARD_REGEXS, line)[0]

    def _match_any(self, regexs, text, options=None, search=False):
        """ Matches any of the list of regexs
            Returns a tuple: (match, regex_matched)
        """
        match = None
        regex = None
        operator = 'search' if search else 'match'
        for regex in regexs:
            if options is not None:
                match = getattr(re, operator)(regex, text, options)
            else:
                match = getattr(re, operator)(regex, text)
            if match:
                break
        return match, regex

    def _finish_fragment(self):
        """ Creates fragment
        """

        if self.fragment:
            self.fragment.finish()
            if not self.found_visible:
                if self.fragment.quoted \
                or self.fragment.signature \
                or (len(self.fragment.content.strip()) == 0):

                    self.fragment.hidden = True
                else:
                    self.found_visible = True
            self.fragments.append(self.fragment)
        self.fragment = None


class Fragment(object):
    """ A Fragment is a part of
        an Email Message, labeling each part.
    """

    def __init__(self, quoted, forwarded, first_line):
        self.signature = False
        self.hidden = False
        self.quoted = quoted
        self.forwarded = forwarded
        self._content = None
        self.lines = [first_line]

    def finish(self):
        """ Creates block of content with lines
            belonging to fragment.
        """
        self.lines.reverse()
        self._content = '\n'.join(self.lines)
        self.lines = None

    @property
    def content(self):
        return self._content

