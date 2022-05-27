from os import mkdir, path, remove, system
from subprocess import Popen
from time import sleep, time
from ytmusicapi import YTMusic
from argparse import ArgumentParser
from codecs import getreader
from http.server import HTTPServer, BaseHTTPRequestHandler
from logging import basicConfig, info
from re import search
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from json import load, dump
from shutil import copy2
from webbrowser import open as open_browser

basicConfig(level=20, datefmt='%H:%M:%S', format='[%(asctime)s] %(message)s')


class SpotifyAPI:
    def scrub_cruft(obj):
        if isinstance(obj, dict):
            excludeItems = [
                "available_markets", "album", "added_at", "disc_number", "duration_ms", "explicit", "external_ids", "href", "is_local", "popularity", "preview_url", "track_number", "uri", "collaborative", "images", "owner", "primary_color", "public",
                "snapshot_id", "added_by", "episode", "video_thumbnail", "external_urls", "id", "type"
            ]
            for i in excludeItems:
                if i in obj:
                    del obj[i]
            for _, v in obj.items():
                SpotifyAPI.scrub_cruft(v)
        elif isinstance(obj, list):
            for v in obj:
                SpotifyAPI.scrub_cruft(v)

    def __init__(self, auth):
        self._auth = auth

    def get(self, url, params={}, tries=3):
        if not url.startswith('https://api.spotify.com/v1/'):
            url = 'https://api.spotify.com/v1/' + url
        if params:
            url += ('&' if '?' in url else '?') + \
            urlencode(params)
        for _ in range(tries):
            try:
                req = Request(url)
                req.add_header('Authorization', 'Bearer ' + self._auth)
                res = urlopen(req)
                reader = getreader('utf-8')
                return load(reader(res))
            except Exception as err:
                info('Couldn\'t load URL: {} ({})'.format(url, err))
                sleep(2)
                info('Trying again...')
        exit(1)

    def list(self, url, params={}):
        last_log_time = time()
        response = self.get(url, params)
        items = response['items']
        while response['next']:
            if time() > last_log_time + 15:
                last_log_time = time()
                info(f"Loaded {len(items)}/{response['total']} items")
            response = self.get(response['next'])
            items += response['items']
        return items

    @staticmethod
    def authorize(client_id, scope):
        url = 'https://accounts.spotify.com/authorize?' + urlencode({'response_type': 'token', 'client_id': client_id, 'scope': scope, 'redirect_uri': 'http://127.0.0.1:{}/redirect'.format(SpotifyAPI._SERVER_PORT)})
        info(f'Logging in (click if it doesn\'t open automatically): {url}')
        open_browser(url)
        server = SpotifyAPI._AuthorizationServer('127.0.0.1', SpotifyAPI._SERVER_PORT)
        try:
            while True:
                server.handle_request()
        except SpotifyAPI._Authorization as auth:
            return SpotifyAPI(auth.access_token)

    _SERVER_PORT = 43019

    class _AuthorizationServer(HTTPServer):
        def __init__(self, host, port):
            HTTPServer.__init__(self, (host, port), SpotifyAPI._AuthorizationHandler)

        def handle_error(self, request, client_address):
            raise

    class _AuthorizationHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path.startswith('/redirect'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>location.replace("token?" + location.hash.slice(1));</script>')
            elif self.path.startswith('/token?'):
                self.send_response(200)
                self.send_header('Content-Type', 'text/html')
                self.end_headers()
                self.wfile.write(b'<script>close()</script>Thanks! You may now close this window.')
                access_token = search('access_token=([^&]*)', self.path).group(1)
                info(f'Received access token from Spotify: {access_token}')
                raise SpotifyAPI._Authorization(access_token)
            else:
                self.send_error(404)

        def log_message(self, format, *args):
            pass

    class _Authorization(Exception):
        def __init__(self, access_token):
            self.access_token = access_token


class YouTubeAPI:
    def setupAPI():
        scriptPath = path.split(__file__)[0]
        if not path.exists(scriptPath + "\\headers_auth.json"):
            print("WARNING: File " + scriptPath + "\\headers_auth.json was not found, please place file in the opend folder!\n\n"
                  "To set up this file go to https://music.youtube.com/ and open network debuging tools\n"
                  "Look for the first item with Status 200, Method Post, Domain music.youtube.com and file start with log_event?alt=json&key= (Right click this item and Copy Request Headers)\n"
                  "Open python and run the following commands (After running these commands paste the previos copied item, press enter, ctrl-z, enter, this token is valid for around 1-2 years or until log off on this browser session)\n"
                  "from ytmusicapi import YTMusic\n"
                  "YTMusic.setup(filepath=\"" + scriptPath + "\headers_auth.json\")")
            open_browser("https://music.youtube.com/")
            Popen(r'explorer /select, ' + __file__)
        while not path.exists(scriptPath + "\\headers_auth.json"):
            sleep(1)
        return YTMusic(scriptPath + "\\headers_auth.json")

    def createPlaylist(title, description: str = "Automaticly generated from script."):
        scriptPath = path.split(__file__)[0]
        if args.test:
            playlistID = "testing"
        else:
            playlistID = ytmusic.create_playlist(title, description)
        newPlaylistIDs = open(scriptPath + "\\createdPlaylistIDs.dmp", "a", encoding="UTF-8")
        newPlaylistIDs.write(playlistID + "\n")
        newPlaylistIDs.close
        return playlistID

    def searchSong(songName, playlistMode):
        # Strict song search
        if "Safe" in playlistMode or "Export" in playlistMode:
            playlistMode = ""
        search_results = ytmusic.search(songName, filter="songs", ignore_spelling=True)
        try: # yapf: Disable | Debuging an unknow problem.
            for songdata in search_results:
                if songdata["duration_seconds"] < args.maxLenght:
                    if playlistMode == "" or playlistMode.lower() in songdata["title"].lower() or playlistMode.lower() in songdata["artists"][0]["name"].lower():
                        for i in songName.split(" - "):
                            if i.lower() in songdata["title"].lower() or i.lower() in songdata["artists"][0]["name"].lower():
                                return songdata
        except IndexError:
            print("IndexError between line 150 and 155, exiting!\n\n" + str(search_results))
        # Strict video search
        search_results = ytmusic.search(songName, filter="videos", ignore_spelling=True)
        for songdata in search_results:
            if songdata["duration_seconds"] < args.maxLenght:
                if playlistMode == "" or playlistMode.lower() in songdata["title"].lower() or playlistMode.lower() in songdata["artists"][0]["name"].lower():
                    for i in songName.split(" - "):
                        if i.lower() in songdata["title"].lower() or i.lower() in songdata["artists"][0]["name"].lower():
                            return songdata
        # Loose song search
        search_results = ytmusic.search(songName, filter="songs", ignore_spelling=True)
        for songdata in search_results:
            if songdata["duration_seconds"] < args.maxLenght:
                if playlistMode == "" or playlistMode.lower() in songdata["title"].lower() or playlistMode.lower() in songdata["artists"][0]["name"].lower():
                    for i in songName.replace(" - ", " ").split(" "):
                        if i.lower() in songdata["title"].lower() or i.lower() in songdata["artists"][0]["name"].lower():
                            return songdata
        # Loose video search
        search_results = ytmusic.search(songName, filter="videos", ignore_spelling=True)
        for songdata in search_results:
            if songdata["duration_seconds"] < args.maxLenght:
                if playlistMode == "" or playlistMode.lower() in songdata["title"].lower() or playlistMode.lower() in songdata["artists"][0]["name"].lower():
                    for i in songName.replace(" - ", " ").split(" "):
                        if i.lower() in songdata["title"].lower() or i.lower() in songdata["artists"][0]["name"].lower():
                            return songdata
        return "Failed"

    def appendPlaylist(playlistID: str, songs: list, songLen: int = "?", playlistMode: str = ""):
        songCount = 0
        goodCount = 0
        for song in songs:
            if playlistMode == "NightCore" and playlistMode not in song:
                song = song.replace(" - ", " " + playlistMode + " - ")
            songCount += 1
            addedState = False
            skipState = False
            search_results = YouTubeAPI.searchSong(song, playlistMode)
            if search_results == "Failed":
                addedState = False
                skipState = True
                cacheHandler.logToFile("Warning (" + str(songCount) + " / " + str(songLen) + ") | Unable to find song or video: " + song + "\n")
            exceptionCount = 0
            while (not addedState and not skipState and exceptionCount <= 3):
                try:
                    if args.test:
                        outputAdd = {}
                        outputAdd["status"] = "STATUS_SUCCEEDED"
                    else:
                        outputAdd = ytmusic.add_playlist_items(playlistID, [search_results["videoId"]])
                    addedState = True
                except Exception:
                    exceptionCount += 1
                    addedState = False
                    info("Info (" + str(songCount) + " / " + str(songLen) + "): | Unable to add song to playlist, most likely a bad request was send or theres a timeout on adding more songs (Sleeping for 5 minutes then retrying, after 3 tries skipping)!")
                    cooldown = 300
                    while cooldown > 0:
                        sleep(1)
                        cooldown -= 1
            if addedState and not skipState:
                if outputAdd["status"] == "STATUS_SUCCEEDED":
                    goodCount += 1
                    info("Added (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
                elif outputAdd["status"] == "STATUS_FAILED":
                    if outputAdd["actions"][0]["addToToastAction"]["item"]["notificationActionRenderer"]["responseText"]["runs"][0]["text"] == "This song is already in the playlist":
                        info("Song already present (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
                    else:
                        cacheHandler.logToFile("NOT ADDED (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
        return goodCount, songCount

    def likeSongs(songs: list, songLen: int = "?", playlistMode: str = ""):
        songCount = 0
        goodCount = 0
        for song in songs:
            if playlistMode == "NightCore" and playlistMode not in song:
                song = song.replace(" - ", " " + playlistMode + " - ")
            songCount += 1
            addedState = False
            skipState = False
            search_results = YouTubeAPI.searchSong(song, playlistMode)
            if search_results == "Failed":
                addedState = False
                skipState = True
                cacheHandler.logToFile("Warning (" + str(songCount) + " / " + str(songLen) + ") | Unable to find song or video: " + song + "\n")
            exceptionCount = 0
            while (not addedState and not skipState and exceptionCount <= 3):
                try:
                    if args.test:
                        pass
                    else:
                        outputLike = ytmusic.rate_song(search_results["videoId"], "LIKE")
                    addedState = True
                except Exception:
                    exceptionCount += 1
                    addedState = False
                    info("Info (" + str(songCount) + " / " + str(songLen) + "): | Unable to like song, most likely a bad request was send or theres a timeout on liking more songs (Sleeping for 5 minutes before retrying, after 3 tries skipping)!")
                    cooldown = 300
                    while cooldown > 0:
                        sleep(1)
                        cooldown -= 1
            if addedState and not skipState:
                try:
                    if args.test:
                        goodCount += 1
                        info("Liked (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
                    elif outputLike["actions"][0]["addToToastAction"]["item"]["notificationActionRenderer"]["responseText"]["runs"][0]["text"] == "Added to your likes":
                        goodCount += 1
                        info("Liked (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
                    else:
                        cacheHandler.logToFile("UNABLE TO VERIFY LIKE (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
                except (KeyError, TypeError):
                    cacheHandler.logToFile("UNABLE TO VERIFY LIKE (" + str(songCount) + " / " + str(songLen) + "): " + search_results["title"] + " | " + search_results["artists"][0]["name"])
        return goodCount, songCount

    def purgePlaylists():
        if args.auto:
            info("WARNING: Skipping purging playlists becouse --auto flag was given!")
            return None
        if input("Do you want to remove all songs from known merge playlists.\nWARNING: This is not reaverable (y/n)! ").lower() == "y":
            if args.purgePlaylists == "purgeLiked":
                playlistTitle, playlistID, playlistMode = YouTubeAPI.getMergePlaylists("Liked")
                print("\n----------------\n")
                cacheHandler.logToFile("Started purging of: " + playlistTitle + "\n")
                userDone = False
                speedMode = False
                askedSpeedMode = False
                while not userDone:
                    if not "Safe" in playlistMode:
                        playlistData = ytmusic.get_liked_songs(500)
                        if playlistData["tracks"] == []:
                            info("No tracks to purge in: " + playlistTitle)
                            userDone = True
                        songCount = 0
                        for trackData in playlistData["tracks"]:
                            songCount += 1
                            if not args.test:
                                ytmusic.rate_song(trackData['videoId'], "INDIFFERENT")
                                if not speedMode:
                                    sleep(0.5)
                            info("Purged song from " + playlistTitle + " (" + str(songCount) + " / " + str(len(playlistData["tracks"])) + "): " + trackData["title"] + " | " + trackData["artists"][0]["name"])
                    else:
                        print("\n----------------\n")
                        info("Info: Skipped purge of playlist " + playlistTitle + " becouse its a safe playlists!")
                    if not speedMode:
                        if input("\nStop removing songs from liked (y/n)? ").lower() == "n":
                            if not askedSpeedMode:
                                if input("\nSpeed remove all songs (y/n)? ").lower() == "y":
                                    speedMode = True
                                askedSpeedMode = True
                        else:
                            userDone = True
            else:
                mergeData = YouTubeAPI.getMergePlaylists()
                for knownMergePlaylist in mergeData:
                    playlistTitle, playlistID, playlistMode = YouTubeAPI.getMergePlaylists(knownMergePlaylist)
                    if not "Safe" in playlistMode:
                        if playlistID != "Like":
                            print("\n----------------\n")
                            cacheHandler.logToFile("Started purging of: " + playlistTitle + "\n")
                            playlistData = ytmusic.get_playlist(playlistID, limit=2500)
                            if playlistData["tracks"] == []:
                                info("No tracks to purge in: " + playlistTitle)
                            songCount = 0
                            for trackData in playlistData["tracks"]:
                                songCount += 1
                                removedState = False
                                while not removedState:
                                    try:
                                        if not args.test:
                                            ytmusic.remove_playlist_items(playlistID, [trackData])
                                        removedState = True
                                    except Exception:
                                        removedState = False
                                        info("Info: Unable to purge song (" + str(songCount) + " / " + str(len(playlistData["tracks"])) + "): " + trackData["title"] + " | " + trackData["artists"][0]["name"] +
                                             "\nTheres a timeout on removing more songs (Sleeping for 5 minutes before retrying, after 3 tries skipping)!")
                                        cooldown = 300
                                        while cooldown > 0:
                                            sleep(1)
                                            cooldown -= 1
                                info("Purged song from " + playlistTitle + " (" + str(songCount) + " / " + str(len(playlistData["tracks"])) + "): " + trackData["title"] + " | " + trackData["artists"][0]["name"])
                else:
                    print("\n----------------\n")
                    info("Info: Skipped purge of playlist " + playlistTitle + " becouse its a safe playlists!")
        exit()

    def removePlaylists():
        scriptPath = path.split(__file__)[0]
        if not path.exists(scriptPath + "\\createdPlaylistIDs.dmp"):
            info("WARNING: No cache file for created playlist found! | Source: " + scriptPath + "\\createdPlaylistIDs.dmp")
            return None
        if args.auto:
            info("WARNING: Skipping purging playlists becouse --auto flag was given!")
            return None
        if input("Do you want to remove playlists stored in the cache file.\nWARNING: This is not reaverable (y/n)! ").lower() == "y":
            cachedPlaylistIDs = open(scriptPath + "\\createdPlaylistIDs.dmp", "r", encoding="UTF-8")
            cachedPlaylistIDsList = cachedPlaylistIDs.read().split("\n")
            cachedPlaylistIDs.close
            cachedPlaylistIDsList.pop()
            excludeIDs = []
            mergeData = YouTubeAPI.getMergePlaylists()
            for knownMergePlaylist in mergeData:
                playlistTitle, playlistID, playlistMode = YouTubeAPI.getMergePlaylists(knownMergePlaylist)
                if "Safe" in playlistMode:
                    excludeIDs.append(playlistID)
            for i in cachedPlaylistIDsList:
                if i in excludeIDs:
                    info("Info: Skipped removal of playlist with ID (" + i + ") becouse its a safe playlists!")
                else:
                    info("WARNING: Removed playlist with ID (" + i + ")")
                    if not args.test:
                        ytmusic.delete_playlist(i)
            if input("Do you want to remove the cached files.\nWARNING: This is not reaverable (y/n)! ").lower() == "y":
                if not args.test:
                    remove(scriptPath + "\\createdPlaylistIDs.dmp")
                    remove(scriptPath + "\\log.dmp")
        exit()

    def getMergePlaylists(title: str = ""):
        scriptPath = path.split(__file__)[0]
        mergeFile = open(scriptPath + "\\Merge.txt", "r", encoding="UTF-8")
        mergeFileList = mergeFile.read().split("\n")
        playlistTitle = ""
        playlistMeta = True
        data = {}
        for line in mergeFileList:
            if line != "":
                if line == "<MetaData>":
                    playlistTitle = ""
                    playlistMeta = True
                elif playlistMeta:
                    if "Title=" in line:
                        playlistTitle = line.replace("Title=", "")
                        data[playlistTitle] = {}
                        data[playlistTitle]["MetaData"] = []
                        data[playlistTitle]["Merge"] = []
                    if "Mode=" in line or "PlaylistID=" in line:
                        try:
                            data[playlistTitle]["MetaData"].append(line)
                        except KeyError:
                            info("WARNING: Merge.txt file is inproparly formated!\nRead the README.md file for instructions on the format!")
                            exit()
                if line == "<\MetaData>":
                    playlistMeta = False
                elif not playlistMeta:
                    try:
                        data[playlistTitle]["Merge"].append(line)
                    except KeyError:
                        info("WARNING: Merge.txt file is inproparly formated!\nRead the README.md file for instructions on the format!")
                        exit()
        if title == "":
            return data
        else:
            playlistID = ""
            playlistMode = ""
            for playlist in data:
                if title in data[playlist]["Merge"]:
                    for metaData in data[playlist]["MetaData"]:
                        if metaData.startswith("PlaylistID="):
                            playlistID = metaData.replace("PlaylistID=", "")
                        if metaData.startswith("Mode="):
                            playlistMode = metaData.replace("Mode=", "")
                    return playlist, playlistID, playlistMode
            return title, "", ""

    def exportToDmp():
        print("\n----------------\n")
        cacheHandler.logToFile("Started with export playlists to file!")
        scriptPath = path.split(__file__)[0]
        exportFile = open(scriptPath + "\\Export.dmp", "w", encoding="UTF-8")
        exportFile.write("")
        exportFile.close()
        exportFile = open(scriptPath + "\\Export.dmp", "a", encoding="UTF-8")
        mergeData = YouTubeAPI.getMergePlaylists()
        for knownMergePlaylist in mergeData:
            playlistTitle, playlistID, playlistMode = YouTubeAPI.getMergePlaylists(knownMergePlaylist)
            if "Export" in playlistMode:
                exportFile.write(playlistTitle + "\n")
                if playlistID == "Like":
                    likedSongsData = ytmusic.get_liked_songs(5000)
                    for track in likedSongsData["tracks"]:
                        exportFile.write(track["title"] + " - " + track["artists"][0]["name"] + "\n")
                    exportFile.write("<playlistEnd><\playlistEnd>\n")
                else:
                    playlistData = ytmusic.get_playlist(playlistID, limit=5000)
                    for track in playlistData["tracks"]:
                        exportFile.write(track["title"] + " - " + track["artists"][0]["name"] + "\n")
                    exportFile.write("<playlistEnd><\playlistEnd>\n")
                cacheHandler.logToFile("Exported playlists to file: " + playlistTitle)
        exportFile.close()
        print("\n----------------\n")
        cacheHandler.logToFile("Done with export playlists to file!")
        exit()

    def migrateDB(database):
        ignorePlaylists = []
        playlistCount = 0
        for name in database:
            playlistCount += 1
            if not name in ignorePlaylists and playlistCount > args.skip:
                playlistTitle, playlistID, playlistMode = YouTubeAPI.getMergePlaylists(name)
                print("\n----------------\n")
                cacheHandler.logToFile("Started export from: " + name + " to: " + playlistTitle + " (Playlist: " + str(playlistCount) + " / " + str(len(database)) + " | Songs: " + str(len(database[name])) + ")\n")
                if "Safe" in playlistMode or "Export" in playlistMode:
                    playlistMode == ""
                elif playlistMode != "":
                    info("Mode " + playlistMode)
                if playlistID == "Like":
                    output = YouTubeAPI.likeSongs(reversed(database[name]), len(database[name]), playlistMode)
                elif playlistID == "":
                    playlistID = YouTubeAPI.createPlaylist(name)
                    output = YouTubeAPI.appendPlaylist(playlistID, reversed(database[name]), len(database[name]), playlistMode)
                else:
                    output = YouTubeAPI.appendPlaylist(playlistID, reversed(database[name]), len(database[name]), playlistMode)
                print("\n----------------\n")
                cacheHandler.logToFile("Done with export from: " + name + " to: " + playlistTitle + " (Playlist: " + str(playlistCount) + " / " + str(len(database)) + " | Migrated: " + str(output[0]) + " / " + str(output[1]) + ")\n\n----------------\n\n")
        print("\n----------------\n\n")
        cacheHandler.logToFile("Done with all exports!")
        print("\n----------------\n")


class cacheHandler:
    def updateOsu():
        if not path.exists(path.expandvars(r"%LOCALAPPDATA%\\osu!\\collection.db")):
            info("WARNING: Osu collection database not found, skipping Osu Import!")
            return None
        if args.auto:
            info("WARNING: Skipping Osu Import becouse --auto flag was given!")
            return None
        scriptPath = path.split(__file__)[0]
        copy2(path.expandvars(r"%LOCALAPPDATA%\\osu!\\collection.db"), scriptPath)
        if not path.exists("C:\\Program Files (x86)\\Collection Manager\\App.exe"):
            open_browser("https://github.com/Piotrekol/CollectionManager/releases/download/1.0.196/CollectionManagerSetup.exe")
            print("Downloading dependensy (Waiting till program is installed), if it doesn't open click here: https://github.com/Piotrekol/CollectionManager/releases/download/1.0.196/CollectionManagerSetup.exe")
            while not path.exists("C:\\Program Files (x86)\\Collection Manager"):
                sleep(1)
        else:
            print(
                "\nDrag an drop collection.db into the Collection Manager and modefy the collection as you please.\nRemove all colums exept for the title and copy (ctlr + c) paste the playlists after entering the title.\nLeave the title empty when done.\n"
            )
            system('powershell "Start-Process \'C:\\Program Files (x86)\\Collection Manager\\App.exe\'')
        Popen(r'explorer /select, ' + __file__)
        collectionDmp = open(scriptPath + "\\osuCache.dmp", "w")
        collectionDmp.write("")
        collectionDmp.close()
        inputBusy = True
        sleep(5)
        while (inputBusy):
            songCount = 0
            print("\nKnown playlists: \n")
            for knownPlaylists in YouTubeAPI.getMergePlaylists():
                print(knownPlaylists)
            currentTitle = input("\nTitle: ")
            if not currentTitle == "":
                collectionDmp = open(scriptPath + "\\osuCache.dmp", "a")
                collectionDmp.write(currentTitle + "\n")
                collectionDmpTmp = open(scriptPath + "\\osuCache.dmp.tmp", "w")
                collectionDmpTmp.write("")
                collectionDmpTmp.close()
                print("Paste songs in opened file.")
                system('notepad "' + scriptPath + "\\osuCache.dmp.tmp"
                       '"')
                currentSongs = open(scriptPath + "\\osuCache.dmp.tmp", "r").read().split("\n")
                currentSongsCheck = []
                for i in currentSongs:
                    if i not in currentSongsCheck:
                        songCount += 1
                        currentSongsCheck.append(i)
                        collectionDmp.write(i + "\n")
                collectionDmp.write("<playlistEnd><\\playlistEnd>\n")
                collectionDmp.close()
                print("Title: " + currentTitle + " Songs: " + str(songCount))
            else:
                remove(scriptPath + "\\collection.db")
                remove(scriptPath + "\\osuCache.dmp.tmp")
                inputBusy = False

    def updateSpotify():
        scriptPath = path.split(__file__)[0]
        if args.token:
            spotify = SpotifyAPI(args.token)
        else:
            spotify = SpotifyAPI.authorize(client_id='5c098bcc800e45d49e476265bc9b6934', scope='playlist-read-private playlist-read-collaborative user-library-read')
        info('Loading user info...')
        me = spotify.get('me')
        info('Logged in as {display_name} ({id})'.format(**me))
        playlists = []
        if 'liked' in args.migrate:
            info('Loading liked songs...')
            liked_tracks = spotify.list('users/{user_id}/tracks'.format(user_id=me['id']), {'limit': 50})
            playlists += [{'name': 'Liked Songs', 'tracks': liked_tracks}]
        if 'playlists' in args.migrate:
            info('Loading playlists...')
            playlist_data = spotify.list('users/{user_id}/playlists'.format(user_id=me['id']), {'limit': 50})
            info(f'Found {len(playlist_data)} playlists')
            for playlist in playlist_data:
                info('Loading playlist: {name} ({tracks[total]} songs)'.format(**playlist))
                playlist['tracks'] = spotify.list(playlist['tracks']['href'], {'limit': 100})
            playlists += playlist_data
        SpotifyAPI.scrub_cruft(playlists)
        with open(scriptPath + "\\spotifyCache.json", 'w', encoding='utf-8') as f:
            dump(playlists, f, indent=2)
        info("Wrote file: " + scriptPath + "\\spotifyCache.json")
        spotifyDB = load(open(scriptPath + "\\spotifyCache.json", "r"))
        noTitleCount = 1
        currentFile = open(scriptPath + "\\spotifyCache.dmp", "w", encoding="UTF-8")
        currentFile.write("")
        currentFile.close
        currentFile = open(scriptPath + "\\spotifyCache.dmp", "a", encoding="UTF-8")
        for i in spotifyDB:
            if i["name"] == "":
                skipInteraction = False
                playlistData = YouTubeAPI.getMergePlaylists()
                for playlist in playlistData:
                    for mergeData in playlistData[playlist]["Merge"]:
                        if "[Unknown " + str(noTitleCount) + "]" in mergeData:
                            i["name"] = "[Unknown " + str(noTitleCount) + "]"
                            skipInteraction = True
                if args.auto:
                    i["name"] = "[Unknown]"
                if not skipInteraction:
                    trackCount = 0
                    unknownPlaylistTracks = ""
                    for i1 in i["tracks"]:
                        trackCount += 1
                        if trackCount <= 10:
                            unknownPlaylistTracks += str(i1["track"]["name"]) + " | " + i1["track"]["artists"][0]["name"] + "\n"
                    trackCountShow = 10
                    if trackCount < trackCountShow:
                        trackCountShow = trackCount
                    print("\n\nWARNING! Playlist [Unknown " + str(noTitleCount) + "] has no Title! Songs (" + str(trackCountShow) + " / " + str(trackCount) + "):\n" + unknownPlaylistTracks +
                          "\nWhat should the name of the playlist be?\n\nKnown playlists: ")
                    for knownPlaylists in YouTubeAPI.getMergePlaylists():
                        print(knownPlaylists)
                    inputNewTitle = ""
                    while inputNewTitle == "":
                        inputNewTitle = input("\nTitle: ")
                    i["name"] = inputNewTitle
                noTitleCount += 1
            if i["name"] != "":
                if ":" in i["name"]:
                    i["name"] = i["name"].replace(":", ";")
                if "|" in i["name"]:
                    i["name"] = i["name"].replace("|", "-")
                if "//" in i["name"]:
                    i["name"] = i["name"].replace("//", "-")
                if "*" in i["name"]:
                    i["name"] = i["name"].replace("*", "^")
                currentFile.write(i["name"] + "\n")
                for i1 in i["tracks"]:
                    if i1["track"] != None and i1["track"]["name"] != "":
                        currentFile.write(i1["track"]["name"] + " - " + i1["track"]["artists"][0]["name"] + "\n")
                currentFile.write("<playlistEnd><\\playlistEnd>\n")
        info("Updated: spotifyCache.dmp")
        currentFile.close
        remove(scriptPath + "\\spotifyCache.json")

    def quary():
        scriptPath = path.split(__file__)[0]
        playlists = {}
        cacheFiles = ["spotifyCache.dmp", "osuCache.dmp", "Export.dmp"]
        for cacheFile in cacheFiles:
            if path.exists(scriptPath + "\\" + cacheFile):
                cacheFileData = open(scriptPath + "\\" + cacheFile, "r", encoding="UTF-8")
                titleCheck = True
                for line in cacheFileData.read().split("\n"):
                    if line != "":
                        if line == "<playlistEnd><\playlistEnd>":
                            titleCheck = True
                        elif titleCheck:
                            title = line
                            titleCheck = False
                        else:
                            try:
                                playlists[title].append(line)
                            except KeyError:
                                playlists[title] = [line]
                cacheFileData.close
        return playlists

    def logToFile(log, file: str = "log.dmp"):
        scriptPath = path.split(__file__)[0]
        if "\\" in file:
            subFolder, fileTmp = file.split("\\")
            if not path.exists(scriptPath + "\\" + subFolder):
                mkdir(scriptPath + "\\" + subFolder)
        logFile = open(scriptPath + "\\" + file, "a", encoding="UTF-8")
        logFile.write(log)
        logFile.close
        if file == "log.dmp":
            info(log)


if __name__ == "__main__":
    scriptPath = path.split(__file__)[0]
    parser = ArgumentParser(description="Migrate your Spotify playlists and/ or Osu! collection to YTMusic.")
    parser.add_argument("--token", metavar="OAUTH_TOKEN", help="Use a Spotify OAuth token (requires the `playlist-read-private` permission)")
    parser.add_argument("--cache", default="liked,playlists,osu", help="Cache liked, playlists and/ or osu collections (default:liked,playlists,osu)")
    parser.add_argument("--maxLenght", default=450, type=int, help="Maximal lenght of songs in seconds. (Default: 450)")
    parser.add_argument("--skip", default=0, type=int, help="Skip the first X playlists.")
    parser.add_argument("-auto", action="store_true", help="Skips over all user interaction (This can couse some playlists to not get migrated).")
    parser.add_argument("--purgePlaylists",
                        default="no",
                        choices=["no", "purge", "purgeLiked", "remove"],
                        help="Remove playlist that have been generated by this script or remove all songs from know merge playlists (purgeLiked trys to remove ratings form liked songs).")
    parser.add_argument("-storeToTxt", action="store_true", help="Stores songs of currently known merge playlists to txt files.")
    parser.add_argument("-setup", action="store_true", help="Start script in setup mode (See README.md).")
    parser.add_argument("-test", action="store_true", help="Test the script, will not create, append or like songs (Just log output)")
    args = parser.parse_args()
    if args.setup:
        scriptPath = path.split(__file__)[0]
        YTMusic.setup(filepath=scriptPath + "\\headers_auth.json")
        exit()
    ytmusic = YouTubeAPI.setupAPI()
    if args.purgePlaylists == "purge" or args.purgePlaylists == "purgeLiked":
        YouTubeAPI.purgePlaylists()
    elif args.purgePlaylists == "remove":
        YouTubeAPI.removePlaylists()
    elif args.storeToTxt:
        YouTubeAPI.exportToDmp()
    if "osu" in args.migrate:
        cacheHandler.updateOsu()
    if "liked" in args.migrate or "playlists" in args.migrate:
        cacheHandler.updateSpotify()
    YouTubeAPI.migrateDB(cacheHandler.quary())
