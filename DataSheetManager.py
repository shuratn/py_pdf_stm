import os
from pathlib import Path

import requests
from tqdm import tqdm

from DataSheet import DataSheet


class DataSheetManager:
    STM32_DATASHEET_URL = 'https://www.st.com/resource/en/datasheet/{}re.pdf'
    DATASHEET_URLS = {'STM32': STM32_DATASHEET_URL}

    def __init__(self, controllers):
        self.controllers = controllers
        self.controller_datasheets = {}



    def get_or_download(self):
        for controller in self.controllers:
            for known_controller,url in self.DATASHEET_URLS.items(): #type: str,str
                if known_controller.upper() in controller:
                    path = Path('./')/known_controller / controller / "{}_ds.pdf".format(controller)
                    if path.exists():
                        datasheet = DataSheet(str(path))
                    else:
                        print('Unknown yet controller, trying to download datasheet')
                        r = requests.get(url.format(controller), stream=True)
                        if r.status_code == 200:
                            os.makedirs(path.parent, exist_ok=True)
                            with path.open('wb') as f:
                                total_length = int(r.headers.get('content-length'))
                                for chunk in tqdm(r.iter_content(chunk_size=1024), total=int(total_length / 1024) + 1, unit='Kbit'):
                                    if chunk:
                                        f.write(chunk)
                                        f.flush()
                                f.close()
                            datasheet = DataSheet(str(path))
                        else:
                            raise Exception('Invalid controller name')
                        
