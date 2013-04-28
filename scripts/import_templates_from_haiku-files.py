import hashlib
import os.path
import StringIO
import sys
import urllib2
import zipfile

CATKEYS_ARCHIVE_LOCATION = "http://www.haiku-files.org/catkeys.zip"
CATKEYS_MD5_LOCATION     = "http://www.haiku-files.org/catkeys.zip.md5"

import argparse
parser = argparse.ArgumentParser(description='Import the newest catalogs from Haiku files and copy to Pootle')
parser.add_argument('pootle_catalogs_dir', metavar='output_dir', type=str,
                   help='the location of Pootle\'s catalogs dir for Haiku')
args = parser.parse_args()


####
# Utility functions
####

# utility function to copy a catkeys file
def strip_and_save(path, input_data):
    absolute_path = os.path.join(args['pootle_catalogs_dir'], path)
    if not os.path.exists(os.path.split(absolute_path)[0]):
        os.makedirs(os.path.split(absolute_path)[0])

    f = open(absolute_path, "w")
    lines = input_data.readlines()

    f.write(lines[0])
    # skip the first line
    for line in lines[1:]:
        f.write(line.rsplit('\t', 1)[0] + '\n')

    f.close()


####
# Procedure
####

if __name__ == "__main__":
    # Get the archive with the catkeys
    try:
        archive = urllib2.urlopen(CATKEYS_ARCHIVE_LOCATION)
    except:
        sys.stderr.write("There was an error downloading the catkeys from %s\n" % 
            (CATKEYS_ARCHIVE_LOCATION, ))
    archive = StringIO.StringIO(archive.read())

    # Check MD5
    try:
        md5_file = urllib2.urlopen(CATKEYS_MD5_LOCATION)
    except:
        sys.stderr.write("Error: cannot download the catkeys MD5 file from %s\n" %
            (CATKEYS_MD5_LOCATION,))
    
    m = hashlib.md5()
    m.update(archive.read())
    
    if m.hexdigest() not in md5_file.read():
        sys.stderr.write("Error: MD5 digest of the catkeys file does not match the md5 on the server")
        sys.exit(-1)
    
    archive.seek(0)

    try:
        zipfile = zipfile.ZipFile(archive, mode="r")
    except:
        sys.stderr.write("There was an error processing the zip file from haiku-files.org")
        sys.exit(-1)
    template_list = []
    for f in zipfile.namelist():
        if "en.catkeys" in f:
            template_list.append(f)

    for template in template_list:
        data = StringIO.StringIO(zipfile.read(template))
        strip_and_save(template, data)

