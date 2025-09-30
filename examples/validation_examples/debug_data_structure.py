#!/usr/bin/env python3
"""
Debug script to inspect robocrystallographer data structures.
Useful for understanding condensed output format.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from ase.build import bulk, molecule
from pymatgen.io.ase import AseAtomsAdaptor
from robocrys import StructureCondenser
import json


def inspect_structure(name, atoms):
    """Inspect robocrys condensed structure in detail"""
    print("\n" + "="*60)
    print(f"Inspecting: {name}")
    print("="*60)

    if atoms.cell.volume < 0.1:
        atoms = atoms.copy()
        atoms.center(vacuum=10.0)
        atoms.set_pbc(True)

    adaptor = AseAtomsAdaptor()
    structure = adaptor.get_structure(atoms)

    try:
        structure.add_oxidation_state_by_guess()
    except:
        pass

    condenser = StructureCondenser()
    condensed = condenser.condense_structure(structure)

    print(f"\nTop-level keys: {list(condensed.keys())}")
    print(f"Dimensionality: {condensed.get('dimensionality')}")
    print(f"Formula: {condensed.get('formula')}")
    print(f"Space group: {condensed.get('spg_symbol')}")
    print(f"Crystal system: {condensed.get('crystal_system')}")

    sites = condensed.get('sites', {})
    print(f"\nSites (type: {type(sites).__name__}):")
    print(f"  Keys: {list(sites.keys())}")

    if sites:
        site_idx = list(sites.keys())[0]
        site_data = sites[site_idx]
        print(f"\nFirst site (index {site_idx}) structure:")
        print(f"  Keys: {list(site_data.keys())}")
        print(f"  Element: {site_data.get('element')}")
        print(f"  Geometry: {site_data.get('geometry')}")
        print(f"  NN (type: {type(site_data.get('nn')).__name__}): {site_data.get('nn')}")
        print(f"  NNN (type: {type(site_data.get('nnn')).__name__}): {site_data.get('nnn')}")

    distances = condensed.get('distances', {})
    print(f"\nDistances (type: {type(distances).__name__}):")
    print(f"  Keys: {list(distances.keys())}")
    if distances:
        dist_idx = list(distances.keys())[0]
        print(f"  Site {dist_idx} distances: {distances[dist_idx]}")

    print("\n--- Full JSON (first site only) ---")
    if sites:
        print(json.dumps(sites[list(sites.keys())[0]], indent=2, default=str))


if __name__ == "__main__":
    print("Robocrystallographer Data Structure Inspector")

    cu = bulk('Cu', 'fcc', a=3.6)
    inspect_structure("Cu FCC", cu)

    water = molecule('H2O')
    inspect_structure("H2O Molecule", water)

    print("\n" + "="*60)
    print("Inspection complete")
    print("="*60)