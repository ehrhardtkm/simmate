# -*- coding: utf-8 -*-

error_list = []

import os
import numpy as np
from numpy import exp
from random import random
from simmate.toolkit.transformations import rmc as transform_mod
from simmate.toolkit.validators import structure as validator_mod
from simmate.apps.epdf_rmc.slab import RdfSlab
from simmate.apps.epdf_rmc.interpolator import CrossSection
# from simmate.apps.epdf_rmc.hrmc import Lammps_HRMC
import lammps
import multiprocessing
from multiprocessing.shared_memory import SharedMemory
import copy
from itertools import combinations
import pickle

from pymatgen.io.lammps.data import LammpsData
import multiprocessing
from pymatgen.core import Structure
import lammps
from lammps import LAMMPS_INT, LMP_STYLE_GLOBAL
from lammps import PyLammps


class Lammps_HRMC():
    def __init__(self, lmp_file, task_id):
        self.lmp = lammps.lammps(cmdargs=["-log", "none", "-screen", "none",  "-nocite"])
        self.lmp_file = lmp_file
        self.task_id = task_id


    def lammps_file(self, structure):
        lammps = LammpsData.from_structure(structure)
        lammps.set_charge_atom_type({'Al':1.4175, 'O':-0.945})
        #need a lock here
        filename = f'{self.task_id}.lmp'
        lammps.write_file(filename)
         
    def simple_lmp(self, structure):
        self.lammps_file(structure)
    
        for line in self.lmp_file:
            if line.startswith('read_data'):            
                self.lmp.command(f'read_data {self.task_id}.lmp')
            else:
                self.lmp.command(line)
        '''
        alternative is to overwrite the in.lmp copy somewhere and then read that in with lmp.file()
        '''
    
    
        # lmp = lammps.lammps(cmdargs=["-log", "none", "-screen", "none",  "-nocite"])
        # lmp.file('in.lmp')
        # lmp.command("variable e equal pe")
        self.lmp.close()
        return
    
    
    def lammps_energy(self, structure):
        """
        #Create lammps file
        self.lammps_file(structure)
        
        # Initialize LAMMPS instance
        # lmp = lammps.lammps(cmdargs=["-log", "none", "-screen", "none",  "-nocite"])
        lmp = PyLammps(cmdargs=["-log", "none", "-screen", "none",  "-nocite"])
        # lmp = lammps.lammps()
        
        # # lines = open('in.lmp','r').readlines()
        # # for line in lines: lmp.command(line)
        # lmp.file('in.lmp')
        
        
        """
        self.lammps_file(structure)
        for line in self.lmp_file:
            if line.startswith('read_data'):            
                self.lmp.command(f'read_data {self.task_id}.lmp')
            else:
                self.lmp.command(line)
        
        self.lmp.command("variable e equal pe")
        
        # run 0 to get energy of perfect lattice
        # emin = minimum energy
        
        self.lmp.command("run 0")
        
        #natoms = lmp.extract_global("natoms")
        #energy = lmp.extract_compute("thermo_pe",LMP_STYLE_GLOBAL,LAMMPS_INT) / natoms
        energy = self.lmp.extract_compute("thermo_pe",LMP_STYLE_GLOBAL,LAMMPS_INT)
        # energy = energy / (6.23 * 10**23) * (2.611 * 10 **22) * 600
        
        pe = round(energy, 5) 

        # Clean up
        self.lmp.close() 
        return pe


