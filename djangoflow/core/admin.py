from django.contrib import admin

from core.models import Organizer, Event, Sponsor, Category, Income, Profile, Invoice

admin.site.register(Profile)
admin.site.register(Organizer)
admin.site.register(Event)
admin.site.register(Sponsor)
admin.site.register(Category)
admin.site.register(Income)
admin.site.register(Invoice)
