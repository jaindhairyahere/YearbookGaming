from rest_framework import serializers
from utils.serializers import SerializerMethodField
from communication_app.models import Channel, Subscription, GameRequest
from app_admin.serializers import YearbookUserSerializer

class ChannelSerializer(serializers.ModelSerializer):
    """Serializer Class for Channel Model"""
    class Meta:
        model = Channel
        fields = ('__all__')
        
class SubscriptionSerializer(serializers.ModelSerializer):
    """Serializer Class for Subscription Model"""
    user = YearbookUserSerializer()
    channel = ChannelSerializer()
    class Meta:
        model = Subscription
        field = ('user', 'channel')
        

class GameRequestSerializer(serializers.ModelSerializer):
    sender = YearbookUserSerializer()
    receiver = YearbookUserSerializer()
    channel = ChannelSerializer()
    class Meta:
        model = GameRequest
        fields = ("__all__")
        depth = 1
    