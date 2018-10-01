import os
from pathlib import Path
from typing import List

import requests
from tqdm import tqdm

from DataSheet import DataSheet
from KL_DataSheet import KL_DataSheet


class DataSheetManager:
    STM32_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}re.pdf'
    KL_DATASHEET_URL = 'https://www.nxp.com/docs/en/data-sheet/{}.pdf' #KL17P64M48SF6
    DATASHEET_URLS = {
        'STM32': (STM32_DATASHEET_URL,DataSheet),
        'KL': (KL_DATASHEET_URL,KL_DataSheet),
    }

    def __init__(self, controllers:List[str]):
        self.controllers = controllers
        self.controller_datasheets = {}


    def get_or_download(self):
        for controller in self.controllers:
            for known_controller, (url,datasheet_loader) in self.DATASHEET_URLS.items():  # type: str,str
                if known_controller.upper() in controller.upper():
                    path = Path('./') /'Datasheets'/ known_controller / controller / "{}_ds.pdf".format(controller)
                    if path.exists():
                        datasheet = datasheet_loader(str(path))
                    else:
                        print(controller,' is unknown , trying to download datasheet')
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
                    self.controller_datasheets[controller.upper()] = datasheet

    def __getitem__(self, item:str):
        return self.controller_datasheets.get(item.upper(),None)


if __name__ == '__main__':
    manager = DataSheetManager(['STM32L451','STM32L452','KL17P64M48SF6'])
    manager.get_or_download()
    print(manager.controller_datasheets)

