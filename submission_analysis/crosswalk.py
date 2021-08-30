import json
import pandas as pd
from collections import defaultdict
from typing import Optional


class Crosswalk:
    def __init__(self,
                 block_crosswalk_path: str,
                 vtd_crosswalk_path: Optional[str] = None):
        blocks_crosswalk = pd.read_csv(block_crosswalk_path, sep='|')
        blocks_crosswalk['block_id_2010'] = (
            blocks_crosswalk['STATE_2010'].astype(str) +
            blocks_crosswalk['COUNTY_2010'].astype(str).str.zfill(3) +
            blocks_crosswalk['TRACT_2010'].astype(str).str.zfill(6) +
            blocks_crosswalk['BLK_2010'].astype(str).str.zfill(4))
        blocks_crosswalk['block_id_2020'] = (
            blocks_crosswalk['STATE_2020'].astype(str) +
            blocks_crosswalk['COUNTY_2020'].astype(str).str.zfill(3) +
            blocks_crosswalk['TRACT_2020'].astype(str).str.zfill(6) +
            blocks_crosswalk['BLK_2020'].astype(str).str.zfill(4))

        block_group_2010_to_blocks_2020 = defaultdict(set)
        for block_2010, block_2020 in zip(blocks_crosswalk['block_id_2010'],
                                          blocks_crosswalk['block_id_2020']):
            block_group_2010_to_blocks_2020[block_2010[:12]].add(block_2020)
        self.block_group_2010_to_blocks_2020 = dict(
            block_group_2010_to_blocks_2020)

        if vtd_crosswalk_path is None:
            self.vtd_to_blocks_2020 = {}
        else:
            self.vtd_to_blocks_2020 = {
                vtd: set(blocks)
                for vtd, blocks in json.load(open(vtd_crosswalk_path)).items()
            }

    def map_2010_block_groups(self, bgs):
        return set.union(*(self.block_group_2010_to_blocks_2020[bg]
                           for bg in bgs))

    def map_vtds(self, vtds):
        return set.union(*(self.vtd_to_blocks_2020[vtd] for vtd in vtds))
