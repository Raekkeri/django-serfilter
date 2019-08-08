import django
from django.contrib.auth import get_user_model
from django.test import override_settings
if django.VERSION[0] < 2:
    from django.conf.urls import url
else:
    from django.urls import re_path as url
from rest_framework import serializers
from rest_framework.generics import ListAPIView
from rest_framework.test import APITestCase, APIRequestFactory

from django_serfilter import SerializerBackend, FilterMixin

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username')


def make_list_view(cls, serializer_class=None):
    _serializer_class = serializer_class or UserSerializer
    class View(ListAPIView):
        queryset = User.objects.order_by('id')
        filter_backends = [SerializerBackend]
        serializer_filter_class = cls
        serializer_class = _serializer_class
    return View.as_view()


@override_settings(ROOT_URLCONF=__name__)
class TestSimpleBackend(APITestCase):
    def setUp(self):
        self.u1 = User.objects.create(username='mary', email='mary@example.com')
        self.u2 = User.objects.create(username='mary-ann',
                                      email='m.a@python.org')
        self.factory = APIRequestFactory()

    def test_simple_serializer_filter(self):
        class Serializer(FilterMixin, serializers.Serializer):
            username = serializers.CharField(required=False)

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

        view = make_list_view(Serializer)
        response = view(self.factory.get('/?username=ann'))
        assert response.data == [{'id': self.u2.id, 'username': 'mary-ann'}]


    def test_serializer_with_filter_by_list(self):
        class Expected(Exception):
            pass

        class Serializer(FilterMixin, serializers.Serializer):
            id = serializers.IntegerField(required=False)
            username = serializers.CharField(required=False)

            class Meta:
                filter_by = ('id',)

            def filter_by_id(self, qs, _id):
                return qs.filter(pk=_id)

            def filter_by_username(self, qs, username):
                raise Expected('Should not get here')

        view = make_list_view(Serializer)
        response = view(self.factory.get(f'/?username=ann&id={self.u1.id}'))
        assert response.data == [{'id': self.u1.id, 'username': 'mary'}]

        # Finally just make sure the exception would be raised:
        Serializer.Meta.filter_by = None
        view = make_list_view(Serializer)
        with self.assertRaises(Expected):
            view(self.factory.get(f'/?username=ann&id={self.u1.id}'))

    def test_serializer_with_filter_named(self):
        class Serializer(FilterMixin, serializers.Serializer):
            id = serializers.IntegerField(required=False)
            username = serializers.CharField(required=False)

            class Meta:
                filter_by = ('id',)
                filter_named = {'users': ('username',)}

            def filter_by_id(self, qs, _id):
                return qs.filter(pk=_id)

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

        view = make_list_view(Serializer)
        response = view(self.factory.get(f'/?username=ann&id={self.u1.id}'))
        assert response.data == [{'id': self.u1.id, 'username': 'mary'}]

        del Serializer.Meta.filter_by
        view = make_list_view(Serializer)
        response = view(self.factory.get(f'/?username=ann&id={self.u1.id}'))
        assert response.data == []

    def test_plain_serializer_class_only_without_filter_by(self):
        class CombinedUserSerializer(FilterMixin, serializers.Serializer):
            id = serializers.IntegerField(required=False)
            username = serializers.CharField(required=False)

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

            def filter_by_id(self, qs, _id):
                return qs.filter(pk=_id)

        view = make_list_view(None, CombinedUserSerializer)
        expected = [{'id': self.u2.id, 'username': 'mary-ann'}]
        response = view(self.factory.get(f'/?id={self.u2.id}'))
        assert response.data == expected
        response = view(self.factory.get(f'/?username=ann'))
        assert response.data == expected
        response = view(self.factory.get(f'/?id={self.u1.id}&username=ann'))
        assert response.data == []

    def test_model_serializer_class_only_without_filter_by(self):
        class CombinedUserSerializer(FilterMixin, UserSerializer):
            class Meta(UserSerializer.Meta):
                filter_by = ('id', 'username')
                # The id field needs read_only=False for it to be
                # present in `validated_data`. Also set all fields
                # "not required" so that serializer validation succeeds.
                extra_kwargs = {
                    'id': {'read_only': False, 'required': False},
                    'username': {'required': False}}

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

            def filter_by_id(self, qs, _id):
                return qs.filter(pk=_id)

        view = make_list_view(None, CombinedUserSerializer)
        expected = [{'id': self.u2.id, 'username': 'mary-ann'}]
        response = view(self.factory.get(f'/?id={self.u2.id}'))
        assert response.data == expected
        response = view(self.factory.get(f'/?username=ann'))
        assert response.data == expected
        response = view(self.factory.get(f'/?id={self.u1.id}&username=ann'))
        assert response.data == []

    def test_serializer_not_instance_of_mixin(self):
        class Serializer(serializers.Serializer):
            id = serializers.IntegerField(required=False)
            username = serializers.CharField(required=False)

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

        view = make_list_view(Serializer)
        response = view(self.factory.get(f'/?username=ann'))
        assert response.data == [{'id': self.u2.id, 'username': 'mary-ann'}]

        view = make_list_view(None, Serializer)
        response = view(self.factory.get(f'/?username=ann'))
        assert response.data == [{'id': self.u2.id, 'username': 'mary-ann'}]

    def test_model_serializer_not_instance_of_mixin(self):
        class Serializer(serializers.ModelSerializer):
            # set `email` as a normal CharField otherwise it requires a valid
            # email format.
            email = serializers.CharField()

            class Meta:
                model = User
                fields = ('id', 'username', 'email')

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

            def filter_by_email(self, qs, email):
                return qs.filter(email__icontains=email)

        view = make_list_view(Serializer)
        response = view(self.factory.get(f'/?username=ann&email=@python.org'))
        assert response.data == [{'id': 2, 'username': 'mary-ann'}]

        view = make_list_view(None, Serializer)
        response = view(self.factory.get(f'/?username=ann&email=@python.org'))
        assert response.data == [{'id': 2, 'username': 'mary-ann',
                                  'email': 'm.a@python.org'}]

    def test_backend_with_named_filters(self):
        class Serializer(serializers.Serializer):
            id = serializers.IntegerField(required=False)
            username = serializers.CharField(required=False)

            class Meta:
                filter_named = {
                    'users': ('username',)
                }

            def filter_by_username(self, qs, username):
                return qs.filter(username__icontains=username)

        view = make_list_view(Serializer)
        response = view(self.factory.get('/?username=ann'))
        assert response.data == [{'id': self.u2.id, 'username': 'mary-ann'}]
