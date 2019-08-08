from functools import partial
from itertools import chain

from django.utils.functional import cached_property
from rest_framework import serializers
from rest_framework.filters import BaseFilterBackend


class SerializerBackend(BaseFilterBackend):
    def filter_queryset(self, request=None, queryset=None, view=None):
        serializer_class = getattr(view, 'serializer_filter_class', None)
        if not serializer_class:
            serializer_class = view.serializer_class

        if not issubclass(serializer_class, FilterMixin):
            namespaces = {}
            if getattr(serializer_class, 'Meta', None):
                namespaces['Meta'] = serializer_class.Meta
            serializer_class = type(
                'DefaultSerializerFilter', (FilterMixin, serializer_class),
                namespaces)

        serializer = serializer_class(data=request.GET)
        return serializer.filter(queryset)


class FilterMixin(object):
    class Meta:
        filter_by = None
        filter_named = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self._filter_by:
            self._configure_filter_by(None, self._filter_by)

        filter_named = self._filter_named
        if filter_named:
            assert isinstance(filter_named, dict), (
                '`Meta.filter_named` must be a dict')
            for name, filter_by in filter_named.items():
                self._configure_filter_by(name, filter_by)

    def _configure_filter_by(self, name, filter_by):
        if isinstance(filter_by, dict):
            fields = filter_by.get('fields', tuple())
            filter_together = filter_by.get('filter_together')
        elif isinstance(filter_by, (list, tuple)):
            fields = filter_by
            filter_together = None
        else:
            raise NotImplementedError('`filter_by` must a type of either '
                                      '`tuple`, `list`, or `dict`')

        f = partial(self.filter, name=name, fields=fields,
                    filter_together=filter_together)
        filter_func_name = 'filter_{}'.format(name) if name else 'filter'
        setattr(self, filter_func_name, f)

    def filter(self, qs, name=None, fields=None, filter_together=None,
               raise_exception=True):
        #if isinstance(self._filter_by, dict) and not name:
            #raise NotImplementedError(
                #'Cannot call `filter` directly if `Meta.filter_fields` is '
                #'a dict')
        filter_together = filter_together or {}

        if not self.is_valid(raise_exception=raise_exception):
            return qs

        g = self.validated_data.items()
        if fields is not None:
            g = ((k, v) for k, v in self.validated_data.items() if k in fields)

        name_list = ['filter_by_']
        if name:
            name_list.insert(0, 'filter_{}_by_'.format(name))

        for k, v in g:
            for name in name_list:
                func = getattr(self, name + k, None)
                if func:
                    qs = func(qs, v)
                    break
            else:
                if not k in chain.from_iterable(filter_together.values()):
                    funcs = ', '.join([(n + k) for n in name_list])
                    raise AttributeError(
                        'Implement one of the following: ' + funcs)

        for k, fields in filter_together.items():
            func_name = name_list[0] + k
            try:
                func = getattr(self, func_name)
            except AttributeError:
                raise AttributeError(f'Implement {func_name}')
            kwargs = {field: self.validated_data[field] for field in fields}
            qs = func(qs, **kwargs)

        return qs

    @cached_property
    def _filter_by(self):
        meta = getattr(self, 'Meta', None)
        if meta:
            return getattr(meta, 'filter_by', None)

    @cached_property
    def _filter_named(self):
        meta = getattr(self, 'Meta', None)
        if meta:
            return getattr(meta, 'filter_named', None)
