# Copyright (C) 2009 Abhishek Mukherjee <abhishek.mukher.g@gmail.com>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 1, or (at your option)
# any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.

import os
from xlgui.preferences import widgets
from xl import xdg
from xl.nls import gettext as _

name = _('Notify')
basedir = os.path.dirname(os.path.realpath(__file__))
ui = os.path.join(basedir, "notifyprefs_pane.ui")


class ResizeCovers(widgets.CheckPreference):
    default = True
    name = 'plugin/notify/resize'


class AttachToTray(widgets.CheckPreference):
    default = True
    name = 'plugin/notify/attach_tray'


class BodyArtistAlbum(widgets.TextViewPreference):
    default = _("by %(artist)s\nfrom <i>%(album)s</i>")
    name = 'plugin/notify/body_artistalbum'


class BodyArtist(widgets.TextViewPreference):
    default = _("by %(artist)s")
    name = 'plugin/notify/body_artist'


class BodyAlbum(widgets.TextViewPreference):
    default = _("from %(album)s")
    name = 'plugin/notify/body_album'


class Summary(widgets.TextViewPreference):
    default = _("%(title)s")
    name = 'plugin/notify/summary'

