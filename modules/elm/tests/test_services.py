from datetime import date
from decimal import Decimal
from types import SimpleNamespace

import pytest
from django.http import Http404
from rest_framework.test import APIRequestFactory

from modules.elm.api.serializers import (
    LeaveApplicationCreateSerializer,
    OfflineLeaveRecordSerializer,
)
from modules.elm.api.views import ApplicationDetailView, PrintableApplicationView
from modules.elm.models import EmployeeLeaveBalance, HolidayCalendar, LeaveApplication
from modules.elm.selectors.balances import get_user_balances
from modules.elm.services.admin import record_offline_leave
from modules.elm.services.applications import (
    request_extension,
    review_resumption,
    submit_application,
    withdraw_application,
)


def make_principal(user_id=1001, kind="staff", permissions=(), roles=()):
    grants = frozenset(permissions)
    return SimpleNamespace(
        user_id=user_id,
        kind=kind,
        roles=roles,
        has_permission=lambda code: code in grants,
        has_any_permission=lambda *codes: any(code in grants for code in codes),
        has_module=lambda code: code == "leave_elm",
    )


@pytest.mark.django_db
def test_submission_counts_closed_holidays_across_calendar_years():
    HolidayCalendar.objects.create(
        date=date(2027, 1, 1),
        name="New Year",
        is_restricted_holiday=False,
        year=2027,
    )
    principal = make_principal(permissions={"leave_elm.application.apply"})

    application = submit_application(
        principal,
        {
            "leave_category": "CL",
            "start_date": date(2026, 12, 31),
            "end_date": date(2027, 1, 3),
            "reason": "Personal leave",
        },
    )

    assert application.calculated_days == Decimal("1")


@pytest.mark.django_db
def test_extension_is_persisted_and_requires_approved_parent():
    parent = LeaveApplication.objects.create(
        user_id=1001,
        leave_category="EL",
        start_date=date(2026, 10, 1),
        end_date=date(2026, 10, 3),
        calculated_days=Decimal("3"),
        reason="Annual leave",
        status="approved",
    )
    principal = make_principal(
        permissions={"leave_elm.application.extend", "leave_elm.application.apply"}
    )

    extension = request_extension(
        principal,
        parent.pk,
        {
            "start_date": date(2026, 10, 4),
            "end_date": date(2026, 10, 5),
            "reason": "Continue annual leave",
        },
    )

    assert extension.is_extension is True
    assert extension.parent_application_id == parent.pk


@pytest.mark.django_db
def test_offline_record_serializer_parses_json_dates_and_updates_balance(monkeypatch):
    serializer = OfflineLeaveRecordSerializer(
        data={
            "user_id": 1001,
            "leave_category": "CL",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "calculated_days": "1.00",
            "offline_sanction_reference": "OFF-2026-001",
        }
    )
    assert serializer.is_valid(), serializer.errors
    monkeypatch.setattr(
        "modules.elm.services.admin.directory.get_users",
        lambda user_ids: {1001: SimpleNamespace(kind="staff")},
    )

    application = record_offline_leave(
        make_principal(permissions={"leave_elm.admin.manage"}),
        serializer.validated_data,
    )

    balance = EmployeeLeaveBalance.objects.get(
        user_id=1001,
        year=2026,
        leave_category="CL",
    )
    assert application.start_date == date(2026, 10, 5)
    assert application.is_offline_sanctioned is True
    assert balance.availed_days == Decimal("1.00")


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("employee_kind", "earned_leave", "vacation_leave"),
    [("staff", Decimal("30.0"), Decimal("0.0")), ("faculty", Decimal("0.0"), Decimal("60.0"))],
)
def test_default_balances_match_employee_kind(employee_kind, earned_leave, vacation_leave):
    balances = {
        balance.leave_category: balance for balance in get_user_balances(1001, 2026, employee_kind)
    }

    assert balances["EL"].allocated_days == earned_leave
    assert balances["VL"].allocated_days == vacation_leave


def test_leave_serializer_rejects_half_day_for_non_cl():
    serializer = LeaveApplicationCreateSerializer(
        data={
            "leave_category": "EL",
            "start_date": "2026-10-05",
            "end_date": "2026-10-05",
            "half_day_type": "first_half",
            "reason": "Personal leave",
        }
    )

    assert not serializer.is_valid()
    assert "half_day_type" in serializer.errors


@pytest.mark.django_db
def test_printable_application_escapes_user_supplied_html():
    application = LeaveApplication.objects.create(
        user_id=1001,
        leave_category="CL",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
        calculated_days=Decimal("1"),
        reason="<script>alert(1)</script>",
        status="pending_unit_head",
    )
    principal = make_principal(
        permissions={"leave_elm.application.view_self"},
    )
    request = APIRequestFactory().get("/")
    request.principal = principal

    response = PrintableApplicationView.as_view()(request, pk=application.pk)

    assert response.status_code == 200
    assert "<script>" not in response.data["printable_html"]
    assert "&lt;script&gt;" in response.data["printable_html"]


@pytest.mark.django_db
def test_foreign_application_is_not_found_to_owner_only_actions_and_reads():
    application = LeaveApplication.objects.create(
        user_id=2002,
        leave_category="CL",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 5),
        calculated_days=Decimal("1"),
        reason="Private reason",
        status="pending_unit_head",
    )
    principal = make_principal(
        permissions={
            "leave_elm.application.view_self",
            "leave_elm.application.withdraw",
        },
    )

    with pytest.raises(Http404):
        withdraw_application(principal, application.pk)

    request = APIRequestFactory().get("/")
    request.principal = principal
    response = ApplicationDetailView.as_view()(request, pk=application.pk)

    assert response.status_code == 404


@pytest.mark.django_db
def test_rejected_resumption_does_not_complete_leave():
    application = LeaveApplication.objects.create(
        user_id=1001,
        leave_category="EL",
        start_date=date(2026, 10, 5),
        end_date=date(2026, 10, 7),
        calculated_days=Decimal("3"),
        reason="Annual leave",
        status="approved",
        resumption_date=date(2026, 10, 7),
        resumption_status="pending",
    )

    result = review_resumption(
        make_principal(permissions={"leave_elm.application.approve"}),
        application.pk,
        decision="rejected",
    )

    assert result.status == "approved"
    assert result.resumption_status == "rejected"
