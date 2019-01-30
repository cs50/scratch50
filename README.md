Scratch50
=========

Installation:
-------------

    pip install requests

Usage: 
------

    python scratch50.py -d https://scratch.mit.edu/projects/26329122/
    python scratch50.py -o 26329122.sb2

Output:

JSON containing information on all sprites and their scripts in the project file.

Note:
####

As of Scratch 3, the API used to download projects no longer applies for sb3 files;
instead, you must download the .sb3 manually and then run the `-o` command on the
downloaded file.