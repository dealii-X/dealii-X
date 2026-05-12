# Gmsh

Open-source geometry and mesh generation tool used in dealii-X for
pre-processing, CAD-driven workflows, and exchange with the simulation
codes in the stack.

[Homepage](https://gmsh.info/) [Repository](https://gitlab.onelab.info/gmsh/gmsh)

<div class="repo-placeholder">
The Gmsh-related integration has been fully internalized within the current deal.II codebase as a set of utilities within the `GMSH` namespace of the `deal.II` library, allowing users to import partitioned meshes directly from separate gmsh files, without the need to partition them within deal.II.
</div>

- Role: geometry authoring, meshing, and mesh format interchange across the project.
- Highlights: CAD kernel support, scripting, API bindings, and HPC-friendly preprocessing.
- Local path for integration assets: `tools/gmsh`
