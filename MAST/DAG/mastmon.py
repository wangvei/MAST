import os
from MAST.utility.picklemanager import PickleManager
from MAST.DAG.dagscheduler import DAGScheduler
from MAST.utility import MASTError
from MAST.utility import dirutil
import time
from MAST.DAG.dagutil import *
abspath = os.path.abspath


class MASTmon(object):
    """MASTmon is a daemon to run dagscheduler class.
        This finds newly submitted session (recipe) and manage them. \n
        Also completed session is moved in archive directory by MASTmon.
        For consistency, users may touch sesssions in the archive directory."""
    
    def __init__(self):
        self.registered_dir = set()

        self.home = os.path.expandvars(os.environ['MAST_SCRATCH'])
        self._ARCHIVE = os.path.expandvars(os.environ['MAST_ARCHIVE'])

        self.pm = PickleManager()
        self.pn_mastmon = os.path.join(self.home,'mastmon_info.pickle')
        self.scheduler = DAGScheduler()
        self.version = 0.1
        
        try:
            if not os.path.exists(self.home):
                os.makedirs(self.home)
            if not os.path.exists(self._ARCHIVE):
                os.makedirs(self._ARCHIVE)
        except:
            raise MASTError(self.__class__.__name__,
                    "Error making directory for MASTmon and completed sessions")

    def add_sessions(self, new_session_dirs):
        """recipe_dirs is a set of sessions in MASTmon home directory"""
        for session_dir in  new_session_dirs:
            #print 'session_dir =', session_dir
            if not os.path.exists(session_dir):
                raise MASTError("mastmon, add_sessions", "No session_dir at %s" % session_dir)
            os.chdir(session_dir)
            self.move_extra_files(session_dir)
            if not os.path.isfile('mast.pickle'):
                raise MASTError("mastmon, add_sessions", "No pickle file at %s/%s" % (session_dir, 'mast.pickle'))
            mastobj = self.pm.load_variable('mast.pickle')	
            depdict = mastobj.dependency_dict
            ingredients = mastobj.ingredients

            if self.scheduler is None:
                print 'step 1: create DAGScheduler object'
                self.scheduler = DAGScheduler()
            
            try: 
                self.scheduler.addjobs(ingredients_dict=ingredients, dependency_dict=depdict, sname=session_dir)    
            except:
                raise MASTError(self.__class__.__name__,
                    "Error adding jobs to scheduler.")
                
            os.chdir(self.home)
                
        self.registered_dir = self.registered_dir.union(new_session_dirs)

    def _save(self):
        """Save current stauts of MASTmon such as registered_dir and scheduler"""
        var_dict = {}
        var_dict['registered_dir'] = self.registered_dir
        var_dict['scheduler'] = self.scheduler
        var_dict['version']  = self.version
        self.pm.save(var_dict,filename=self.pn_mastmon)
        
    def _load(self):
        """Load MASTmon's information pickle file"""

        if os.path.isfile(self.pn_mastmon):
            var_dict = self.pm.load_variable(self.pn_mastmon)
            if 'version' in var_dict and var_dict['version'] != self.version:
                errorstr = "Error: mastmon_info.pickle is version %.2f while mastmon version is %.2f" % (var_dict['version'],self.version)
                raise MASTError(self.__class__.__name__, errorstr)

            if 'registered_dir' in var_dict:
                self.registered_dir = var_dict['registered_dir']
                
            if 'scheduler' in var_dict:
                self.scheduler = var_dict['scheduler']
        
    def run(self, niter=None, verbose=0, stopcond=None, interval=None):
        """Run Mastmon. First of all, this makes MASTmon go to mastmon home load dagscheduler pickle.
            In addition, there are couple of options to run mastmon. \n
            ex) mastmon.run()  # run MASTmon forever as a real daemon. By default interval is 10 sec. \n
            ex) mastmon.run(interval=30) # run MASTmon forever as a real daemon. By default interval is 30 sec. \n
            ex) mastmon.run(niter=1) # run MASTmon one iteration for crontab user. By default interval is 10 sec. \n
            ex) mastmon.run(niter=20,stopcond='NOSESSION') # run MASTmon for 20 iterations. \n
            And stop it all sessions are done.
        """
        # move to mastmon home
        curdir = os.getcwd()
        try:
            os.chdir(self.home)    
        except:
            os.chdir(curdir)
            errorstr = "Error: Failed to move to MASTmon home %s" % self.home
            raise MASTError(self.__class__.__name__, errorstr)
        
        dirutil.lock_directory(self.home, 1) # Wait 5 seconds

        if verbose == 1:
            print "MAST is in: ", os.getcwd()
        if interval is None:
            interval = SCHEDULING_INTERVAL
            
        #load dagscheduler pickle
        self._load()
        iter = 0;
        while True:
            if niter is not None and iter >= niter:
                break
            
            iter = iter + 1
            # get directories from mast home
            session_dirs = os.walk('.').next()[1]
            if verbose == 1:
                print "Session dirs: ", session_dirs

            # remove 'archive' directory from the list of session directories
            if self._ARCHIVE in session_dirs:
                session_dirs.remove(self._ARCHIVE)

            else:
                # if masthome doesn't have 'archive', then make it
                #os.system('mkdir %s' % os.path.join(abspath(self.home),self._ARCHIVE))
                if not os.path.exists(self._ARCHIVE):
                    os.makedirs(self._ARCHIVE)

            new_session_dirs = set(session_dirs) - self.registered_dir
            if verbose == 1:
                print "new session dirs: ",new_session_dirs

            # add new sessions
            self.add_sessions(new_session_dirs)

            # run it for n iterations or until all sessions are complete
            csnames = self.scheduler.run(niter=1, verbose=verbose)
            self.scheduler.show_session_table()
            #remove complete sessions

            self.registered_dir = self.registered_dir - csnames

            # save scheduler object
            self._save()

            if stopcond is not None:
                if stopcond.upper() == 'NOSESSION' and len(self.registered_dir) == 0:
                    break
                
            #time.sleep(interval) #TTM remove this sleep
                          
        # move back to original directory
        dirutil.unlock_directory(self.home) #unlock directory
        os.chdir(curdir)
            
                         
    def move_extra_files(self, recipedir):
        """Move extra files like input.py, output, and personalized recipe
            into the recipe directory.
            Args:
                recipedir <str>: Recipe directory
        """
        mypm = PickleManager(os.path.join(self.home, recipedir, 'input_options.pickle'))
        myinputoptions = mypm.load_variable()
        workdir = myinputoptions.get_item("mast","working_directory")
        inpstem = myinputoptions.get_item("mast","input_stem")
        inpstembase = os.path.basename(inpstem)
                                     
        listdir = os.listdir(self.home)
        listdir.sort()
        for mystr in listdir:
            if inpstembase in mystr:
                os.rename(os.path.join(self.home, mystr), 
                    os.path.join(workdir, mystr))
            else:
                pass
                                     
        return


