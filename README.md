# Sheet-music-reader-GTK
Sheet music reader and organiser on GTK framework

I rewrote the code I had because I couldn't get the correct
packages installed on my PostmarketOs device.
This version is tested and most features work, like persistent zoom level and scroll per page, annotation scaling, dragging and remove.

Playlist is added. You can select a base folder where you store your music, which is stored persistently.
In this folder you make a folder for each orchestra where you put all your pdfs, and a separate folder named "Concert" which will be used for managing concert order.

Every time you open the app you can select which orchestra you need the music for.

In the Concert folder you place a .txt file where you store the order of the titles separated by a comma. 
Like: ```Piece, test, Arban,.... ```
This order will be kept, opening pages with "next" or "back" when the txt file is present.
If no txt is in the folder this will be ignored and just one pdf(selected pdf) will open.


Annotations work partially, but are not placed accurately when pdf is rotated.
I added a drag button to drag annotations as a partial fix.

If someone can help with this, please do so because I am not a programmer.
