from sqlalchemy import Column, String, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from uuid import uuid4
from datetime import datetime
from hashlib import sha256
from json import loads

Base = declarative_base()

# abstract classes


class _Reference(Base):
    __abstract__ = True

    id = Column(String(36), primary_key=True, index=True)
    name = Column(String(150), index=True)
    description = Column(Text)
    creation_datetime = Column(DateTime)
    changing_datetime = Column(DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not kwargs.get('id'): self.id = str(uuid4())
        if not kwargs.get('creation_datetime'): self.creation_datetime = datetime.now()
        if not kwargs.get('changing_datetime'): self.changing_datetime = datetime.now()

    def __str__(self):
        return f'{self.__tablename__ = }; {self.id =}; {self.name = }; {self.description = }'

    @property
    def values(self):
        # temporary prototype solution
        return {"id":self.id, "name":self.name, "description":self.description}

# data classes


class ParameterType(_Reference):
    __tablename__ = 'parameters_types'
    parameters = relationship('Parameter', backref='type')

    @property
    def parameters_list(self):
        return [parameter.value for parameter in self.parameters]


class Parameter(_Reference):
    __tablename__ = 'parameters'

    type_id = Column(String(36), ForeignKey('parameters_types.id'), index=True)
    value_variants = relationship('ParameterValueVariant', backref='parameter')

    @property
    def values(self):
        values = super(Parameter, self).values
        values['type_id'] = self.type_id
        if self.type:
            values.update({'type': self.type.values})
        else:
            values['type'] = {}
        return values

    @property
    def value_variants_list(self):
        return [variant.values for variant in self.value_variants]


class ParameterValueVariant(_Reference):
    __tablename__ = 'parameters_values_variants'

    parameter_id = Column(String(36), ForeignKey('parameters.id'), index=True)

    @property
    def values(self):
        values = super(ParameterValueVariant, self).values
        values['parameter_id'] = self.parameter_id
        if self.parameter:
            values.update({'parameter': self.parameter.values})
        else:
            values['parameter'] = {}
        return values


class TextGeneratingResult(Base):
    __tablename__ = 'text_generating_results'

    id = Column(String(36), primary_key=True, index=True)
    _hash_key = Column(String(150), index=True)
    _parameters = Column(Text)
    result = Column(Text)
    creation_time = Column(DateTime)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not kwargs.get('id'):
            self.id = str(uuid4())
        if not kwargs.get('creation_time'):
            self.creation_time = datetime.now()

    @property
    def parameters(self) -> str:
        return self._parameters

    @parameters.setter
    def parameters(self, value: str):
        self._parameters = value
        self._hash_key = sha256(value.encode()).hexdigest()

    @classmethod
    def find_result(cls, session, parameters: str) -> list:
        results = cls._get_results_by_hash_key(session, parameters)
        # not an optimal algorithm but there is no need for optimization
        if results:
            return cls._find_results_by_parameters(parameters, results)
        else:
            all_data = session.query(cls).all()
            return cls._find_results_by_parameters(parameters, all_data)

    @classmethod
    def _get_results_by_hash_key(cls, session, parameters: str) -> list:
        hash_key = sha256(parameters.encode()).hexdigest()
        return session.query(cls).filter_by(_hash_key=hash_key).all()

    @staticmethod
    def _find_results_by_parameters(parameters: str, results: list) -> list:
        parameters_dict = loads(parameters)
        return [result for result in results if loads(result.parameters) == parameters_dict]



