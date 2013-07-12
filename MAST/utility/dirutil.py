import os
import sys
import fnmatch
from MAST.utility import MASTError
from MAST.utility.metadata import Metadata

def walkdirs(existdir, mindepth=1, maxdepth=5, matchme=""):
    """Walk through directory and return list of subdirectories."""
    if not(os.path.exists(existdir)):
        raise MASTError("utility","No directory at " +existdir)
#   walk and make main list
    walkme=""
    walkentry=""
    walkme = os.walk(existdir)
    if walkme == ():
        raise MASTError("utility walkdirs","No folders found in " + existdir)
    bigdirlist=[]
    for walkentry in walkme:
        bigdirlist.append(walkentry[0])
#   sort list and pare down according to min/max depth
    numsep=0
    minnumsep=0
    maxnumsep=0
    numsep = existdir.count('/') # find base number of forward slashes
    minnumsep = numsep + mindepth
    maxnumsep = numsep + maxdepth
    onedir=""
    onenumsep=0
    smalldirlist=[]
    for onedir in bigdirlist:
        onenumsep = onedir.count('/')
        if (onenumsep >= minnumsep) and (onenumsep <= maxnumsep):
            smalldirlist.append(onedir)
    smalldirlist.sort()
    if not matchme == "":
        matchdirlist=[]
        for mydir in smalldirlist:
            if fnmatch.fnmatch(mydir, matchme):
                matchdirlist.append(mydir)
        return matchdirlist
    else:
        return smalldirlist

def walkfiles(existdir, mindepth=1, maxdepth=5, matchme=""):
    """Walk through directory and subdirectories and return list of files.
        Args:
            existdir <str>: directory under which to search.
            mindepth <int>: minimum depth of folders to search;
                            default 1 = within that directory
            maxdepth <int>: maximum depth of folders to search; default 5
            matchme <str>: string to match; every file ending in matchme
                            will be found, since a * is required at the front
                            to match the full paths.
    """
    if not(os.path.exists(existdir)):
        raise MASTError("utility","No directory at " +existdir)
#   walk and make main list
    walkme=""
    walkentry=""
    walkme = os.walk(existdir)
    if walkme == ():
        raise MASTError("utility walkfiles","No folders found in " + existdir)
    filetree=""
    diritem=""
    fileitem=""
    fullfile=""
    filelist=[]
    filetree = os.walk(existdir)
    for diritem in filetree:
        for fileitem in diritem[2]:
            fullfile = diritem[0] + '/' + fileitem
            filelist.append(fullfile)
    #for fullfile in filelist:
    #    print fullfile
#   #   sort and pare file list
    paredfilelist=[]
    numsep=0
    minnumsep=0
    maxnumsep=0
    numsep = existdir.count('/') # find base number of forward slashes
    minnumsep = numsep + mindepth
    maxnumsep = numsep + maxdepth
    onefile=""
    onenumsep=0
    for onefile in filelist:
        onenumsep = onefile.count('/')
        if (onenumsep >= minnumsep) and (onenumsep <= maxnumsep):
            paredfilelist.append(onefile)
    paredfilelist.sort()
    if not matchme == "":
        matchfilelist=[]
        if not matchme[0] == "*":
            matchme="*"+matchme
        for myfile in paredfilelist:
            if fnmatch.fnmatch(myfile, matchme):
                matchfilelist.append(myfile)
        return matchfilelist
    else:
        return paredfilelist

def get_mast_install_path():
    getpath = os.getenv('MAST_INSTALL_PATH')
    if getpath == None:
        raise MASTError("utility dirutil","No path set in environment variable MAST_INSTALL_PATH")
    return getpath
def get_mast_scratch_path():
    getpath = os.getenv('MAST_SCRATCH')
    if getpath == None:
        raise MASTError("utility dirutil","No path set in environment variable MAST_SCRATCH")
    return getpath

def get_mast_archive_path():
    getpath = os.getenv('MAST_ARCHIVE')
    if getpath == None:
        raise MASTError("utility dirutil","No path set in environment variable MAST_ARCHIVE")
    return getpath

def directory_is_locked(dirname):
    if os.path.isfile(dirname + "/mast.write_files.lock"):
        return True
    else:
        return False

def lock_directory(dirname, waitmax=1000):
    """Lock a directory using a lockfile.
        Args:
            dirname <str>: Directory name
            waitmax <int>: maximum number of 5-second waits
    """
    import time
    if directory_is_locked(dirname):
        wait_to_write(dirname, waitmax)
    lockfile = open(dirname + "/mast.write_files.lock", 'wb')
    lockfile.writelines(time.ctime())
    lockfile.close()

def unlock_directory(dirname):
    try:
        os.remove(dirname + "/mast.write_files.lock")
    except OSError:
        raise MASTError("utility unlock_directory",
            "Tried to unlock directory %s which was not locked." % dirname)


def wait_to_write(dirname, waitmax=1000):
    """Wait to write to directory.
        Args:
            dirname <str>: Directory name
            waitmax <int>: maximum number of 5-second waits
    """
    if waitmax < 1:
        waitmax = 1
    import time
    waitcount = 1
    while directory_is_locked(dirname) and (waitcount < waitmax):
        time.sleep(5)
        waitcount = waitcount + 1
    if directory_is_locked(dirname):
        raise MASTError("utility wait_to_write", 
            "Timed out waiting to obtain lock on directory %s" % dirname)
def search_for_metadata_file(metastring="",dirname="", metafilename="metadata.txt", verbose=1):
    """Match a metadata file based on input.
        Args:
            metastring <str>: equals-sign-separated metatag=value pairs with
                                commas separating the meta sections.
                Example: "ingredtype=phonon, neblabel=vac1-vac2, charge=0"
            dirname <str>: directory name to start. Default "" goes to ARCHIVE.
            metafilename <str>: metadata file name. Default "metadata.txt"
            verbose <int>: 1 for verbose messages, 0 otherwise
        Returns:
            dlist <list of str>: list of directories containing matching
                                    metadata files.
    """
    if dirname=="":
        dirname = get_mast_archive_path()
    allmetas = walkfiles(dirname, 1, 5, metafilename)
    if len(allmetas) == 0:
        raise MASTError("utility dirutil, search_for_metadata_file", "No matching metafiles found in %s for tags %s." % (dirname, metastring))
    metaparse=dict()
    metasplit = metastring.split(",")
    for metaitem in metasplit:
        onesplit=metaitem.strip().split("=")
        metaparse[onesplit[0].strip()]=onesplit[1].strip()
    metamatch=list()
    mustmatch=len(metaparse.keys())
    for mtry in allmetas:
        mokay=0
        mymeta = Metadata(metafile=mtry)
        for metatag,metaval in metaparse.iteritems():
            searchresult = mymeta.search_data(metatag)
            if searchresult[1] == metaval:
                mokay=mokay+1
            else:
                if verbose == 1:
                    print metatag, searchresult
        if mokay == mustmatch:
            metamatch.append(mtry)
    if verbose==1:
        print allmetas
        print metaparse
        print metamatch
    return metamatch



                
