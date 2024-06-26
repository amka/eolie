# Copyright (c) 2017-2021 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GLib, WebKit

from urllib.parse import urlparse

from eolie.define import App


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
        self.__signal_ids.append(
            webview.connect("enter-fullscreen", self.__on_enter_fullscreen))
        self.__signal_ids.append(
            webview.connect("leave-fullscreen", self.__on_leave_fullscreen))
        self.__signal_ids.append(
            webview.connect("insecure-content-detected",
                            self.__on_insecure_content_detected))
        self.__signal_ids.append(
            webview.connect("mouse-target-changed",
                            self.__on_mouse_target_changed))
        self.__signal_ids.append(
            webview.connect("destroy", self.__on_destroy))
        self.__bfl_signal_id = webview.get_back_forward_list().connect(
                "changed",
                self.__on_back_forward_list_changed)
        accept_tls = App().websettings.get("accept_tls", webview.uri)
        self._window.toolbar.end.show_tls_button(accept_tls)
        self._window.toolbar.actions.set_actions(self.__current_webview)
        self._window.toolbar.title.entry.set_uri(webview.uri)
        self._window.toolbar.title.entry.icons.show_geolocation(False)
        self._window.toolbar.title.entry.icons.show_readable_button(False)
        self._window.toolbar.title.entry.icons.set_loading(False)
        self._window.toolbar.title.entry.progress.hide()
        if webview.get_uri() is None and\
                webview.uri is not None and\
                webview.related is None:
            webview.load_uri(webview.uri)
        if webview.uri == "populars:":
            self._window.toolbar.title.entry.set_default_placeholder()
        else:
            self._window.toolbar.title.entry.set_title(webview.title)

    def dismiss_webview(self, webview):
        """
            Dismiss webview from handlers
            @param webview as WebView
        """
        if self.__current_webview is None or webview != self.__current_webview:
            return
        for signal_id in self.__signal_ids:
            webview.disconnect(signal_id)
        if self.__bfl_signal_id is not None:
            webview.get_back_forward_list().disconnect(self.__bfl_signal_id)
        self.__signal_ids = []
        self.__bfl_signal_id = None
        self.__current_webview = None

#######################
# PRIVATE             #
#######################
    def __on_destroy(self, webview):
        """
            No more signals handlers
            @param webview as WebView
        """
        self.__signal_ids = []
        self.__bfl_signal_id = None
        self.__current_webview = None

    def __on_title_changed(self, webview, title):
        """
            Update title
            @param webview as WebView
            @param title as str
        """
        self._window.toolbar.title.entry.set_title(title)

    def __on_uri_changed(self, webview, uri):
        """
            Update title bar
            @param webview as WebView
            @param uri as str
        """
        if self.reading:
            self.toggle_reading()
        accept_tls = App().websettings.get("accept_tls", uri)
        self._window.toolbar.end.show_tls_button(accept_tls)
        self._window.toolbar.title.entry.set_uri(uri)

    def __on_estimated_load_progress(self, webview, value):
        """
            Update progress bar
            @param webview as WebView
            @param value GparamFloat
        """
        value = webview.get_estimated_load_progress()
        self._window.toolbar.title.entry.progress.set_fraction(value)

    def __on_back_forward_list_changed(self, bf_list, added, removed):
        """
            Update actions
            @param bf_list as WebKit.BackForwardList
            @param added as WebKit.BackForwardListItem
            @param removed as WebKit.BackForwardListItem
            @param webview as WebView
        """
        if self.__current_webview is not None:
            self._window.toolbar.actions.set_actions(self.__current_webview)

    def __on_readability_status(self, webview, status):
        """
            Show/hide toolbar indicator
            @param webview as WebView
            @param status as bool
        """
        self._window.toolbar.title.entry.icons.show_readable_button(status)

    def __on_load_changed(self, webview, event):
        """
            Update UI based on current event
            @param webview as WebView
            @param event as WebKit.LoadEvent
        """
        parsed = urlparse(webview.uri)
        wanted_scheme = parsed.scheme in ["http", "https", "file"]
        if event == WebKit.LoadEvent.STARTED:
            self._window.toolbar.title.entry.icons.set_loading(True)
            self._window.toolbar.title.entry.icons.show_geolocation(False)
            self._window.toolbar.title.entry.icons.show_readable_button(False)
        elif event == WebKit.LoadEvent.COMMITTED:
            if not wanted_scheme:
                GLib.idle_add(self._window.toolbar.title.start_search)
        elif event == WebKit.LoadEvent.FINISHED:
            self._window.toolbar.title.entry.icons.set_loading(False)
            self._window.toolbar.title.entry.progress.set_fraction(1.0)
            if wanted_scheme:
                GLib.idle_add(webview.grab_focus)
            webview.check_readability()

    def __on_enter_fullscreen(self, webview):
        """
            Go fullscreen
            @param webview as WebView
        """
        self._window.fullscreen(False)

    def __on_leave_fullscreen(self, webview):
        """
            Leave fullscreen
            @param webview as WebView
        """
        self._window.unfullscreen(False)

    def __on_insecure_content_detected(self, webview, event):
        """
            @param webview as WebView
            @param event as WebKit.InsecureContentEvent
        """
        self._window.toolbar.title.entry.set_insecure_content()

    def __on_mouse_target_changed(self, webview, hit, modifiers):
        """
            Show uri label
            @param webview as WebView
            @param hit as WebKit.HitTestResult
            @param modifiers as Gdk.ModifierType
        """
        if hit.context_is_link():
            self._uri_label.set_text(hit.get_link_uri())
            self._uri_label.show()
        else:
            self._uri_label.hide()