class RMC():
      
    def __init__(self,experimental_G_csv, sigma, q_scatter, q_temp, init_temp):
        self.experimental_G_csv = experimental_G_csv
        self.batched_error_constant = sigma
        self.batched_temp = init_temp
        self.current_error = float()
        self.current_energy = float()
        self.q_temp = q_temp
        self.q_scatter = q_scatter
    
    def apply_oxi_state(self, valences, struct):
        # BV = BVAnalyzer()
        # valences = BV.get_valences(self)
        for i in range(len(struct.sites)):
            struct.sites[i].oxi_state = valences[i]
        return
    
    
    #generate and check function to parallelize
    def make_candidate_structure(self, current_structure, validator_objects, transformer, lmp_input, task_id):
        new_structure = transformer.apply_transformation(current_structure)
        new_structure.xyz_df = new_structure.xyz()
    
        is_valid = True  # true until proven otherwise
        for validator in validator_objects:
            if not validator.check_structure(new_structure):
                is_valid = False
                break  # one failure is enough to stop and reject the structure
        if not is_valid:
            new_structure = False
        else:
            #  do pdf error check
            neighborlist = new_structure.get_all_neighbors(r=10.0)
            keep_new, new_error = self.choose_acceptance("single", new_structure, neighborlist,self.batched_error_constant, self.batched_temp, lmp_input, task_id)
            if keep_new:
                pass
            else:
                new_structure = False
        return new_structure
      
    def choose_acceptance(self, version, structure, neighborlist, error_constant, temp, lmp_input, task_id):
        #HRMC
        lammps_run = Lammps_HRMC(lmp_input, task_id)
        new_energy = lammps_run.lammps_energy(structure)
        
        structure.load_experimental_from_file(self.experimental_G_csv)
        new_error,slope = structure.prdf_error(neighborlist)
        
        keep_new = True
        if new_error < self.current_error and new_energy <= self.current_energy:
            # accept new structure
            with open('acceptance_probabilities.txt', 'a') as out:
                out.write(f'{version}: {keep_new}, n/a, {new_error}, {new_energy}\n')
            pass
        else:
            # HRMC, with energy term
            probability = exp(
                (-1 * (abs(new_error - self.current_error)) / error_constant) + ((self.current_energy - new_energy) / ( (1.987204259 * 10**-3) * temp)) 
            )
            if random() < probability:
                pass
            else:
                keep_new = False
            #logging probability info for record keeping
            with open('acceptance_probabilities.txt', 'a') as out:
                out.write(f'{version}: {keep_new}, {probability}, {new_error}, {new_energy}\n')
        return keep_new, new_error
      
        # neighborlist update with custom approach. then do pdf error check. use __init__ for experimental_G_csv. Then use probability and return true or False 
    def update_neighbors(self, shm_name, size, n_idx):
        #put in the parallelized method, deserialization
        #attach to existing shared memory
        shm = SharedMemory(name=shm_name)
        structure_data = shm.buf[:size].tobytes()
        structure = pickle.loads(structure_data)
    
        n_site = structure.sites[n_idx]
        nns = structure.get_sites_in_sphere(n_site.coords, r = 10.0)
        #remove the site itself because the pymatgen method includes it
        updated_neighbors = (n_idx, [nn for nn in nns if nn.index != n_idx])
        
        shm.close()
    
        return updated_neighbors      
          
    def worker_task(self, structure, lmp_input, task_id):
        lammps_run = Lammps_HRMC(lmp_input, task_id)
        energy = lammps_run.lammps_energy(structure)
        return energy     
          
    def run_rmc(self,
        num_processes = int(),
        initial_structure="amorphous_al2o3.vasp",
        experimental_G_csv="al2o3_5nm_gr.txt",
        keV=200,
        prdf_args={"bin_size": 0.04},
        #for testing, changed error_constant from 5E-7 to 0.002
        # self.batched_error_constant=0.002,
        transformations: dict = {
            # "ASECoordinatePerturbation":{}, #simmate version of RattleMutation from ase, rattle_prob auto set to 0.3
            "AtomHop": {}, # consider adding a second, smaller step size "max_step": 0.2
        },
        validators={
        },
        lmp_filepath='in.lmp',
        
        max_steps= 100,
    ):
    
        if os.path.exists("errors.txt"):
            os.remove("errors.txt")
        if os.path.exists("XDATCAR"):
            os.remove("XDATCAR")
        if os.path.exists("acceptance_probabilities.txt"):
            os.remove("acceptance_probabilities.txt")         

        
        """
        STAGING
        """
        nsteps = 0
        
        #energy weighting staging
        final_temp = 300

        
        #batch number staging
        num_batch = num_processes
        # decay_const = 0.1
        # batch_decay = exp(- decay_const * num_batch)

        """
        INITIAL STRUCTURE AND CALCULATION SETUP
        """
        #lammps input setup
        lmp_input = []    
        with open(lmp_filepath, 'r') as file:
            for line in file:
                lmp_input.append(line)
                
                
        
        # convert to our python class
        initial_structure = RdfSlab.from_file(initial_structure)
        initial_structure.xyz_df = initial_structure.xyz()
        #create neighborlist
        initial_structure_neighborlist = initial_structure.get_all_neighbors(r=10.0)
        
        #cache/store interpolated radii
        struct_consts = CrossSection(initial_structure)
        
        valences = initial_structure.oxidation_state_list()
        self.apply_oxi_state(valences, initial_structure)
        charges = struct_consts.partial_charges()
        database_radii = struct_consts.database_ionic_radii()
        interpolated_radii = struct_consts.interpolated_ionic_radii(charges, database_radii)
        setattr(initial_structure, 'interpolated_radii', interpolated_radii)

        TCS = {}
        el_tuple = initial_structure.symbol_set
        for el in el_tuple:
            el_charge = charges[el]
            TCS[el] = struct_consts.interpolated_TCS(el, el_charge, keV)
        setattr(initial_structure, 'TCSs', TCS)
        print(TCS)

    
        # load experimental G(r)
        initial_structure.load_experimental_from_file(self.experimental_G_csv)
    
        # convert validators + transformations all to proper python class
        # below is an example loop with transformations
        transformation_objects = []
        for t_name, t_kwargs in transformations.items():
            t_class = getattr(transform_mod, t_name)
            t_obj = t_class(**t_kwargs)
            transformation_objects.append(t_obj)
            
    
        # dynamically build our validator objects
        validator_objects = []
        for v_name, v_kwargs in validators.items():
            if hasattr(validator_mod, v_name):
                v_class = getattr(validator_mod, v_name)
                v_obj = v_class(**v_kwargs)
            else:
                raise Exception(f"Unknown validator provided ({v_name})")
            validator_objects.append(v_obj)

        
        """
        INITIALIZE RMC LOOP
        """
        current_structure = copy.deepcopy(initial_structure)
        current_structure_neighborlist = initial_structure_neighborlist
        self.current_error,slope = current_structure.prdf_error(current_structure_neighborlist)
        default_id = 100
        #Start HRMC
        initial_e = self.worker_task(initial_structure, lmp_input, default_id)
        # lammps_run = Lammps_HRMC()
        # current_energy = lammps_run.lammps_energy(current_structure)
        # del lammps_run
        # lammps_run.close()
        
        self.current_energy = initial_e
        
        
        nsteps = 0
        current_e = round(self.current_error, 5)
        print(f'Step {nsteps}. Sum of residuals = {current_e}. Energy = {self.current_energy}.')
        counter = []
        moves = 0
        moves_attempted = 0
        
        """
        RUN RMC LOOP
        """
        while nsteps < max_steps:
            nsteps += 1
        
            if nsteps % 5000 == 0:
                if os.path.exists("pdfs.png"):
                    os.remove("pdfs.png") 
                # if os.path.exists("errors.png"):
                #     os.remove("errors.png") 
                current_structure.plot_pdf(current_structure_neighborlist, experimental_G_csv, slope)
                # current_structure.plot_error()
    
            # TODO apply with validation
            transformer = transformation_objects[0]  # just grab the first transformation
            
            trial_structure = copy.deepcopy(current_structure)
            
            # new_structure = self.make_candidate_structure(trial_structure, validator_objects, transformer)
            # if not new_structure:
            #     continue
            # new_structure_neighborlist = new_structure.get_all_neighbors(r=10.0)
            
            new_structure = copy.deepcopy(current_structure)
            
            with multiprocessing.Pool(processes=num_processes) as pool:
                tasks = list(range(num_batch))
                inputs = [(trial_structure, validator_objects, transformer, lmp_input, task_id) for task_id in tasks]
                results = pool.starmap(self.make_candidate_structure, inputs)
                                
            moves_attempted += num_batch       
            moved_atoms = []

            for candidate_structure in results:
                if candidate_structure:
                    # new_energy = energy
                    idx = candidate_structure.move_indices[0]
                    moved_atoms.append([idx, candidate_structure.sites[idx]])
                    
            # check distance between this atom and all other moved atoms
            for i, j in combinations(moved_atoms, 2):
                # distance = np.linalg.norm(i[2]-j[2])
                #this becomes:
                distance = np.linalg.norm(i[1].coords-j[1].coords)
                try: #only do this if min distance constraint is in use
                    min_distance = validator_objects[1].min_distances[f'{i[1].species_string}', f'{j[1].species_string}']
                    if distance < min_distance:
                        try:
                            moved_atoms.remove(i)
                        except:
                            pass
                except: 
                    pass
            if len(moved_atoms) == 0:
                continue
            
            all_changed = set()
            for c_idx, c_site in moved_atoms:
                new_structure.sites[c_idx] = c_site
            #edit neighbor list here
            new_structure_neighborlist = new_structure.get_all_neighbors(r=10.0)
            #update xyz_df
            new_structure.xyz_df = new_structure.xyz()

            # new_structure_neighborlist = current_structure_neighborlist

            #     new_neighbors = new_structure.get_sites_in_sphere(c_site.coords, r=10.0)
            #     new_neighbors = [nn for nn in new_neighbors if nn.index != c_idx]
    
            #     old_neighbors = current_structure_neighborlist[c_idx]
    
            #     """fastest approach""" 
            #     new = set()
            #     old = set()
            #     for nn in new_neighbors:
            #         new.add(int(nn.index))
            #     for nn in old_neighbors:
            #         old.add(int(nn.index))
            #     changed = new | old
            #     all_changed = all_changed | changed
            
            # #when low number of processes available
            # for n_idx in all_changed:
            #     n_site = new_structure.sites[n_idx]
            #     nns = new_structure.get_sites_in_sphere(n_site.coords, r=10.0)
            #     new_structure_neighborlist[n_idx] = [nn for nn in nns if nn.index != n_idx]
            
            # #when high number of processes available            
            # #implement parallel structure with shared_memory here
            # serial_struct = pickle.dumps(new_structure)
            # size = len(serial_struct)
            # shm_name = 'structure'
            # shm = SharedMemory(name=shm_name, create=True, size=size)
            # shm.buf[:size] = serial_struct
            
            # with multiprocessing.Pool(processes=num_processes) as pool:
            #     inputs = [(shm.name, size, n_idx) for n_idx in all_changed]
            #     results = pool.starmap(self.update_neighbors, inputs)
                
            # #Clean up every cycle
            # shm.close()
            # shm.unlink()

            # start_time = time.time()
            # for site_update in results:
            #     n_idx = site_update[0]
            #     new_structure_neighborlist[n_idx] = site_update[1]
            # duration = time.time() - start_time

            #make sure a normal structure is outputted
            # new_structure.to(fmt='POSCAR', filename='test_output.vasp')
            
            keep_new, new_error = self.choose_acceptance("batch", new_structure, new_structure_neighborlist, self.batched_error_constant, self.batched_temp, lmp_input, default_id)

            if keep_new:
                new_energy = self.worker_task(new_structure, lmp_input, default_id)
                new_energy = round(new_energy, 5)
                new_error = round(new_error, 7)
                
                print(f'Step {nsteps}. Accepted, sum of residuals = {new_error}.  Energy = {new_energy}')
                current_structure = copy.deepcopy(new_structure)                    
                current_structure_neighborlist = current_structure.get_all_neighbors(r=10.0)
                self.current_error = new_error
                self.current_energy = new_energy
                error_list.append(f'{nsteps},{new_error}')
                current_structure.to(fmt='POSCAR', filename='output.vasp')
                moves += len(moved_atoms)
                with open('errors.txt', 'a') as out:
                    out.write(f"step # = {nsteps}, error = {new_error}, moved = {len(moved_atoms)}, tot_moves = {moves}, moves attempted = {moves_attempted}, error_const = {self.batched_error_constant}\n")
                with open('error_plotting.txt', 'a') as out:
                    out.write(f'{nsteps} {new_error} {new_energy}\n')
                frame_num = len(error_list)
                current_structure.write_xdatcar(frame_num)

                
                counter.append(nsteps)
            
            #quenching scheme
            if self.batched_temp > final_temp:
                self.batched_temp = self.batched_temp * self.q_temp ** nsteps
            self.batched_error_constant = self.batched_error_constant *  self.q_scatter ** (nsteps / 2)
            #use this line to change the number in a batch. need rounding to return an integer value
            # num_batch = round(num_batch * batch_decay)
            
        output_structure = current_structure
        output_structure.to(fmt='POSCAR', filename='output.vasp')
        print(f'counter = {counter}')
        print(f'moves ={moves}')
        return output_structure
   

        
        
        
