import os
import sys
from pathlib import Path
from typing import List

import requests
from tqdm import tqdm

from DataSheetParsers.DataSheet import DataSheet
from DataSheetParsers.MK_E_DataSheet import MK_DataSheet
from DataSheetParsers.KE_E_DataSheet import KE_DataSheet
from DataSheetParsers.KV_E_DataSheet import KV_DataSheet
from DataSheetParsers.KL_E_DataSheet import KL_DataSheet
from DataSheetParsers.TI_DataSheet import TI_DataSheet


class DataSheetManager:
    STM32L_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}.pdf'
    STM32F_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}.pdf'
    # MKL_DATASHEET_URL = 'https://www.nxp.com/docs/en/product-selector-guide/KINETISLMCUSELGD.pdf'  # KL17P64M48SF6
    # MK_DATASHEET_URL = 'https://www.nxp.com/docs/en/product-selector-guide/KINETISKMCUSELGD.pdf'  # MK11DN512AVMC5
    MKM_DATASHEET_URL = 'https://www.nxp.com/docs/en/data-sheet/{}.pdf'  # MKM
    TI_DATASHEET_URL = 'http://www.ti.com/lit/ds/symlink/{}.pdf'  # MKM
    # KL_DATASHEET_URL = 'https://www.nxp.com/docs/en/data-sheet/{}.pdf' #KL17P64M48SF6
    DATASHEET_URLS = {
        'STM32L': (STM32L_DATASHEET_URL, DataSheet),
        'STM32F': (STM32F_DATASHEET_URL, DataSheet),
        'KL': (MKM_DATASHEET_URL, KL_DataSheet),
        'KE': (MKM_DATASHEET_URL, KE_DataSheet),
        'KV': (MKM_DATASHEET_URL, KV_DataSheet),
        'MK': (MKM_DATASHEET_URL, MK_DataSheet),
        'MSP': (TI_DATASHEET_URL, TI_DataSheet),
        'CC': (TI_DATASHEET_URL, TI_DataSheet),
    }

    def __init__(self, datasheets: List[str]) -> None:
        self.datasheets = datasheets
        self.datasheets_datasheets = {}

    def get_datasheet_loader(self, mc: str):
        for loader in sorted(self.DATASHEET_URLS, key=lambda l: len(l), reverse=True):
            if loader.upper() in mc.upper():
                return loader, self.DATASHEET_URLS[loader]
        return None, (None, None)

    def get_or_download(self):
        with tqdm(self.datasheets,desc="Parsing datasheet",) as bar:
            for controller in bar:
                bar.set_description('Parsing {}'.format(controller))
                known_controller, (url, datasheet_loader) = self.get_datasheet_loader(controller)
                if known_controller:

                    if known_controller.upper() in controller.upper():
                        # if known_controller == 'MKL' or (known_controller == 'MK' and known_controller!='MKM'):
                        #     path = Path('./') / 'Datasheets' / known_controller / "{}.pdf".format(known_controller)
                        # else:
                        path = Path('./') / 'Datasheets' / known_controller / "{}.pdf".format(controller)
                        path = path.absolute()
                        if not path.parent.exists():
                            path.parent.mkdir(exist_ok=True)
                        if path.exists():
                            datasheet = datasheet_loader(str(path))
                        else:
                            if self.get_datasheet_loader(controller)[0] == 'MK':
                                print('CAN\'T DOWNLOAD NXP DATASHEETS AUTOMATICALLY', file=sys.stderr)
                                print('PLEASE ADD {} DATASHEET MANUALLY!'.format(controller), file=sys.stderr)
                                continue
                            print(controller, ' is unknown , trying to download datasheet')
                            url = url.format(controller)
                            r = requests.get(url, stream=True)
                            if r.status_code == 200:
                                os.makedirs(path.parent, exist_ok=True)
                                with path.open('wb') as f:
                                    total_length = int(r.headers.get('content-length'))
                                    for chunk in tqdm(r.iter_content(chunk_size=1024), total=int(total_length / 1024) + 1,
                                                      unit='Kbit'):
                                        if chunk:
                                            f.write(chunk)
                                            f.flush()
                                    f.close()
                                datasheet = datasheet_loader(str(path))
                            else:
                                raise Exception('Invalid controller name')
                        self.datasheets_datasheets[controller.upper()] = datasheet
                    else:
                        raise Exception(
                            'DATASHEET\LOADER for {} was not found\n'
                            'Proposal: remove or correct name of it'.format(controller))

    def __getitem__(self, item: str):
        return self.datasheets_datasheets.get(item.upper(), None)


if __name__ == '__main__':
    manager = DataSheetManager(['msp432p4011'])
    manager.get_or_download()
    print(manager.datasheets_datasheets)
