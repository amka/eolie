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

from gi.repository import Gtk, GLib, Adw

from locale import strcoll
from time import time

from eolie.define import App
from eolie.widget_bookmark_rating import BookmarkRatingWidget


class TagWidget(Gtk.FlowBoxChild):
    """
        Tag widget with some visual effects
    """

    def __init__(self, title, bookmark_id):
        """
            Init widget
            @param title as str
            @param bookmark_id as int
        """
        Gtk.FlowBoxChild.__init__(self)
        self.__bookmark_id = bookmark_id
        self.__title = title
        grid = Gtk.Grid()
        grid.show()
        grid.get_style_context().add_class("linked")
        self.__entry = Gtk.Entry()
        self.__entry.get_style_context().add_class("tag")
        self.__entry.show()
        self.__entry.set_text(title)
        self.__button = Gtk.Button.new_from_icon_name("window-close-symbolic",
                                                      Gtk.IconSize.BUTTON)
        self.__button.show()
        self.__button.get_style_context().add_class("tag")
        grid.add(self.__entry)
        grid.add(self.__button)
        self.add(grid)
        self.__entry.connect("changed", self.__on_entry_changed)
        self.__button.connect("clicked", self.__on_button_clicked)

    @property
    def label(self):
        """
            Get label
            @return str
        """
        return self.__entry.get_text()

#######################
# PRIVATE             #
#######################
    def __on_button_clicked(self, button):
        """
            Save/Remove tag
            @param button as Gtk.Button
        """
        if button.get_style_context().has_class("suggested-action"):
            title = self.__entry.get_text()
            App().bookmarks.rename_tag(self.__title, title)
            # Update mtime for all tagged bookmarks
            if App().sync_worker is not None:
                mtime = round(time(), 2)
                tag_id = App().bookmarks.get_tag_id(title)
                if tag_id is not None:
                    for (bookmark_id, bookmark_uri, bookmark_title) in\
                            App().bookmarks.get_bookmarks(tag_id):
                        App().bookmarks.set_mtime(bookmark_id, mtime + 1)
                        App().sync_worker.push_bookmark(bookmark_id)
            self.__entry.set_text(title)
            self.__title = title
            self.__on_entry_changed(self.__entry)
        else:
            tag_title = self.__entry.get_text()
            tag_id = App().bookmarks.get_tag_id(tag_title)
            if tag_id is not None:
                App().bookmarks.del_tag_from(tag_id, self.__bookmark_id)
            App().bookmarks.clean_tags()
            self.destroy()

    def __on_entry_changed(self, entry):
        """
            Update button state
            @param entry as Gtk.Entry
        """
        self.__button.set_sensitive(True)
        style_context = self.__button.get_style_context()
        image = self.__button.get_image()
        title = entry.get_text()
        tag_id = App().bookmarks.get_tag_id(title)
        if title == self.__title:
            style_context.remove_class("suggested-action")
            image.set_from_icon_name("window-close-symbolic",
                                     Gtk.IconSize.BUTTON)
        elif tag_id is not None or not title:
            self.__button.set_sensitive(False)
            image.set_from_icon_name("dialog-error-symbolic",
                                     Gtk.IconSize.BUTTON)
        else:
            style_context.add_class("suggested-action")
            image.set_from_icon_name("object-select-symbolic",
                                     Gtk.IconSize.BUTTON)


