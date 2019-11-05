# Copyright (c) 2017-2019 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.

from gi.repository import Gio, Gtk, GLib

from gettext import gettext as _

from eolie.define import App


class MoveToMenu(Gtk.Grid):
    """
        Menu allowing to move webviews to a window
    """

    def __init__(self, webviews, window, back=True):
        """
            Init menu
            @param webviews as [WebView]
            @param window as Window
            @param back as bool
        """
        self.__window = window
        self.__actions = []
        self.__webviews = list(webviews)
        Gtk.Menu.__init__(self)
        self.set_margin_start(5)
        self.set_margin_end(5)
        self.set_margin_top(5)
        self.set_margin_bottom(5)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        # Back button
        if back:
            item = Gtk.ModelButton.new()
            item.set_hexpand(True)
            item.set_property("centered", True)
            item.set_property("text", _("Move to"))
            item.set_property("inverted", True)
            item.set_property("menu-name", "main")
            item.show()
            self.add(item)

        action = Gio.SimpleAction(name="switch_window")
        action = Gio.SimpleAction.new("switch_window",
                                      GLib.VariantType.new("s"))
        action.connect('activate',
                       self.__on_action_activate)
        window.add_action(action)

        # New window button
        item = Gtk.ModelButton.new()
        item.set_hexpand(True)
        item.set_property("text", _("New window"))
        item.set_action_name("win.switch_window")
        item.set_action_target_value(GLib.Variant("s", "new_window"))
        item.show()
        self.add(item)
        if len(App().windows) > 1:
            item = Gtk.Separator.new(Gtk.Orientation.HORIZONTAL)
            item.show()
            self.add(item)

        for window in App().windows:
            if window == window:
                continue
            item = Gtk.ModelButton.new()
            item.set_hexpand(True)
            item.set_property("text", window.get_title())
            item.set_action_name("win.switch_window")
            item.set_action_target_value(GLib.Variant("s", str(window)))
            item.show()
            item.connect("enter-notify-event",
                         self.__on_enter_notify_event,
                         window)
            item.connect("leave-notify-event",
                         self.__on_leave_notify_event,
                         window)
            self.add(item)

    def do_hide(self):
        """
            Remove action on hide
        """
        Gtk.Grid.do_hide(self)
        self.__window.remove_action("switch_window")

#######################
# PRIVATE             #
#######################
    def __on_enter_notify_event(self, widget, event, window):
        """
            Mark window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
            @param window as Window
        """
        window.mark(True)

    def __on_leave_notify_event(self, widget, event, window):
        """
            Unmark window
            @param widget as Gtk.Widget
            @param event as Gdk.Event
            @param window as Window
        """
        window.mark(False)

    def __on_action_activate(self, action, variant):
        """
            Moves webviews to window
            @param action as  Gio.SimpleAction
            @param variant as GLib.Variant
            @param window as Window
        """
        window = None
        window_str = variant.get_string()

        # Get wanted window
        if window_str == "new_window":
            window = App().get_new_window()
        else:
            for window in App().windows:
                if window_str == str(window):
                    break
        if window is None:
            return

        # Move webviews to window
        for webview in self.__webviews:
            self.__window.container.remove_webview(webview)
            window.container.add_webview(webview)
            webview.set_window(window)
