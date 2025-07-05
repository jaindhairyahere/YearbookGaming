class MessageQueue:
    DEFAULT_BROKER = "rabbitmq"
    DEFAULT_SCHEME = "amqp"
    DEFAULT_QUEUE_NAME = 'text_1'
    DEFAULT_EXCHANGE_NAME = 'message'
    DEFAULT_EXCHANGE_TYPE = "fanout"
    DEFAULT_RECONNECTION_THRESHOLD = 100
    DEFAULT_ROUTING_KEY = "content.tickets.json"
        
class POSTGRES:
    DEFAULT_DB = "YearbookGamingdb"
    DEFAULT_USER = "YearbookGamingadmin"
    DEFAULT_PASSWORD = "paassword"
    DEFAULT_HOST = "db"
    DEFAULT_PORT = 5432

class Cache:
    DEFAULT_BROKER = "REDIS"
    DEFAULT_USER = "default"
    DEFAULT_PASSWORD = ""
    DEFAULT_SCHEME = "redis"
    DEFAULT_PORT = 6379
    DEFAULT_HOST = "cache"
    DEFAULT_SUFFIX = ""