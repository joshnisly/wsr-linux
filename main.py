#!/usr/bin/env python3

""" Functionality inspired by WinSplit Revolution. Code copied from x11pygrid. """

import signal
from Xlib import display, X

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GLib  # noqa
from gi.repository import Gdk  # noqa


_POSITIONS = {
    'topleft': {
        'pos': [[0, 0, 33.33, 50], [0, 0, 50, 50]],
        'key': 'KP_7'
    },
    'bottomleft': {
        'pos': [[0, 50, 33.33, 50], [0, 50, 50, 50]],
        'key': 'KP_1'
    },

    'topmiddle': {
        'pos': [[33.33, 0, 33.33, 50], [25, 0, 50, 50]],
        'key': 'KP_8'
    },
    'bottommiddle': {
        'pos': [[33.33, 50, 33.33, 50], [25, 50, 50, 50]],
        'key': 'KP_2'
    },

    'topright': {
        'pos': [[66.66, 0, 33.33, 50], [50, 0, 50, 50]],
        'key': 'KP_9'
    },
    'bottomright': {
        'pos': [[66.66, 50, 33.33, 50], [50, 50, 50, 50]],
        'key': 'KP_3'
    },

    'left': {
        'pos': [[0, 0, 33.3, 100], [0, 0, 50, 100]],
        'key': 'KP_4'
    },
    'middle': {
        'pos': [[33.33, 0, 33.33, 100], [25, 0, 50, 100]],
        'key': 'KP_5'
    },
    'right': {
        'pos': [[66.66, 0, 33.33, 100], [50, 0, 50, 100]],
        'key': 'KP_6'
    },
}
_ACCELERATOR = '<Ctrl><Mod1><Mod2>'


class WinSplitRevolution(object):

    def __init__(self):
        self.display = display.Display()
        self.root = self.display.screen().root
        self.keys = {}

    def start(self):
        """ Write config if not found and watch for keyboard events. """
        self.root.change_attributes(event_mask=X.KeyPressMask)
        self._bind_keys()
        for event in range(0, self.root.display.pending_events()):
            self.root.display.next_event()
        GLib.io_add_watch(self.root.display, GLib.IO_IN, self._check_event)
        print('Running. Press CTRL+C to cancel.')
        Gtk.main()

    def _bind_keys(self):
        """ Bind keys from config """
        for posname in _POSITIONS:
            # See https://developer.gnome.org/gtk3/stable/gtk3-Keyboard-Accelerators.html#gtk-accelerator-parse
            keysym, modmask = Gtk.accelerator_parse(_ACCELERATOR + _POSITIONS[posname]['key'])
            keycode = self.display.keysym_to_keycode(keysym)

            self.keys[keycode] = posname
            self.root.grab_key(keycode, modmask, 1, X.GrabModeAsync, X.GrabModeAsync)

    def _check_event(self, source, condition, handle=None):
        """ Check keyboard event has all the right buttons pressed. """
        handle = handle or self.root.display
        for _ in range(0, handle.pending_events()):
            event = handle.next_event()
            if event.type == X.KeyPress and event.detail in self.keys:
                posname = self.keys[event.detail]
                self._handle_event(posname)

        return True

    def _handle_event(self, posname):
        try:
            screen = Gdk.Screen.get_default()
            window = self._get_active_window(screen)
            if not window:
                return

            monitor_id = screen.get_monitor_at_window(window)

            windowframe = window.get_frame_extents()
            workarea = screen.get_monitor_workarea(monitor_id)

            positions = _POSITIONS[posname]['pos']
            for pos_def in positions:
                pos = self._calc_pos(pos_def, workarea)
                edges = [
                    (pos['x'], windowframe.x),
                    (pos['y'], windowframe.y),
                    (pos['width'], windowframe.width),
                    (pos['height'], windowframe.height)
                ]
                total_delta = sum([abs(x[0] - x[1]) for x in edges])
                if total_delta > 200:  # TODO: figure out why terminals are so far off.
                    self._move_window(window, pos)
                    return
        except Exception as e:
            print('Unable to move window: %s' % e)

    def _move_window(self, window, pos):
        window.unmaximize()
        window.set_shadow_width(0, 0, 0, 0)
        window_bar_height = window.get_origin().y - window.get_root_origin().y
        window.move_resize(pos['x'], pos['y'], pos['width'], pos['height']-window_bar_height)

    def _calc_pos(self, pos_def, workarea):
        return {
            'x': workarea.x + int(pos_def[0] * workarea.width / 100),
            'y': workarea.y + int(pos_def[1] * workarea.height / 100),
            'width': int(pos_def[2] * workarea.width / 100),
            'height': int(pos_def[3] * workarea.height / 100),
        }

    def _get_active_window(self, screen):
        """ Get the current active window. """
        window = screen.get_active_window()
        if not screen.supports_net_wm_hint(Gdk.atom_intern('_NET_ACTIVE_WINDOW', True)): return None
        if not screen.supports_net_wm_hint(Gdk.atom_intern('_NET_WM_WINDOW_TYPE', True)): return None
        if window.get_type_hint().value_name == 'GDK_WINDOW_TYPE_HINT_DESKTOP': return None
        return window

    def _get_workarea(self, screen, monitorid, config):
        """ get the monitor workarea taking into account config padding. """
        return screen.get_monitor_workarea(monitorid)


def main():
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    WinSplitRevolution().start()


if __name__ == '__main__':
    main()
