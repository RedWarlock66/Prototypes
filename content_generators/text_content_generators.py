from pathlib import Path
from abc import ABC, abstractmethod
from json import load
from content_generation_service.content_generators.GPT import ConversationAPI


class GeneratorFactory(ABC):
    _generators = {}

    @classmethod
    def register_generator(cls, name: str, value):
        cls._generators[name] = value

    @classmethod
    def get_generator(cls, name: str) -> 'ContentGenerator':
        return cls._generators[name]()


class ContentGenerator(ABC):
    _settings_file = Path(__file__).resolve().parent / 'settings/generation_settings.json'

    def __init__(self):
        self._settings = self._read_settings()

    @abstractmethod
    def generate_content(self, description: str) -> dict:
        pass

    def _read_settings(self):
        with open(self._settings_file, 'r') as settings_file:
            settings = load(settings_file)
        return settings


class ChatGPTGenerator(ContentGenerator):
    def __init__(self):
        super().__init__()
        self._api = ConversationAPI()

    def generate_content(self, description: str) -> dict:
        prompt = f'{self._settings["text"]["prompt_start"]}\n' \
                 f'{description}\n' \
                 f'{self._settings["text"]["prompt_end"]}'
        result = self._api.send_message('user', prompt)
        if result['success']:
            return {'success': True, 'result': result['result']['content']}
        else:
            return {'success': False, 'result': result['result']['description']}


GeneratorFactory.register_generator('ChatGPT', ChatGPTGenerator)


