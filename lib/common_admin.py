from django.contrib import admin


class BaseAdmin(admin.ModelAdmin):
    list_display = ['created_time']
    extra_list_display = []

    def get_list_display(self, request):
        return self.extra_list_display + self.list_display
