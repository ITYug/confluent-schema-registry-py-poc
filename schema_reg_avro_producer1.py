from uuid import uuid4

from confluent_kafka import SerializingProducer
from confluent_kafka.serialization import StringSerializer
from confluent_kafka.schema_registry import SchemaRegistryClient
from confluent_kafka.schema_registry.avro import AvroSerializer


def delivery_report(err, msg):
    """
    Reports the failure or success of a message delivery.
    Args:
        err (KafkaError): The error that occurred on None on success.
        msg (Message): The message that was produced or failed.
    Note:
        In the delivery report callback the Message.key() and Message.value()
        will be the binary format as encoded by any configured Serializers and
        not the same object that was passed to produce().
        If you wish to pass the original object(s) for key and value to delivery
        report callback we recommend a bound callback or lambda where you pass
        the objects along.
    """
    if err is not None:
        print("Delivery failed for User record {}: {}".format(msg.key(), err))
        return
    print('User record {} successfully produced to {} [{}] at offset {}'.format(
        msg.key(), msg.topic(), msg.partition(), msg.offset()))


class User(object):
    """
    User record
    Args:
        name (str): User's name
        favorite_number (int): User's favorite number
        favorite_color (str): User's favorite color
        address(str): User's address; confidential
    """

    def __init__(self, name, address, favorite_number, favorite_color):
        self.name = name
        self.favorite_number = favorite_number
        self.favorite_color = favorite_color
        # address should not be serialized, see user_to_dict()
        self._address = address


def user_to_dict(user, ctx):
    """
    Returns a dict representation of a User instance for serialization.
    Args:
        user (User): User instance.
        ctx (SerializationContext): Metadata pertaining to the serialization
            operation.
    Returns:
        dict: Dict populated with user attributes to be serialized.
    """
    # User._address must not be serialized; omit from dict
    return dict(name=user.name,
                favorite_number=user.favorite_number,
                favorite_color=user.favorite_color)


topic = "schema1"
schema_str = """
{
    "namespace": "confluent.io.examples.serialization.avro",
    "name": "User",
    "type": "record",
    "fields": [
        {"name": "name", "type": "string"},
        {"name": "favorite_number", "type": "int"},
        {"name": "favorite_color", "type": "string"}
    ]
}
"""
schema_registry_conf = {'url': "http://localhost:8081"}
schema_registry_client = SchemaRegistryClient(schema_registry_conf)

avro_serializer = AvroSerializer(schema_str,
                                 schema_registry_client,
                                 user_to_dict)

producer_conf = {'bootstrap.servers': "localhost:9092",
                 'key.serializer': StringSerializer('utf_8'),
                 'value.serializer': avro_serializer}

producer = SerializingProducer(producer_conf)

print("Producing user records to topic {}. ^C to exit.".format(topic))
while True:
    # Serve on_delivery callbacks from previous calls to produce()
    producer.poll(0.0)
    try:
        user = User(name="user1",
                    address="city1",
                    favorite_color="Red",
                    favorite_number=10)
        producer.produce(topic=topic, key=str(uuid4()), value=user,
                         on_delivery=delivery_report)
    except KeyboardInterrupt:
        break
    except ValueError:
        print("Invalid input, discarding record...")
        continue

print("\nFlushing records...")
producer.flush()
