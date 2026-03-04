import paho.mqtt.client as mqtt

BROKER = "localhost"
PORT = 1883
TOPIC = "tima/factors"


def on_connect(client, userdata, flags, rc):
    print(f"Connected with result code {rc}")
    client.subscribe(TOPIC)
    print(f"Subscribed to topic: {TOPIC}")


def on_message(client, userdata, msg):
    print(f"Message received on {msg.topic}: {msg.payload.decode()}")


def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(BROKER, PORT, 60)
    print("Listening for messages. Press Ctrl+C to exit.")
    try:
        client.loop_forever()
    except KeyboardInterrupt:
        print("Exiting...")


if __name__ == "__main__":
    main()
