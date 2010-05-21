# desktopcover - displays Exaile album covers on the desktop
# Copyright (C) 2006-2010  Johannes Sasongko <sasongko@gmail.com>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import division
import gobject
import gtk

from xl import (
    common,
    covers,
    event,
    main,
    settings
)
from xl.nls import gettext as _
from xlgui import (
    guiutil,
    icons
)

import desktopcover_preferences

DESKTOPCOVER = None

def __migrate_anchor_setting():
    """
        Migrates gravity setting from the old
        integer values to the new string values
    """
    gravity = settings.get_option('plugin/desktopcover/anchor', 'topleft')
    gravity_map = DesktopCover.gravity_map

    if gravity not in gravity_map:
        gravities = gravity_map.keys()
        
        try:
            gravity = gravity_map[gravities[gravity]]
        except IndexError, TypeError:
            gravity = 'topleft'

        settings.set_option('plugin/desktopcover/anchor', gravity)

def enable(exaile):
    """
        Enables the desktop cover plugin
    """
    __migrate_anchor_setting()

    global DESKTOPCOVER
    DESKTOPCOVER = DesktopCover()

def disable(exaile):
    """
        Disables the desktop cover plugin
    """
    global DESKTOPCOVER
    DESKTOPCOVER.destroy()

def get_preferences_pane():
    return desktopcover_preferences

