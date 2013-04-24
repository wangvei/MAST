from MAST.utility.picklemanager import PickleManager
from MAST.parsers.recipeparsers import RecipeParser
from MAST.recipe.recipesetup import RecipeSetup
from MAST.recipe.recipe_plan import RecipePlan
import sys
import subprocess
import os
import copy

def mastclear():
    os.system('rm -rf mgal_perfect_opt*')
#    os.system('rm mast.pickle')

def myrun(cmd):
    p = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
    return p

# this script location /home/hwkim/MAST4pymatgen/test/dagtest
print "=============================================================="
print "Let me assume that this script is run in that script location "
print "Right now I do not know how to set the directory for output   " 
print "=============================================================="

argv=[]
mastrootdir = os.environ['SCRIPTPATH']
print 'mast root directory : '+mastrootdir
binpath = os.path.join(mastrootdir,'bin/mast')
bindir= os.path.join(mastrootdir,'bin')
print 'bindir : '+bindir
print 'binpath : '+binpath
inputfile = os.path.join(mastrootdir,'test/full_workflow_test/test.inp')

print 'input directory : ' + inputfile
argv.append('-i')
argv.append(inputfile)
sys.path.append(bindir)

subprocess.call([sys.executable, binpath, argv[0],argv[1]])

pm = PickleManager()
mastobj = pm.load_variable('mast.pickle')
depdict = mastobj.dependency_dict
ingredients = mastobj.ingredients

njobs = len(ingredients)

from MAST.DAG.dagscheduler import DAGScheduler
from MAST.DAG.dagscheduler import JobEntry
from MAST.DAG.dagscheduler import DAGParser
from MAST.DAG.dagscheduler import SessionEntry
from MAST.DAG.dagscheduler import JobEntry
from MAST.DAG.dagscheduler import JobTable
from MAST.DAG.dagscheduler import SessionTable
from MAST.DAG.dagscheduler import set2str
from MAST.DAG.dagscheduler import JOB
import time
# seession id
# Basic operation in DAGScheduler
# Default running mode 'noqsub' for machines which have no qsub
print 'step 1: create DAGScheduler object'
scheduler = DAGScheduler()

print 'step 2: add jobs'
scheduler.addjobs(ingredients_dict=ingredients, dependency_dict = depdict)
print 'start scheduling'
"""
scheduler.run()
scheduler.show_session_table()

os.system('ls')
print '\nclear previous result\n'
mastclear()
os.system('ls')

print '\nrestart scheduler in a different mode'
# new sesssion with qsub and 'serial' mode
print 'load data again'
mastobj = pm.load_variable('mast.pickle')
depdict = mastobj.dependency_dict
ingredients = mastobj.ingredients

print 'step 2: add jobs'
scheduler.addjobs(ingredients_dict=ingredients, dependency_dict = depdict)
"""
scheduler.set_mode('serial')

# This is the inside of scheduler.run()

while scheduler.has_incomplete_session():

    print 'step 3: run jobs'
    scheduler.run_jobs()
    print 'step 4: update job status'
    scheduler.update_job_status()
    time.sleep(5)


scheduler.show_session_table()
os.system('rm mast.pickle') 
    