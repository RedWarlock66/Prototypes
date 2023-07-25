from data_model import TextGeneratingResult
from data_api import DataAPI
from json import dumps

data_api = DataAPI('content_generator')
parameters = {"scene":"double sun sunrise", "mood":"romantic"}
result = 'Just a double sunrise. Nothing special'
results = data_api.save_text_generation_result(dumps(parameters), result)
print(results)
