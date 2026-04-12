from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='assistant-index'),
    path('api/chat/', views.chat_api, name='chat-api'),
    path('api/tts/', views.tts_api, name='tts-api'),
]
