# Copyright (c) 2017-2020 Cedric Bellegarde <cedric.bellegarde@adishatz.org>
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

from gi.repository import GObject


class Item(GObject.GObject):
    id = GObject.Property(type=int,
                          default=0)
    type = GObject.Property(type=int,
                            default=0)
    title = GObject.Property(type=str,
                             default="")
    uri = GObject.Property(type=str,
                           default="")
    atime = GObject.Property(type=int,
                             default=0)
    score = GObject.Property(type=int,
                             default=0)

    def __init__(self):
        GObject.GObject.__init__(self)
