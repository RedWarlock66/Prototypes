from flask import request, Flask, render_template, make_response, jsonify, redirect
from data_api import DataAPI
from content_generation import Generator
from json import dumps

srvr, port, db_name = "http://127.0.0.1", 4990, 'content_generator'
app, data_api, generator = Flask(__name__), DataAPI(db_name), Generator()


@app.route('/content_generator', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/content_generator/parameters', methods=['GET'])
def parameters():
    return render_template('parameters.html')


@app.route('/content_generator/results_history', methods=['GET'])
def results_history():
    rendered_page = request.cookies.get('results_history')
    return rendered_page if rendered_page else 'No results history available'


@app.route('/content_generator/show_results_history', methods=['POST'])
def show_results_history():
    _parameters = request.get_data(as_text=True)
    if not _parameters:
        results, error_description = 'null', 'null'
    else:
        result = data_api.find_text_generation_results(_parameters)
        results = dumps(result.result) if result.success and result.result else 'null'
        error_description = 'null' if result.success else result.description
    rendered_page = render_template('results_history.html', results=results, error_description=error_description)
    response = make_response(redirect('/content_generator/results_history'))
    response.set_cookie('results_history', rendered_page)
    return response


@app.route('/content_generator/generate_content', methods=['POST'])
def generate_content():
    description = request.get_json(force=True)
    result = generator.generate_text_content(description)
    if result['success']:
        return make_response(jsonify(result['result']), 200)
    else:
        return make_response(result['result'], 400)


@app.route('/content_generator/get_reference_element', methods=['GET'])
def get_reference_element():
    reference_name, _id = request.args.get('reference'), request.args.get('id')
    result = data_api.get_reference_element(reference_name, _id)
    return _make_http_result(result)


@app.route('/content_generator/reference_values_list', methods=['POST'])
def reference_values_list():
    # without checking to simplify
    reference_name = request.args.get('reference')
    _filter = {} if request.content_length == 0 else request.get_json(force=True)
    result = data_api.get_reference_values_list(reference_name, **_filter)
    return _make_http_result(result)


@app.route('/content_generator/get_request_parameters', methods=['GET'])
def get_request_parameters():
    # without transaction or one request to simplify development (no need for optimization, spends less time)
    result = data_api.get_parameters()
    return _make_http_result(result)


@app.route('/content_generator/change_reference_element', methods=['POST'])
def change_reference_element():
    # without checking to simplify
    reference_name, _id, is_new = request.args.get('reference'), request.args.get('id'), 'is_new' in request.args
    values = request.get_json(force=True)
    result = data_api.change_reference_element(reference_name, is_new, _id, **values)
    return _make_http_result(result)


@app.route('/content_generator/delete_reference_element', methods=['DELETE'])
def delete_reference_element():
    # integrity control should be ensured later
    reference_name, _id = request.args.get('reference'), request.args.get('id')
    result = data_api.delete_reference_element(reference_name, _id)
    if result.success:
        return make_response(f'Element {_id} deleted successfully', 200)
    else:
        return make_response(result.description, 400)


@app.route('/content_generator/save_text_generation_result', methods=['POST'])
def save_text_generation_result():
    description = request.get_json(force=True)
    result = data_api.save_text_generation_result(dumps(description['parameters']), description['result'])
    return _make_http_result(result)


@app.route('/content_generator/find_text_generation_results', methods=['POST'])
def find_text_generation_results():
    _parameters = request.get_data(as_text=True)
    result = data_api.find_text_generation_results(_parameters)
    return _make_http_result(result)


def _make_http_result(result):
    if result.success:
        return make_response(jsonify(result.result), 200)
    else:
        return make_response(result.description, 400)


if __name__ == "__main__":
    data_api.create_database()
    app.run(debug=True, port=port)