from sdk.moveapps_spec import hook_impl
from sdk.moveapps_io import MoveAppsIo
from movingpandas import TrajectoryCollection
import logging
import matplotlib.pyplot as plt
import tempfile

from random_walk_package import AnimalMovementProcessor
from random_walk_package import apply_moveapps_id_dtype_patch, debug_patch_state

class App(object):

    def __init__(self, moveapps_io):
        self.moveapps_io = moveapps_io

    @hook_impl
    def execute(self, data: TrajectoryCollection, config: dict) -> TrajectoryCollection:
        apply_moveapps_id_dtype_patch()
        debug_patch_state()
        with tempfile.TemporaryDirectory(dir=".") as tmp_dir:
            traj_col_copy = data.to_point_gdf().copy()
            proc = AnimalMovementProcessor(data=data)
            proc.create_landcover_data_txt(False, 1000, tmp_dir)
            supp_gdf = proc.add_features(data.to_point_gdf())
            traj_col_copy["terrain"] = supp_gdf["terrain"].values
            result = TrajectoryCollection(traj_col_copy,
                                                traj_id_col=data.get_traj_id_col(),
                                                t=data.t,
                                                crs=data.get_crs())
            return result
