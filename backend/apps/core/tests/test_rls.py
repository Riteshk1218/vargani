"""The database refuses cross-organization access even when application code forgets its filter."""

import pytest
from django.db import DatabaseError, connection, transaction

from apps.core import rls
from apps.people.models import Person

pytestmark = pytest.mark.django_db


@pytest.fixture
def two_orgs(make_org):
    a, b = make_org("A"), make_org("B")
    Person.objects.create(organization=a, full_name="Person of A")
    Person.objects.create(organization=b, full_name="Person of B")
    yield a, b
    rls.deactivate()


def test_unfiltered_query_only_sees_the_active_organization(two_orgs):
    a, b = two_orgs
    rls.activate(a.pk)
    # Deliberately no organization filter: the database applies it.
    assert list(Person.objects.values_list("full_name", flat=True)) == ["Person of A"]
    assert not Person.objects.filter(organization=b).exists()
    rls.deactivate()
    assert Person.objects.count() == 2


def test_writing_into_another_organization_is_refused(two_orgs):
    a, b = two_orgs
    rls.activate(a.pk)
    with pytest.raises(DatabaseError), transaction.atomic():
        Person.objects.create(organization=b, full_name="Smuggled")
    # Updates of other organizations' rows silently match nothing.
    assert Person.objects.filter(full_name="Person of B").update(full_name="Hacked") == 0
    rls.deactivate()
    assert Person.objects.filter(full_name="Person of B").exists()


def test_request_sets_and_clears_the_organization(two_orgs, client_for):
    a, _b = two_orgs
    response = client_for(a.admin_user, a).get("/api/v1/people/")
    assert response.status_code == 200
    with connection.cursor() as cursor:
        cursor.execute("SELECT current_setting('app.org_id', true)")
        assert cursor.fetchone()[0] in ("", None)  # cleared after the request


def test_every_tenant_table_has_row_level_security():
    with connection.cursor() as cursor:
        cursor.execute(
            """
            SELECT c.relname, c.relrowsecurity, c.relforcerowsecurity
            FROM pg_class c JOIN information_schema.columns col
              ON col.table_name = c.relname AND col.column_name = 'organization_id' AND col.table_schema = 'public'
            WHERE c.relkind = 'r'
            """
        )
        rows = cursor.fetchall()
    missing = sorted(name for name, enabled, forced in rows if not (enabled and forced))
    assert missing == [], f"add these tables to core/rls.py TENANT_TABLES and a migration: {missing}"
    assert {name for name, *_ in rows} == set(rls.TENANT_TABLES)
