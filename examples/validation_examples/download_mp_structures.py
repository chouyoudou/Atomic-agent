"""Download and cache structures from Materials Project for testing."""

import sys
sys.path.insert(0, '.')

from mp_api.client import MPRester
from ase.io import write
from pymatgen.io.ase import AseAtomsAdaptor
import os

# Materials Project API key
with open('mp_api', 'r') as f:
    API_KEY = f.read().strip()


def download_and_save_structures():
    """Download representative structures and save as files."""
    print("Downloading structures from Materials Project...")

    cache_dir = "examples/validation_examples/mp_structures"
    os.makedirs(cache_dir, exist_ok=True)

    with MPRester(API_KEY) as mpr:
        structures_to_download = [
            ("BaTiO3", "Perovskite"),
            ("Al2O3", "Corundum"),
            ("ZnS", "Zinc Blende"),
        ]

        adaptor = AseAtomsAdaptor()

        for formula, description in structures_to_download:
            print(f"\nSearching for {formula} ({description})...")

            docs = mpr.materials.summary.search(
                formula=formula,
                fields=["material_id", "structure", "formula_pretty"],
                num_chunks=1,
                chunk_size=1
            )

            if docs:
                doc = docs[0]
                print(f"  Found: {doc.material_id}")

                # Convert to ASE and save
                atoms = adaptor.get_atoms(doc.structure)
                filename = f"{cache_dir}/{formula}_{doc.material_id}.xyz"
                write(filename, atoms)
                print(f"  Saved: {filename}")
            else:
                print(f"  Not found!")

    print("\n✅ Download complete!")


if __name__ == "__main__":
    download_and_save_structures()