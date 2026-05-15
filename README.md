# gige

GigE camera acquisition tool for EPICS-controlled cameras. Configures the camera via EPICS PVs and saves frames as TIFF files.

## Project structure

```
src/gige/
    __init__.py   # exports Gige1Camera
    camera.py     # Gige1Camera class
    main.py       # CLI entry point
config.yaml       # example configuration
```

## Installation

Install the package into your Python environment (this also installs all dependencies):

```
pip install -e .
```

Or with uv:

```
uv sync
```

## Running from the command line

After installation, run the acquisition script with:

```
uv run gige config.yaml
uv run gige --help
uv run gige -v config.yaml   # verbose/debug logging
```

## Importing the camera class (e.g. in Spyder)

Once the package is installed (`pip install -e .`), import the camera class directly:

```python
from gige import Gige1Camera

camera = Gige1Camera(
    base_pv="BLXXX-DI-GIGE-01",
    folder_path="/path/to/output",
    file_no=1,
    acquire_time=0.5,
    num_images=1,
    width=1936,
    height=1216,
    x_start=1,
    y_start=1,
    image_mode=1,
    data_type=12,
    file_template="%s%s%06d.tiff",
    poll_interval=0.1,
)

if camera.check_connection(timeout=5.0):
    camera.acquire()
```

## Configuration

All parameters for the CLI are set in a YAML file. See `config.yaml` for an example with descriptions of each field.
