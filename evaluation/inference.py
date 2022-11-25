from typing import Tuple, Any
import numpy as np
import torch
import schnetpack as spk
from ase import io
import scipy
import scipy.linalg
from pyscf import gto

from data.utils import read_xyz_file
from phisnet_fork.utils.transform_hamiltonians import transform_hamiltonians_from_lm_to_ao
from phisnet_fork.utils.custom_data_module import CustomDataModule
from phisnet_fork.utils.phisnet import PhisNet
from phisnet_fork.train import load_model

def calculate_overlap_matrix(geometry_path: str, basis: str) -> np.ndarray:
  mol = gto.M(atom=geometry_path,
              basis=basis,
              spin=0)
  myscf = mol.RHF()
  return myscf.get_ovlp(mol)

def infer_orbitals_from_phisnet_model(model_path: str, 
                                      geometry_path: str,
                                      basis: str = 'sto_6g') -> Tuple[np.ndarray, np.ndarray]:
  use_gpu = torch.cuda.is_available()
  if use_gpu:
    device = torch.device('cuda')
  else:
    device = torch.device('cpu')

  model = torch.load(model_path, map_location=device).to(device)
  model.eval()

  geometry = read_xyz_file(geometry_path)
  R = np.array([[atom.x, atom.y, atom.z] for atom in geometry]) * 1.8897261258369282 # convert angstroms to bohr
  R = torch.stack([torch.tensor(R, dtype=torch.float32)]).to(device)
  output = model(R=R)
  F = output['full_hamiltonian'][0].detach().cpu().numpy()
    
  # sort fock matrix back
  atoms = ''
  for atom in geometry:
    atoms += atom.type
  orbital_convention = 'fulvene_minimal_basis'
  F = transform_hamiltonians_from_lm_to_ao(F, atoms=atoms, convention=orbital_convention)

  # F -> MO coeffs
  S = calculate_overlap_matrix(geometry_path, basis)
  mo_e, mo = scipy.linalg.eigh(F, S)
  return mo_e, mo
  

def infer_orbitals_from_F_model(model_path: str, 
                                geometry_path: str,
                                basis: str = 'sto_6g', 
                                basis_set_size: int = 36,
                                cutoff=5.0) -> Tuple[np.ndarray, np.ndarray]:
  if torch.cuda.is_available():
    device = torch.device('cuda')
  else:
    device = torch.device('cpu')

  # transform geometry into input batch
  atoms = io.read(geometry_path)
  converter = spk.interfaces.AtomsConverter(neighbor_list=spk.transform.ASENeighborList(cutoff=cutoff), dtype=torch.float32, device=device)
  input = converter(atoms)
  
  # load model
  model = torch.load(model_path, map_location=device).to(device)
  model.eval()

  # predicting Fock matrix
  output = model(input)
  values = output['F'].detach().cpu().numpy()
  F = values.reshape(basis_set_size, basis_set_size)
  F = 0.5 * (F + F.T)

  S = calculate_overlap_matrix(geometry_path, basis)

  # F -> MO coeffs
  mo_e, mo = scipy.linalg.eigh(F, S)

  return mo_e, mo

def infer_orbitals_from_mo_model(model_path: str, 
                                geometry_path: str,
                                basis: str = 'sto_6g', 
                                basis_set_size: int = 36,
                                cutoff=5.0) -> Tuple[np.ndarray, np.ndarray]:
  if torch.cuda.is_available():
    device = torch.device('cuda')
  else:
    device = torch.device('cpu')

  # transform geometry into input batch
  atoms = io.read(geometry_path)
  converter = spk.interfaces.AtomsConverter(neighbor_list=spk.transform.ASENeighborList(cutoff=cutoff), dtype=torch.float32, device=device)
  input = converter(atoms)
  
  # load model
  model = torch.load(model_path, map_location=device).to(device)
  model.eval()

  # predicting MO coefficient C matrix
  output = model(input)
  for key in ['mo_coeffs', 'mo_coeffs_adjusted']:
    if key in output.keys():
      values = output[key].detach().cpu().numpy()
      mo = values.reshape(basis_set_size, basis_set_size)
      mo_e = np.zeros(len(mo))
      mo = np.asarray(mo.tolist(), order='C')
      return mo_e, mo