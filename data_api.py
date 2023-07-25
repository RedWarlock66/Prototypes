from sqlalchemy import create_engine, text
from sqlalchemy_utils import create_database, database_exists
from sqlalchemy.orm import sessionmaker
import data_model
from datetime import datetime


# should be a singleton?
class DataAPI:

    _references = {"parameters_types": data_model.ParameterType,
                    "parameters": data_model.Parameter,
                    "parameters_values_variants": data_model.ParameterValueVariant}

    @classmethod
    def _changing_methods(cls):
        return {"parameters_types": cls.change_parameter_type,
                "parameters": cls.change_parameter,
                "parameters_values_variants": cls.change_parameter_value_variant}

    def __init__(self, db_name:str):
        # enough for a prototype
        self._dbname = db_name
        self._engine = create_engine(f'sqlite:///{db_name}.db', echo=True)
        # will it be better to create a session once or to create a new session every time? Should check it
        self._session = sessionmaker(bind=self._engine)

    def create_database(self) -> '_ResultDescription':
        if not database_exists(self._engine.url):
            create_database(self._engine.url)
            data_model.Base.metadata.create_all(self._engine)
        return _ResultDescription()

    def create_tables(self) -> '_ResultDescription':
        # simple code without checking
        data_model.Base.metadata.create_all(self._engine, checkfirst=True)
        return _ResultDescription()

    def get_reference_element(self, reference_name: str, _id: str) -> '_ResultDescription':
        if reference_name not in self._references:
            return _ResultDescription(success=False, description=f'There is no reference {reference_name}. '
                                                                 f'Choose one of the {self._references.keys()}')
        return _ResultDescription(result=self._get_element_by_id(self._references[reference_name], _id))

    def get_reference_values_list(self, reference_name: str, **_filter) -> '_ResultDescription':
        if reference_name not in self._references:
            return _ResultDescription(success=False, description=f'There is no reference {reference_name}. '
                                                                 f'Choose one of the {self._references.keys()}')
        with self._session() as session:
            elements = session.query(self._references[reference_name]).filter_by(**_filter).all()
            result = [element.values for element in elements]
        return _ResultDescription(result=result)

    def change_reference_element(self, reference_name:str, is_new: bool, _id: str = None,
                                 **values) -> '_ResultDescription':
        # such repeating patterns should be refactored with decorators
        if reference_name not in self._references:
            return _ResultDescription(success=False, description=f'There is no reference {reference_name}. '
                                                                 f'Choose one of the {self._references.keys()}')
        changing_methods = self._changing_methods()
        result = changing_methods[reference_name](self, is_new=is_new, _id=_id, **values)
        return result

    def change_parameter_type(self, is_new: bool,
                              _id: str = None, name: str = None, description: str = None, **kwargs) -> '_ResultDescription':
        return self._change_reference_instance(data_model.ParameterType, is_new,
                                               id=_id, name=name, description=description)

    def change_parameter(self, is_new: bool, type_id: str = None,
                         _id: str = None, name: str = None, description: str = None, **kwargs) -> '_ResultDescription':
        if is_new and not type_id: raise Exception('Type id for the new element is not specified!')
        return self._change_reference_instance(data_model.Parameter, is_new,
                                               type_id=type_id, id=_id, name=name, description=description)

    def change_parameter_value_variant(self, is_new: bool, parameter_id: str = None, _id: str = None,
                                        name: str = None, description: str = None, **kwargs) -> '_ResultDescription':
        if is_new and not parameter_id: raise Exception('Parameter id for the new element is not specified!')
        return self._change_reference_instance(data_model.ParameterValueVariant, is_new,
                                               parameter_id=parameter_id, id=_id, name=name, description=description)

    def delete_reference_element(self, reference_name: str, _id: str) -> '_ResultDescription':
        if reference_name not in self._references:
            return _ResultDescription(success=False, description=f'There is no reference {reference_name}. '
                                                                 f'Choose one of the {self._references.keys()}')
        with self._session() as session:
            element_instance = session.query(self._references[reference_name]).filter_by(id=_id).first()
            if element_instance is not None:
                try:
                    session.delete(element_instance)
                    session.commit()
                    result = _ResultDescription()
                except Exception as error:
                    result = _ResultDescription(success=False,
                                                description=f'Unable to delete the element due to {str(error)}')
            else:
                result = _ResultDescription(success=False,
                                            description=f'There is no {reference_name} element with {_id = }')
        return result

    def get_parameters(self) -> '_ResultDescription':
        # data model should be used next time
        query = text('SELECT parameters_types.id as type_id, parameters_types.name as type, '
                     'parameters.id as parameter_id, parameters.name as parameter, '
                     'parameters_values_variants.name as variant '
                     'FROM parameters_types LEFT JOIN parameters ON parameters_types.id = parameters.type_id '
                     'LEFT JOIN parameters_values_variants ON parameters.id = parameters_values_variants.parameter_id')
        with self._session() as session:
            try:
                query_result = session.execute(query)
            except Exception as error:
                result = _ResultDescription(success=False, description=f'Unable to get parameters due to {str(error)}')
            else:
                # an old method. should be replaced with something more beautiful
                parameters = {}
                for row in query_result:
                    if row.type not in parameters:
                        parameters[row.type] = {'id': row.type_id, 'parameters': {}}
                    if row.parameter not in parameters[row.type]['parameters'] and row.parameter is not None:
                        parameters[row.type]['parameters'][row.parameter] = {'id': row.parameter_id, 'variants': []}
                    if row.variant:
                        parameters[row.type]['parameters'][row.parameter]['variants'].append(row.variant)
                result = _ResultDescription(result=parameters)
        return result

    def save_text_generation_result(self, parameters: str, result: str) -> '_ResultDescription':
        with self._session() as session:
            results_table = data_model.TextGeneratingResult()
            results_table.parameters = parameters
            results_table.result = result
            session.add(results_table)
            try:
                session.commit()
                result = _ResultDescription()
            except Exception as error:
                result = _ResultDescription(success=False, description=f'Unable to save result due to {str(error)}')
        return result

    def find_text_generation_results(self, parameters: str) -> '_ResultDescription':
        with self._session() as session:
            try:
                records = data_model.TextGeneratingResult.find_result(session, parameters)
                result = _ResultDescription(result=[record.result for record in records])
            except Exception as error:
                result = _ResultDescription(success=False, description=f'Unable to find results due to {str(error)}')
        return result

    def _change_reference_instance(self, reference: data_model._Reference, is_new:bool = False,
                                   **values) -> '_ResultDescription':
        _id, result = values.get('id'), None
        if not is_new and _id is None:
            return _ResultDescription(False, 'Id was not specified!')
        with self._session() as session:
            reference_instance = reference() if is_new \
                else session.query(reference).filter_by(id=_id).first()
            if reference_instance is None:
                result = _ResultDescription(False, f'Id {_id} does not exist in the database!')
            else:
                for name, value in values.items():
                    if value is not None: setattr(reference_instance, name, value)
                reference_instance.changing_datetime = datetime.now()
                try:
                    session.add(reference_instance)
                    session.commit()
                    result = _ResultDescription(result=reference_instance.values)
                except Exception as error:
                    result = _ResultDescription(success=False,
                                                description=f'Unable to change the element due to {str(error)}')
        return result

    def _get_element_by_id(self, reference:data_model._Reference, _id: str) -> [dict, None]:
        with self._session() as session:
            element_instance = session.query(reference).filter_by(id=_id).first()
            result = element_instance.values if element_instance else None
        return result


class _ResultDescription:
    def __init__(self, success: bool = True, description: str = '', result=None):
        self.success = success
        self.description = description
        self.result = result

    def __str__(self):
        return f'Success: {self.success}\nDescription:{self.description}\nResult:\n{self.result}'

    def __getitem__(self, item):
        return self.result[item] if isinstance(self.result, dict) else None