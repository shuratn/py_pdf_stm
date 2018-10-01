from feature_extractor import FeatureListExtractor


class STM32FeatureListExtractor(FeatureListExtractor):

    def extract_tables(self):  # OVERRIDE THIS FUNCTION FOR NEW CONTROLLER
        print('Extracting tables for', self.controller)
        datasheet = self.datasheet
        table_page = datasheet.table_root.childs[1].page
        page_num = datasheet.get_page_num(table_page)
        table_pt1 = self.extract_table(datasheet, page_num)
        table_pt2 = self.extract_table(datasheet, page_num + 1)
        table_pt3 = self.extract_table(datasheet, page_num + 2)
        if table_pt1:
            self.features_tables.append(table_pt1[0])
        if table_pt2:
            self.features_tables.append(table_pt2[0])
        if table_pt3:
            self.features_tables.append(table_pt3[0])


    def handle_feature(self, name, value):
        if 'USART' in name and 'LPUART' in name:
            values = value.split('\n')
            return [('USART', values[0]), ('LPUART', values[1])]
        if 'GPIOs' in name and 'Wakeup' in name:
            values = value.split('\n')
            return [('GPIOs', values[0]), ('Wakeup pins', values[1])]
        if 'ADC' in name and 'Number' in name:
            adc_type = name.split('ADC')[0] + 'ADC'
            values = value.split('\n')
            return [(adc_type, {'count': values[0], 'channels': values[1]})]

        return super().handle_feature(name, value)

    def unify_names(self, controller_features):
        return controller_features
