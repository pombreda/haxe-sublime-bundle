import os
import sublime
import sublime_plugin

if int(sublime.version()) >= 3000:
    from plistlib import readPlistFromBytes
else:
    from plistlib import readPlist

try:  # Python 3
    from .haxe_helper import HaxeComplete_inst
    from .haxe_format import format_statement
except (ValueError):  # Python 2
    from haxe_helper import HaxeComplete_inst
    from haxe_format import format_statement


class HaxeColorScheme(sublime_plugin.EventListener):

    def __init__(self):
        self.init()

    def init(self):
        if sublime.active_window() is None or \
                sublime.active_window().active_view() is None:
            sublime.set_timeout(self.init, 200)
            return

        self.settings = sublime.load_settings('Preferences.sublime-settings')
        self.settings.add_on_change(
            'color_scheme', lambda: self.parse_scheme())
        self.parse_scheme()

    @staticmethod
    def get_color(name):
        if HaxeColorScheme.color_map is None or \
                name not in HaxeColorScheme.color_map:
            return None
        return HaxeColorScheme.color_map[name]

    @staticmethod
    def get_styles():
        if HaxeColorScheme.styles is None:
            if HaxeColorScheme.color_map is None:
                return ''

            colors = (
                HaxeColorScheme.get_color('popupBackground') or
                HaxeColorScheme.get_color('lineHighlight') or
                HaxeColorScheme.get_color('background'),
                HaxeColorScheme.get_color('popupForeground') or
                HaxeColorScheme.get_color('foreground'))
            HaxeColorScheme.styles = \
                '<style>html{background-color:%s;color:%s;}</style>' % colors

        return HaxeColorScheme.styles

    def parse_scheme(self):
        HaxeColorScheme.styles = None
        HaxeColorScheme.color_map = None

        color_scheme = self.settings.get('color_scheme')

        try:
            if int(sublime.version()) >= 3000:
                b = sublime.load_binary_resource(color_scheme)
                pl = readPlistFromBytes(b)
            else:
                pl = readPlist(os.path.join(os.path.abspath(
                    sublime.packages_path() + '/..'), color_scheme))
        except:
            return

        def safe_update(fr, to):
            for k in fr.keys():
                if k not in to:
                    to[k] = fr[k]

        dct = {}
        for d in pl.settings:
            if 'settings' not in d:
                continue
            s = d['settings']
            if 'scope' not in d:
                safe_update(s, dct)
            else:
                scope = d['scope']
                scopes = [sc.strip() for sc in scope.split(',')]
                if 'text' in scopes or 'source' in scopes:
                    dct.update(d.settings)

        HaxeColorScheme.color_map = dct


class HaxeShowPopup(sublime_plugin.TextCommand):

    def run(self, edit, text=None):
        view = self.view
        if not text:
            return

        view.show_popup(
            HaxeColorScheme.get_styles() + text,
            max_width=700)


class HaxeHint(sublime_plugin.TextCommand):

    def insert_snippet(self, hints):
        view = self.view
        snippet = ''
        i = 1
        for h in hints:
            var = '%d:%s' % (i, h)
            if snippet == '':
                snippet = var
            else:
                snippet += ',${%s}' % var
            i += 1

        snippet = format_statement(view, snippet)

        view.run_command('insert_snippet', {
            'contents': '${' + snippet + '}'
        })

    def run(self, edit, input=''):
        complete = HaxeComplete_inst()
        view = self.view

        if input == '(':
            sel = view.sel()
            emptySel = True
            for r in sel:
                if not r.empty():
                    emptySel = False
                    break

            autoMatch = view.settings().get('auto_match_enabled', False)

            if autoMatch:
                if emptySel:
                    view.run_command('insert_snippet', {
                        'contents': '($0)'
                    })
                else:
                    view.run_command('insert_snippet', {
                        'contents': '(${0:$SELECTION})'
                    })
            else:
                view.run_command('insert', {
                    'characters': '('
                })
        else:
            view.run_command('insert', {
                'characters': input
            })

        autocomplete = view.settings().get('auto_complete', True)
        if not autocomplete:
            return

        haxe_smart_snippets = view.settings().get('haxe_smart_snippets', False)
        haxe_use_popup = view.settings().get('haxe_use_popup', True) and \
            int(sublime.version()) >= 3070

        if not haxe_smart_snippets and not haxe_use_popup:
            return

        for r in view.sel():
            comps, hints = complete.get_haxe_completions(view, r.end())

            if haxe_use_popup:
                self.show_popup(hints)
            elif haxe_smart_snippets and input:
                self.insert_snippet(hints)

    def show_popup(self, hints):
        view = self.view
        text = ''

        for h in hints:
            if not text:
                text = '{}%s{}' % h
            else:
                text += ',%s' % h

        text = format_statement(view, text)
        text = text.format('<b>', '</b>')

        view.run_command('haxe_show_popup', {
            'text': text
        })
