from sdk.moveapps_spec import hook_impl
from movingpandas import TrajectoryCollection
from pathlib import Path
import tempfile
from zipfile import ZIP_DEFLATED, ZipFile

from environmentcma import annotate_study_pickle, RangeType


class App(object):

    def __init__(self, moveapps_io):
        self.moveapps_io = moveapps_io

    @hook_impl
    def execute(self, data: TrajectoryCollection, config: dict) -> TrajectoryCollection:
        range_type = RangeType(config["range_type"])
        add_utm = True if config["addUtm"] == "true" else False
        with tempfile.TemporaryDirectory(dir=".") as tmp_dir:
            annotated_tcol = annotate_study_pickle(
                trajectories=data,
                output_directory=tmp_dir,
                range_type=range_type,
                resolution=1000,
                add_utm=add_utm,
            )

            if config["keepGeoTiffs"] == "true":
                output_directory = Path(tmp_dir)
                artifact_path = Path(
                    self.moveapps_io.create_artifacts_file("tiffs.zip")
                )
                artifact_path.parent.mkdir(parents=True, exist_ok=True)
                geotiffs = sorted(
                    path
                    for path in output_directory.rglob("*")
                    if path.is_file() and path.suffix.lower() in {".tif", ".tiff"}
                )
                with ZipFile(artifact_path, "w", compression=ZIP_DEFLATED) as archive:
                    for geotiff in geotiffs:
                        archive.write(
                            geotiff,
                            arcname=geotiff.relative_to(output_directory),
                        )

            return annotated_tcol
