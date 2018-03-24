# Copyright (c) 2017-2018 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import Gtk

from gettext import gettext as _

from eolie.define import App
from eolie.logger import Logger


class ImportBookmarksDialog:
    """
        Import bookarks dialog
    """

    class __Choice:
        FIREFOX = 0
        CHROMIUM = 1
        CHROME = 2
        OTHERS = 3

    def __init__(self, window):
        """
            Init widget
            @param window as Gtk.Window
        """
        self.__window = window
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Eolie/DialogImportBookmarks.ui")
        builder.connect_signals(self)
        self.__dialog = builder.get_object("dialog")
        self.__dialog.set_transient_for(window)
        self.__listbox = builder.get_object("listbox")
        items = ["Firefox", "Chromium", "Chrome"]
        try:
            from bs4 import BeautifulSoup
            BeautifulSoup
            items.append(_("Others"))
        except Exception as e:
            Logger.error("ImportBookmarksDialog::__init__(): %s", e)
        for item in items:
            label = Gtk.Label.new(item)
            label.show()
            self.__listbox.add(label)
        headerbar = builder.get_object("headerbar")
        self.__dialog.set_titlebar(headerbar)

    def run(self):
        """
            Run dialog
        """
        self.__dialog.run()
        self.__dialog.destroy()

#######################
# PROTECTED           #
#######################
    def _on_dialog_response(self, dialog, response_id):
        """
            Import bookmarks
            @param dialog as Gtk.Dialog
            @param response_id as int
        """
        if response_id == Gtk.ResponseType.DELETE_EVENT:
            return
        index = self.__listbox.get_selected_row().get_index()
        if index == self.__Choice.FIREFOX:
            App().bookmarks.import_firefox()
        elif index == self.__Choice.CHROME:
            App().bookmarks.import_chromium(True)
        elif index == self.__Choice.CHROMIUM:
            App().bookmarks.import_chromium(False)
        else:
            dialog = Gtk.FileChooserDialog(
                _("Import HTML bookmarks"), self.__window,
                Gtk.FileChooserAction.OPEN,
                (Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL,
                 Gtk.STOCK_OPEN, Gtk.ResponseType.OK))
            dialog.connect("response", self.__on_file_chooser_response)
            dialog.run()
            dialog.destroy()
        self.__window.close_popovers()

#######################
# PRIVATE             #
#######################
    def __on_file_chooser_response(self, dialog, response_id):
        """
            Import file
            @param dialog as GtkFileChooserDialog
            @param response_id as int
        """
        if response_id == Gtk.ResponseType.OK:
            path = dialog.get_filename()
            App().bookmarks.import_html(path)
