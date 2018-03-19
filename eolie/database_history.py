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

from gi.repository import GLib

import sqlite3
import itertools
from urllib.parse import urlparse
from threading import Lock

from eolie.utils import noaccents, get_random_string
from eolie.define import EOLIE_DATA_PATH, Type
from eolie.localized import LocalizedCollation
from eolie.sqlcursor import SqlCursor
from eolie.logger import Logger
from eolie.database_upgrade import DatabaseUpgrade


class DatabaseHistory:
    """
        Eolie history db
    """
    DB_PATH = "%s/history.db" % EOLIE_DATA_PATH

    __UPGRADES = {
        1: "ALTER TABLE history ADD opened INT NOT NULL DEFAULT 0",
        2: "ALTER TABLE history ADD netloc TEXT NOT NULL DEFAULT ''",
        3: "DELETE FROM history WHERE popularity=0",
        4: "DELETE FROM history_atime WHERE NOT EXISTS (SELECT * FROM history\
            WHERE history.rowid=history_atime.history_id)"
    }

    # SQLite documentation:
    # In SQLite, a column with type INTEGER PRIMARY KEY
    # is an alias for the ROWID.
    # Here, we define an id INT PRIMARY KEY but never feed it,
    # this make VACUUM not destroy rowids...
    __create_history = '''CREATE TABLE history (
                                               id INTEGER PRIMARY KEY,
                                               title TEXT NOT NULL,
                                               uri TEXT NOT NULL,
                                               netloc TEXT NOT NULL,
                                               guid TEXT NOT NULL,
                                               mtime REAL NOT NULL,
                                               opened INT NOT NULL DEFAULT 0,
                                               popularity INT NOT NULL
                                               )'''
    __create_history_atime = '''CREATE TABLE history_atime (
                                                history_id INT NOT NULL,
                                                atime REAL NOT NULL
                                               )'''

    def __init__(self):
        """
            Create database tables or manage update if needed
        """
        upgrade = DatabaseUpgrade(Type.HISTORY)
        self.thread_lock = Lock()
        if not GLib.file_test(self.DB_PATH, GLib.FileTest.IS_REGULAR):
            try:
                if not GLib.file_test(EOLIE_DATA_PATH, GLib.FileTest.IS_DIR):
                    GLib.mkdir_with_parents(EOLIE_DATA_PATH, 0o0750)
                # Create db schema
                with SqlCursor(self) as sql:
                    sql.execute(self.__create_history)
                    sql.execute(self.__create_history_atime)
                    sql.execute("PRAGMA user_version=%s" % upgrade.version)
            except Exception as e:
                Logger.error("DatabaseHistory::__init__(): %s", e)
        else:
            upgrade.upgrade(self)

    def add(self, title, uri, mtime, guid=None, atimes=[]):
        """
            Add a new entry to history, if exists, update it
            @param title as str
            @param uri as str
            @param mtime as int
            @parma guid as str
            @param atime as [int]
            @return history id as int
        """
        if not uri:
            return
        uri = uri.rstrip('/')
        parsed = urlparse(uri)
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid, popularity FROM history\
                                  WHERE uri=?", (uri,))
            v = result.fetchone()
            # Update current item
            if v is not None:
                history_id = v[0]
                guid = self.get_guid(history_id)
                sql.execute("UPDATE history\
                             SET uri=?, netloc=?, mtime=?,\
                                 title=?, guid=?, popularity=?\
                             WHERE rowid=?", (uri, parsed.netloc, mtime, title,
                                              guid, v[1]+1, history_id))
            # Add a new item
            else:
                # Find an uniq guid
                while guid is None:
                    guid = get_random_string(12)
                    if self.exists_guid(guid):
                        guid = None
                result = sql.execute("INSERT INTO history\
                                      (title, uri, netloc,\
                                       mtime, popularity, guid)\
                                      VALUES (?, ?, ?, ?, ?, ?)",
                                     (title, uri, parsed.netloc,
                                      mtime, 0, guid))
                history_id = result.lastrowid
            # Only add new atimes to db
            if not atimes:
                atimes = [mtime]
            current_atimes = self.get_atimes(history_id)
            for atime in atimes:
                if atime not in current_atimes:
                    sql.execute("INSERT INTO history_atime\
                                 (history_id, atime)\
                                 VALUES (?, ?)", (history_id, atime))
            return history_id

    def remove(self, history_id):
        """
            Remove item from history
            @param history id as int
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE from history\
                         WHERE rowid=?", (history_id,))

    def clear_from(self, atime):
        """
            Clear history from atime
            @param atime as int
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM history_atime\
                         WHERE atime >= ?", (atime,))

    def clear_to(self, atime):
        """
            Clear history to atime
            @param atime as int
        """
        with SqlCursor(self) as sql:
            sql.execute("DELETE FROM history_atime\
                         WHERE atime <= ?", (atime,))

    def get_from_atime(self, atime):
        """
            Get history ids from atime
            @param atime as int
            @return modified history ids as [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT DISTINCT history.rowid\
                                  FROM history, history_atime\
                                  WHERE history_atime.history_id=history.rowid\
                                  AND atime >= ?", (atime,))
            return list(itertools.chain(*result))

    def get_empties(self):
        """
            Get empties history entries (without atime)
            @return history ids as [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT history.rowid FROM history\
                                  WHERE NOT EXISTS (\
                                    SELECT rowid FROM history_atime AS ha\
                                    WHERE ha.history_id=history.rowid)")
            return list(itertools.chain(*result))

    def get(self, atime):
        """
            Get history for atime (current day)
            @param atime as int
            @return (str, str, int)
        """
        one_day = 86400
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT history.rowid, title, uri, atime\
                                  FROM history, history_atime\
                                  WHERE history.rowid=history_atime.history_id\
                                  AND atime >= ? AND atime <= ?\
                                  ORDER BY atime DESC",
                                 (atime, atime + one_day))
            return list(result)

    def get_id(self, uri):
        """
            Get history id
            @param uri as str
            @return history_id as int
        """
        with SqlCursor(self) as sql:
            uri = uri.rstrip('/')
            result = sql.execute("SELECT rowid\
                                  FROM history\
                                  WHERE uri=?",
                                 (uri,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_title(self, history_id):
        """
            Get history title
            @param history_id as int
            @return title as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT title\
                                  FROM history\
                                  WHERE rowid=?", (history_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_uri(self, history_id):
        """
            Get history uri
            @param history_id as int
            @return uri as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT uri\
                                  FROM history\
                                  WHERE rowid=?", (history_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return ""

    def get_guid(self, history_id):
        """
            Get history item guid
            @param history_id as int
            @return guid as str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT guid\
                                  FROM history\
                                  WHERE rowid=?", (history_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_mtime(self, history_id):
        """
            Get history mtime
            @param history_id as int
            @return mtime as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT mtime\
                                  FROM history\
                                  WHERE rowid=?", (history_id,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return 0

    def get_atimes(self, history_id):
        """
            Get history access times
            @param history_id as int
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT atime\
                                  FROM history_atime\
                                  WHERE history_id=?", (history_id,))
            return list(itertools.chain(*result))

    def get_id_by_guid(self, guid):
        """
            Get id for guid
            @param guid as str
            @return id as int
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM history\
                                  WHERE guid=?", (guid,))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def get_ids_for_mtime(self, mtime):
        """
            Get ids that need to be synced related to mtime
            @param mtime as int
            @return [int]
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT rowid\
                                  FROM history\
                                  WHERE mtime > ?", (mtime,))
            return list(itertools.chain(*result))

    def get_match(self, uri):
        """
            Try to get best uri matching
            @parma uri as str
            @return str
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT uri\
                                  FROM history\
                                  WHERE uri like ?\
                                  ORDER BY popularity DESC,\
                                  length(uri) ASC\
                                  LIMIT 1",
                                 ("%" + uri + "%",))
            v = result.fetchone()
            if v is not None:
                return v[0]
            return None

    def set_title(self, history_id, title):
        """
            Set history title
            @param history_id as int
            @param title as str
            @param commit as bool
        """
        with SqlCursor(self) as sql:
            sql.execute("UPDATE history\
                         SET title=?\
                         WHERE rowid=?", (title, history_id,))

    def get_populars(self, netloc, limit):
        """
            Get popular bookmarks
            @param netloc as str
            @param limit as bool
            @return [(id, title, uri)]
        """
        with SqlCursor(self) as sql:
            if netloc:
                # Hack: we return history.mtime as count because we know
                # it will not be used
                result = sql.execute("\
                                SELECT rowid,\
                                       uri,\
                                       uri,\
                                       title,\
                                       mtime\
                                FROM history\
                                WHERE netloc=?\
                                AND popularity!=0\
                                ORDER BY popularity DESC,\
                                mtime DESC\
                                LIMIT ?", (netloc, limit))
            else:
                result = sql.execute("\
                                SELECT rowid,\
                                       uri,\
                                       netloc,\
                                       netloc,\
                                       COUNT(uri)\
                                FROM history\
                                GROUP BY netloc\
                                ORDER BY MAX(popularity) DESC,\
                                mtime DESC\
                                LIMIT ?", (limit,))
            return list(result)

    def get_opened_pages(self):
        """
            Get page with opened state
            @return [(uri, title)]
        """
        with SqlCursor(self) as sql:
            try:
                result = sql.execute("SELECT uri, title\
                                      FROM history\
                                      WHERE opened=1")
                return list(result)
            finally:
                sql.execute("UPDATE history\
                             SET opened=0\
                             WHERE opened=1")

    def set_page_state(self, uri, mtime=None):
        """
            Mark page with uri as opened if mtime is not None
            @param uri as str
            @param mtime as double
        """
        if uri is None:
            return
        uri = uri.rstrip('/')
        with SqlCursor(self) as sql:
            if mtime is None:
                sql.execute("UPDATE history\
                             SET opened=0\
                             WHERE uri=?\
                             AND opened=1", (uri,))
            else:
                sql.execute("UPDATE history\
                             SET opened=1 WHERE uri=?\
                             AND mtime=?", (uri, mtime))

    def set_atimes(self, history_id, atimes):
        """
            Set history atime
            @param history_id as int
            @param atimes as [int]
            @param commit as bool
        """
        with SqlCursor(self) as sql:
            current_atimes = self.get_atimes(history_id)
            for atime in atimes:
                if atime not in current_atimes:
                    sql.execute("INSERT INTO history_atime (history_id, atime)\
                                 VALUES (?, ?)", (history_id, atime))

    def set_mtime(self, history_id, mtime):
        """
            Set history mtime
            @param history_id as int
            @param mtime as int
        """
        with SqlCursor(self) as sql:
            sql.execute("UPDATE history\
                         SET mtime=? where rowid=?", (mtime, history_id))

    def search(self, search, limit):
        """
            Search string in db (uri and title)
            @param search as str
            @param limit as int
            @return [(id, title, uri, score)] as [(int, str, str, int)]
        """
        words = search.split(" ")
        # Remove empty items
        words = [value.strip() for value in words]
        words = list(filter(lambda x: x != '', words))
        items = []
        with SqlCursor(self) as sql:
            filters = ()
            for word in words:
                if not word:
                    continue
                filters += ("%" + word + "%", "%" + word + "%")
            filters += (limit,)
            request = "SELECT rowid, title, uri\
                       FROM history"
            if words:
                request += " WHERE"
            else:
                request += " ORDER BY popularity DESC, mtime DESC"
            words_copy = list(words)
            while words_copy:
                word = words_copy.pop(0)
                request += " (title LIKE ? OR uri LIKE ?)"
                if words_copy:
                    request += " AND "
            if words:
                request += " ORDER BY length(uri) ASC"
            request += " LIMIT ?"

            result = sql.execute(request, filters)
            items += list(result)

            # And then search containing one item
            request = "SELECT rowid, title, uri\
                       FROM history"
            if words:
                request += " WHERE"
            else:
                request += " ORDER BY popularity DESC, mtime DESC"
            words_copy = list(words)
            while words_copy:
                word = words_copy.pop(0)
                request += " (title LIKE ? OR uri LIKE ?)"
                if words_copy:
                    request += " OR "
            if words:
                request += " ORDER BY length(uri) ASC"
            request += " LIMIT ?"
            result = sql.execute(request, filters)
            items += list(result)
        # Do some scoring calculation on items
        scored_items = []
        uris = []
        for item in items:
            score = 0
            for word in words:
                lower_word = word.lower()
                title = item[1].lower()
                uri = item[2].lower()
                # Title match
                if title.find(lower_word) != -1:
                    score += 1
                # URI match
                if uri.find(lower_word) != -1:
                    score += 1
                    parsed = urlparse(uri)
                    # If netloc match word, +1
                    if parsed.netloc.find(lower_word + "."):
                        score += 1
                    # If root +1
                    if not parsed.path:
                        score += 1
            scored_item = (item[0], item[1], item[2], score)
            if item[2] not in uris:
                scored_items.append(scored_item)
                uris.append(item[2])
        return scored_items

    def reset_popularity(self, uri):
        """
            Reset popularity for uri
            @param uri as str
        """
        with SqlCursor(self) as sql:
            parsed = urlparse(uri)
            if parsed.scheme:
                sql.execute("UPDATE history SET popularity=0 WHERE uri=?",
                            (uri,))
            else:
                sql.execute("UPDATE history SET popularity=0 WHERE netloc=?",
                            (uri,))

    def exists_guid(self, guid):
        """
            Check if guid exists in db
            @return bool
        """
        with SqlCursor(self) as sql:
            result = sql.execute("SELECT guid FROM history\
                                  WHERE guid=?", (guid,))
            v = result.fetchone()
            return v is not None

    def get_cursor(self):
        """
            Return a new sqlite cursor
        """
        try:
            c = sqlite3.connect(self.DB_PATH, 600.0)
            c.create_collation('LOCALIZED', LocalizedCollation())
            c.create_function("noaccents", 1, noaccents)
            return c
        except Exception as e:
            Logger.error("DatabaseHistory::get_cursor(): %s", e)
            exit(-1)

#######################
# PRIVATE             #
#######################
