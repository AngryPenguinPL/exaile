#!/usr/bin/env python
# Copyright (C) 2007 Dan O'Reilly

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

import gobject
import gtk
from xl import common, media, library, plugins, xlmisc
from gettext import gettext as _
from xl.panels import collection
import xl.path


PLUGIN_NAME = "MTP Device Manager"
PLUGIN_AUTHORS = ["Dan O'Reilly <oreilldf@gmail.com>"]
PLUGIN_VERSION = "0.4.0"
PLUGIN_DESCRIPTION = _(r"""MTP device manager.
\n\nDepends:
\nlibmtp: http://libmtp.sourceforge.net/
\npymtp: http://nick125.com/projects/pymtp/""")
PLUGIN_ENABLED = False
PLUGIN_ICON = None

try:
    import pymtp
    MTP_INSTALLED = True
except:
    MTP_INSTALLED = False

CONNS = plugins.SignalContainer()


class MTPTrack(media.Track):
    '''
        MTPTrack class for holding media.Track info, the LIBMTP_Track
        item_id, and identifying the track type as 'device' so things get
        handled correctly by exaile.
    '''
    type = 'device'

    def __init__(self, title_t, artist_t, album_t, track_t, year_t, length_t, genre_t):
        '''
            Initializes a media.Track type with the necessary metadata
        '''
        media.Track.__init__(self, title=title_t, artist=artist_t, album=album_t,
                             genre=genre_t, track=track_t, year=year_t, length=length_t)
        self.type = 'device'
        mtp_item_id = None


class MTPPlaylist(object):
    """
        Container for MTP Playlist
    """

    def __init__(self, playlist, root=False):
        self.playlist = playlist
        self.root = root
        self.name = playlist.name
        self.tracks = playlist.tracks
        self.no_tracks = playlist.no_tracks
        self.playlist_id = playlist.playlist_id
    
    def __str__(self):
        return self.name


