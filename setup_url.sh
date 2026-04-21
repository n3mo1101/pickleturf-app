for app in accounts courts bookings openplay inventory dashboard announcements transactions; do
  echo "from django.urls import path
app_name = '$app'
urlpatterns = []" > $app/urls.py
done