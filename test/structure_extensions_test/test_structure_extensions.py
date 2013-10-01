import os
import time
import unittest
from unittest import SkipTest
import filecmp
from filecmp import dircmp
import MAST
from MAST.ingredients.pmgextend.structure_extensions import StructureExtensions
import shutil
import pymatgen
import numpy as np

testname ="structure_extensions_test"
#oldcontrol = os.getenv("MAST_CONTROL")
#oldrecipe = os.getenv("MAST_RECIPE_PATH")
#oldscratch = os.getenv("MAST_SCRATCH")
#print "Old directories:"
#print oldcontrol
#print oldrecipe
#print oldscratch
testdir = os.path.join(os.getenv("MAST_INSTALL_PATH"),'test',testname)


class TestSE(unittest.TestCase):
    """Test StructureExtensions
    """
    def setUp(self):
        os.chdir(testdir)

    def tearDown(self):
        pass
    def test_induce_defect_frac(self):
        perfect = pymatgen.io.vaspio.Poscar.from_file("POSCAR_perfect").structure
        compare_vac1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_vac1").structure
        compare_int1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_int1").structure
        compare_sub1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_sub1").structure
        coord_type='fractional'
        threshold=1.e-4
        vac1={'symbol':'O', 'type': 'vacancy', 'coordinates':  np.array([0.25, 0.75, 0.25])}
        int1={'symbol':'Ni', 'type': 'interstitial', 'coordinates': np.array([0.3, 0.3, 0.3])}
        sub1={'symbol':'Fe', 'type': 'substitution','coordinates':np.array([0.25, 0.25,0.75])}
        sxtend = StructureExtensions(struc_work1=perfect)
        struc_vac1 = sxtend.induce_defect(vac1, coord_type, threshold)
        struc_int1 = sxtend.induce_defect(int1, coord_type, threshold)
        struc_sub1 = sxtend.induce_defect(sub1, coord_type, threshold)
        self.assertEqual(struc_vac1,compare_vac1)
        self.assertEqual(struc_int1,compare_int1)
        self.assertEqual(struc_sub1,compare_sub1)
    
    def test_sort_structure_and_neb_lines(self):
        perfect1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_defectgroup1").structure
        compare_sorted1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_sorted1").structure
        perfect2 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_defectgroup2").structure
        compare_sorted2 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_sorted2").structure
        neblines = list()
        neblines.append(["Cr","0.3 0 0","0 0 0"])
        neblines.append(["Ni","0.6 0 0","0.3 0 0"])
        sxtend1 = StructureExtensions(struc_work1=perfect1)
        sorted1 = sxtend1.sort_structure_and_neb_lines(neblines,"00",3)
        sxtend2 = StructureExtensions(struc_work1=perfect2)
        sorted2 = sxtend2.sort_structure_and_neb_lines(neblines,"04",3)
        self.assertEqual(sorted1, compare_sorted1)
        self.assertEqual(sorted2, compare_sorted2)
    def test_interpolation(self):
        ep1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_ep1").structure
        ep2 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_ep2").structure
        compare_im1 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_im1").structure
        compare_im2 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_im2").structure
        compare_im3 = pymatgen.io.vaspio.Poscar.from_file("POSCAR_im3").structure
        sxtend = StructureExtensions(struc_work1 = ep1, struc_work2 = ep2)
        slist = sxtend.do_interpolation(3)
        self.assertEqual(slist[0],ep1)
        self.assertEqual(slist[1],compare_im1)
        self.assertEqual(slist[2],compare_im2)
        self.assertEqual(slist[3],compare_im3)
        self.assertEqual(slist[4],ep2)

        
        
