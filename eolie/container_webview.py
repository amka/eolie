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

from gi.repository import WebKit2, GLib

from urllib.parse import urlparse

from eolie.define import App, Indicator


class WebViewContainer:
    """
        WebView management for container
    """

    def __init__(self):
        """
            Init container
        """
        self.__current_webview = None
        self.__signal_ids = []
        self.__bfl_signal_id = None

    def set_visible_webview(self, webview):
        """
            Manage webview signals
            @param webview as WebView
        """
        self.dismiss_webview(self.__current_webview)
        self.__current_webview = webview
        self.__signal_ids.append(
            webview.connect("load-changed", self.__on_load_changed))
        self.__signal_ids.append(
            webview.connect("title-changed", self.__on_title_changed))
        self.__signal_ids.append(
            webview.connect("uri-changed", self.__on_uri_changed))
        self.__signal_ids.append(
            webview.connect("readability-status",
                            self.__on_readability_status))
        self.__signal_ids.append(
            webview.connect("notify::estimated-load-progress",
                            self.__on_estimated_load_progress))
        self.__bfl_signal_id = webview.get_back_forward_list().connect(
                "changed",
                self.__on_back_forward_list_changed)

    def dismiss_webview(self, webview):
        """
            Dismiss webview from handlers
            @param webview as WebView
        """
        if webview != self.__current_webview:
            return
        for signal_id in self.__signal_ids:
            webview.disconnect(signal_id)
        if self.__bfl_signal_id is not None:
            webview.get_back_forward_list().disconnect(self.__bfl_signal_id)
        self.__signal_ids = []
        self.__bfl_signal_id = None

#######################
# PRIVATE             #
#######################
    def __on_title_changed(self, webview, title):
        """
            Update title
            @param webview as WebView
            @param title as str
        """
        self._window.toolbar.title.set_title(title)
        self.sites_manager.update_label(webview)

    def __on_uri_changed(self, webview, uri):
        """
            Update title bar
            @param webview as WebView
            @param uri as str
        """
        accept_tls = App().websettings.get_accept_tls(uri)
        self._window.toolbar.end.show_tls_button(accept_tls)
        self._window.toolbar.title.set_uri(uri)

    def __on_estimated_load_progress(self, webview, value):
        """
            Update progress bar
            @param webview as WebView
            @param value GparamFloat
        """
        value = self.__current_webview.get_estimated_load_progress()
        self._window.toolbar.title.progress.set_fraction(value)

    def __on_back_forward_list_changed(self, bf_list, added, removed):
        """
            Update actions
            @param bf_list as WebKit2.BackForwardList
            @param added as WebKit2.BackForwardListItem
            @param removed as WebKit2.BackForwardListItem
            @param webview as WebView
        """
        self._window.toolbar.actions.set_actions(self.__current_webview)

    def __on_readability_status(self, webview, status):
        """
            Show/hide toolbar indicator
            @param webview as WebView
            @param status as bool
        """
        self._window.toolbar.title.show_readable_button(status)

    def __on_load_changed(self, webview, event):
        """
            Update UI based on current event
            @param webview as WebView
            @param event as WebKit2.LoadEvent
        """
        parsed = urlparse(webview.uri)
        self._window.toolbar.title.set_uri(webview.uri)
        wanted_scheme = parsed.scheme in ["http", "https", "file"]
        if event == WebKit2.LoadEvent.STARTED:
            # self._window.container.find_widget.set_search_mode(False)
            self._window.toolbar.title.set_title(webview.uri)
            # self._window.toolbar.title.show_readable_button(False)
            if wanted_scheme:
                self._window.toolbar.title.set_loading(True)
            else:
                # Give focus to url bar
                self._window.toolbar.title.start_search()
            self._window.toolbar.title.show_indicator(Indicator.NONE)
        elif event == WebKit2.LoadEvent.COMMITTED:
            self._window.toolbar.title.set_title(webview.uri)
        elif event == WebKit2.LoadEvent.FINISHED:
            self._window.toolbar.title.set_loading(False)
            self._window.toolbar.title.progress.set_fraction(1.0)
            # Give focus to webview
            if wanted_scheme:
                GLib.idle_add(self.grab_focus)
            self.check_readability(webview)
