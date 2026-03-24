# vsputils

Python wrapper utilities for the [OpenVSP](http://openvsp.org/) API, providing streamlined interfaces for model manipulation, aerodynamic analysis, and results processing.

## Features

- **Model Manipulation** — Load VSP models, modify design parameters, and swap airfoils programmatically
- **Aerodynamic Analysis** — Execute VSPAERO sweeps, stability analyses, and parasitic drag computations
- **Results Processing** — Extract analysis results into pandas DataFrames for polar, load distribution, stability, and drag data
- **Batch Execution** — Run multi-case studies from YAML configuration files with schema validation
- **Aerodynamic Calculations** — Fit drag polars, compute aerodynamic center, and transfer moment references
- **Visualization** — Plot spanwise load distributions

## Installation

Requires Python >= 3.12 and a working [OpenVSP](http://openvsp.org/) installation with Python bindings (`openvsp` package).

```bash
cd python
pip install .
```

## Usage

### Model modification

```python
import vsputils.vsputils as vspu

vspu.restart("aircraft.vsp3")
vspu.change_parm("Wing", "XSec_1", "Span", 35.0)
vspu.change_airfoil("Wing", 0, "naca2412.dat")
```

### Running analyses with the Runner

```python
import vsputils.runner as vspr

runners = vspr.load_yaml("cases.yml")

for runner in runners:
    runner.run_all()
    print(runner.polar)   # DataFrame with Alpha, CDi, CDo, CL, CM, etc.
    print(runner.load)    # Spanwise load distributions
    print(runner.stab)    # Stability derivatives

# Save/load results
vspr.dump_cases(runners, "results.json")
runners = vspr.load_cases("results.json")
```

### Aerodynamic utilities

```python
import vsputils.aero as vspa

# Fit drag polar (CL vs CD polynomial)
dp = vspa.drag_polar(runner.polar)

# Aerodynamic center as function of alpha
xac_poly = vspa.xac(runner.polar, runner.aero_refs)

# Parasite drag vs velocity curve
cd0_func = vspa.parasite_drag(velocity, cd0)
```

### Case configuration (YAML)

```yaml
cases:
  - name: baseline
    fname: aircraft.vsp3
    changes:
      - "Wing:XSec_1:Span:35.0"
    airfoils:
      - "Wing:0:naca2412.dat"
    del_subsurf: false
    analyses:
      VSPAEROComputeGeometry:
        GeomSet: -1
      VSPAEROSweep:
        AlphaStart: -2
        AlphaEnd: 10
        AlphaNpts: 7
      ParasiteDrag:
        FileName: drag_output.txt
```

## Modules

| Module | Description |
|--------|-------------|
| `vsputils.vsputils` | Core OpenVSP API wrappers for model I/O, parameter changes, analysis execution, and result extraction |
| `vsputils.runner` | `Runner` class for orchestrating full analysis workflows from YAML/JSON configs |
| `vsputils.aero` | Aerodynamic calculations — drag polars, aerodynamic center, moment transfer, parasite drag fitting |
| `vsputils.plot` | Plotting utilities for spanwise load distributions |

## Testing

```bash
cd python
pytest
```

# Docker

Dockerfiles to create Docker images for running OpenVSP via scripts (no GUI or Python).

## Building an image

The build context must contain the OpenVSP repository. With the following layout:

```
OpenVSP/
├── repo/       # Clone of OpenVSP git repository
└── vsputils/   # This repository
```

Run from the `OpenVSP/` directory:

```bash
docker build --build-arg REPO_PATH=./repo --network host -t openvsp:latest -f vsputils/docker/Dockerfile .
```

Use other options such as `--network host` as needed.

## Running an image

```bash
docker run -it openvsp /bin/bash
```

The image has its working directory at `/tmp/wdir`. To run an analysis with a model and script:

```bash
docker run --rm \
  -v /home/me/models:/tmp/wdir \
  -v /home/me/scripts:/tmp/scr \
  openvsp vspscript -script /tmp/scr/af.vspscript ap.vsp3 > stdout.log 2> stderr.log
```

The command above will redirect the outputs _in the host_, not in the container.


# License

See [LICENSE](LICENSE) for details.
