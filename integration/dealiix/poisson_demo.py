"""Transfer-test receiver using the native ImmersX Poisson solver, not liver physics."""
import argparse
import json
from pathlib import Path
import subprocess

from .contracts import Series
from .sources import sha256


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("manifest")
    parser.add_argument("binary")
    parser.add_argument("--time", type=float, default=.006)
    args = parser.parse_args()
    series = Series(args.manifest)
    pressure_pa = series.at(args.time, "P")
    # This numerical test uses dimensionless scalar u = pressure / 10000 Pa.
    value = pressure_pa / 10000.
    parameters = f"""set dimension = 2
set space dimension = 2
subsection Poisson
  set Dirichlet boundary ids = 0
  set FE degree = 1
  set Output directory = output
  set Output name = boundary_pressure
  set Output results also before solving = false
  subsection Dirichlet boundary conditions
    set Function expression = {value:.17g}
    set Variable names = x,y,t
  end
  subsection Domain
    set Initial refinement = 1
    set Grid generator = hyper_cube
    set Grid generator arguments = -1: 1: false
    set Triangulation type = distributed
  end
  subsection Refinement and remeshing
    set Number of refinement cycles = 1
    set Strategy = global
  end
  subsection Right hand side
    set Function expression = 0
    set Variable names = x,y,t
  end
  subsection Solver
    subsection Control
      set Max steps = 100
      set Reduction = 1e-10
      set Tolerance = 1e-12
      set Log result = true
    end
  end
end
"""
    Path("poisson_2d.prm").write_text(parameters)
    subprocess.run([str(Path(args.binary).resolve()), "poisson_2d.prm"], check=True)
    fields = [path for path in Path("output").rglob("*") if path.suffix in (".vtu", ".pvtu")]
    if not fields: raise ValueError("Native ImmersX produced no VTK fields")
    result = {"test": "native-Poisson-scalar-transfer", "physiological_organ_model": False,
              "binary_sha256": sha256(args.binary),
              "source_manifest_sha256": sha256(args.manifest), "sample_time_s": args.time,
              "pressure_pa": pressure_pa, "scalar_scale_pa": 10000., "scalar_boundary_value": value,
              "native_fields": {str(path): sha256(path) for path in fields}}
    Path("result.json").write_text(json.dumps(result, indent=2) + "\n")


if __name__ == "__main__": main()
