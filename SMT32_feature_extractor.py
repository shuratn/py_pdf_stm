from feature_extractor import FeatureListExtractor


class STM32FeatureListExtractor(FeatureListExtractor):

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
