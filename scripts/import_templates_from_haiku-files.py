import hashlib
import os.path
import StringIO
import sys
import subprocess
import urllib2
import zipfile

CATKEYS_ARCHIVE_LOCATION = "https://i18n.haiku-os.org/catkeys.zip"
CATKEYS_MD5_LOCATION = "https://i18n.haiku-os.org/catkeys.zip.md5"

import argparse

parser = argparse.ArgumentParser(description='Import the newest catalogs from Haiku files and copy to Pootle')
parser.add_argument('pootle_catalogs_dir', metavar='output_dir', type=str,
                    help='the location of Pootle\'s catalogs dir for Haiku')
parser.add_argument('--pot2po', metavar='path_to_pot2po', type=str, default='pot2po',
                    help='the path to the pot2po tool')
args = parser.parse_args()


####
# Utility functions
####

# utility function to copy a catkeys file
def strip_and_save(path, input_data):
    absolute_path = os.path.join(args.pootle_catalogs_dir, path)
    if not os.path.exists(os.path.split(absolute_path)[0]):
        os.makedirs(os.path.split(absolute_path)[0])

    f = open(absolute_path, "w")
    lines = input_data.readlines()

    f.write(lines[0])
    # skip the first line
    for line in lines[1:]:
        f.write(line.rsplit('\t', 1)[0] + '\n')

    f.close()


# utility function to check whether the file on disk matches a template. Returns true if there is a match
def compare_template_to_disk(path, input_data):
    absolute_path = os.path.join(args.pootle_catalogs_dir, path)
    if not os.path.exists(os.path.split(absolute_path)[0]):
        return False
    f = open(absolute_path, "r")
    current_fingerprint = f.readline().split('\t')[3]
    new_fingerprint = input_data.readline().split('\t')[3]
    input_data.seek(0)  # reset to beginning of file
    return current_fingerprint == new_fingerprint


####
# Procedure
####

if __name__ == "__main__":
    # Get the archive with the catkeys
    try:
        archive = urllib2.urlopen(CATKEYS_ARCHIVE_LOCATION)
    except:
        sys.stderr.write("There was an error downloading the catkeys from %s\n" %
                         (CATKEYS_ARCHIVE_LOCATION,))
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

    # Rewind to the beginning of the file
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

    # Compare list of templates with data on disk by comparing fingerprints. If the fingerprint changed, write the
    # updated file to disk
    updated_list = []
    for template in template_list:
        data = StringIO.StringIO(zipfile.read(template))
        if not compare_template_to_disk(template, data):
            strip_and_save(template, data)
            updated_list.append(template)
            print("Updated template %s" % template)

    # Now instruct merging with the translated files
    commands = []
    for template in updated_list:
        base_path = os.path.join(args.pootle_catalogs_dir, os.path.dirname(template))
        entries = os.listdir(base_path)
        for entry in entries:
            if not "catkeys" in entry or entry == "en.catkeys":
                continue
            # merge file
            print("Merging %s" % os.path.join(base_path, entry))
            subprocess.check_call([args.pot2po, "-i", os.path.join(base_path, "en.catkeys"),
                                   "-t", os.path.join(base_path, entry),
                                   "-o", os.path.join(base_path, entry)])

