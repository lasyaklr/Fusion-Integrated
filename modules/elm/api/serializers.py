from decimal import Decimal

from rest_framework import serializers

from modules.elm.domain.constants import (
    CL,
    HALF_DAY_FIRST,
    HALF_DAY_NONE,
    HALF_DAY_SECOND,
    LEAVE_CATEGORIES,
)
from modules.elm.models import (
    ApplicationTransition,
    EmployeeLeaveBalance,
    HolidayCalendar,
    LeaveApplication,
)


class EmployeeLeaveBalanceSerializer(serializers.ModelSerializer):
    available_days = serializers.DecimalField(max_digits=5, decimal_places=2, read_only=True)

    class Meta:
        model = EmployeeLeaveBalance
        fields = [
            "id",
            "year",
            "leave_category",
            "allocated_days",
            "availed_days",
            "carried_forward",
            "pending_days",
            "available_days",
        ]


class ApplicationTransitionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ApplicationTransition
        fields = [
            "id",
            "from_status",
            "to_status",
            "actor_user_id",
            "remarks",
            "created_at",
        ]


class LeaveApplicationSerializer(serializers.ModelSerializer):
    transitions = ApplicationTransitionSerializer(many=True, read_only=True)

    class Meta:
        model = LeaveApplication
        fields = [
            "id",
            "user_id",
            "leave_category",
            "start_date",
            "end_date",
            "half_day_type",
            "calculated_days",
            "reason",
            "status",
            "substitute_user_id",
            "substitute_status",
            "substitute_remarks",
            "is_station_leave",
            "station_start_date",
            "station_end_date",
            "station_destination",
            "station_contact_address",
            "station_emergency_phone",
            "unit_head_recommendation",
            "unit_head_remarks",
            "final_decision",
            "final_decision_date",
            "final_remarks",
            "cancellation_reason",
            "is_extension",
            "resumption_date",
            "resumption_status",
            "resumption_remarks",
            "is_offline_sanctioned",
            "offline_sanction_reference",
            "transitions",
            "created_at",
            "updated_at",
        ]


class LeaveApplicationCreateSerializer(serializers.Serializer):
    leave_category = serializers.ChoiceField(choices=LEAVE_CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    half_day_type = serializers.ChoiceField(
        choices=[
            (HALF_DAY_NONE, "Full day"),
            (HALF_DAY_FIRST, "First half"),
            (HALF_DAY_SECOND, "Second half"),
        ],
        required=False,
        default=HALF_DAY_NONE,
    )
    reason = serializers.CharField(max_length=2000)
    substitute_user_id = serializers.IntegerField(required=False, allow_null=True, min_value=1)
    is_station_leave = serializers.BooleanField(required=False, default=False)
    station_start_date = serializers.DateField(required=False, allow_null=True)
    station_end_date = serializers.DateField(required=False, allow_null=True)
    station_destination = serializers.CharField(required=False, allow_blank=True, default="")
    station_contact_address = serializers.CharField(required=False, allow_blank=True, default="")
    station_emergency_phone = serializers.CharField(required=False, allow_blank=True, default="")

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )

        half_day_type = attrs["half_day_type"]
        if half_day_type and attrs["leave_category"] != CL:
            raise serializers.ValidationError(
                {"half_day_type": "Half-day leave is only available for Casual Leave."}
            )
        if half_day_type and attrs["start_date"] != attrs["end_date"]:
            raise serializers.ValidationError(
                {"half_day_type": "Half-day leave must be requested for a single date."}
            )

        if attrs["is_station_leave"]:
            station_start = attrs.get("station_start_date")
            station_end = attrs.get("station_end_date")
            if station_start is None or station_end is None:
                raise serializers.ValidationError(
                    {"station_start_date": "Station leave requires a start and end date."}
                )
            if station_start > station_end:
                raise serializers.ValidationError(
                    {"station_end_date": "End date must be on or after start date."}
                )
            if station_start < attrs["start_date"] or station_end > attrs["end_date"]:
                raise serializers.ValidationError(
                    {"station_start_date": "Station leave dates must fall within the leave period."}
                )
        return attrs


class OfflineLeaveRecordSerializer(serializers.Serializer):
    user_id = serializers.IntegerField(min_value=1)
    leave_category = serializers.ChoiceField(choices=LEAVE_CATEGORIES)
    start_date = serializers.DateField()
    end_date = serializers.DateField()
    calculated_days = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.01"),
    )
    reason = serializers.CharField(required=False, allow_blank=True, default="")
    offline_sanction_reference = serializers.CharField(max_length=128)

    def validate(self, attrs):
        if attrs["start_date"] > attrs["end_date"]:
            raise serializers.ValidationError(
                {"end_date": "End date must be on or after start date."}
            )
        return attrs


class HolidayCalendarPublishSerializer(serializers.Serializer):
    date = serializers.DateField()
    name = serializers.CharField(max_length=128)
    is_restricted_holiday = serializers.BooleanField(required=False, default=False)


class ActionRemarksSerializer(serializers.Serializer):
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SubstituteResponseSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=["accept", "decline"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class UnitHeadRecommendationSerializer(serializers.Serializer):
    recommendation = serializers.CharField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class SanctionDecisionSerializer(serializers.Serializer):
    decision = serializers.ChoiceField(choices=["approved", "rejected"])
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class ResumptionSubmitSerializer(serializers.Serializer):
    actual_date = serializers.DateField()
    remarks = serializers.CharField(required=False, allow_blank=True, default="")


class HolidayCalendarSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayCalendar
        fields = ["id", "date", "name", "is_restricted_holiday", "is_published", "year"]
