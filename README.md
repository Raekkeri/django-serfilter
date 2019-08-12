# django-serfilter

django-serfilter is an easy to use, highly customizable filter backend for Django Rest
Framework's API views. The filtering of this backend is based on serializer and its
fields: each field represents a query parameter, and filtering by that parameter
can be achieved by simply implementing a `filter_by_FOO` method for the serializer
class.

## Examples

### 1. Plain serializer

The simplest use case is to just create a serializer class, define some fields
and implement the `filter_by_...` methods:

```python
from rest_framework import serializers

class UserFilter(serializers.Serializer):
    first_name = serializers.CharField(required=False)
    last_name = serializers.CharField(required=False)

    def filter_by_first_name(self, queryset, name):
        return queryset.filter(first_name__icontains=name)

    def filter_by_last_name(self, queryset, name):
        return queryset.filter(last_name__icontains=name)
```

As is apparent, `UserFilter` will do the actual filtering. Note how
each field is initialized with `required=False` -- this is required simply
to make sure the GET parameters can be omitted from the request, as they
usually should be allowed to be missing. By removing the `required=False`,
the parameter is always required (unless the field is also intialized with
`default=something`).

To complete the example,
lets define an API view and configure it to use the filtering backend,
`SerializerBackend`, and the `UserFilter`:

```python
from django.contrib.auth.models import User
from django_serfilter import SerializerBackend
from rest_framework.generics import ListAPIView


# UserSerializer will be used just to define the output fields of our API
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'first_name', 'last_name', 'email')


# Finally, we can just create a view class and configure it to use
# UserFilter for filtering
class UserView(ListAPIView):
    queryset = User.objects
    filter_backends = [SerializerBackend]
    serializer_filter_class = UserFilter
    serializer_class = UserSerializer
```

After the `UserView` is referenced in Django's URLconf (e.g. at `/users/`),
we can filter the results with `first_name` and `last_name` GET parameters:

```
curl "127.0.0.1:8000/users?first_name=ann&last_name=johnson"
```
