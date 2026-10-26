from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.html import format_html
from drf_spectacular.utils import extend_schema, inline_serializer
from rest_framework import serializers, status
from rest_framework.response import Response
from rest_framework.views import APIView

from fusion_auth.permissions import HasModuleGrant, HasPermission
from modules.elm.api.serializers import (
    ActionRemarksSerializer,
    EmployeeLeaveBalanceSerializer,
    HolidayCalendarPublishSerializer,
    HolidayCalendarSerializer,
    LeaveApplicationCreateSerializer,
    LeaveApplicationSerializer,
    OfflineLeaveRecordSerializer,
    ResumptionSubmitSerializer,
    SanctionDecisionSerializer,
    SubstituteResponseSerializer,
    UnitHeadRecommendationSerializer,
)
from modules.elm.selectors.applications import (
    pending_approvals,
    pending_substitute_requests,
    visible_applications,
)
from modules.elm.selectors.balances import get_user_balances
from modules.elm.selectors.calendars import get_published_holidays
from modules.elm.services.admin import publish_holiday, record_offline_leave
from modules.elm.services.applications import (
    approve_cancellation,
    recommend_unit_head,
    request_cancellation,
    request_extension,
    respond_substitute,
    review_resumption,
    sanction_application,
    submit_application,
    submit_resumption,
    withdraw_application,
)


class MyLeavesView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    @extend_schema(
        responses=inline_serializer(
            name="MyLeavesResponse",
            fields={
                "balances": EmployeeLeaveBalanceSerializer(many=True),
                "applications": LeaveApplicationSerializer(many=True),
            },
        )
    )
    def get(self, request):
        balances = get_user_balances(
            request.principal.user_id,
            timezone.localdate().year,
            request.principal.kind,
        )
        apps = visible_applications(request.principal).filter(user_id=request.principal.user_id)

        return Response(
            {
                "balances": EmployeeLeaveBalanceSerializer(balances, many=True).data,
                "applications": LeaveApplicationSerializer(apps, many=True).data,
            }
        )


class ApplyLeaveView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.apply"),
    ]

    @extend_schema(
        request=LeaveApplicationCreateSerializer, responses={201: LeaveApplicationSerializer}
    )
    def post(self, request):
        ser = LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = submit_application(request.principal, ser.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ApplicationDetailView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer)
    def get(self, request, pk: int):
        app = get_object_or_404(visible_applications(request.principal), pk=pk)
        return Response(LeaveApplicationSerializer(app).data)


class ApplicationWithdrawView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.withdraw"),
    ]

    @extend_schema(request=None, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        app = withdraw_application(request.principal, pk)
        return Response(LeaveApplicationSerializer(app).data)


class SubstituteRequestsView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.substitute.respond"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        apps = pending_substitute_requests(request.principal)
        return Response(LeaveApplicationSerializer(apps, many=True).data)


class SubstituteRespondView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.substitute.respond"),
    ]

    @extend_schema(request=SubstituteResponseSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = SubstituteResponseSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = respond_substitute(
            request.principal,
            pk,
            action=ser.validated_data["action"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class PendingApprovalsView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    @extend_schema(responses=LeaveApplicationSerializer(many=True))
    def get(self, request):
        apps = pending_approvals(request.principal)
        return Response(LeaveApplicationSerializer(apps, many=True).data)


class UnitHeadRecommendView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.review"),
    ]

    @extend_schema(request=UnitHeadRecommendationSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = UnitHeadRecommendationSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = recommend_unit_head(
            request.principal,
            pk,
            recommendation=ser.validated_data["recommendation"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class SanctionDecisionView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    @extend_schema(request=SanctionDecisionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = sanction_application(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class CancellationRequestView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.cancel"),
    ]

    @extend_schema(request=ActionRemarksSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = ActionRemarksSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = request_cancellation(
            request.principal,
            pk,
            reason=ser.validated_data.get("remarks", "Cancellation requested"),
        )
        return Response(LeaveApplicationSerializer(app).data)


class CancellationDecisionView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    @extend_schema(request=SanctionDecisionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = approve_cancellation(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class ExtensionRequestView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.extend"),
    ]

    @extend_schema(
        request=LeaveApplicationCreateSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def post(self, request, pk: int):
        ser = LeaveApplicationCreateSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = request_extension(request.principal, pk, ser.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class ResumptionSubmitView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.resume"),
    ]

    @extend_schema(request=ResumptionSubmitSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = ResumptionSubmitSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = submit_resumption(
            request.principal,
            pk,
            actual_date=ser.validated_data["actual_date"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class ResumptionReviewView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.approve"),
    ]

    @extend_schema(request=SanctionDecisionSerializer, responses=LeaveApplicationSerializer)
    def post(self, request, pk: int):
        ser = SanctionDecisionSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = review_resumption(
            request.principal,
            pk,
            decision=ser.validated_data["decision"],
            remarks=ser.validated_data.get("remarks", ""),
        )
        return Response(LeaveApplicationSerializer(app).data)


class HolidayCalendarView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    @extend_schema(responses=HolidayCalendarSerializer(many=True))
    def get(self, request):
        holidays = get_published_holidays()
        return Response(HolidayCalendarSerializer(holidays, many=True).data)


class OfflineLeaveRecordView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.admin.manage"),
    ]

    @extend_schema(
        request=OfflineLeaveRecordSerializer,
        responses={201: LeaveApplicationSerializer},
    )
    def post(self, request):
        ser = OfflineLeaveRecordSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        app = record_offline_leave(request.principal, ser.validated_data)
        return Response(LeaveApplicationSerializer(app).data, status=status.HTTP_201_CREATED)


class HolidayCalendarPublishView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.admin.manage"),
    ]

    @extend_schema(
        request=HolidayCalendarPublishSerializer,
        responses={201: HolidayCalendarSerializer},
    )
    def post(self, request):
        ser = HolidayCalendarPublishSerializer(data=request.data)
        ser.is_valid(raise_exception=True)
        holiday = publish_holiday(request.principal, ser.validated_data)
        return Response(HolidayCalendarSerializer(holiday).data, status=status.HTTP_201_CREATED)


class PrintableApplicationView(APIView):
    permission_classes = [
        HasModuleGrant("leave_elm"),
        HasPermission("leave_elm.application.view_self"),
    ]

    @extend_schema(
        responses=inline_serializer(
            name="PrintableApplicationResponse",
            fields={
                "printable_html": serializers.CharField(),
                "details": LeaveApplicationSerializer(),
            },
        )
    )
    def get(self, request, pk: int):
        app = get_object_or_404(visible_applications(request.principal), pk=pk)
        return Response(
            {
                "printable_html": format_html(
                    "<h1>Leave Application #{}</h1><p>Applicant: {}</p>"
                    "<p>Category: {}</p><p>Period: {} to {}</p>"
                    "<p>Status: {}</p><p>Reason: {}</p>",
                    app.pk,
                    app.user_id,
                    app.leave_category,
                    app.start_date,
                    app.end_date,
                    app.status,
                    app.reason,
                ),
                "details": LeaveApplicationSerializer(app).data,
            }
        )
