# YTMusic Migrator

Imports playlist, liked songs from Sporify and collections from Osu and caches this data.

This cached data gets exported to new YTMusic playlists or adds songs to already existing playlists.

_Note: I'm not an developer by profession and the code is far from best practice, this is just something I use personaly that I think might be usefull for someone else, if you see any improvements I'm open for suggestions._

## Note

API connections are not made by myself, I've only modefied these for my specific needs.

* YouTube Music Export: <https://github.com/sigma67/ytmusicapi>
  * Exports data to Youtube Music.
* Osu Import: <https://github.com/Piotrekol/CollectionManager>
  * Coverts the hashes out the collection.db file to readable data.
  * Makes it easy to modify collections.
* Spotify Import: <https://github.com/caseychu/spotify-backup>
  * Imports playlists and liked songs from Spotify

## Requirements

* Python 3.10 or greater (Older version not tested).
* Python Modules ytmusicapi.
* Windows 10/ 11.
* Microsoft Notepad (Required for Osu).
* Collection Manager (Required for Osu).

## Set up

* Set up headers_auth.json (Docs: <https://ytmusicapi.readthedocs.io/en/latest/reference.html#library>)
  * Go to <https://music.youtube.com/>
  * Open the network debuging tool of your browser
  * Look for the first item with:
    * Status: "200"
    * Method: "Post"
    * Domain: "music.youtube.com"
    * File: Start with "log_event?alt=json&key="
  * Right click this item click Copy Request Headers
  * Run the script with -setup argument
    * `py YTMusicMigrator.py -setup`
  * Paste the Request Headers in the terminal
  * Press enter, then ctrl-z and enter again
  * Note: This token is valid for about 1-2 years or until you sign out from the browser
* Spotify authentication will be set up by the script based on the logged on session in the browser (If not signed in you will need to sign in again or provide an token)
* Osu collections will be imported and the script will guide you trough this process (Read the output!)
* If you want to merge playlist you need to edit the file Merge.txt
  * Open the file Merge.txt
  * The file is formated with \<metaData> and \<\metaData>
    * Everthing in between is handled as data from the YTMusic playlist that will be the destination
    * The options are:
      * Title=ThisIsATitle -> Mainly so you can reqonize wich playlist this is.
      * PlaylistID=PLi9drqWffJ9FWBo7ZVOiaVy0UQQEm4IbP -> The ID of the playlist (Set to Like to like the songs instead of adding to a playlist).
      * Mode=Nightcore -> This will be appended when searching for songs and requires songs to have this in the title or artist name (Exprimental and not required) alternative supported modes:
        * Safe -> Playlist will always be uneffacted by any purge actions.
        * Export -> Export playlists to txt, to be used in combination with the parameter -storeToTxt
    * Everything after \<\metaData> are Spotify or Osu collections playlist names that needs to be exported to this YTMusic playlist (Until the next \<metaData>).
    * See the file itself for an example.

## Order of migration

1. Spotify liked songs (Old to new)
2. Spotify playlists (Old to new)
    * Order of playlists is mainly fixed from the playlist with the most reasond activity to the oldest.
3. Osu Database (As given with the import)
    * If the same name is given as a playlist from spotify then this will be migrated after the same Spotify playlist.
4. Export file (As given with the import)
    * If the same name is given as a playlist from Spotify or Osu then this will be migrated after the same Spotify and/ or Osu playlist.
