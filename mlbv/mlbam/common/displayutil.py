import mlbv.mlbam.common.config as config


LOG = None

class ANSI(object):
    CONTROL_CODE = {
        'reset': '\033[0m', 'bold': '\033[01m', 'disable': '\033[02m', 'underline': '\033[04m',
        'reverse': '\033[07m', 'strikethrough': '\033[09m', 'invisible': '\033[08m',
    }
    FG_COLOUR = {
        'black':  '\033[30m', 'red': '\033[31m', 'green': '\033[32m', 'orange': '\033[33m',
        'blue': '\033[34m', 'purple': '\033[35m', 'cyan': '\033[36m', 'lightgrey': '\033[37m',
        'darkgrey': '\033[90m', 'lightred': '\033[91m', 'lightgreen': '\033[92m', 'yellow': '\033[93m',
        'lightblue': '\033[94m', 'pink': '\033[95m', 'lightcyan': '\033[96m',
    }
    BG_COLOUR = {
        'black': '\033[40m', 'red': '\033[41m', 'green': '\033[42m', 'orange': '\033[43m',
        'blue': '\033[44m', 'purple': '\033[45m', 'cyan': '\033[46m', 'lightgrey': '\033[47m',
    }

    @staticmethod
    def control_code(code):
        if code is not None and code != '' and code in ANSI.CONTROL_CODE:
            return ANSI.CONTROL_CODE[code]
        # raise AttributeError('Unknown colour: ' + colour_name)
        return ''

    @staticmethod
    def reset():
        return ANSI.CONTROL_CODE['reset']

    @staticmethod
    def fg(colour_name):
        if colour_name is not None and colour_name != '' and colour_name in ANSI.FG_COLOUR:
            return ANSI.FG_COLOUR[colour_name]
        # raise AttributeError('Unknown colour: ' + colour_name)
        return ''

    @staticmethod
    def bg(colour_name):
        if colour_name is not None and colour_name != '' and colour_name in ANSI.BG_COLOUR:
            return ANSI.FG_COLOUR[colour_name]
        # raise AttributeError('Unknown colour: ' + colour_name)
        return ''


class Border(object):
    """Holds border symbols.
    Some unicode characters:  '─' '┄' '╌' '═' '━' '─'
    """

    def __init__(self, use_unicode=True):
        if use_unicode:
            # unicode characters:  '─' '┄' '╌' '═' '━' '─'
            self.border_color = ANSI.fg('darkgrey')
            self.color_off = ANSI.reset()
            self.dash = '─'
            self.thickdash = '─'
            self.doubledash = '═'
            self.pipe = self.border_color + '│' + self.color_off
            self.junction = '┼'
        else:
            # unicode characters:  '─' '┄' '╌' '═' '━' '─'
            self.border_color = ANSI.fg('darkgrey')
            self.color_off = ANSI.reset()
            self.dash = '-'
            self.thickdash = '-'
            self.doubledash = '='
            self.pipe = self.border_color + '|' + self.color_off
            self.junction = '|'