class DesktopCover(gtk.Window):
    gravity_map = {
        'topleft': gtk.gdk.GRAVITY_NORTH_WEST,
        'topright': gtk.gdk.GRAVITY_NORTH_EAST,
        'bottomleft': gtk.gdk.GRAVITY_SOUTH_WEST,
        'bottomright': gtk.gdk.GRAVITY_SOUTH_EAST
    }

    def __init__(self):
        gtk.Window.__init__(self)

        self.image = gtk.Image()
        self.add(self.image)
        self.image.show()

        self.set_accept_focus(False)
        self.set_decorated(False)
        self.set_keep_below(True)
        self.set_resizable(False)
        self.set_role("desktopcover")
        self.set_skip_pager_hint(True)
        self.set_skip_taskbar_hint(True)
        self.set_title("Exaile desktop cover")
        self.stick()

        self._fade_in_id = None
        self._fade_out_id = None
        self._cross_fade_id = None
        self._cross_fade_step = 0
        self._events = [
            'playback_track_start',
            'playback_player_end',
            'cover_set',
            'cover_removed',
            'option_set'
        ]

        for e in self._events:
            event.add_callback(getattr(self, 'on_%s' % e), e)

        try:
            exaile = main.exaile()
        except AttributeError:
            event.add_callback(self.on_exaile_loaded, 'exaile_loaded')
        else:
            self.on_exaile_loaded('exaile_loaded', exaile, None)

    def destroy(self):
        """
            Cleanups
        """
        for e in self._events:
            event.remove_callback(getattr(self, 'on_%s' % e), e)

        gtk.Window.destroy(self)

    def set_cover_from_track(self, track):
        """
            Updates the cover image and triggers cross-fading
        """
        cover_data = covers.MANAGER.get_cover(track)

        if cover_data is None:
            self.hide()
            return

        if not self.props.visible:
            self.show()

        size = settings.get_option('plugin/desktopcover/size', 200)
        upscale = settings.get_option('plugin/desktopcover/override_size', False)
        pixbuf = self.image.get_pixbuf()
        next_pixbuf = icons.MANAGER.pixbuf_from_data(
            cover_data, size=(size, size), upscale=upscale)
        fading = settings.get_option('plugin/desktopcover/fading', False)

        if fading and pixbuf is not None and self._cross_fade_id is None:
            duration = settings.get_option(
                'plugin/desktopcover/fading_duration', 50)

            # Prescale to allow for proper crossfading
            width, height = next_pixbuf.get_width(), next_pixbuf.get_height()
            pixbuf = pixbuf.scale_simple(width, height, gtk.gdk.INTERP_BILINEAR)
            self.image.set_from_pixbuf(pixbuf)

            self._cross_fade_id = gobject.timeout_add(
                int(duration), self.cross_fade, next_pixbuf, duration)
        else:
            self.image.set_from_pixbuf(next_pixbuf)

    def update_position(self):
        """
            Updates the position based
            on gravity and offsets
        """
        gravity = self.gravity_map[settings.get_option(
            'plugin/desktopcover/anchor', 'topleft')]
        x = settings.get_option('plugin/desktopcover/x', 0)
        y = settings.get_option('plugin/desktopcover/y', 0)
        allocation = self.get_allocation()
        workarea_size = guiutil.get_workarea_size()

        if gravity in (gtk.gdk.GRAVITY_NORTH_EAST,
                gtk.gdk.GRAVITY_SOUTH_EAST):
            x = workarea_size[0] - allocation.width - x

        if gravity in (gtk.gdk.GRAVITY_SOUTH_EAST,
                gtk.gdk.GRAVITY_SOUTH_WEST):
            y = workarea_size[1] - allocation.height - y

        self.set_gravity(gravity)
        self.move(int(x), int(y))

    def show(self):
        """
            Override for fade-in
        """
        fading = settings.get_option('plugin/desktopcover/fading', False)

        if fading and self._fade_in_id is None:
            self.set_opacity(0)

        gtk.Window.show(self)

        if fading and self._fade_in_id is None:
            duration = settings.get_option(
                'plugin/desktopcover/fading_duration', 50)
            self._fade_in_id = gobject.timeout_add(
                int(duration), self.fade_in)

    def hide(self):
        """
            Override for fade-out
        """
        fading = settings.get_option('plugin/desktopcover/fading', False)

        if fading and self._fade_out_id is None:
            duration = settings.get_option(
                'plugin/desktopcover/fading_duration', 50)
            self._fade_out_id = gobject.timeout_add(
                int(duration), self.fade_out)
        else:
            gtk.Window.hide(self)
            self.image.set_from_pixbuf(None)

    def fade_in(self):
        """
            Increases opacity until completely opaque
        """
        opacity = self.get_opacity()

        if opacity == 1:
            self._fade_in_id = None

            return False

        self.set_opacity(opacity + 0.1)

        return True

    def fade_out(self):
        """
            Decreases opacity until transparent
        """
        opacity = self.get_opacity()

        if opacity == 0:
            gtk.Window.hide(self)
            self.image.set_from_pixbuf(None)
            self._fade_out_id = None

            return False

        self.set_opacity(opacity - 0.1)

        return True

    def cross_fade(self, next_pixbuf, duration):
        """
            Fades between two cover images

            :param next_pixbuf: the cover image pixbuf to fade to
            :type next_pixbuf: :class:`gtk.gdk.Pixbuf`
            :param duration: the overall time for the fading
            :type duration: int
        """
        if self._cross_fade_step < duration:
            pixbuf = self.image.get_pixbuf()
            width, height = pixbuf.get_width(), pixbuf.get_height()
            alpha = (255 / duration) * self._cross_fade_step

            next_pixbuf.composite(
                dest=pixbuf,
                dest_x=0, dest_y=0,
                dest_width=width, dest_height=height,
                offset_x=0, offset_y=0,
                scale_x=1, scale_y=1,
                interp_type=gtk.gdk.INTERP_BILINEAR,
                overall_alpha=int(alpha)
            )

            self.image.queue_draw()
            self._cross_fade_step += 1

            return True

        self._cross_fade_id = None
        self._cross_fade_step = 0
        
        return False

    def on_playback_track_start(self, type, player, track):
        """
            Updates the cover image and shows the window
        """
        self.set_cover_from_track(track)
        self.update_position()

    def on_playback_player_end(self, type, player, track):
        """
            Hides the window at the end of playback
        """
        self.hide()

    def on_cover_set(self, type, covers, track):
        """
           Updates the cover image after cover selection
        """
        self.set_cover_from_track(track)
        self.update_position()

    def on_cover_removed(self, type, covers, track):
        """
            Hides the window after cover removal
        """
        self.hide()

    def on_option_set(self, type, settings, option):
        """
            Updates the appearance
        """
        if option in ('plugin/desktopcover/anchor',
                'plugin/desktopcover/x',
                'plugin/desktopcover/y'):
            self.update_position()
        elif option in ('plugin/desktopcover/override_size',
                'plugin/desktopcover/size'):
            self.set_cover_from_track(self.player.current)

    def on_exaile_loaded(self, e, exaile, nothing):
        """
            Sets up references after controller is loaded
        """
        self.player = exaile.player

        event.remove_callback(self.on_exaile_loaded, 'exaile_loaded')

# vi: et sts=4 sw=4 tw=80
