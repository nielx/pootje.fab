############
# Imports the catkeys of a new language into the system 
#
# TODO: remove obsolete catalogs
# TODO: run manage.py update_stores
# TODO: run manage.py update_from_templates
# TODO: run manage.py refresh_stats
#
# Note that this script is kept for legacy purposes: all the catkeys are
# already in the current installation of Pootle
#
############

# The location of the en.catkeys
CATALOGS_DIR = "/home/nielx/haiku-repository/data/catalogs"

# The output directory
OUTPUT_DIR = "/srv/pootle/catalogs/haiku"

# The language code (without the catkeys extension)
LANG = 'uk'

############
# Script
############

import os
import shutil

# copy all the catkeys for this language

count = 0
for root, dirs, files in os.walk(CATALOGS_DIR):
    if LANG + '.catkeys' in files:
        stripped_path = os.path.relpath(os.path.join(root, LANG + ".catkeys"), CATALOGS_DIR)
        dirname = os.path.split(stripped_path)[0]
        if not os.path.isdir(os.path.join(OUTPUT_DIR, dirname)):
            print("WARNING: copying a catkeys file to non-existent target directory. Is it obsolete?")
            print(stripped_path)
            os.makedirs(os.path.join(OUTPUT_DIR, dirname))
        shutil.copyfile(os.path.join(CATALOGS_DIR, stripped_path), os.path.join(OUTPUT_DIR, stripped_path))
        count += 1

print("INFO: copied %i files" % (count,))

