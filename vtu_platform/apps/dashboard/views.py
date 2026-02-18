from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render


@staff_member_required
def operations_console(request):
    return render(request, 'dashboard/console.html')