class MTPDeviceDriver(plugins.DeviceDriver):
    '''
        Class that implements an MTP Device Driver
    '''
    name = 'mtpdevice'
    
    def __init__(self):
        """
            Initializes the MTPDeviceDriver class.
        """
        plugins.DeviceDriver.__init__(self)
        self.connected = False
        self.connecting = False
        self.exaile = APP
        self.dp = APP.device_panel
        self.mtp_image = xlmisc.get_icon('gnome-dev-ipod')
        self.track_image = gtk.gdk.pixbuf_new_from_file(xl.path.get_data(
                                        'images', 'track.png'))
        self.playlist_image = gtk.gdk.pixbuf_new_from_file(xl.path.get_data(
                                        'images', 'playlist.png'))
        self.directory_image = xlmisc.get_icon('gnome-fs-directory')


    @common.threaded
    def connect(self, panel):
        '''
            Connects to the MTP device and loads playlist/track
             info into exaile.
        '''
        if self.connecting: self.disconnect()

        self.connecting = True
        self.panel = panel
        self.collection_panel = self.exaile.collection_panel
        self.mtp = pymtp.MTP()
        try:
            self.mtp.connect()
            self.connected = True
        except:
            self.panel.on_connect_complete(None)
            gobject.idle_add(panel.on_error, _("Couldn't connect to the MTP device,"
                                        " wait a few seconds or reconnect the"
                                        " device, then try again."))
            self.connected = False
            self.connecting = False
            return

        self.panel.track_count.set_label(_("Loading tracks..."))
        tracks = self.mtp.get_tracklisting()
        gobject.idle_add(self._load_tracks, tracks)
        
        self.panel.track_count.set_label(_("Loading playlists..."))
        self.playlists = {}
        for playlist in self.mtp.get_playlists():
            p_entry = MTPPlaylist(playlist)
            self.playlists[p_entry] = []
            for track in playlist.__iter__():
                self.playlists[p_entry].append(track)
            
        self.panel.track_count.set_label(_("Loading folders..."))

        self.connecting = False


    def _load_tracks(self, track_list):
        '''
            Loads the tracks from the connected device into the device panel
        '''
        self.all = library.TrackData()
        self.all_dict = {}
        for t in list(track_list):
            song = MTPTrack(t.title, t.artist, t.album, t.tracknumber,
                            t.date, t.duration/1000, t.genre)
            song.mtp_item_id = t.item_id
            # Since MTP tracks don't have an actual path, we use the
            # unique item_id the MTP player assigns it, so that exaile
            # has a way to hunt down the track from the panel tree.
            song.loc = str(t.item_id)
            gobject.idle_add(self.all.append, song)
            self.all_dict[t.item_id] = song
        self.connected = True
        gobject.idle_add(self.panel.on_connect_complete, self)


    def get_menu(self, item, menu):
        return menu


    def get_initial_root(self, model):
        """
            Adds new nodes and returns the one tracks should be added to
        """
        if not self.playlists: return None
        self.mtproot = model.append(None, [self.directory_image, _("Playlists"),
            'nofield'])

        for k, v in self.playlists.iteritems():
            item = model.append(self.mtproot, [self.playlist_image, k,
                                               'nofield'])
            self.load_playlist(item, v, model)
        new_root = model.append(None, [self.mtp_image, _("Music Collection"),
                                       'nofield'])
        return new_root
    
    
    def load_playlist(self, parent, list_contents, model):
        """
            Adds the track list for a given playlist to the device panel
            in Artst - Title format.
        """
        for track_id in list_contents:
            song = self.all_dict[track_id]
            if not song:
                print 'Couldn\'t find playlist track on device'
                continue
            name = song.artist + " - " + song.title
            model.append(parent, [self.track_image, name, 'nofield'])


    def done_loading_tree(self):
        """
            Called when the tree is done loading
        """
        path = self.dp.model.get_path(self.mtproot)
        self.dp.tree.expand_row(path, False)


    def disconnect(self, *a, **k):
        '''
            Disconnects the MTP device
        '''
        self.mtp.disconnect()
        self.panel = None
        self.connected = False
        self.connecting = False
        self.playlists = None
        self.all = None
        self.all_dict = None


    def remove_tracks(self, tracks):
        '''
            Removes tracks from the MTP device
        '''
        for track in tracks:
            print 'deleting ', track
            self.mtp.delete_object(int(track.mtp_item_id))
            self.all.remove(track)
            del self.all_dict[track.mtp_item_id]
            for playlist in self.playlists:
                try:
                    del playlist[track.mtp_item_id]
                except:
                    pass


    def search_tracks(self, keyword):
        '''
            Searches for a keyword if one is provided, and then sorts the
            results based on the panel drop-down box.
        '''
        if keyword:
            check = []
            for track in self.all:
                for item in ('artist', 'album', 'title'):
                    attr = getattr(track, item)
                    if keyword.lower() in attr.lower():
                        check.append(track)
        else:
            check = self.all

        new = []
        for song in check:
            a = {
                'album': library.lstrip_special(song.album),
                'artist': library.lstrip_special(library.the_cutter((song.artist))),
                'title': library.lstrip_special(song.title),
                'genre': library.lstrip_special(song.genre),
                'track': song.track,
            }

            if self.panel.choice.get_active() == 0:  # Artist view
                new.append((a['artist'], a['album'], a['track'], a['title'], song))
            elif self.panel.choice.get_active() == 1:  # Album view
                new.append((a['album'], a['artist'], a['track'], a['title'], song))
            else:  # Genre view
                new.append((a['genre'],a['artist'], a['album'], a['track'], a['title'], song))
        new.sort()
        return library.TrackData([a[-1] for a in new])


    def put_item(self, item):
        '''
            Transfers a track to the MTP device
        '''
        # Just for sanity
        track = item.track
        metadata = pymtp.LIBMTP_Track()

        # Load the metadata from the track into a LIBMTP_Track for transfer
        if (hasattr(track, 'artist')):
            metadata.artist = track.artist
        if (hasattr(track, 'title')):
            metadata.title = track.title
        if (hasattr(track, 'album')):
            metadata.album = track.album
        if (hasattr(track, 'track')):
            metadata.tracknumber = track.track
        if (hasattr(track, 'date')):
            metadata.date = track.date
        if (hasattr(track, 'genre')):
            metadata.genre = track.genre
        if (hasattr(track, '_len')):
            # Convert length to milliseconds so the MTP device
            # will display it properly
            metadata.duration = track.get_duration() * 1000

        song = MTPTrack(track.title, track.artist, track.album, metadata.tracknumber,
                        metadata.date, metadata.duration, metadata.genre)
        filename = str(track.get_filename())
        loc = str(track.get_loc())

        # Transfer the file
        track_id = self.mtp.send_track_from_file(loc, filename, metadata, parent=0)
        song.mtp_item_id = track_id #  Store the id for removing the track later
        # Assign the track a unique location
        song.loc = str(track_id)
        gobject.idle_add(self.all.append, song)
        self.all_dict[track_id] = song
    
    
    def get_song(self, song):
        """
            Transfers a track from the device and to the /tmp/ directory
            on the filesystem, and returns that track object.
        """
        new_loc = "/tmp/" + song.artist + '-' + song.title
        self.mtp.get_track_to_file(int(song.mtp_item_id), str(new_loc))
        song.loc = new_loc
        return song


def initialize():
    '''
        Initializes the plugin
    '''
    global PLUGIN
    
    if not MTP_INSTALLED:
        common.error(APP.window, _("The pymtp library could not be found.  Make"
                                   "sure you install both libmtp and pytmp "
                                   "(http://nick125.com/projects/pymtp/) before using this plugin."))
        return False
    PLUGIN = MTPDeviceDriver()
    if PLUGIN is None:
        return False
    APP.device_panel.add_driver(PLUGIN, PLUGIN_NAME)
    CONNS.connect(APP, 'quit', quit)
    return True


def destroy():
    '''
        Disconnects the device and removes the driver instance from the
        device panel.
    '''
    global PLUGIN
    if PLUGIN.connected is True:
        PLUGIN.mtp.disconnect()
    CONNS.disconnect_all()
    APP.device_panel.remove_driver(PLUGIN)
    PLUGIN = None


def quit(exaile):
    '''
        Disconnects the attached device when user quits exaile
    '''
    global PLUGIN
    if PLUGIN.connected is True:
        PLUGIN.mtp.disconnect()
