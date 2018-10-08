import os
from pathlib import Path
from typing import List

import requests
from tqdm import tqdm

from DataSheetParsers.DataSheet import DataSheet
from DataSheetParsers.MK_DataSheet import MK_DataSheet
from DataSheetParsers.MKL_DataSheet import MKL_DataSheet


class DataSheetManager:
    STM32L_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}re.pdf'
    STM32F_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}.pdf'
    MKL_DATASHEET_URL = 'https://www.nxp.com/docs/en/product-selector-guide/KINETISLMCUSELGD.pdf'  # KL17P64M48SF6
    MK_DATASHEET_URL = 'https://www.nxp.com/docs/en/product-selector-guide/KINETISKMCUSELGD.pdf'  # MK11DN512AVMC5
    # KL_DATASHEET_URL = 'https://www.nxp.com/docs/en/data-sheet/{}.pdf' #KL17P64M48SF6
    DATASHEET_URLS = {
        'STM32L': (STM32L_DATASHEET_URL, DataSheet),
        'STM32F': (STM32F_DATASHEET_URL, DataSheet),
        'MKL': (MKL_DATASHEET_URL, MKL_DataSheet),
        'MK': (MK_DATASHEET_URL, MK_DataSheet),
    }

    def __init__(self, datasheets: List[str]):
        self.datasheets = datasheets
        self.datasheets_datasheets = {}

    def get_datasheet_loader(self,mc:str):
        for loader in sorted(self.DATASHEET_URLS,key=lambda l:len(l),reverse=True):
            if loader.upper() in mc.upper():
                return loader,self.DATASHEET_URLS[loader]
        return None,None

    def get_or_download(self):
        for controller in self.datasheets:
            known_controller, (url, datasheet_loader) =  self.get_datasheet_loader(controller)
            if known_controller.upper() in controller.upper():
                if known_controller == 'MKL' or known_controller == 'MK':
                    path = Path('./') / 'Datasheets' / known_controller / "{}.pdf".format(known_controller)
                else:
                    path = Path('./') / 'Datasheets' / known_controller / "{}.pdf".format(
                        controller)
                path = path.absolute()
                if not path.parent.exists():
                    path.parent.mkdir(exist_ok=True)
                if path.exists():
                    datasheet = datasheet_loader(str(path))
                else:
                    print(controller, ' is unknown , trying to download datasheet')
                    r = requests.get(url.format(controller), stream=True)
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

    def __getitem__(self, item: str):
        return self.datasheets_datasheets.get(item.upper(), None)


if __name__ == '__main__':
    manager = DataSheetManager(['stm32f437ig'])
    manager.get_or_download()
    print(manager.datasheets_datasheets)