class BookmarkEditWidget(Adw.Bin):
    """
        Widget allowing to edit a bookmark
    """

    def __init__(self, bookmark_id, back_enabled=True):
        """
            Init widget
            @param bookmark id as int
            @param enable back button as bool
        """
        super().__init__()
        self.__bookmark_id = bookmark_id
        builder = Gtk.Builder()
        builder.add_from_resource("/org/gnome/Eolie/BookmarkEdit.ui")
        builder.connect_signals(self)
        self.__flowbox = builder.get_object("flowbox")
        self.__flowbox.set_sort_func(self.__sort_tags)
        self.__add_tag_button = builder.get_object("add_tag_button")
        self.__rename_tag_button = builder.get_object("rename_tag_button")
        self.__remove_tag_button = builder.get_object("remove_tag_button")
        self.__title_entry = builder.get_object("title_entry")
        self.__uri_entry = builder.get_object("uri_entry")
        self.__title_entry.set_text(App().bookmarks.get_title(bookmark_id))
        self.__uri_entry.set_text(App().bookmarks.get_uri(bookmark_id))
        builder.get_object("startup_button").set_active(
            App().bookmarks.get_startup(bookmark_id))
        self.__new_tag_entry = builder.get_object("new_tag_entry")
        # Init new tag completion model
        self.__completion_model = Gtk.ListStore(str)
        self.__completion = Gtk.EntryCompletion.new()
        self.__completion.set_model(self.__completion_model)
        self.__completion.set_text_column(0)
        self.__completion.set_inline_completion(False)
        self.__completion.set_popup_completion(True)
        self.__new_tag_entry.set_completion(self.__completion)
        for (tag_id, title) in App().bookmarks.get_all_tags():
            self.__completion_model.append([title])

        for title in App().bookmarks.get_tags(bookmark_id):
            tag = TagWidget(title, bookmark_id)
            tag.show()
            self.__flowbox.add(tag)
        if not back_enabled:
            builder.get_object("back_button").hide()
        bookmark_rating = BookmarkRatingWidget(bookmark_id)
        bookmark_rating.show()
        builder.get_object("bookmark_grid").attach(bookmark_rating, 2, 1, 1, 1)
        self.add(builder.get_object("widget"))
        self.connect("unmap", self.__on_unmap)
        self.__updated = False

#######################
# PROTECTED           #
#######################
    def _on_back_clicked(self, button):
        """
            Destroy self
            @param button as Gtk.Button
        """
        GLib.idle_add(self.hide)
        GLib.timeout_add(2000, self.destroy)

    def _on_del_clicked(self, button):
        """
            Remove item
            @param button as Gtk.Button
        """
        self.disconnect_by_func(self.__on_unmap)
        if App().sync_worker is not None:
            guid = App().bookmarks.get_guid(self.__bookmark_id)
            App().sync_worker.remove_from_bookmarks(guid)
        App().bookmarks.remove(self.__bookmark_id)
        if isinstance(self.get_parent(), Gtk.Popover):
            self.get_parent().hide()
        else:
            self.get_parent().set_visible_child_name("bookmarks")

    def _on_new_tag_entry_activate(self, entry, ignore1=None, ignore2=None):
        """
            Add new tag
            @param entry as Gtk.Entry
        """
        tag_title = self.__new_tag_entry.get_text()
        if not tag_title:
            return
        if not App().bookmarks.has_tag(self.__bookmark_id, tag_title):
            tag_id = App().bookmarks.get_tag_id(tag_title)
            if tag_id is None:
                tag_id = App().bookmarks.add_tag(tag_title)
            App().bookmarks.add_tag_to(tag_id, self.__bookmark_id)
            tag = TagWidget(tag_title, self.__bookmark_id)
            tag.show()
            self.__flowbox.add(tag)
        entry.set_text("")

    def _on_flowbox_size_allocate(self, scrolled, allocation):
        """
            Set scrolled size allocation based on viewport allocation
            @param scrolled as Gtk.ScrolledWindow
            @param flowbox allocation as Gtk.Allocation
        """
        height = allocation.height
        if height > 300:
            height = 300
        scrolled.set_size_request(-1, height)

    def _on_entry_changed(self, entry):
        """
            Mark bookmark as updated
            @param entry as Gtk.Entry
        """
        self.__updated = True

    def _on_load_at_startup_toggled(self, button):
        """
            Set bookmark startup state
            @param button as Gtk.ToggleButton
        """
        App().bookmarks.set_startup(self.__bookmark_id, button.get_active())

#######################
# PRIVATE             #
#######################
    def __sort_tags(self, child1, child2):
        """
            Sort tags
            @param child1 as TagWidget
            @param child2 as TagWidget
        """
        return strcoll(child1.label, child2.label)

    def __on_unmap(self, widget):
        """
            Save uri and title
            @param widget as Gtk.Widget
        """
        if self.__updated:
            App().bookmarks.set_title(self.__bookmark_id,
                                      self.__title_entry.get_text())
            App().bookmarks.set_uri(self.__bookmark_id,
                                    self.__uri_entry.get_text())
            App().bookmarks.clean_tags()
            if App().sync_worker is not None:
                App().bookmarks.set_mtime(self.__bookmark_id,
                                          round(time(), 2) + 1)
                App().sync_worker.push_bookmark(self.__bookmark_id)
