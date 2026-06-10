from django.views.generic import TemplateView


class RoutePlannerPageView(TemplateView):
    template_name = "routes/index.html"
