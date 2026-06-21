from rest_framework import serializers, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.api.permissions import HasEntityRole
from apps.api.serializers.budgets import (
    BudgetProgressSerializer,
    BudgetSerializer,
    ProjectProgressSerializer,
    ProjectSerializer,
    SavingsGoalProgressSerializer,
    SavingsGoalSerializer,
    SuperannuationProjectionRequestSerializer,
    SuperannuationProjectionResponseSerializer,
)
from apps.budgets.exceptions import InvalidProjectionParametersError
from apps.budgets.models import Budget, Project, SavingsGoal
from apps.budgets.services import (
    compute_budget_progress,
    compute_project_actuals,
    compute_savings_goal_progress,
    project_superannuation_balance,
)
from apps.entities.models import EntityRole


class BudgetViewSet(viewsets.ModelViewSet):
    serializer_class = BudgetSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Budget.objects.accessible_by(self.request.user).select_related("entity", "account")
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        budget = self.get_object()
        result = compute_budget_progress(budget)
        return Response(
            BudgetProgressSerializer(
                {
                    "budgeted_amount": result.budgeted_amount,
                    "actual_amount": result.actual_amount,
                    "remaining_amount": result.remaining_amount,
                    "percent_used": result.percent_used,
                }
            ).data
        )


class SavingsGoalViewSet(viewsets.ModelViewSet):
    serializer_class = SavingsGoalSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = SavingsGoal.objects.accessible_by(self.request.user).select_related(
            "entity", "linked_account"
        )
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        goal = self.get_object()
        result = compute_savings_goal_progress(goal)
        return Response(
            SavingsGoalProgressSerializer(
                {
                    "current_balance": result.current_balance,
                    "target_amount": result.target_amount,
                    "remaining_amount": result.remaining_amount,
                    "percent_complete": result.percent_complete,
                    "days_remaining": result.days_remaining,
                }
            ).data
        )


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Project.objects.accessible_by(self.request.user).select_related("entity")
        entity_id = self.request.query_params.get("entity")
        if entity_id:
            qs = qs.filter(entity_id=entity_id)
        return qs

    def get_permissions(self):
        if self.action in ("create", "update", "partial_update", "destroy"):
            return [HasEntityRole(EntityRole.EDITOR)()]
        return [HasEntityRole(EntityRole.VIEWER)()]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        project = self.get_object()
        result = compute_project_actuals(project)
        return Response(
            ProjectProgressSerializer(
                {
                    "actual_to_date": result.actual_to_date,
                    "budget_amount": result.budget_amount,
                    "remaining_amount": result.remaining_amount,
                    "percent_used": result.percent_used,
                }
            ).data
        )


class SuperannuationProjectionView(APIView):
    """Stateless calculator -- no model, no persistence (see step 7 design
    notes). Requires only authentication, since it touches no
    entity-scoped data directly; the frontend sources current_balance
    from a real account balance before calling this."""

    def post(self, request):
        serializer = SuperannuationProjectionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            projected = project_superannuation_balance(
                current_balance=data["current_balance"],
                target_date=data["target_date"],
                annual_contribution=data["annual_contribution"],
                annual_growth_rate=data["annual_growth_rate"],
            )
        except InvalidProjectionParametersError as exc:
            raise serializers.ValidationError({"non_field_errors": [str(exc)]}) from exc
        return Response(
            SuperannuationProjectionResponseSerializer({"projected_balance": projected}).data
        )
