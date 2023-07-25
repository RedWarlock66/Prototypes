from content_generators.text_content_generators import GeneratorFactory as text_generator
from json import load
from pathlib import Path


class Generator:

    # заметочка на будущее - настройки в целом можно читать на уровне класса, а не инстанса
    _settings_file = Path(__file__).resolve().parent / 'content_generators/settings/generation_settings.json'

    def __init__(self):
        self._settings = self._read_setting()
        self._text_generator = text_generator.get_generator(self._settings['text']['default_generator'])

    def generate_text_content(self, description:str, name:str = None) -> dict:
        if name is None:
            generator = self._text_generator
        else:
            get_generator = self._get_text_content_generator(name)
            if get_generator['success']:
                generator = get_generator['result']
            else:
                return get_generator
        return generator.generate_content(description)

    @staticmethod
    def _get_text_content_generator(name:str) -> dict:
        try:
            generator = text_generator.get_generator(name)
        except Exception as error:
            return {'success': False, 'result': f'Text content generator {name} is not supported'}
        else:
            return {'success': True, 'result': generator}

    def _read_setting(self):
        with open(self._settings_file, 'r') as settings_file:
            settings_dict = load(settings_file)
        return settings_dict

