from unittest import TestCase

from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from django_serfilter import FilterMixin


class TestMethodLookup(TestCase):
    def test_fallback_to_unnamed(self):
        class PersonFilterParams(FilterMixin, serializers.Serializer):
            name = serializers.CharField(required=False)
            age = serializers.IntegerField(required=False)
            person_count = serializers.IntegerField(required=False)

            class Meta:
                filter_named = {
                    'persons': ('name', 'age'),
                    'groups': ('age', 'person_count')
                }

            def filter_persons_by_name(self, persons, name):
                return filter(lambda o: name in o['name'], persons)

            def filter_by_age(self, persons, age):
                return filter(lambda o: o['age'] >= age, persons)

            def filter_groups_by_age(self, groups, age):
                return filter(lambda o: o['avg_age'] >= age, groups)

            def filter_groups_by_person_count(self, groups, count):
                return filter(lambda o: o['p_count'] >= count, groups)

        serializer = PersonFilterParams(
            data={'name': 'test', 'age': 11, 'person_count': 5})
        li = serializer.filter_persons([
            {'name': 'tester', 'age': 10},
            {'name': 'kelly', 'age': 12},
            {'name': 'estester', 'age': 11},
        ])
        assert list(li) == [{'name': 'estester', 'age': 11}]

        li = serializer.filter_groups([
            {'name': 'frogsies', 'avg_age': 11.1, 'p_count': 3},
            {'name': 'berrybears', 'avg_age': 12.2, 'p_count': 5},
            {'name': 'bunnies', 'avg_age': 8.6, 'p_count': 12},
        ])
        assert list(li) == [{'name': 'berrybears', 'avg_age': 12.2, 'p_count': 5}]

    def test_method_missing(self):
        class Serializer(FilterMixin, serializers.Serializer):
            q = serializers.CharField(required=False)

        serializer = Serializer(data={'q': 1})
        with self.assertRaises(AttributeError) as ctx:
            serializer.filter([])

        assert ctx.exception.args[0] == ('Implement one of the following: '
                                         'filter_by_q')

    def test_filter_named_is_present_and_use_plain_filter(self):
        class Serializer(FilterMixin, serializers.Serializer):
            class Meta:
                filter_named = {'list': ('q',)}

            q = serializers.CharField(required=False)

        serializer = Serializer(data={'q': 1})
        with self.assertRaises(AttributeError) as ctx:
            serializer.filter([])

        assert (ctx.exception.args[0] ==
                'Implement one of the following: filter_by_q')


class TestSerializerValidation(TestCase):
    def test_serializer_not_valid(self):
        class Serializer(FilterMixin, serializers.Serializer):
            q = serializers.CharField()

        serializer = Serializer(data={'Q': 1})
        with self.assertRaises(ValidationError) as ctx:
            serializer.filter([])

        assert ctx.exception.args[0] == {'q': ['This field is required.']}

    def test_fail_validation_error_silently(self):
        class Serializer(FilterMixin, serializers.Serializer):
            q = serializers.CharField()

        serializer = Serializer(data={'Q': 1})
        result = serializer.filter([], raise_exception=False)
        assert result == []


class TestFilterTogether(TestCase):
    def test_filter_together_with_filter_by(self):
        class Serializer(FilterMixin, serializers.Serializer):
            city = serializers.CharField(required=False)
            distance = serializers.IntegerField(required=False)
            postal_code = serializers.IntegerField(required=False)

            class Meta:
                filter_by = {
                    'filter_together': {
                        'nearby': ('city', 'distance'),
                    }
                }

            def filter_by_nearby(self, li, city, distance):
                if city == 'paris':
                    li.remove('sidney')
                return li

        serializer = Serializer(data={
            'city': 'paris', 'distance': 1000, 'postal_code': 84843})
        result = serializer.filter(['marseille', 'sidney'])
        assert result == ['marseille']

    def test_filter_together_with_named_filter(self):
        class Serializer(FilterMixin, serializers.Serializer):
            city = serializers.CharField(required=False)
            distance = serializers.IntegerField(required=False)
            postal_code = serializers.IntegerField(required=False)

            class Meta:
                filter_named = {
                    'cities': {
                        'filter_together': {
                            'nearby': ('city', 'distance'),
                        }
                    }
                }

            def filter_cities_by_nearby(self, li, city, distance):
                if city == 'paris':
                    li.remove('sidney')
                return li

        serializer = Serializer(data={
            'city': 'paris', 'distance': 1000, 'postal_code': 84843})
        result = serializer.filter_cities(['marseille', 'sidney'])
        assert result == ['marseille']
