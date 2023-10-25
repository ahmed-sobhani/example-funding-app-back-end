from django.contrib import admin

from finance.models import Gateway, Payment


class PaymentAdmin(admin.ModelAdmin):
    list_display = [
        "invoice_number", "user", "created_time", "modified_time",
        "amount", "gateway", "is_paid"
    ]
    list_filter = ("is_paid", "gateway")
    list_editable = ("is_paid", )
    search_fields = ["user__username", "user__phone_number", "user__email", "invoice_number"]
    date_hierarchy = "created_time"
    ordering = ('-created_time',)
    # readonly_fields = ('is_paid',)


admin.site.register(Payment, PaymentAdmin)
admin.site.register(Gateway)
