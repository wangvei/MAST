##############################################################
# This code is part of the MAterials Simulation Toolkit (MAST)
# 
# Maintainer: Tam Mayeshiba
# Last updated: 2015-02-12 by Tam Mayeshiba
##############################################################
from pymatgen.io.vaspio import *
import numpy as np
import logging
from MAST.utility.dirutil import *
from MAST.utility import MASTError
from MAST.utility import MASTFile
from MAST.utility import MASTObj
from MAST.utility import Metadata
from MAST.utility import loggerutils
from pymatgen.core.structure import Structure
from pymatgen.util.coord_utils import find_in_coord_list
from pymatgen.util.coord_utils import find_in_coord_list_pbc
from pymatgen.core.sites import PeriodicSite
from MAST.ingredients.pmgextend.structure_extensions import StructureExtensions as SE
from MAST.utility import InputOptions

class AtomIndex(MASTObj):
    """Atom Index
    """
    def __init__(self, **kwargs):
        allowed_keys = {
            'input_options': (InputOptions, None, 'Input options')
        }
        MASTObj.__init__(self, allowed_keys, **kwargs)            
        self.sdir = "structure_index_files"
        self.startSE = ""
        self.startdict = ""
        self.startdefects = ""
        self.startdefectphonons = ""
        self.startnebs = ""
        self.startnebphonons = ""
        self.scalingSEs = dict()
        self.scalingdicts = dict()
        self.scalingdefects = dict()
        self.scalingdefectphonons = dict()
        self.scalingnebs = dict()
        self.scalingnebphonons = dict()
        self.input_options = self.keywords['input_options']
        self.scaling = self.input_options.get_item('structure','scaling')
        if self.scaling == None:
            self.scaling = dict()
        self.startstr = self.input_options.get_item('structure','structure')
        self.atomcount=1
        self.allatoms = ""
        return
    
    def make_structure_index_directory(self):
        """Make structure index directory
        """
        if os.path.isdir(self.sdir):
            import time
            time.sleep(1)
        if os.path.isdir(self.sdir):
            raise MASTError(self.__class__.__name__, "Structure index directory already exists!")
        os.mkdir(self.sdir)
        return

    def write_undefected_atom_indices(self):
        """Write undefected atom indices, including scaled indices.
            Also write an undefected manifest file.
        """
        scales = self.scaling.keys()
        scales.append("")
        for scaling_label in scales:
            if scaling_label == "":
                mySE=SE(struc_work1=self.startstr.copy())
                mystruc=mySE.keywords['struc_work1']
            else:
                mySE=SE(struc_work1=self.startstr.copy(), scaling_size=self.scaling[scaling_label][0])
                mystruc=mySE.scale_structure()
            alist=list()
            manname=os.path.join(self.sdir,"manifest_undefected_%s" % scaling_label)
            for site in mystruc:
                akey=self.get_new_key()
                aname="atom_index_%s" % akey
                aname = os.path.join(self.sdir, aname)
                ameta = Metadata(metafile=aname)
                ameta.write_data("atom_index",akey)
                ameta.write_data("original_frac_coords", site.frac_coords)
                ameta.write_data("element", site.species_string)
                ameta.write_data("scaling_label", scaling_label)
                alist.append(akey)
            self.write_manifest_file(alist,manname)
        return 
    
    def get_new_key(self):
        """Get a new key.
        """
        self.atomcount = self.atomcount + 1
        return self.convert_int_to_atomidx(self.atomcount)

    def convert_int_to_atomidx(self, aint):
        """Convert an integer to an atom index.
            Args:
                aint <int>: integer
            Returns:
                atomidx <str>: atom index string
        """
        spad=16
        atomidx=hex(aint).zfill(spad)
        return atomidx
    
    def write_manifest_file(self, aidxlist, fname):
        """Make a manifest file.
            Args:
                aidxlist <list of str>: List of atom indices
                fname <str>: File name
        """
        myfile = open(fname, 'wb')
        for aidx in aidxlist:
            myfile.write("%s\n" % aidx)
        myfile.close()
        return

    def write_defected_atom_indices(self):
        """Write any additional defect atom indices and make manifests.
        """
        defect_dict=self.input_options.get_item('defects','defects')
        if defect_dict == None:
            return None
        dlabels=defect_dict.keys()
        
        scales = self.scaling.keys()
        scales.append("")
        for scaling_label in scales:
            alist=list(self.read_manifest_file("%s/manifest_undefected_%s" % (self.sdir, scaling_label)))
            if scaling_label == "":
                mySE=SE(struc_work1=self.startstr.copy())
            else:
                mySE=SE(struc_work1=self.startstr.copy(), scaling_size=self.scaling[scaling_label][0])
            for dlabel in dlabels:
                dlist = list(alist)
                manname=os.path.join(self.sdir,"manifest_defect_%s_%s" % (dlabel, scaling_label))
                dsubkeys=defect_dict[dlabel].keys()
                for dsubkey in dsubkeys:
                    if "subdefect_" in dsubkey:
                        dtype=defect_dict[dlabel][dsubkey]['type']
                        dcoords=defect_dict[dlabel][dsubkey]['coordinates']
                        delement=defect_dict[dlabel][dsubkey]['symbol']
                        if not (scaling_label == ""):
                            dcoords = mySE.get_scaled_coordinates(dcoords)
                        if dtype == "interstitial":
                            didx=self.find_orig_frac_coord_in_atom_indices(dcoords, delement, scaling_label, False, 0.001)
                            if didx == None:
                                akey=self.get_new_key()
                                aname="atom_index_%s" % akey
                                aname = os.path.join(self.sdir, aname)
                                ameta = Metadata(metafile=aname)
                                ameta.write_data("atom_index",akey)
                                ameta.write_data("original_frac_coords", dcoords)
                                ameta.write_data("element", delement)
                                ameta.write_data("scaling_label", scaling_label)
                                dlist.append(akey)
                            else:
                                dlist.append(didx)
                        elif dtype == "vacancy":
                            didx=self.find_orig_frac_coord_in_atom_indices(dcoords, delement, scaling_label, False, 0.001)
                            try:
                                dlist.remove(didx)
                            except ValueError:
                                raise MASTError(self.__class__.__name__, "For defect %s, cannot remove atom index %s from list: %s" % (dlabel, didx, dlist))
                        elif dtype in ["substitution","antisite"]:
                            didxlist=self.find_orig_frac_coord_in_atom_indices(dcoords, "", scaling_label, True, 0.001) #leave element empty; just search coords
                            for didx in didxlist:
                                dmeta = Metadata(metafile="%s/atom_index_%s" % (self.sdir, didx))
                                dmetaelem = dmeta.read_data("element")
                                if not (delement == dmetaelem):
                                    if didx in dlist:
                                        dlist.remove(didx)
                            didxsub=self.find_orig_frac_coord_in_atom_indices(dcoords, delement, scaling_label, False, 0.001) #leave element empty; just search coords
                            if didxsub == None:
                                akey=self.get_new_key()
                                aname="atom_index_%s" % akey
                                aname = os.path.join(self.sdir, aname)
                                ameta = Metadata(metafile=aname)
                                ameta.write_data("atom_index",akey)
                                ameta.write_data("original_frac_coords", dcoords)
                                ameta.write_data("element", delement) #sub element here
                                ameta.write_data("scaling_label", scaling_label)
                                dlist.append(akey)
                            else:
                                dlist.append(didxsub)
                self.write_manifest_file(dlist, manname)
        return 
    
    def read_manifest_file(self, filename):
        """Read a manifest file.
        """
        mlist=list()
        mfile = open(filename, 'rb')
        mlines = mfile.readlines()
        mfile.close()
        for mline in mlines:
            mline = mline.strip()
            mlist.append(mline)
        return mlist
    
    def find_orig_frac_coord_in_atom_indices(self, coord, element="", scaling_label="", find_multiple=False, tol=0.0001):
        """Find the atomic index of an original FRACTIONAL coordinate in the 
            structure dictionary.
            Args:
                coord <numpy array of float>: coordinate to find
                element <str>: element symbol to match
                                If blank, matches any element.
                scaling_label <str>: scaling label
                                    If blank, must match NO scaling (blank)
                find_multiple <boolean>: allow multiple matches. Default False.
                tol <float>: tolerance
            Returns:
                atomic index <hex string>: atomic index of match, 
                    if find_multiple is false
                list of atomic indices of matches, if find_multiple is true
                Returns None if no match is found
        """
        import glob
        matchstring = "%s/atom_index_*" % self.sdir
        idxnames = glob.glob(matchstring)
        rtol=tol*100
        coord_matches=list()
        elem_matches=list()
        scaling_matches=list()
        for aname in idxnames:
            ameta=Metadata(metafile=aname)
            aidx=ameta.read_data("atom_index")
            atom_ofc=ameta.read_data("original_frac_coords")
            atom_ofc_arr=np.array(atom_ofc[1:-1].split(),'float')
            if np.allclose(atom_ofc_arr,coord,rtol,tol):
                coord_matches.append(aidx)
        if element == "":
            elem_matches = list(coord_matches)
        else:
            for aidx in coord_matches:
                ameta=Metadata(metafile="%s/atom_index_%s" % (self.sdir, aidx))
                atom_elem=ameta.read_data("element")
                if (element == atom_elem):
                    elem_matches.append(aidx)
        for aidx in elem_matches:
            ameta=Metadata(metafile="%s/atom_index_%s" % (self.sdir, aidx))
            ascale=ameta.read_data("scaling_label")
            if (scaling_label == ascale):
                scaling_matches.append(aidx)
        allmatches = list(scaling_matches)
        if len(allmatches) == 0:
            return None
        if len(allmatches) > 1:
            if not find_multiple:
                raise MASTError(self.__class__.__name__,
                    "Multiple matches found for coordinate %s: %s" % (coord, allmatches))
            else:
                return allmatches
        if len(allmatches) == 1:
            if not find_multiple:
                return allmatches[0]
            else:
                return allmatches
        return None

    def write_defected_phonon_sd_manifests(self):
        """Write defected phonon structure dynamics manifests.
        """
        defect_dict=self.input_options.get_item('defects','defects')
        if defect_dict == None:
            return None
        dlabels=defect_dict.keys()
        
        scales = self.scaling.keys()
        scales.append("")
        for scaling_label in scales:
            if scaling_label == "":
                mySE=SE(struc_work1=self.startstr.copy())
            else:
                mySE=SE(struc_work1=self.startstr.copy(), scaling_size=self.scaling[scaling_label][0])
            for dlabel in dlabels:
                pdict=dict(defect_dict[dlabel]["phonon"])
                for phonon_label in pdict.keys():
                    pcoordsraw = pdict[phonon_label]['phonon_center_site']
                    pthresh = pdict[phonon_label]['threshold']
                    pcrad = pdict[phonon_label]['phonon_center_radius']
                    pcoords = np.array(pcoordsraw.split(),'float')
                    if not (scaling_label == ""):
                        pcoords = mySE.get_scaled_coordinates(pcoords)
                     
                    #pindices = self.find_orig_frac_coord_in_structure_dictionary(sdict, pcoords, pthresh+pcrad, True)
                    pindices = self.find_orig_frac_coord_in_atom_indices(pcoords,"",scaling_label,True,0.001+pcrad)
                    manname=os.path.join(self.sdir,"manifest_phonon_sd_%s_%s_%s" % (dlabel, phonon_label, scaling_label))
                    self.write_manifest_file(pindices, manname) 
        return 

    def write_neb_endpoint_manifests(self):
        """Make NEB endpoint manifests.
        """
        neb_dict=self.input_options.get_item('neb','nebs')
        if neb_dict == None:
            return None
        nlabels=neb_dict.keys()
        
        scales = self.scaling.keys()
        scales.append("")
        for scaling_label in scales:
            if scaling_label == "":
                mySE=SE(struc_work1=self.startstr.copy())
            else:
                mySE=SE(struc_work1=self.startstr.copy(), scaling_size=self.scaling[scaling_label][0])
            for nlabel in nlabels:
                def1 = nlabel.split("-")[0].strip()
                def2 = nlabel.split("-")[1].strip()
                manname1=os.path.join(self.sdir,"manifest_neb_%s_%s_%s" % (nlabel, def1, scaling_label))
                manname2=os.path.join(self.sdir,"manifest_neb_%s_%s_%s" % (nlabel, def2, scaling_label))
                mlist1=list(self.read_manifest_file("%s/manifest_defect_%s_%s" % (self.sdir, def1, scaling_label)))
                mlist2=list(self.read_manifest_file("%s/manifest_defect_%s_%s" % (self.sdir, def2, scaling_label)))
                maddtoend1=list()
                maddtoend2=list()
                nlines=list(neb_dict[nlabel]["lines"])
                for nline in nlines:
                    ncoord1 = np.array(nline[1].split(), 'float')
                    ncoord2 = np.array(nline[2].split(), 'float')
                    if not (scaling_label == ""):
                        ncoord1 = mySE.get_scaled_coordinates(ncoord1)
                        ncoord2 = mySE.get_scaled_coordinates(ncoord2)
                    nelem = nline[0]
                    nidx1 = self.find_orig_frac_coord_in_atom_indices(ncoord1, nelem, scaling_label, False, 0.001)
                    nidx2 = self.find_orig_frac_coord_in_atom_indices(ncoord2, nelem, scaling_label, False, 0.001)
                    try:
                        mlist1.remove(nidx1)
                    except ValueError:
                        raise MASTError(self.__class__.__name__, "For neb %s, cannot remove atom index %s from mlist1: %s" % (nlabel, nidx1, mlist1))
                    maddtoend1.append(nidx1) #resort matches to the bottom
                    try:
                        mlist2.remove(nidx2)
                    except ValueError:
                        raise MASTError(self.__class__.__name__, "For neb %s, cannot remove atom index %s from mlist2: %s" % (nlabel, nidx2, mlist2))
                    maddtoend2.append(nidx2)
                if not (mlist1==mlist2):
                    raise MASTError("NEB %s truncated manifests do not match: %s, %s" % (nlabel, mlist1, mlist2))
                mlist1.extend(maddtoend1)
                mlist2.extend(maddtoend2)
                self.write_manifest_file(mlist1, manname1)
                self.write_manifest_file(mlist2, manname2)
        return
    def write_neb_phonon_sd_manifests(self):
        """Make NEB phonon manifests.
        """
        neb_dict=self.input_options.get_item('neb','nebs')
        if neb_dict == None:
            return None
        nlabels=neb_dict.keys()
        
        scales = self.scaling.keys()
        scales.append("")
        for scaling_label in scales:
            if scaling_label == "":
                mySE=SE(struc_work1=self.startstr.copy())
            else:
                mySE=SE(struc_work1=self.startstr.copy(), scaling_size=self.scaling[scaling_label][0])
            for nlabel in nlabels:
                pdict = dict(neb_dict[nlabel]["phonon"])
                for phonon_label in pdict.keys():
                    pcoordsraw = pdict[phonon_label]['phonon_center_site']
                    pthresh = pdict[phonon_label]['threshold']
                    pcrad = pdict[phonon_label]['phonon_center_radius']
                    pcoords = np.array(pcoordsraw.split(),'float')
                    if not (scaling_label == ""):
                        pcoords = mySE.get_scaled_coordinates(pcoords)
                     
                    #pindices = self.find_orig_frac_coord_in_structure_dictionary(sdict, pcoords, pthresh+pcrad, True)
                    pindices = self.find_orig_frac_coord_in_atom_indices(pcoords,"",scaling_label,True,0.001+pcrad)
                    manname=os.path.join(self.sdir,"manifest_phonon_sd_%s_%s_%s" % (nlabel, phonon_label, scaling_label))
                    self.write_manifest_file(pindices, manname) 
        return



    def set_up_initial_index(self):
        """Set up the initial index (first time).
        """
        self.make_structure_index_directory()
        self.write_undefected_atom_indices()
        self.write_defected_atom_indices()
        self.write_defected_phonon_sd_manifests()
        self.write_neb_endpoint_manifests()
        self.write_neb_phonon_sd_manifests() 
        return

    def OLD_set_structure_from_inputs(self, input_options):
        """Make a pymatgen structure and update the
            structure key.
            Args:
                input_options <InputOptions>
        """
        strposfile = input_options.get_item('structure','posfile')
        if strposfile is None:
            iopscoords=input_options.get_item('structure','coordinates')
            iopslatt=input_options.get_item('structure','lattice')
            iopsatoms=input_options.get_item('structure','atom_list')
            iopsctype=input_options.get_item('structure','coord_type')
            structure = MAST2Structure(lattice=iopslatt,
                coordinates=iopscoords, atom_list=iopsatoms,
                coord_type=iopsctype)
        elif ('poscar' in strposfile.lower()):
            from pymatgen.io.vaspio import Poscar
            structure = Poscar.from_file(strposfile).structure
        elif ('cif' in strposfile.lower()):
            from pymatgen.io.cifio import CifParser
            structure = CifParser(strposfile).get_structures()[0]
        else:
            error = 'Cannot build structure from file %s' % strposfile
            raise MASTError(self.__class__.__name__, error)
        input_options.update_item('structure','structure',structure)
        if not input_options.get_item('structure','use_structure_index'):
            pass
        else:
            self.do_structure_indexing(input_options)
        return

    def add_atom_specific_keywords_to_structure_dictionary(self):
        """Add atom specific keywords using the coordinates section
        """
        return
    
    def add_element_specific_keywords_to_structure_dictionary(self):
        """Add element specific keywords using the elementmap section
        """
        return


    

    #'phonon': {'solute': {'phonon_center_site': '0.25 0.50 0.25', 'threshold': 0.1, 'phonon_center_radius': 0.5}
    
    #'mast_neb_settings': {'images': 1, 'phonon': {'movingsolvent': {'phonon_center_site': '0.375 0.5 0.375', 'threshold': 0.1, 'phonon_center_radius': 0.5}}, 'lines': [['Al', ' 0.25 0.5 0.25', ' 0.5 0.5 0.5']]}, 'mast_ppn': '1', 'ismear': '1', 'nebs': {'1nn-solute': {'images': 1, 'phonon': {'movingsolute': {'phonon_center_site': '0.375 0.500 0.375', 'threshold': 0.1, 'phonon_center_radius': 0.5}}, 'lines': [['Mg', ' 0.25 0.50 0.25', ' 0.5 0.5 0.5']]}, 'pureinit-purefin': {'images': 1, 'phonon': {'movingsolvent': {'phonon_center_site': '0.375 0.5 0.375', 'threshold': 0.1, 'phonon_center_radius': 0.5}}, 'lines': [['Al', ' 0.25 0.5 0.25', ' 0.5 0.5 0.5']]}}
